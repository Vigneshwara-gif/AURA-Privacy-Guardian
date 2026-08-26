"""
Tests for AuraEngineService execution boundary, scan_once, and persistence.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import pytest

from aura.core.config import Settings
from aura.core.paths import AuraPaths
from aura.engine.service import AuraEngineService
from aura.models.types import ScanResult
from aura.sensors.collector import SensorCollector
from aura.storage.sqlite import StorageEngine


@pytest.fixture
def engine_service(tmp_path: Path) -> AuraEngineService:
    db_path = tmp_path / "engine_test.db"
    storage = StorageEngine(db_path)
    paths = AuraPaths(
        install_root=Path(__file__).resolve().parents[1],
        user_root=tmp_path,
        user_root_origin="test",
    )
    settings = Settings()
    collector = SensorCollector(sample_interval=0.05)
    service = AuraEngineService(
        settings=settings,
        paths=paths,
        storage=storage,
        collector=collector,
    )
    yield service
    storage.close()


def test_engine_lifecycle_and_status(engine_service: AuraEngineService) -> None:
    """Verify engine start, stop, and status queries."""
    status_initial = engine_service.get_status()
    assert status_initial["status"] == "STANDBY"

    engine_service.start()
    status_running = engine_service.get_status()
    assert status_running["status"] == "OPERATIONAL"

    engine_service.stop()
    assert engine_service.get_status()["status"] == "STANDBY"


def test_engine_scan_once_live_and_persisted(engine_service: AuraEngineService) -> None:
    """Verify scan_once runs end-to-end and records to SQLite."""
    res = engine_service.scan_once(probe_camera=False, is_demo=False)
    assert isinstance(res, ScanResult)
    assert res.scan_id
    assert res.telemetry.cpu_percent >= 0.0
    assert res.event.risk_score >= 0.0
    assert res.event.severity in {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL", "NORMAL"}

    # Verify event stored in SQLite
    events = engine_service.storage.get_recent_events()
    assert len(events) >= 1
    assert events[0]["correlation_id"] == res.scan_id

    # Verify telemetry stored in SQLite
    telemetry_rows = engine_service.storage.get_recent_telemetry()
    assert len(telemetry_rows) >= 1


def test_engine_scan_once_demo_quarantine(engine_service: AuraEngineService) -> None:
    """Verify synthetic demo scans are quarantined and NOT stored in SQLite."""
    count_before = engine_service.storage.get_event_count()

    synthetic_payload = {"CPU": 95.0, "Net": 6000.0, "Cam": 1, "Process_Count": 420, "Remote_Connections": 90}
    res = engine_service.scan_once(synthetic=synthetic_payload, is_demo=True)
    assert res.is_demo is True
    assert res.event.risk_score >= 50.0  # High risk expected for synthetic spike

    count_after = engine_service.storage.get_event_count()
    assert count_after == count_before  # Quarantined from DB
