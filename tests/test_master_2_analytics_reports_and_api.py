"""
Integration tests for Master 2 Analytics, Reports, and REST APIs using ASGI runner.
"""

import json
import os
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
async def test_master_2_intelligence_endpoints(tmp_path):
    db_file = tmp_path / "test_m2.db"
    settings = Settings()
    storage = StorageEngine(db_file)
    collector = SensorCollector()
    engine = AuraEngineService(settings=settings, storage=storage, collector=collector)
    session_mgr = SessionManager()

    bootstrap = session_mgr.create_bootstrap_code(scope=AuthScope.OPERATOR)
    app = create_app(
        engine=engine,
        storage=storage,
        settings=settings,
        session_manager=session_mgr,
    )

    # 1. Exchange token
    st, _, res_b = await asgi_client(
        app,
        "POST",
        "/api/v1/auth/session",
        headers=[
            (b"x-aura-bootstrap", bootstrap.encode("utf-8")),
            (b"content-type", b"application/json"),
        ],
        body=b'{"client_name": "M2TestClient"}',
    )
    assert st == 200
    token = json.loads(res_b)["session_id"]
    auth_headers = [(b"authorization", f"Bearer {token}".encode("utf-8"))]

    # 2. Test /processes/{pid}/dna
    cur_pid = os.getpid()
    st_dna, _, res_dna = await asgi_client(app, "GET", f"/api/v1/processes/{cur_pid}/dna", headers=auth_headers)
    assert st_dna == 200
    dna_data = json.loads(res_dna)
    assert dna_data["pid"] == cur_pid
    assert "identity" in dna_data

    # 3. Test /network/investigate
    st_net, _, res_net = await asgi_client(app, "GET", "/api/v1/network/investigate", headers=auth_headers)
    assert st_net == 200
    assert "active_endpoints" in json.loads(res_net)

    # 4. Test /persistence/analysis
    st_pers, _, res_pers = await asgi_client(app, "GET", "/api/v1/persistence/analysis", headers=auth_headers)
    assert st_pers == 200
    assert "analyzed_items" in json.loads(res_pers)

    # 5. Test /threats/hunts/run
    st_hunt, _, res_hunt = await asgi_client(app, "POST", "/api/v1/threats/hunts/run", headers=auth_headers)
    assert st_hunt == 200
    assert "matches" in json.loads(res_hunt)

    # 6. Test /ai/explain
    st_exp, _, res_exp = await asgi_client(app, "GET", "/api/v1/ai/explain", headers=auth_headers)
    assert st_exp == 200
    assert "feature_explanations" in json.loads(res_exp)

    # 7. Test /timeline
    st_tlm, _, res_tlm = await asgi_client(app, "GET", "/api/v1/timeline", headers=auth_headers)
    assert st_tlm == 200
    assert isinstance(json.loads(res_tlm), list)

    # 8. Test /analytics/overview
    st_anl, _, res_anl = await asgi_client(app, "GET", "/api/v1/analytics/overview", headers=auth_headers)
    assert st_anl == 200
    assert "current_security_score" in json.loads(res_anl)

    # 9. Test /reports/generate
    st_rep, _, res_rep = await asgi_client(app, "POST", "/api/v1/reports/generate", headers=auth_headers)
    assert st_rep == 200
    rep_data = json.loads(res_rep)
    assert "report_id" in rep_data
    assert "sections" in rep_data

    storage.close()
