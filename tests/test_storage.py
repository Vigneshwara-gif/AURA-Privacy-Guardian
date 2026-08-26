"""
Tests for modern SQLite storage engine, WAL mode, migrations, and retention.
"""

from __future__ import annotations

import concurrent.futures
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import pytest

from aura.models.types import (
    PrivacyHardwareStatus,
    SecurityEvent,
    SensorHealthRecord,
    SensorStatus,
    TelemetrySnapshot,
)
from aura.storage.csv_import import import_legacy_csv_to_sqlite
from aura.storage.sqlite import StorageEngine


@pytest.fixture
def temp_storage(tmp_path: Path) -> StorageEngine:
    db_path = tmp_path / "test_aura.db"
    engine = StorageEngine(db_path, busy_timeout=2.0, wal_mode=True)
    yield engine
    engine.close()


def test_sqlite_initialization_and_wal(temp_storage: StorageEngine) -> None:
    """Verify SQLite initializes properly with WAL mode and schema."""
    conn = temp_storage._get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode;")
    mode = cur.fetchone()[0]
    assert mode.upper() in {"WAL", "MEMORY"}  # In-memory or WAL on Windows

    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cur.fetchall()}
    cur.close()
    assert "schema_migrations" in tables
    assert "telemetry" in tables
    assert "security_events" in tables
    assert "scan_runs" in tables
    assert "baseline_profiles" in tables


def test_telemetry_and_event_persistence(temp_storage: StorageEngine) -> None:
    """Verify storing and querying structured telemetry and security events."""
    snapshot = TelemetrySnapshot(
        cpu_percent=42.5,
        memory_percent=68.2,
        disk_percent=55.0,
        net_upload_kbps=1240.5,
        process_count=320,
        camera_status=PrivacyHardwareStatus.AVAILABLE,
        microphone_status=PrivacyHardwareStatus.NOT_DETECTED,
        sensor_health=[
            SensorHealthRecord(name="CPU", status=SensorStatus.HEALTHY, value="42.5%", detail="8 cores"),
        ],
    )
    row_id = temp_storage.record_telemetry(snapshot)
    assert row_id > 0

    event = SecurityEvent(
        event_type="TEST_ALERT",
        severity="HIGH",
        risk_score=65.0,
        summary="High network transfer rate detected",
        evidence=[{"signal": "network", "value": 1240.5}],
    )
    event_id = temp_storage.record_security_event(event)
    assert event_id == event.event_id

    events = temp_storage.get_recent_events(limit=10)
    assert len(events) == 1
    assert events[0]["event_id"] == event.event_id
    assert events[0]["severity"] == "HIGH"
    assert events[0]["risk_score"] == 65.0
    assert len(events[0]["evidence"]) == 1

    counts = temp_storage.get_event_counts_by_severity()
    assert counts.get("HIGH") == 1

    telemetry_rows = temp_storage.get_recent_telemetry(limit=10)
    assert len(telemetry_rows) == 1
    assert telemetry_rows[0]["cpu_percent"] == 42.5
    assert telemetry_rows[0]["camera_status"] == "AVAILABLE"


def test_concurrent_writes(temp_storage: StorageEngine) -> None:
    """Verify thread safety and locking behavior under concurrent writes."""
    num_threads = 5
    records_per_thread = 20

    def write_batch(thread_id: int) -> int:
        written = 0
        for i in range(records_per_thread):
            event = SecurityEvent(
                event_type="CONCURRENT_TEST",
                severity="INFO",
                risk_score=float(thread_id * 10),
                summary=f"Thread {thread_id} record {i}",
            )
            temp_storage.record_security_event(event)
            written += 1
        return written

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(write_batch, t) for t in range(num_threads)]
        results = [f.result() for f in futures]

    assert sum(results) == num_threads * records_per_thread
    assert temp_storage.get_event_count() == num_threads * records_per_thread


def test_retention_pruning(temp_storage: StorageEngine) -> None:
    """Verify retention pruning deletes records older than cutoffs."""
    now = datetime.now(timezone.utc)
    old_time = (now - timedelta(days=100)).isoformat()
    recent_time = (now - timedelta(days=2)).isoformat()

    old_event = SecurityEvent(timestamp=old_time, summary="Old event")
    recent_event = SecurityEvent(timestamp=recent_time, summary="Recent event")

    temp_storage.record_security_event(old_event)
    temp_storage.record_security_event(recent_event)
    assert temp_storage.get_event_count() == 2

    pruned = temp_storage.prune_retention(retention_days=90, metrics_retention_days=14)
    assert pruned["events"] == 1
    assert temp_storage.get_event_count() == 1

    remaining = temp_storage.get_recent_events()
    assert remaining[0]["event_id"] == recent_event.event_id


def test_legacy_csv_import(temp_storage: StorageEngine, tmp_path: Path) -> None:
    """Verify importing historical CSV data into SQLite."""
    csv_file = tmp_path / "system_logs.csv"
    csv_file.write_text(
        "Timestamp,CPU,Memory,Disk,Net,Process_Count,Severity,Risk_Score\n"
        "2026-08-20 12:00:00,35.2,50.1,40.0,250.0,300,LOW,15.0\n"
        "2026-08-20 12:05:00,85.0,75.0,40.0,4500.0,450,HIGH,60.0\n",
        encoding="utf-8",
    )

    count = import_legacy_csv_to_sqlite(csv_file, temp_storage)
    assert count == 2
    assert temp_storage.get_event_count() == 2
    events = temp_storage.get_recent_events()
    assert len(events) == 2
