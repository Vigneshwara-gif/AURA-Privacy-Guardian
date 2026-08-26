"""
Validation tests for Phase 2 contracts, Pydantic schemas, and discriminated unions.
"""

from __future__ import annotations

import json
from pydantic import TypeAdapter, ValidationError
import pytest

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
from aura.contracts.errors import ApiErrorResponse, ErrorCode
from aura.contracts.stream import (
    HeartbeatMessage,
    LiveStreamMessage,
    StreamMessageType,
    TelemetryTickMessage,
)
from aura.models.types import PrivacyHardwareStatus, SensorStatus


def test_agent_status_contract() -> None:
    """Verify AgentStatus schema validation and serialization."""
    status = AgentStatus(
        state=AgentState.RUNNING,
        version="1.0.0",
        pid=12345,
        uptime_seconds=3600.5,
        degraded_components=[],
    )
    data = status.model_dump()
    assert data["state"] == "RUNNING"
    assert data["uptime_seconds"] == 3600.5

    # Invalid state rejected
    with pytest.raises(ValidationError):
        AgentStatus(state="INVALID_STATE")  # type: ignore[arg-type]


def test_agent_health_response_contract() -> None:
    """Verify full AgentHealthResponse model."""
    health = AgentHealthResponse(
        agent=AgentStatus(state=AgentState.RUNNING, pid=100),
        collection=CollectionHealth(interval_seconds=5.0),
        storage=StorageHealth(total_events=42),
        detection=DetectionHealth(model_status="READY"),
        sensors=[
            SensorHealthItem(name="CPU", status=SensorStatus.HEALTHY, value="10%", detail="Nominal"),
        ],
        diagnostics=DiagnosticsHealth(error_count=0),
    )
    assert health.agent.state == AgentState.RUNNING
    assert health.sensors[0].status == SensorStatus.HEALTHY


def test_api_command_and_query_validation() -> None:
    """Verify command constraints and query parameter bounding."""
    # Valid scan request
    req = ScanRequest(probe_camera=True, is_demo=False)
    assert req.probe_camera is True
    assert req.is_demo is False

    # Bounded pagination
    pag = PaginationQuery(limit=100, offset=20)
    assert pag.limit == 100

    with pytest.raises(ValidationError):
        PaginationQuery(limit=0)  # limit < 1 rejected

    with pytest.raises(ValidationError):
        PaginationQuery(limit=1000)  # limit > 500 rejected

    # Telemetry history regex validation
    q = TelemetryHistoryQuery(metric="cpu_percent")
    assert q.metric == "cpu_percent"

    with pytest.raises(ValidationError):
        TelemetryHistoryQuery(metric="DROP TABLE telemetry;--")  # Malicious/invalid metric rejected


def test_risk_response_contract() -> None:
    """Verify RiskResponse boundaries and structure."""
    risk = RiskResponse(
        risk_score=75.0,
        severity="HIGH",
        reasons=["High network activity"],
        evidence=[EvidenceItem(signal="Network", value=4500.0, unit="KB/s", weight=22)],
    )
    assert risk.risk_score == 75.0
    assert risk.severity == "HIGH"
    assert risk.evidence[0].weight == 22

    # Out of bounds score rejected
    with pytest.raises(ValidationError):
        RiskResponse(risk_score=150.0, severity="CRITICAL")


def test_api_error_response_sanitization() -> None:
    """Verify standardized error model."""
    err = ApiErrorResponse(
        code=ErrorCode.UNAUTHORIZED,
        message="Invalid local session token",
        correlation_id="req-12345",
    )
    assert err.code == ErrorCode.UNAUTHORIZED
    assert err.correlation_id == "req-12345"


def test_auth_contracts() -> None:
    """Verify auth handshake request/response schemas."""
    req = SessionHandshakeRequest(client_name="Test Client", requested_scope=AuthScope.ADMIN)
    assert req.requested_scope == AuthScope.ADMIN

    res = SessionHandshakeResponse(
        status=AuthSessionStatus.AUTHENTICATED,
        session_id="sess-abc-123",
        scope=AuthScope.ADMIN,
    )
    assert res.status == AuthSessionStatus.AUTHENTICATED


def test_websocket_discriminated_union_parsing() -> None:
    """Verify parsing tagged union WebSocket messages."""
    adapter = TypeAdapter(LiveStreamMessage)

    # 1. Parse heartbeat
    hb_json = json.dumps({"type": "heartbeat", "sequence": 42, "version": 1})
    parsed_hb = adapter.validate_json(hb_json)
    assert isinstance(parsed_hb, HeartbeatMessage)
    assert parsed_hb.type == StreamMessageType.HEARTBEAT
    assert parsed_hb.sequence == 42

    # 2. Parse telemetry tick
    tick_json = json.dumps({
        "type": "telemetry_tick",
        "version": 1,
        "payload": {
            "timestamp": "2026-08-25T12:00:00Z",
            "cpu_percent": 15.5,
            "memory_percent": 45.0,
            "disk_percent": 60.0,
            "net_upload_kbps": 120.0,
            "net_download_kbps": 300.0,
            "process_count": 350,
            "established_connections": 40,
            "listening_connections": 15,
            "remote_connections": 25,
            "camera_status": "AVAILABLE",
            "microphone_status": "NOT_DETECTED",
        }
    })
    parsed_tick = adapter.validate_json(tick_json)
    assert isinstance(parsed_tick, TelemetryTickMessage)
    assert parsed_tick.payload.cpu_percent == 15.5
    assert parsed_tick.payload.camera_status == PrivacyHardwareStatus.AVAILABLE

    # 3. Invalid discriminator rejected
    with pytest.raises(ValidationError):
        adapter.validate_json(json.dumps({"type": "UNKNOWN_TYPE", "payload": {}}))
