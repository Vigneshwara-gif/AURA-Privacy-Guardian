"""
Comprehensive REST API transport, security middleware, and endpoint tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
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
        # Override default host if explicitly provided
        custom_keys = {h[0].lower() for h in headers}
        req_headers = [h for h in req_headers if h[0].lower() not in custom_keys] + headers

    response_status = 200
    response_headers: dict[str, str] = {}
    response_body = bytearray()

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        nonlocal response_status, response_headers, response_body
        if message["type"] == "http.response.start":
            response_status = message["status"]
            for k, v in message.get("headers", []):
                response_headers[k.decode("latin1").lower()] = v.decode("latin1")
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string,
        "headers": req_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8787),
        "state": {},
    }

    await app(scope, receive, send)
    return response_status, response_headers, bytes(response_body)


@pytest.fixture
def test_app(tmp_path: Path) -> Any:
    db_path = tmp_path / "api_test.db"
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
    yield app
    storage.close()


@pytest.mark.anyio
async def test_host_header_guard(test_app: Any) -> None:
    """Verify HostHeaderGuardMiddleware blocks DNS Rebinding."""
    # 1. Valid local Host header
    status, _, _ = await asgi_client(
        test_app,
        "GET",
        "/api/v1/status",
        headers=[(b"host", b"127.0.0.1:8787")],
    )
    # Status is 401 (auth required), meaning request passed host guard
    assert status == 401

    # 2. Malicious / Foreign Host header -> 400 Bad Request
    status, _, body = await asgi_client(
        test_app,
        "GET",
        "/api/v1/status",
        headers=[(b"host", b"evil-attacker.com")],
    )
    assert status == 400
    data = json.loads(body)
    assert data["code"] == "INVALID_REQUEST"


@pytest.mark.anyio
async def test_auth_session_handshake_flow(test_app: Any) -> None:
    """Verify bootstrap exchange returns session token."""
    session_mgr: SessionManager = test_app.state.session_manager
    code = session_mgr.create_bootstrap_code(scope=AuthScope.OPERATOR, ttl_seconds=60.0)

    req_body = json.dumps({"client_name": "AURA Test Dashboard"}).encode("utf-8")
    status, _, body = await asgi_client(
        test_app,
        "POST",
        "/api/v1/auth/session",
        headers=[
            (b"content-type", b"application/json"),
            (b"x-aura-bootstrap", code.encode("utf-8")),
        ],
        body=req_body,
    )
    assert status == 200
    res = json.loads(body)
    assert res["status"] == "AUTHENTICATED"
    assert res["scope"] == "OPERATOR"
    token = res["session_id"]

    # Use token on protected endpoint
    status, _, body = await asgi_client(
        test_app,
        "GET",
        "/api/v1/status",
        headers=[(b"authorization", f"Bearer {token}".encode("utf-8"))],
    )
    assert status == 200
    stat = json.loads(body)
    assert stat["version"] == "1.0.0"


@pytest.mark.anyio
async def test_rbac_scope_enforcement(test_app: Any) -> None:
    """Verify READ_ONLY token cannot execute OPERATOR operations."""
    session_mgr: SessionManager = test_app.state.session_manager
    read_token, _ = session_mgr.create_session(scope=AuthScope.READ_ONLY)
    op_token, _ = session_mgr.create_session(scope=AuthScope.OPERATOR)

    # 1. READ_ONLY hitting GET /health -> 200 OK
    status, _, _ = await asgi_client(
        test_app,
        "GET",
        "/api/v1/health",
        headers=[(b"authorization", f"Bearer {read_token}".encode("utf-8"))],
    )
    assert status == 200

    # 2. READ_ONLY hitting POST /scan/trigger -> 403 Forbidden
    scan_body = json.dumps({"probe_camera": False, "is_demo": True}).encode("utf-8")
    status, _, body = await asgi_client(
        test_app,
        "POST",
        "/api/v1/scan/trigger",
        headers=[
            (b"authorization", f"Bearer {read_token}".encode("utf-8")),
            (b"content-type", b"application/json"),
        ],
        body=scan_body,
    )
    assert status == 403
    err = json.loads(body)
    assert err["code"] == "FORBIDDEN"

    # 3. OPERATOR hitting POST /scan/trigger -> 200 OK
    status, _, body = await asgi_client(
        test_app,
        "POST",
        "/api/v1/scan/trigger",
        headers=[
            (b"authorization", f"Bearer {op_token}".encode("utf-8")),
            (b"content-type", b"application/json"),
        ],
        body=scan_body,
    )
    assert status == 200
    scan_res = json.loads(body)
    assert scan_res["state"] == "COMPLETED"


@pytest.mark.anyio
async def test_rest_endpoints_and_sanitization(test_app: Any) -> None:
    """Verify all GET/POST endpoints and sanitized error formats."""
    session_mgr: SessionManager = test_app.state.session_manager
    token, _ = session_mgr.create_session(scope=AuthScope.OPERATOR)
    auth_header = (b"authorization", f"Bearer {token}".encode("utf-8"))

    # 1. Live telemetry
    status, _, body = await asgi_client(test_app, "GET", "/api/v1/telemetry/live", headers=[auth_header])
    assert status == 200
    telemetry = json.loads(body)
    assert "cpu_percent" in telemetry

    # 2. Risk current
    status, _, body = await asgi_client(test_app, "GET", "/api/v1/risk/current", headers=[auth_header])
    assert status == 200
    risk = json.loads(body)
    assert "risk_score" in risk

    # 3. Events query
    status, _, body = await asgi_client(test_app, "GET", "/api/v1/events", headers=[auth_header])
    assert status == 200
    events = json.loads(body)
    assert "items" in events

    # 4. Config metadata
    status, _, body = await asgi_client(test_app, "GET", "/api/v1/config", headers=[auth_header])
    assert status == 200

    # 5. Non-existent event returns clean 404 ApiErrorResponse
    status, _, body = await asgi_client(
        test_app,
        "GET",
        "/api/v1/events/non-existent-id",
        headers=[auth_header],
    )
    assert status == 404
    err = json.loads(body)
    assert err["code"] == "NOT_FOUND"
    assert "non-existent-id" in err["message"]


@pytest.mark.anyio
async def test_missing_and_invalid_auth_tokens(test_app: Any) -> None:
    """Verify protected endpoints reject missing or invalid tokens with HTTP 401."""
    # 1. Missing Authorization header on GET /telemetry/live
    status, _, body = await asgi_client(test_app, "GET", "/api/v1/telemetry/live")
    assert status == 401
    err = json.loads(body)
    assert err["code"] == "UNAUTHORIZED"
    assert "Bearer token is required" in err["message"]

    # 2. Missing Authorization header on POST /scan/trigger
    scan_body = json.dumps({"is_demo": True}).encode("utf-8")
    status, _, body = await asgi_client(
        test_app,
        "POST",
        "/api/v1/scan/trigger",
        headers=[(b"content-type", b"application/json")],
        body=scan_body,
    )
    assert status == 401
    err = json.loads(body)
    assert err["code"] == "UNAUTHORIZED"

    # 3. Invalid Authorization header
    status, _, body = await asgi_client(
        test_app,
        "POST",
        "/api/v1/scan/trigger",
        headers=[
            (b"authorization", b"Bearer completely-bogus-token-12345"),
            (b"content-type", b"application/json"),
        ],
        body=scan_body,
    )
    assert status == 401
    err = json.loads(body)
    assert err["code"] == "UNAUTHORIZED"
    assert "invalid or has expired" in err["message"]


@pytest.mark.anyio
async def test_authenticated_scan_trigger_and_persistence(test_app: Any) -> None:
    """Verify authenticated scan trigger executes, returns result, and persists event."""
    session_mgr: SessionManager = test_app.state.session_manager
    token, _ = session_mgr.create_session(scope=AuthScope.OPERATOR)
    auth_header = (b"authorization", f"Bearer {token}".encode("utf-8"))

    # Trigger authenticated scan
    scan_body = json.dumps({"probe_camera": False, "probe_microphone": False, "is_demo": False}).encode("utf-8")
    status, _, body = await asgi_client(
        test_app,
        "POST",
        "/api/v1/scan/trigger",
        headers=[auth_header, (b"content-type", b"application/json")],
        body=scan_body,
    )
    assert status == 200
    res = json.loads(body)
    assert res["state"] == "COMPLETED"
    assert res["scan_id"] is not None
    assert res["elapsed_seconds"] >= 0.0

    # Query events to confirm scan event persistence
    status, _, body = await asgi_client(test_app, "GET", "/api/v1/events", headers=[auth_header])
    assert status == 200
    events = json.loads(body)
    assert len(events["items"]) >= 1
