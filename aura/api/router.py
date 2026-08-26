"""
REST and WebSocket route definitions for AURA Local API.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import JSONResponse

from aura.api.auth import SessionManager
from aura.api.dependencies import (
    get_current_claims,
    get_engine,
    get_rate_limiter,
    get_session_manager,
    get_storage,
    get_stream_manager,
    require_scope,
)
from aura.api.errors import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
)
from aura.api.ratelimit import RateLimiter
from aura.api.stream import StreamManager
from aura.contracts.agent import (
    AgentHealthResponse,
    AgentState,
    AgentStatus,
    CollectionHealth,
    DetectionHealth,
    DiagnosticsHealth,
    SensorHealthItem,
    StorageHealth,
)
from aura.contracts.api import (
    EventAcknowledgeRequest,
    EventQuery,
    EvidenceItem,
    MonitoringStartRequest,
    MonitoringStopRequest,
    PaginatedResponse,
    PaginationQuery,
    RiskResponse,
    ScanRequest,
    ScanStage,
    ScanState,
    ScanStatusResponse,
    SecurityEventResponse,
    TelemetryHistoryQuery,
    TelemetryResponse,
)
from aura.contracts.auth import (
    AuthScope,
    AuthSessionStatus,
    AuthTokenClaims,
    SessionHandshakeRequest,
    SessionHandshakeResponse,
)
from aura.engine.service import AuraEngineService
from aura.storage.sqlite import StorageEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


# ======================================================================
# Authentication Routes
# ======================================================================

@router.post(
    "/auth/session",
    response_model=SessionHandshakeResponse,
    summary="Exchange one-time bootstrap code for authenticated session token",
)
async def exchange_session_token(
    request: Request,
    body: SessionHandshakeRequest,
    x_aura_bootstrap: str | None = Header(default=None, alias="X-AURA-Bootstrap"),
    bootstrap_query: str | None = Query(default=None, alias="bootstrap"),
    session_manager: SessionManager = Depends(get_session_manager),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> SessionHandshakeResponse:
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not rate_limiter.check(f"auth:{client_ip}", max_requests=10, window_seconds=60.0):
        raise RateLimitError("Authentication attempt limit exceeded. Try again in 1 minute.")

    bootstrap_code = x_aura_bootstrap or bootstrap_query
    if not bootstrap_code:
        raise AuthenticationError("Bootstrap token required via X-AURA-Bootstrap header or query param")

    try:
        session_token, claims = session_manager.exchange_bootstrap(
            code=bootstrap_code,
            client_name=body.client_name,
        )
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc

    return SessionHandshakeResponse(
        status=AuthSessionStatus.AUTHENTICATED,
        session_id=session_token,
        scope=claims.scope,
        expires_at=claims.expires_at,
        server_time=datetime.now(timezone.utc).isoformat(),
    )


# ======================================================================
# Status & Health Routes (READ_ONLY Scope)
# ======================================================================

@router.get("/status", response_model=AgentStatus, summary="Get high-level engine operational status")
async def get_agent_status(
    engine: AuraEngineService = Depends(get_engine),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> AgentStatus:
    status_dict = engine.get_status()
    is_running = status_dict.get("status") == "OPERATIONAL"
    return AgentStatus(
        state=AgentState.RUNNING if is_running else AgentState.STOPPED,
        version="1.0.0",
        uptime_seconds=0.0,
        degraded_components=[],
    )


@router.get("/health", response_model=AgentHealthResponse, summary="Detailed multi-subsystem health rollup")
async def get_agent_health(
    engine: AuraEngineService = Depends(get_engine),
    storage: StorageEngine = Depends(get_storage),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> AgentHealthResponse:
    status_dict = engine.get_status()
    is_running = status_dict.get("status") == "OPERATIONAL"

    agent_stat = AgentStatus(
        state=AgentState.RUNNING if is_running else AgentState.STOPPED,
        version="1.0.0",
    )
    coll_health = CollectionHealth(
        interval_seconds=engine.settings.sensors.collection_interval_seconds,
    )
    stor_health = StorageHealth(
        status="HEALTHY",
        total_events=storage.get_event_count(),
    )
    det_health = DetectionHealth(
        model_status="READY",
        training_samples=engine.model.training_samples,
    )

    # Collect live sensor snapshot for health records
    snap = engine.collector.collect_snapshot(probe_camera=False)
    sensors_list = [
        SensorHealthItem(
            name=h.name,
            status=h.status,
            value=h.value,
            detail=h.detail,
        )
        for h in snap.sensor_health
    ]

    return AgentHealthResponse(
        agent=agent_stat,
        collection=coll_health,
        storage=stor_health,
        detection=det_health,
        sensors=sensors_list,
        diagnostics=DiagnosticsHealth(error_count=0),
    )


@router.get("/telemetry/live", response_model=TelemetryResponse, summary="Current live telemetry snapshot")
async def get_live_telemetry(
    engine: AuraEngineService = Depends(get_engine),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> TelemetryResponse:
    snap = await asyncio.to_thread(engine.collector.collect_snapshot)
    return TelemetryResponse(
        timestamp=snap.timestamp,
        cpu_percent=snap.cpu_percent,
        cpu_cores=snap.cpu_cores,
        cpu_frequency_mhz=snap.cpu_frequency_mhz,
        memory_percent=snap.memory_percent,
        memory_used_gb=snap.memory_used_gb,
        memory_total_gb=snap.memory_total_gb,
        disk_percent=snap.disk_percent,
        disk_free_gb=snap.disk_free_gb,
        disk_total_gb=snap.disk_total_gb,
        disk_path=snap.disk_path,
        net_upload_kbps=snap.net_upload_kbps,
        net_download_kbps=snap.net_download_kbps,
        process_count=snap.process_count,
        established_connections=snap.established_connections,
        listening_connections=snap.listening_connections,
        remote_connections=snap.remote_connections,
        camera_status=snap.camera_status,
        microphone_status=snap.microphone_status,
    )


@router.get("/telemetry/history", summary="Query historical telemetry time-series")
async def get_telemetry_history(
    metric: str = Query(..., pattern="^(cpu_percent|memory_percent|disk_percent|disk_io_kbps|net_up_kbps|net_down_kbps|process_count|remote_conns)$"),
    limit: int = Query(default=100, ge=1, le=1000),
    storage: StorageEngine = Depends(get_storage),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> list[dict[str, Any]]:
    series = await asyncio.to_thread(storage.get_telemetry_series, metric, limit)
    return [{"timestamp": ts, "value": val} for ts, val in series]


@router.get("/risk/current", response_model=RiskResponse, summary="Current risk score and explainable evidence")
async def get_current_risk(
    engine: AuraEngineService = Depends(get_engine),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> RiskResponse:
    # Run rapid live scan without mutating DB
    res = await asyncio.to_thread(engine.scan_once, is_demo=True)
    evidence_items = [
        EvidenceItem(
            signal=e.get("signal", "Signal"),
            severity=e.get("severity", "INFO"),
            value=e.get("value"),
            unit=e.get("unit"),
            weight=int(e.get("weight", 0)),
        )
        for e in res.event.evidence
    ]
    return RiskResponse(
        risk_score=res.event.risk_score,
        severity=res.event.severity,
        reasons=res.reasons,
        evidence=evidence_items,
        privacy_flags=res.privacy_flags,
        compound_exfiltration_flag="potential_data_exfiltration" in res.privacy_flags,
    )


@router.get("/sensors", response_model=list[SensorHealthItem], summary="Get all sensor health statuses")
async def get_sensors(
    engine: AuraEngineService = Depends(get_engine),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> list[SensorHealthItem]:
    snap = await asyncio.to_thread(engine.collector.collect_snapshot)
    return [
        SensorHealthItem(
            name=h.name,
            status=h.status,
            value=h.value,
            detail=h.detail,
        )
        for h in snap.sensor_health
    ]


@router.get("/events", response_model=PaginatedResponse[SecurityEventResponse], summary="Query security events log")
async def get_events(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    min_severity: str | None = Query(default=None),
    storage: StorageEngine = Depends(get_storage),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> PaginatedResponse[SecurityEventResponse]:
    raw_events = await asyncio.to_thread(storage.get_recent_events, limit + 1, min_severity)
    total_count = await asyncio.to_thread(storage.get_event_count)

    has_more = len(raw_events) > limit
    items_raw = raw_events[:limit]

    items = [
        SecurityEventResponse(
            event_id=e["event_id"],
            timestamp=e["timestamp"],
            event_type=e["event_type"],
            severity=e["severity"],
            risk_score=float(e["risk_score"]),
            source=e["source"],
            summary=e["summary"],
            evidence=e.get("evidence", []),
            confidence=float(e["confidence"]) if e.get("confidence") is not None else None,
            affected_resource=e.get("affected_resource", ""),
            correlation_id=e.get("correlation_id", ""),
            schema_version=int(e.get("schema_version", 1)),
        )
        for e in items_raw
    ]

    return PaginatedResponse(
        items=items,
        total_count=total_count,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/events/{event_id}", response_model=SecurityEventResponse, summary="Inspect single security event")
async def get_single_event(
    event_id: str,
    storage: StorageEngine = Depends(get_storage),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> SecurityEventResponse:
    events = await asyncio.to_thread(storage.get_recent_events, 200)
    evt = next((e for e in events if e["event_id"] == event_id), None)
    if not evt:
        raise NotFoundError(f"Security event '{event_id}' not found")

    return SecurityEventResponse(
        event_id=evt["event_id"],
        timestamp=evt["timestamp"],
        event_type=evt["event_type"],
        severity=evt["severity"],
        risk_score=float(evt["risk_score"]),
        source=evt["source"],
        summary=evt["summary"],
        evidence=evt.get("evidence", []),
        confidence=float(evt["confidence"]) if evt.get("confidence") is not None else None,
        affected_resource=evt.get("affected_resource", ""),
        correlation_id=evt.get("correlation_id", ""),
        schema_version=int(evt.get("schema_version", 1)),
    )


@router.get("/config", summary="Retrieve non-sensitive configuration metadata")
async def get_config_summary(
    engine: AuraEngineService = Depends(get_engine),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> dict[str, Any]:
    return engine.settings.summary()


# ======================================================================
# Command & State Operations (OPERATOR Scope)
# ======================================================================

@router.post("/scan/trigger", response_model=ScanStatusResponse, summary="Trigger manual security assessment scan")
async def trigger_scan(
    body: ScanRequest,
    engine: AuraEngineService = Depends(get_engine),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
) -> ScanStatusResponse:
    if not rate_limiter.check(f"scan:{claims.token_id}", max_requests=6, window_seconds=60.0):
        raise RateLimitError("Scan trigger rate limit exceeded (maximum 6 scans per minute).")

    res = await asyncio.to_thread(
        engine.scan_once,
        probe_camera=body.probe_camera,
        probe_microphone=body.probe_microphone,
        is_demo=body.is_demo,
    )

    return ScanStatusResponse(
        scan_id=res.scan_id,
        state=ScanState.COMPLETED,
        stage=ScanStage.FINALIZING,
        started_at=res.timestamp,
        completed_at=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=res.duration_ms / 1000.0,
        result_summary=res.event.summary,
        risk_score=res.event.risk_score,
        severity=res.event.severity,
        is_demo=res.is_demo,
    )


@router.post("/engine/start", response_model=AgentStatus, summary="Start/resume continuous monitoring engine")
async def start_engine(
    body: MonitoringStartRequest,
    engine: AuraEngineService = Depends(get_engine),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
) -> AgentStatus:
    if not rate_limiter.check(f"state:{claims.token_id}", max_requests=10, window_seconds=60.0):
        raise RateLimitError("State command rate limit exceeded.")

    engine.start()
    return AgentStatus(state=AgentState.RUNNING, version="1.0.0")


@router.post("/engine/stop", response_model=AgentStatus, summary="Stop/pause continuous monitoring engine")
async def stop_engine(
    body: MonitoringStopRequest,
    engine: AuraEngineService = Depends(get_engine),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
) -> AgentStatus:
    if not rate_limiter.check(f"state:{claims.token_id}", max_requests=10, window_seconds=60.0):
        raise RateLimitError("State command rate limit exceeded.")

    engine.stop()
    return AgentStatus(state=AgentState.STOPPED, version="1.0.0")


@router.post("/events/{event_id}/ack", response_model=SecurityEventResponse, summary="Acknowledge a security event")
async def acknowledge_event(
    event_id: str,
    body: EventAcknowledgeRequest,
    storage: StorageEngine = Depends(get_storage),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
) -> SecurityEventResponse:
    if not rate_limiter.check(f"ack:{claims.token_id}", max_requests=30, window_seconds=60.0):
        raise RateLimitError("Acknowledgement rate limit exceeded.")

    events = await asyncio.to_thread(storage.get_recent_events, 200)
    evt = next((e for e in events if e["event_id"] == event_id), None)
    if not evt:
        raise NotFoundError(f"Security event '{event_id}' not found")

    return SecurityEventResponse(
        event_id=evt["event_id"],
        timestamp=evt["timestamp"],
        event_type=evt["event_type"],
        severity=evt["severity"],
        risk_score=float(evt["risk_score"]),
        source=evt["source"],
        summary=evt["summary"],
        evidence=evt.get("evidence", []),
    )


# ======================================================================
# WebSocket Live Stream Route
# ======================================================================

@router.websocket("/stream")
async def stream_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    session_manager: SessionManager = Depends(get_session_manager),
    stream_manager: StreamManager = Depends(get_stream_manager),
) -> None:
    """Authenticated real-time WebSocket live-stream endpoint."""
    # Origin check
    origin = websocket.headers.get("origin", "")
    allowed_origins = {"http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:8787", "http://localhost:8787"}
    if origin and origin not in allowed_origins:
        logger.warning("Rejected WebSocket connection from unauthorized Origin: %r", origin)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Auth validation
    if not token:
        sec_protocol = websocket.headers.get("sec-websocket-protocol", "")
        if sec_protocol and sec_protocol.startswith("bearer."):
            token = sec_protocol.split(".", 1)[1].strip()

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    claims = session_manager.validate_session(token)
    if claims is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    client_id = f"{claims.token_id}-{uuid.uuid4().hex[:6]}"
    try:
        queue = await stream_manager.register_client(client_id, websocket, claims)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Max client limit reached")
        return

    await websocket.accept()

    async def _send_loop() -> None:
        try:
            while True:
                msg = await queue.get()
                await websocket.send_text(msg)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    async def _recv_loop() -> None:
        try:
            while True:
                await websocket.receive_text()
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    send_task = asyncio.create_task(_send_loop())
    recv_task = asyncio.create_task(_recv_loop())

    try:
        done, pending = await asyncio.wait(
            [send_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, WebSocketDisconnect):
                pass
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        logger.debug("WebSocket client [%s] disconnected: %s", client_id, exc)
    finally:
        for t in (send_task, recv_task):
            if not t.done():
                t.cancel()
        await stream_manager.remove_client(client_id)
