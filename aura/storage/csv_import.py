"""
Migration utility to import legacy data/system_logs.csv into SQLite.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import uuid
import pandas as pd

from aura.models.types import SecurityEvent, TelemetrySnapshot
from aura.storage.sqlite import StorageEngine

logger = logging.getLogger(__name__)


def import_legacy_csv_to_sqlite(
    csv_path: Path | str,
    storage: StorageEngine,
) -> int:
    """Read historical data/system_logs.csv and import records into SQLite without duplication."""
    path = Path(csv_path)
    if not path.exists() or path.stat().st_size == 0:
        logger.info("Legacy CSV not found or empty: %s", path)
        return 0

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        logger.warning("Could not parse legacy CSV %s: %exc", path, exc)
        return 0

    if df.empty:
        return 0

    count = 0
    with storage.transaction() as cur:
        for _, row in df.iterrows():
            ts_raw = str(row.get("Timestamp", "")).strip()
            if not ts_raw or ts_raw == "nan":
                continue

            # Format timestamp to ISO 8601
            try:
                dt = pd.to_datetime(ts_raw).to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                iso_ts = dt.isoformat()
            except Exception:
                iso_ts = ts_raw

            severity = str(row.get("Severity", row.get("Risk", "INFO"))).upper()
            if severity not in {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                severity = "INFO"

            try:
                risk_score = float(row.get("Risk_Score", 0.0))
            except (ValueError, TypeError):
                risk_score = 0.0

            event_id = f"legacy-{uuid.uuid4().hex[:12]}"
            summary = f"Historical scan imported from {path.name}"

            cur.execute(
                """
                INSERT OR IGNORE INTO security_events (
                    event_id, timestamp, event_type, severity, risk_score, source,
                    summary, evidence_json, confidence, affected_resource,
                    correlation_id, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event_id,
                    iso_ts,
                    "HISTORICAL_SCAN",
                    severity,
                    risk_score,
                    "LegacyCSVImport",
                    summary,
                    None,
                    None,
                    "",
                    "",
                    1,
                ),
            )

            # Telemetry row
            try:
                cpu = float(row.get("CPU", 0.0))
                mem = float(row.get("Memory", 0.0))
                disk = float(row.get("Disk", 0.0))
                net_up = float(row.get("Net", row.get("Net_Up", 0.0)))
                net_down = float(row.get("Net_Down", 0.0))
                procs = int(row.get("Process_Count", 0))
                rem_conns = int(row.get("Remote_Connections", 0))
            except Exception:
                cpu = mem = disk = net_up = net_down = 0.0
                procs = rem_conns = 0

            cur.execute(
                """
                INSERT INTO telemetry (
                    timestamp, cpu_percent, memory_percent, disk_percent, disk_io_kbps,
                    net_up_kbps, net_down_kbps, process_count, established_conns,
                    listening_conns, remote_conns, camera_status, microphone_status,
                    sensor_health_json, raw_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    iso_ts,
                    cpu,
                    mem,
                    disk,
                    0.0,
                    net_up,
                    net_down,
                    procs,
                    0,
                    0,
                    rem_conns,
                    "UNKNOWN",
                    "UNKNOWN",
                    None,
                    None,
                ),
            )
            count += 1

    logger.info("Successfully imported %d legacy CSV records into SQLite", count)
    return count
