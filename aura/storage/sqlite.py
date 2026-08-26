"""
Production SQLite storage engine for AURA.

Enforces WAL mode, thread safety, parameterized queries, and bounded retention.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import sqlite3
import threading
from typing import Any, Generator

from aura.models.types import SecurityEvent, TelemetrySnapshot
from aura.storage.schema import CURRENT_SCHEMA_VERSION, MIGRATIONS

logger = logging.getLogger(__name__)


class StorageEngine:
    """Thread-safe SQLite storage engine with WAL mode and schema migrations."""

    def __init__(
        self,
        db_path: Path | str,
        busy_timeout: float = 5.0,
        wal_mode: bool = True,
    ) -> None:
        self.db_path = Path(db_path)
        self.busy_timeout = busy_timeout
        self.wal_mode = wal_mode
        self._lock = threading.RLock()
        self._local = threading.local()
        self._all_connections: set[sqlite3.Connection] = set()

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

    def _get_connection(self) -> sqlite3.Connection:
        """Return a thread-local SQLite connection configured for AURA."""
        conn = getattr(self._local, "connection", None)
        if conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=self.busy_timeout,
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode; explicit BEGIN for transactions
            )
            conn.row_factory = sqlite3.Row
            if self.wal_mode:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute(f"PRAGMA busy_timeout={int(self.busy_timeout * 1000)};")
            conn.execute("PRAGMA foreign_keys=ON;")
            self._local.connection = conn
            with self._lock:
                self._all_connections.add(conn)
        return conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager providing an ACID transaction with automatic rollback on error."""
        conn = self._get_connection()
        with self._lock:
            conn.execute("BEGIN IMMEDIATE;")
            cursor = conn.cursor()
            try:
                yield cursor
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                cursor.close()

    def migrate(self) -> None:
        """Apply all unapplied schema migrations."""
        with self._lock:
            conn = self._get_connection()
            # Ensure schema_migrations table exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL,
                    description TEXT NOT NULL
                );
            """)

            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version ASC;")
            applied_versions = {row["version"] for row in cursor.fetchall()}
            cursor.close()

            for migration in MIGRATIONS:
                if migration.version not in applied_versions:
                    logger.info("Applying schema migration v%d: %s", migration.version, migration.description)
                    conn.executescript(migration.up_sql)
                    conn.execute(
                        "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?, ?, ?);",
                        (
                            migration.version,
                            datetime.now(timezone.utc).isoformat(),
                            migration.description,
                        ),
                    )

    def record_telemetry(self, snapshot: TelemetrySnapshot) -> int:
        """Persist a single telemetry snapshot and return its row ID."""
        sql = """
        INSERT INTO telemetry (
            timestamp, cpu_percent, memory_percent, disk_percent, disk_io_kbps,
            net_up_kbps, net_down_kbps, process_count, established_conns,
            listening_conns, remote_conns, camera_status, microphone_status,
            sensor_health_json, raw_payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        sensor_health_json = json.dumps([h.to_dict() for h in snapshot.sensor_health])
        raw_payload_json = json.dumps(snapshot.raw_payload) if snapshot.raw_payload else None

        with self.transaction() as cur:
            cur.execute(
                sql,
                (
                    snapshot.timestamp,
                    snapshot.cpu_percent,
                    snapshot.memory_percent,
                    snapshot.disk_percent,
                    snapshot.disk_io_write_kbps,
                    snapshot.net_upload_kbps,
                    snapshot.net_download_kbps,
                    snapshot.process_count,
                    snapshot.established_connections,
                    snapshot.listening_connections,
                    snapshot.remote_connections,
                    snapshot.camera_status.value,
                    snapshot.microphone_status.value,
                    sensor_health_json,
                    raw_payload_json,
                ),
            )
            return int(cur.lastrowid)

    def record_security_event(self, event: SecurityEvent) -> str:
        """Persist a security event record and return its event ID."""
        sql = """
        INSERT INTO security_events (
            event_id, timestamp, event_type, severity, risk_score, source,
            summary, evidence_json, confidence, affected_resource,
            correlation_id, schema_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        evidence_json = json.dumps(event.evidence) if event.evidence else None

        with self.transaction() as cur:
            cur.execute(
                sql,
                (
                    event.event_id,
                    event.timestamp,
                    event.event_type,
                    event.severity,
                    event.risk_score,
                    event.source,
                    event.summary,
                    evidence_json,
                    event.confidence,
                    event.affected_resource,
                    event.correlation_id,
                    event.schema_version,
                ),
            )
            return event.event_id

    def record_scan_run(
        self,
        scan_id: str,
        started_at: str,
        completed_at: str,
        trigger_source: str,
        is_demo: bool = False,
        is_success: bool = True,
        risk_score: float | None = None,
        severity: str | None = None,
        error_message: str | None = None,
    ) -> str:
        """Persist a scan run record."""
        sql = """
        INSERT INTO scan_runs (
            scan_id, started_at, completed_at, trigger_source,
            is_demo, is_success, risk_score, severity, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.transaction() as cur:
            cur.execute(
                sql,
                (
                    scan_id,
                    started_at,
                    completed_at,
                    trigger_source,
                    1 if is_demo else 0,
                    1 if is_success else 0,
                    risk_score,
                    severity,
                    error_message,
                ),
            )
            return scan_id

    def get_recent_events(
        self,
        limit: int = 100,
        min_severity: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query recent security events ordered reverse-chronologically."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if min_severity:
            cursor.execute(
                "SELECT * FROM security_events WHERE severity = ? ORDER BY timestamp DESC LIMIT ?;",
                (min_severity.upper(), max(1, limit)),
            )
        else:
            cursor.execute(
                "SELECT * FROM security_events ORDER BY timestamp DESC LIMIT ?;",
                (max(1, limit),),
            )

        rows = cursor.fetchall()
        cursor.close()
        results: list[dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            if d.get("evidence_json"):
                try:
                    d["evidence"] = json.loads(d["evidence_json"])
                except Exception:
                    d["evidence"] = []
            else:
                d["evidence"] = []
            results.append(d)
        return results

    def get_event_count(self) -> int:
        """Return total count of recorded security events."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM security_events;")
        row = cursor.fetchone()
        cursor.close()
        return int(row["count"]) if row else 0

    def get_telemetry_count(self) -> int:
        """Return total count of recorded telemetry snapshots."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM telemetry;")
        row = cursor.fetchone()
        cursor.close()
        return int(row["count"]) if row else 0

    def get_event_counts_by_severity(self) -> dict[str, int]:
        """Return distribution of security events by severity."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT severity, COUNT(*) AS total FROM security_events GROUP BY severity;")
        counts = {row["severity"]: int(row["total"]) for row in cursor.fetchall()}
        cursor.close()
        return counts

    def get_recent_telemetry(self, limit: int = 100) -> list[dict[str, Any]]:
        """Query recent telemetry rows."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT ?;",
            (max(1, limit),),
        )
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    def get_telemetry_series(self, metric: str, limit: int = 300) -> list[tuple[str, float]]:
        """Return time-series pairs for a specific numeric column in telemetry."""
        allowed_columns = {
            "cpu_percent",
            "memory_percent",
            "disk_percent",
            "disk_io_kbps",
            "net_up_kbps",
            "net_down_kbps",
            "process_count",
            "remote_conns",
        }
        if metric not in allowed_columns:
            raise ValueError(f"Invalid metric column requested: {metric}")

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT timestamp, {metric} FROM telemetry WHERE {metric} IS NOT NULL ORDER BY timestamp DESC LIMIT ?;",
            (max(1, limit),),
        )
        rows = cursor.fetchall()
        cursor.close()
        # Return chronological order
        return [(row["timestamp"], float(row[metric])) for row in reversed(rows)]

    def prune_retention(
        self,
        retention_days: int = 90,
        metrics_retention_days: int = 14,
    ) -> dict[str, int]:
        """Prune telemetry and events older than retention thresholds."""
        cutoff_events = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        cutoff_telemetry = (datetime.now(timezone.utc) - timedelta(days=metrics_retention_days)).isoformat()

        pruned = {"events": 0, "telemetry": 0, "scan_runs": 0}
        with self.transaction() as cur:
            cur.execute("DELETE FROM telemetry WHERE timestamp < ?;", (cutoff_telemetry,))
            pruned["telemetry"] = cur.rowcount

            cur.execute("DELETE FROM security_events WHERE timestamp < ?;", (cutoff_events,))
            pruned["events"] = cur.rowcount

            cur.execute("DELETE FROM scan_runs WHERE started_at < ?;", (cutoff_events,))
            pruned["scan_runs"] = cur.rowcount

        logger.info("Storage retention pruning completed: %s", pruned)
        return pruned

    def close(self) -> None:
        """Close all registered SQLite connections."""
        with self._lock:
            for conn in list(self._all_connections):
                try:
                    conn.close()
                except Exception:
                    pass
            self._all_connections.clear()
        self._local.connection = None
