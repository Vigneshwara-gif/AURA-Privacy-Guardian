"""
REST and WebSocket route definitions for AURA Local API.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from aura.contracts.intelligence import (
    AnalyticsMetricsResponse,
    AnomalyExplanationResponse,
    FullSecurityAuditReportResponse,
    NetworkInvestigationResponse,
    OpenShortcutRequest,
    PersistenceAnalysisResponse,
    ProcessDNAResponse,
    ResponseActionResultResponse,
    SecurityAlertResponse,
    SecurityIncidentResponse,
    TerminateProcessRequest,
    ThreatHuntResultResponse,
    TimelineItemResponse,
    UpdateIncidentStateRequest,
)
from aura.intelligence.alerts import AlertEngine
from aura.intelligence.analytics import SecurityAnalyticsEngine
from aura.intelligence.explainability import AIExplainabilityEngine
from aura.intelligence.findings import FindingSeverity
from aura.intelligence.incidents import IncidentManager, IncidentState
from aura.intelligence.network_intel import NetworkInvestigationEngine
from aura.intelligence.persistence_intel import PersistenceIntelligenceEngine
from aura.intelligence.process_dna import ProcessDNAService
from aura.intelligence.reports import SecurityReportGenerator
from aura.intelligence.response import SafeResponseEngine
from aura.intelligence.threat_hunter import ThreatHuntingEngine
from aura.intelligence.timeline import ForensicTimelineEngine

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from aura.contracts.system import (
    FullScanReportResponse,
    PersistenceInventoryResponse,
    ProcessTreeNodeResponse,
    ScheduledTaskResponse,
    SecurityFindingModel,
    SecurityPostureResponse,
    StartupAppResponse,
    SystemTelemetryResponse,
    CameraIntelligenceResponse,
    MicrophoneIntelligenceResponse,
    PrivacySentinelSummaryResponse,
    WindowsServiceResponse,
)
from aura.sensors.camera import CameraIntelligenceCollector
from aura.sensors.microphone import MicrophoneIntelligenceCollector
from aura.sensors.event_log import WindowsEventLogCollector
from aura.sensors.persistence import PersistenceIntelligenceCollector
from aura.sensors.process_tree import ProcessTreeBuilder
from aura.sensors.security_posture import SecurityPostureCollector
from aura.sensors.system_intel import SystemIntelligenceCollector

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

# ======================================================================
# Process Intelligence & Investigation Routes
# ======================================================================

class TerminateProcessRequest(BaseModel):
    confirm: bool = True
    reason: str = Field(min_length=1, default="Terminated by operator via AURA security action")


class OpenShortcutRequest(BaseModel):
    target: str


@router.get("/processes", summary="Query active processes with memory, CPU, and sockets")
async def list_processes(
    limit: int = Query(default=20, ge=1, le=100),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> list[dict[str, Any]]:
    from aura.sensors.process_intel import ProcessIntelligenceCollector
    from aura.sensors.network_intel import NetworkIntelligenceCollector

    procs = await asyncio.to_thread(ProcessIntelligenceCollector.get_top_processes, limit)
    conns = await asyncio.to_thread(NetworkIntelligenceCollector.get_active_connections, 100)

    pid_conns: dict[int, int] = {}
    for c in conns:
        if c.pid:
            pid_conns[c.pid] = pid_conns.get(c.pid, 0) + 1

    return [
        {
            "pid": p.pid,
            "name": p.name,
            "memory_mb": round(p.memory_rss_bytes / (1024 * 1024), 1),
            "status": p.status,
            "open_sockets": pid_conns.get(p.pid, 0),
        }
        for p in procs
    ]


@router.get(
    "/processes/tree",
    response_model=list[ProcessTreeNodeResponse],
    summary="Get full hierarchical parent-child Windows process tree",
)
async def get_process_tree(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    roots = ProcessTreeBuilder.get_process_tree()
    return [r.to_dict() for r in roots]


@router.get(
    "/processes/{pid}/tree",
    response_model=ProcessTreeNodeResponse,
    summary="Get process tree subtree rooted at a specific PID",
)
async def get_process_subtree(
    pid: int,
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    node = ProcessTreeBuilder.get_process_subtree(pid)
    if not node:
        raise NotFoundError(f"Process with PID {pid} not found in process tree.")
    return node.to_dict()


@router.get("/processes/{pid}", summary="Detailed process investigation")
async def investigate_process(
    pid: int,
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> dict[str, Any]:
    from aura.sensors.process_intel import ProcessIntelligenceCollector
    from aura.sensors.network_intel import NetworkIntelligenceCollector

    p_info = await asyncio.to_thread(ProcessIntelligenceCollector.get_process_by_pid, pid)
    if not p_info:
        raise NotFoundError(f"Process PID {pid} not found or terminated.")

    conns = await asyncio.to_thread(NetworkIntelligenceCollector.get_active_connections, 200)
    proc_conns = [c.to_dict() for c in conns if c.pid == pid]

    return {
        "pid": p_info.pid,
        "name": p_info.name,
        "exe_path": p_info.exe_path,
        "parent_pid": p_info.parent_pid,
        "created_time": p_info.created_time,
        "cpu_percent": p_info.cpu_percent,
        "memory_mb": round(p_info.memory_rss_bytes / (1024 * 1024), 1),
        "username": p_info.username,
        "is_elevated": p_info.is_elevated,
        "active_sockets": proc_conns,
    }


@router.post("/processes/{pid}/terminate", summary="Safe, user-confirmed process termination")
async def terminate_process(
    pid: int,
    body: TerminateProcessRequest,
    storage: StorageEngine = Depends(get_storage),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
) -> dict[str, Any]:
    import psutil
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Process termination requires explicit confirmation (confirm: true).")

    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except psutil.TimeoutExpired:
            proc.kill()

        storage.record_audit_log(
            action="PROCESS_TERMINATED",
            actor=claims.issued_to,
            target=f"PID {pid} ({proc_name})",
            details={"reason": body.reason, "pid": pid, "process_name": proc_name},
            result="SUCCESS",
        )
        return {
            "status": "TERMINATED",
            "pid": pid,
            "process_name": proc_name,
            "message": f"Process {proc_name} (PID: {pid}) terminated cleanly.",
        }
    except psutil.NoSuchProcess:
        raise NotFoundError(f"Process PID {pid} does not exist.")
    except psutil.AccessDenied as exc:
        storage.record_audit_log(
            action="PROCESS_TERMINATION_DENIED",
            actor=claims.issued_to,
            target=f"PID {pid}",
            details={"reason": body.reason, "error": str(exc)},
            result="ACCESS_DENIED",
        )
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: Terminating PID {pid} requires Windows administrative elevation.",
        )


# ======================================================================
# Audit Logs & Reports Routes
# ======================================================================

@router.get("/audit/logs", summary="Query audit ledger of system and security actions")
async def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    storage: StorageEngine = Depends(get_storage),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(storage.get_audit_logs, limit)


@router.get("/reports/export", summary="Export comprehensive security & privacy audit report")
async def export_report(
    format: str = Query(default="json", pattern="^(json|markdown)$"),
    engine: AuraEngineService = Depends(get_engine),
    storage: StorageEngine = Depends(get_storage),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    import sys
    snap = await asyncio.to_thread(engine.collector.collect_snapshot, probe_camera=True, probe_microphone=True)
    events = await asyncio.to_thread(storage.get_recent_events, 20)
    audit = await asyncio.to_thread(storage.get_audit_logs, 20)
    risk_res = await asyncio.to_thread(engine.scan_once, is_demo=True)

    report_data = {
        "report_title": "AURA Privacy Guardian Security & Privacy Audit Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host_platform": sys.platform,
        "system_status": {
            "cpu_percent": snap.cpu_percent,
            "memory_percent": snap.memory_percent,
            "disk_free_gb": snap.disk_free_gb,
            "process_count": snap.process_count,
            "established_connections": snap.established_connections,
            "camera_status": snap.camera_status.value,
            "microphone_status": snap.microphone_status.value,
        },
        "risk_evaluation": {
            "risk_score": risk_res.event.risk_score,
            "severity": risk_res.event.severity,
            "summary": risk_res.event.summary,
            "reasons": risk_res.reasons,
        },
        "recent_security_events": events,
        "audit_trail": audit,
    }

    if format == "markdown":
        md = f"# AURA Security & Privacy Audit Report\n**Generated:** {report_data['generated_at']}\n**Overall Risk:** {risk_res.event.risk_score:.1f} / 100 ({risk_res.event.severity})\n\n## Host Hardware & Telemetry\n- CPU Utilization: {snap.cpu_percent:.1f}%\n- Physical RAM: {snap.memory_percent:.1f}%\n- Active Processes: {snap.process_count}\n- Established Connections: {snap.established_connections}\n- Camera Sensor State: {snap.camera_status.value}\n- Microphone Sensor State: {snap.microphone_status.value}\n\n## Recent Security Incidents ({len(events)})\n"
        for e in events[:5]:
            md += f"- **[{e['severity']}] {e['event_type']}**: {e['summary']} ({e['timestamp']})\n"
        return {"report_markdown": md}

    return report_data


# ======================================================================
# Windows Privacy & Security Shortcuts
# ======================================================================

@router.get("/shortcuts/windows-privacy", summary="List verified Windows system privacy settings URI shortcuts")
async def get_privacy_shortcuts(
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> list[dict[str, str]]:
    return [
        {"id": "camera", "name": "Camera Privacy Settings", "uri": "ms-settings:privacy-webcam", "description": "Configure app camera permissions"},
        {"id": "microphone", "name": "Microphone Privacy Settings", "uri": "ms-settings:privacy-microphone", "description": "Configure app microphone permissions"},
        {"id": "security", "name": "Windows Security", "uri": "windowsdefender:", "description": "Open Windows Defender security dashboard"},
        {"id": "privacy", "name": "Windows General Privacy", "uri": "ms-settings:privacy", "description": "Open Windows privacy controls"},
    ]


@router.post("/shortcuts/open", summary="Safely open Windows system settings shortcut")
async def open_shortcut(
    body: OpenShortcutRequest,
    storage: StorageEngine = Depends(get_storage),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
) -> dict[str, str]:
    import sys
    import os
    allowed_uris = {
        "ms-settings:privacy-webcam",
        "ms-settings:privacy-microphone",
        "windowsdefender:",
        "ms-settings:privacy",
    }
    if body.target not in allowed_uris:
        raise HTTPException(status_code=400, detail="Invalid shortcut target URI.")

    if sys.platform == "win32":
        try:
            os.startfile(body.target)
            storage.record_audit_log(
                action="OPENED_WINDOWS_SHORTCUT",
                actor=claims.issued_to,
                target=body.target,
                result="SUCCESS",
            )
            return {"status": "OPENED", "target": body.target}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to launch shortcut: {exc}")
    return {"status": "UNSUPPORTED", "message": "Shortcuts only supported on Windows host."}


# ======================================================================
# Historical Risk Route
# ======================================================================

@router.get("/risk/history", summary="Historical risk score series from SQLite")
async def get_risk_history_route(
    limit: int = Query(default=100, ge=1, le=500),
    storage: StorageEngine = Depends(get_storage),
    _: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(storage.get_risk_history, limit)


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
    allowed_origins = {"http://127.0.0.1:5173", "http://localhost:5173", "http://localhost:4173", "http://127.0.0.1:8787", "http://localhost:8787"}
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


# ==============================================================================
# MASTER 1: CORE WINDOWS SECURITY ENGINE ENDPOINTS
# ==============================================================================

@router.get(
    "/system/info",
    response_model=SystemTelemetryResponse,
    summary="Get comprehensive real Windows system telemetry and hardware metrics",
)
async def get_system_info(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    snap = SystemIntelligenceCollector.collect_snapshot()
    return {
        "timestamp": snap.timestamp,
        "os_name": snap.os_name,
        "os_version": snap.os_version,
        "os_build": snap.os_build,
        "os_display_version": snap.os_display_version,
        "architecture": snap.architecture,
        "hostname": snap.hostname,
        "logged_in_user": snap.logged_in_user,
        "boot_time_iso": snap.boot_time_iso,
        "uptime_seconds": snap.uptime_seconds,
        "cpu_model": snap.cpu_model,
        "cpu_physical_cores": snap.cpu_physical_cores,
        "cpu_logical_cores": snap.cpu_logical_cores,
        "cpu_frequency_current_mhz": snap.cpu_frequency_current_mhz,
        "cpu_frequency_max_mhz": snap.cpu_frequency_max_mhz,
        "cpu_overall_percent": snap.cpu_overall_percent,
        "cpu_cores": [{"core_index": c.core_index, "utilization_percent": c.utilization_percent} for c in snap.cpu_cores],
        "memory_total_gb": snap.memory_total_gb,
        "memory_used_gb": snap.memory_used_gb,
        "memory_available_gb": snap.memory_available_gb,
        "memory_percent": snap.memory_percent,
        "swap_total_gb": snap.swap_total_gb,
        "swap_used_gb": snap.swap_used_gb,
        "partitions": [
            {
                "mountpoint": p.mountpoint,
                "device": p.device,
                "fstype": p.fstype,
                "total_gb": p.total_gb,
                "used_gb": p.used_gb,
                "free_gb": p.free_gb,
                "percent": p.percent,
            }
            for p in snap.partitions
        ],
    }




@router.get(
    "/persistence/inventory",
    response_model=PersistenceInventoryResponse,
    summary="Get consolidated persistence inventory (Startup apps, Services, Tasks)",
)
async def get_persistence_inventory(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    snap = PersistenceIntelligenceCollector.collect_inventory()
    return {
        "timestamp": snap.timestamp,
        "startup_apps": [
            {
                "name": a.name,
                "command": a.command,
                "source_location": a.source_location,
                "user_context": a.user_context,
                "is_enabled": a.is_enabled,
                "executable_path": a.executable_path,
                "exists_on_disk": a.exists_on_disk,
            }
            for a in snap.startup_apps
        ],
        "services_count": snap.services_count,
        "running_services_count": snap.running_services_count,
        "services": [
            {
                "name": s.name,
                "display_name": s.display_name,
                "status": s.status,
                "start_type": s.start_type,
                "bin_path": s.bin_path,
                "username": s.username,
            }
            for s in snap.services
        ],
        "scheduled_tasks_count": snap.scheduled_tasks_count,
        "scheduled_tasks": [
            {
                "task_name": t.task_name,
                "next_run_time": t.next_run_time,
                "status": t.status,
                "author": t.author,
            }
            for t in snap.scheduled_tasks
        ],
    }


@router.get(
    "/security/posture",
    response_model=SecurityPostureResponse,
    summary="Get real Windows Defender, Firewall, Update, SecureBoot, and UAC security posture",
)
async def get_security_posture(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    snap = SecurityPostureCollector.collect_posture()
    return {
        "timestamp": snap.timestamp,
        "defender": {
            "is_installed": snap.defender.is_installed,
            "antivirus_enabled": snap.defender.antivirus_enabled,
            "realtime_protection_enabled": snap.defender.realtime_protection_enabled,
            "ioav_protection_enabled": snap.defender.ioav_protection_enabled,
            "antispyware_enabled": snap.defender.antispyware_enabled,
            "signature_version": snap.defender.signature_version,
            "quick_scan_age_days": snap.defender.quick_scan_age_days,
            "full_scan_age_days": snap.defender.full_scan_age_days,
        },
        "firewall": {
            "domain_profile_enabled": snap.firewall.domain_profile_enabled,
            "private_profile_enabled": snap.firewall.private_profile_enabled,
            "public_profile_enabled": snap.firewall.public_profile_enabled,
            "all_profiles_secure": snap.firewall.all_profiles_secure,
        },
        "is_reboot_pending": snap.update_posture.is_reboot_pending,
        "reboot_reasons": snap.update_posture.reboot_reasons,
        "secure_boot_enabled": snap.secure_boot_enabled,
        "tpm_present": snap.tpm_present,
        "uac_enabled": snap.uac_enabled,
        "overall_posture_score": snap.overall_posture_score,
    }


@router.get(
    "/security/events/system-logs",
    summary="Get recent Windows Security & System event log items",
)
async def get_system_log_events(
    count: int = Query(default=10, ge=1, le=100),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    events = WindowsEventLogCollector.get_recent_system_events(count=count)
    return [
        {
            "event_id": e.event_id,
            "log_name": e.log_name,
            "provider": e.provider,
            "timestamp": e.timestamp,
            "level": e.level,
            "user_name": e.user_name,
            "computer": e.computer,
            "description": e.description,
        }
        for e in events
    ]


@router.post(
    "/scan/full",
    response_model=FullScanReportResponse,
    summary="Trigger a comprehensive 16-category Full PC Security Scan",
)
async def trigger_full_pc_scan(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
    engine: AuraEngineService = Depends(get_engine),
) -> Any:
    res = engine.execute_full_pc_scan()
    return res.to_dict()


@router.get(
    "/scan/full/latest",
    response_model=FullScanReportResponse,
    summary="Get the most recent Full PC Security Scan report",
)
async def get_latest_full_scan(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
    engine: AuraEngineService = Depends(get_engine),
) -> Any:
    res = engine.get_latest_full_scan()
    if not res:
        # Run a scan if none has run yet
        fresh = engine.execute_full_pc_scan()
        return fresh.to_dict()
    return res


@router.get(
    "/scan/full/{scan_id}",
    response_model=FullScanReportResponse,
    summary="Get specific Full PC Security Scan report by ID",
)
async def get_full_scan_by_id(
    scan_id: str,
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
    engine: AuraEngineService = Depends(get_engine),
) -> Any:
    res = engine.get_full_scan_by_id(scan_id)
    if not res:
        raise NotFoundError(f"Scan with ID {scan_id} not found.")
    return res


@router.get(
    "/security/findings",
    response_model=list[SecurityFindingModel],
    summary="Query unified security findings from full PC audits and rules",
)
async def get_security_findings(
    limit: int = Query(default=50, ge=1, le=200),
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
    engine: AuraEngineService = Depends(get_engine),
) -> Any:
    return engine.get_findings(limit=limit, severity=severity, status=status, category=category)


class UpdateFindingStatusRequest(BaseModel):
    remediation_status: Literal["OPEN", "INVESTIGATING", "RESOLVED", "IGNORED"]


@router.post(
    "/security/findings/{finding_id}/status",
    summary="Update remediation status for a security finding",
)
async def update_finding_status(
    finding_id: str,
    body: UpdateFindingStatusRequest,
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
    engine: AuraEngineService = Depends(get_engine),
) -> Any:
    success = engine.update_finding_status(finding_id=finding_id, new_status=body.remediation_status)
    if not success:
        raise NotFoundError(f"Finding with ID {finding_id} not found.")
    return {"finding_id": finding_id, "remediation_status": body.remediation_status, "updated": True}


@router.get(
    "/privacy/camera",
    response_model=CameraIntelligenceResponse,
    summary="Get genuine Windows camera hardware inventory, permissions, and active/recent usage",
)
async def get_camera_intelligence(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    snap = CameraIntelligenceCollector.collect_snapshot()
    return snap.to_dict()


@router.get(
    "/privacy/microphone",
    response_model=MicrophoneIntelligenceResponse,
    summary="Get genuine Windows microphone audio endpoints, permissions, and active/recent usage",
)
async def get_microphone_intelligence(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    snap = MicrophoneIntelligenceCollector.collect_snapshot()
    return snap.to_dict()


@router.get(
    "/privacy/summary",
    response_model=PrivacySentinelSummaryResponse,
    summary="Get consolidated privacy sentinel health score and hardware telemetry",
)
async def get_privacy_summary(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    cam_snap = CameraIntelligenceCollector.collect_snapshot()
    mic_snap = MicrophoneIntelligenceCollector.collect_snapshot()

    priv_score = 100
    if cam_snap.is_active:
        priv_score -= 30
    if mic_snap.is_active:
        priv_score -= 25
    if cam_snap.system_permission == "DENIED":
        priv_score -= 10
    if mic_snap.system_permission == "DENIED":
        priv_score -= 10
    priv_score = max(0, min(100, priv_score))

    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "timestamp": now_iso,
        "camera": cam_snap.to_dict(),
        "microphone": mic_snap.to_dict(),
        "overall_privacy_score": priv_score,
    }


# ==============================================================================
# MASTER 2: SECURITY INTELLIGENCE & INVESTIGATION ENDPOINTS
# ==============================================================================

@router.get(
    "/processes/{pid}/dna",
    response_model=ProcessDNAResponse,
    summary="Get complete Process DNA profile (identity, execution, network, privacy, security)",
)
async def get_process_dna(
    pid: int,
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    dna = ProcessDNAService.get_process_dna(pid)
    if not dna:
        raise NotFoundError(f"Process with PID {pid} not found or terminated.")
    return dna.to_dict()


@router.get(
    "/network/investigate",
    response_model=NetworkInvestigationResponse,
    summary="Investigate active socket flows, endpoint classifications, and exposure vectors",
)
async def investigate_network(
    limit: int = Query(default=150, ge=1, le=500),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    snap = NetworkInvestigationEngine.investigate(limit=limit)
    return snap.to_dict()


@router.get(
    "/persistence/analysis",
    response_model=PersistenceAnalysisResponse,
    summary="Deep analysis of Run keys, startup apps, services, and scheduled tasks",
)
async def analyze_persistence(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    snap = PersistenceIntelligenceEngine.analyze()
    return snap.to_dict()


@router.post(
    "/threats/hunts/run",
    response_model=ThreatHuntResultResponse,
    summary="Execute multi-vector threat hunting queries across memory, network, and registry",
)
async def run_threat_hunts(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
) -> Any:
    res = ThreatHuntingEngine.execute_hunts()
    return res.to_dict()


@router.get(
    "/ai/explain",
    response_model=AnomalyExplanationResponse,
    summary="Explainable AI anomaly report with normalized feature bounds and LOF insights",
)
async def explain_anomaly(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
    engine: AuraEngineService = Depends(get_engine),
) -> Any:
    telem = engine.collector.collect_snapshot(probe_camera=False, probe_microphone=False)
    posture = SecurityPostureCollector.collect_posture()
    exp = AIExplainabilityEngine.explain(telemetry=telem, ensemble=engine.scan_engine.ensemble, posture=posture)
    return exp.to_dict()


@router.get(
    "/timeline",
    response_model=list[TimelineItemResponse],
    summary="Get chronological forensic security timeline items",
)
async def get_timeline(
    limit: int = Query(default=50, ge=1, le=200),
    severity: str | None = Query(default=None),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    items = ForensicTimelineEngine.get_timeline(limit=limit, severity=severity)
    return [i.to_dict() for i in items]


@router.get(
    "/incidents",
    response_model=list[SecurityIncidentResponse],
    summary="Get list of security incidents",
)
async def get_incidents(
    limit: int = Query(default=50, ge=1, le=100),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    incidents = IncidentManager.get_incidents(limit=limit)
    return [i.to_dict() for i in incidents]


@router.get(
    "/incidents/{incident_id}",
    response_model=SecurityIncidentResponse,
    summary="Get specific security incident by ID",
)
async def get_incident_by_id(
    incident_id: str,
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    inc = IncidentManager.get_incident_by_id(incident_id)
    if not inc:
        raise NotFoundError(f"Incident {incident_id} not found.")
    return inc.to_dict()


@router.post(
    "/incidents/{incident_id}/state",
    summary="Update incident lifecycle state",
)
async def update_incident_state(
    incident_id: str,
    body: UpdateIncidentStateRequest,
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
) -> Any:
    state_enum = IncidentState(body.state)
    success = IncidentManager.update_incident_state(
        incident_id=incident_id,
        new_state=state_enum,
        actor=claims.issued_to,
        note=body.note,
    )
    if not success:
        raise NotFoundError(f"Incident {incident_id} not found.")
    return {"incident_id": incident_id, "state": body.state, "updated": True}


@router.post(
    "/response/terminate-process",
    response_model=ResponseActionResultResponse,
    summary="Safely terminate a suspicious process with audit logging",
)
async def terminate_process_endpoint(
    body: TerminateProcessRequest,
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
) -> Any:
    res = SafeResponseEngine.terminate_process(pid=body.pid, actor=claims.issued_to)
    return res.to_dict()


@router.post(
    "/response/open-shortcut",
    response_model=ResponseActionResultResponse,
    summary="Open Windows privacy or security configuration shortcut",
)
async def open_shortcut_endpoint(
    body: OpenShortcutRequest,
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
) -> Any:
    res = SafeResponseEngine.open_system_shortcut(shortcut_type=body.shortcut_type, actor=claims.issued_to)
    return res.to_dict()


@router.get(
    "/alerts",
    response_model=list[SecurityAlertResponse],
    summary="Get recent security alerts",
)
async def get_alerts_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
) -> Any:
    alerts = AlertEngine.get_alerts(limit=limit)
    return [a.to_dict() for a in alerts]


@router.post(
    "/alerts/{alert_id}/acknowledge",
    summary="Acknowledge a security alert",
)
async def acknowledge_alert_endpoint(
    alert_id: str,
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
) -> Any:
    success = AlertEngine.acknowledge_alert(alert_id=alert_id, actor=claims.issued_to)
    if not success:
        raise NotFoundError(f"Alert {alert_id} not found.")
    return {"alert_id": alert_id, "acknowledged": True}


@router.get(
    "/analytics/overview",
    response_model=AnalyticsMetricsResponse,
    summary="Get aggregated security and privacy analytics metrics",
)
async def get_analytics_overview(
    time_window: str = Query(default="24h"),
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.READ_ONLY)),
    storage: StorageEngine = Depends(get_storage),
) -> Any:
    metrics = SecurityAnalyticsEngine.compute_metrics(storage=storage, time_window=time_window)
    return metrics.to_dict()


@router.post(
    "/reports/generate",
    response_model=FullSecurityAuditReportResponse,
    summary="Generate comprehensive executive & technical security audit report",
)
async def generate_report_endpoint(
    claims: AuthTokenClaims = Depends(require_scope(AuthScope.OPERATOR)),
    storage: StorageEngine = Depends(get_storage),
) -> Any:
    rep = SecurityReportGenerator.generate_full_report(storage=storage)
    return rep.to_dict()
