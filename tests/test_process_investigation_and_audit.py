"""
Unit and integration tests for Process Intelligence, Investigation API,
Audit Logging, and System Reports.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from aura.api.auth import SessionManager
from aura.api.ratelimit import RateLimiter
from aura.api.server import create_app
from aura.api.stream import StreamManager
from aura.contracts.auth import AuthScope
from aura.core.config import Settings
from aura.core.paths import AuraPaths
from aura.engine.service import AuraEngineService
from aura.sensors.collector import SensorCollector
from aura.storage.sqlite import StorageEngine
from tests.test_api_transport import asgi_client


@pytest.fixture
def app_with_auth(tmp_path: Path):
    db_path = tmp_path / "proc_audit_test.db"
    storage = StorageEngine(db_path)
    paths = AuraPaths(
        install_root=Path(__file__).resolve().parents[1],
        user_root=tmp_path,
        user_root_origin="test",
    )
    settings = Settings()
    collector = SensorCollector(sample_interval=0.05)
    engine = AuraEngineService(settings=settings, paths=paths, storage=storage, collector=collector)
    session_manager = SessionManager()
    stream_manager = StreamManager()
    rate_limiter = RateLimiter()

    app = create_app(
        engine=engine,
        storage=storage,
        settings=settings,
        session_manager=session_manager,
        stream_manager=stream_manager,
        rate_limiter=rate_limiter,
    )
    token, _ = session_manager.create_session(scope=AuthScope.OPERATOR)
    yield app, storage, token
    storage.close()


@pytest.mark.anyio
async def test_process_list_and_investigation_endpoints(app_with_auth) -> None:
    app, storage, token = app_with_auth
    auth_header = (b"authorization", f"Bearer {token}".encode("utf-8"))

    # 1. GET /api/v1/processes
    status, _, body = await asgi_client(app, "GET", "/api/v1/processes?limit=10", headers=[auth_header])
    assert status == 200
    procs = json.loads(body)
    assert isinstance(procs, list)
    assert len(procs) > 0
    top_pid = procs[0]["pid"]

    # 2. GET /api/v1/processes/{pid}
    status, _, body = await asgi_client(app, "GET", f"/api/v1/processes/{top_pid}", headers=[auth_header])
    assert status == 200
    proc_detail = json.loads(body)
    assert proc_detail["pid"] == top_pid
    assert "name" in proc_detail
    assert "memory_mb" in proc_detail


@pytest.mark.anyio
async def test_audit_logs_and_reports_export(app_with_auth) -> None:
    app, storage, token = app_with_auth
    auth_header = (b"authorization", f"Bearer {token}".encode("utf-8"))

    # 1. Record an audit log
    storage.record_audit_log(
        action="CONFIG_UPDATED",
        actor="SecurityAdmin",
        target="NetworkSensitivity",
        details={"old": 3.0, "new": 2.5},
        result="SUCCESS",
    )

    # 2. Query /api/v1/audit/logs
    status, _, body = await asgi_client(app, "GET", "/api/v1/audit/logs?limit=10", headers=[auth_header])
    assert status == 200
    logs = json.loads(body)
    assert len(logs) >= 1
    assert logs[0]["action"] == "CONFIG_UPDATED"

    # 3. Export JSON report
    status, _, body = await asgi_client(app, "GET", "/api/v1/reports/export?format=json", headers=[auth_header])
    assert status == 200
    report = json.loads(body)
    assert "report_title" in report
    assert "system_status" in report
    assert "risk_evaluation" in report

    # 4. Export Markdown report
    status, _, body = await asgi_client(app, "GET", "/api/v1/reports/export?format=markdown", headers=[auth_header])
    assert status == 200
    md_report = json.loads(body)
    assert "report_markdown" in md_report
    assert "# AURA Security & Privacy Audit Report" in md_report["report_markdown"]


@pytest.mark.anyio
async def test_windows_privacy_shortcuts_api(app_with_auth) -> None:
    app, storage, token = app_with_auth
    auth_header = (b"authorization", f"Bearer {token}".encode("utf-8"))

    status, _, body = await asgi_client(app, "GET", "/api/v1/shortcuts/windows-privacy", headers=[auth_header])
    assert status == 200
    shortcuts = json.loads(body)
    assert len(shortcuts) >= 4
    assert any(s["uri"] == "ms-settings:privacy-webcam" for s in shortcuts)
