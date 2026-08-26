"""
Versioned REST API data contracts, commands, query models, and responses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

from aura.models.types import PrivacyHardwareStatus

T = TypeVar("T")


class ScanState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ScanStage(str, Enum):
    INITIALIZING = "INITIALIZING"
    COLLECTING_SENSORS = "COLLECTING_SENSORS"
    RUNNING_DETECTION = "RUNNING_DETECTION"
    EVALUATING_RISK = "EVALUATING_RISK"
    PERSISTING = "PERSISTING"
    FINALIZING = "FINALIZING"


# ----------------------------------------------------------------------
# Query contracts
# ----------------------------------------------------------------------

class PaginationQuery(BaseModel):
    limit: int = Field(default=50, ge=1, le=500, description="Max records to return")
    offset: int = Field(default=0, ge=0, description="Record offset for pagination")


class EventQuery(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    min_severity: str | None = Field(default=None, description="Optional filter e.g. HIGH, CRITICAL")
    event_type: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class TelemetryHistoryQuery(BaseModel):
    metric: str = Field(
        ...,
        pattern="^(cpu_percent|memory_percent|disk_percent|disk_io_kbps|net_up_kbps|net_down_kbps|process_count|remote_conns)$",
        description="Numeric metric column name",
    )
    limit: int = Field(default=100, ge=1, le=1000)
    start_time: str | None = None
    end_time: str | None = None


# ----------------------------------------------------------------------
# Command contracts
# ----------------------------------------------------------------------

class ScanRequest(BaseModel):
    probe_camera: bool = Field(default=False, description="Enable non-intrusive camera device capability check")
    probe_microphone: bool = Field(default=False, description="Enable non-intrusive audio endpoint check")
    is_demo: bool = Field(default=False, description="Run synthetic demo scan (quarantined from DB)")


class MonitoringStartRequest(BaseModel):
    interval_seconds: float = Field(default=5.0, ge=1.0, le=300.0, description="Collection interval in seconds")


class MonitoringStopRequest(BaseModel):
    reason: str = Field(default="User requested stop", description="Reason for stopping agent loop")


class EventAcknowledgeRequest(BaseModel):
    event_id: str = Field(..., description="ID of event to acknowledge")
    acknowledged_by: str = Field(default="user", description="Operator identity or source")
    notes: str = Field(default="", description="Optional analyst notes")


# ----------------------------------------------------------------------
# Response contracts
# ----------------------------------------------------------------------

class TelemetryResponse(BaseModel):
    timestamp: str
    cpu_percent: float
    cpu_cores: int = 0
    cpu_frequency_mhz: float = 0.0
    memory_percent: float
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0
    disk_percent: float
    disk_free_gb: float = 0.0
    disk_total_gb: float = 0.0
    disk_path: str = "C:\\"
    net_upload_kbps: float
    net_download_kbps: float
    process_count: int
    established_connections: int
    listening_connections: int
    remote_connections: int
    camera_status: PrivacyHardwareStatus
    microphone_status: PrivacyHardwareStatus


class EvidenceItem(BaseModel):
    signal: str
    severity: str = "INFO"
    value: Any = None
    unit: str | None = None
    weight: int = 0


class RiskResponse(BaseModel):
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Composite 0-100 risk triage score")
    severity: str = Field(..., description="Severity band: NORMAL, LOW, MEDIUM, HIGH, CRITICAL")
    reasons: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    privacy_flags: list[str] = Field(default_factory=list)
    compound_exfiltration_flag: bool = False


class SecurityEventResponse(BaseModel):
    event_id: str
    timestamp: str
    event_type: str
    severity: str
    risk_score: float
    source: str
    summary: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float | None = None
    affected_resource: str = ""
    correlation_id: str = ""
    schema_version: int = 1
    incident_id: str = ""
    is_resolved: bool = False


class ScanStatusResponse(BaseModel):
    scan_id: str
    state: ScanState
    stage: ScanStage
    started_at: str
    completed_at: str | None = None
    elapsed_seconds: float = Field(default=0.0, ge=0.0)
    result_summary: str | None = None
    risk_score: float | None = None
    severity: str | None = None
    is_demo: bool = False
    error_code: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total_count: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    has_more: bool
