"""
Discriminated / tagged live-stream message models for WebSocket / SSE streaming.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field

from aura.contracts.agent import AgentStatus, SensorHealthItem
from aura.contracts.api import ScanStatusResponse, SecurityEventResponse, TelemetryResponse
from aura.contracts.errors import ApiErrorResponse


class StreamMessageType(str, Enum):
    TELEMETRY_TICK = "telemetry_tick"
    SECURITY_EVENT = "security_event"
    SENSOR_HEALTH_CHANGE = "sensor_health_change"
    AGENT_STATUS_CHANGE = "agent_status_change"
    SCAN_PROGRESS = "scan_progress"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class BaseStreamMessage(BaseModel):
    version: int = Field(default=1, description="Message schema format version")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TelemetryTickMessage(BaseStreamMessage):
    type: Literal[StreamMessageType.TELEMETRY_TICK] = StreamMessageType.TELEMETRY_TICK
    payload: TelemetryResponse


class SecurityEventMessage(BaseStreamMessage):
    type: Literal[StreamMessageType.SECURITY_EVENT] = StreamMessageType.SECURITY_EVENT
    payload: SecurityEventResponse


class SensorHealthChangeMessage(BaseStreamMessage):
    type: Literal[StreamMessageType.SENSOR_HEALTH_CHANGE] = StreamMessageType.SENSOR_HEALTH_CHANGE
    payload: list[SensorHealthItem]


class AgentStatusChangeMessage(BaseStreamMessage):
    type: Literal[StreamMessageType.AGENT_STATUS_CHANGE] = StreamMessageType.AGENT_STATUS_CHANGE
    payload: AgentStatus


class ScanProgressMessage(BaseStreamMessage):
    type: Literal[StreamMessageType.SCAN_PROGRESS] = StreamMessageType.SCAN_PROGRESS
    payload: ScanStatusResponse


class HeartbeatMessage(BaseStreamMessage):
    type: Literal[StreamMessageType.HEARTBEAT] = StreamMessageType.HEARTBEAT
    sequence: int = Field(default=0, ge=0)


class ErrorStreamMessage(BaseStreamMessage):
    type: Literal[StreamMessageType.ERROR] = StreamMessageType.ERROR
    payload: ApiErrorResponse


LiveStreamMessage = Annotated[
    Union[
        TelemetryTickMessage,
        SecurityEventMessage,
        SensorHealthChangeMessage,
        AgentStatusChangeMessage,
        ScanProgressMessage,
        HeartbeatMessage,
        ErrorStreamMessage,
    ],
    Field(discriminator="type"),
]
