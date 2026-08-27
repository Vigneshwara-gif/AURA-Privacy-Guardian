"""
Integration tests for MASTER 1 REST API endpoints using pure ASGI client.
"""

import json
from pathlib import Path
from typing import Any
import pytest

from aura.api.auth import SessionManager
from aura.api.server import create_app
from aura.contracts.auth import AuthScope
from aura.core.config import Settings
from aura.engine.service import AuraEngineService
from aura.sensors.collector import SensorCollector
from aura.storage.sqlite import StorageEngine


async def asgi_client(
    app: Any,
    method: str,
    path: str,
    headers: list[tuple[bytes, bytes]] | None = None,
    body: bytes = b"",
    query_string: bytes = b"",
) -> tuple[int, dict[str, str], bytes]:
    """Pure-Python asynchronous ASGI test runner."""
    req_headers = [(b"host", b"127.0.0.1:8787")]
    if headers:
        custom_keys = {h[0].lower() for h in headers}
        req_headers = [h for h in req_headers if h[0].lower() not in custom_keys] + headers

    response_status = 200
    response_headers: dict[str, str] = {}
    response_body = bytearray()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string,
        "headers": req_headers,
        "client": ("127.0.0.1", 54321),
        "server": ("127.0.0.1", 8787),
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        nonlocal response_status, response_headers, response_body
        if message["type"] == "http.response.start":
            response_status = message["status"]
            response_headers = {
                k.decode("latin1").lower(): v.decode("latin1")
                for k, v in message.get("headers", [])
            }
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    await app(scope, receive, send)
    return response_status, response_headers, bytes(response_body)


@pytest.mark.anyio
async def test_master_1_system_and_scan_endpoints(tmp_path):
    db_file = tmp_path / "test_api.db"
    settings = Settings()
    storage = StorageEngine(db_file)
    collector = SensorCollector()
    engine = AuraEngineService(settings=settings, storage=storage, collector=collector)
    session_mgr = SessionManager()

    # Generate bootstrap token
    bootstrap = session_mgr.create_bootstrap_code(scope=AuthScope.OPERATOR)

    app = create_app(
        engine=engine,
        storage=storage,
        settings=settings,
        session_manager=session_mgr,
    )

    # 1. Exchange session token
    st, _, res_b = await asgi_client(
        app,
        "POST",
        "/api/v1/auth/session",
        headers=[
            (b"x-aura-bootstrap", bootstrap.encode("utf-8")),
            (b"content-type", b"application/json"),
        ],
        body=b'{"client_name": "TestClient"}',
    )
    assert st == 200
    token = json.loads(res_b)["session_id"]
    auth_headers = [(b"authorization", f"Bearer {token}".encode("utf-8"))]

    # 2. Test /system/info
    st_sys, _, res_sys = await asgi_client(app, "GET", "/api/v1/system/info", headers=auth_headers)
    assert st_sys == 200
    assert "os_name" in json.loads(res_sys)

    # 3. Test /processes/tree
    st_tree, _, res_tree = await asgi_client(app, "GET", "/api/v1/processes/tree", headers=auth_headers)
    assert st_tree == 200
    assert isinstance(json.loads(res_tree), list)

    # 4. Test /persistence/inventory
    st_pers, _, res_pers = await asgi_client(app, "GET", "/api/v1/persistence/inventory", headers=auth_headers)
    assert st_pers == 200
    assert "startup_apps" in json.loads(res_pers)

    # 5. Test /security/posture
    st_pos, _, res_pos = await asgi_client(app, "GET", "/api/v1/security/posture", headers=auth_headers)
    assert st_pos == 200
    assert "overall_posture_score" in json.loads(res_pos)

    # 6. Test /scan/full (Trigger full scan)
    st_scan, _, res_scan = await asgi_client(app, "POST", "/api/v1/scan/full", headers=auth_headers)
    assert st_scan == 200
    scan_data = json.loads(res_scan)
    assert "scan_id" in scan_data
    assert len(scan_data["categories_scanned"]) == 16

    # 7. Test /scan/full/latest
    st_latest, _, res_latest = await asgi_client(app, "GET", "/api/v1/scan/full/latest", headers=auth_headers)
    assert st_latest == 200
    assert json.loads(res_latest)["scan_id"] == scan_data["scan_id"]

    # 8. Test /security/findings
    st_find, _, res_find = await asgi_client(app, "GET", "/api/v1/security/findings", headers=auth_headers)
    assert st_find == 200
    assert isinstance(json.loads(res_find), list)

    storage.close()
