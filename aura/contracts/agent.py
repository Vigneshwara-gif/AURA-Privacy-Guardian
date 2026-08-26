"""
Typed contracts for AURA background agent state, lifecycle, and subsystem health.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from aura.models.types import SensorStatus


class AgentState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    STOPPING = "STOPPING"
    CRASHING = "CRASHING"
    FAILED = "FAILED"


class AgentStatus(BaseModel):
    state: AgentState = Field(..., description="Current operational state of background daemon")
    version: str = Field(default="1.0.0", description="AURA engine release version")
    pid: int | None = Field(default=None, description="OS Process ID of running agent")
    started_at: str | None = Field(default=None, description="UTC ISO timestamp when agent started")
    uptime_seconds: float = Field(default=0.0, ge=0.0, description="Total active runtime in seconds")
    last_successful_collection: str | None = Field(default=None, description="UTC timestamp of last sensor cycle")
    last_persistence: str | None = Field(default=None, description="UTC timestamp of last SQLite write")
    consecutive_failures: int = Field(default=0, ge=0, description="Consecutive failed loop cycles")
    degraded_components: list[str] = Field(default_factory=list, description="Subsystems currently impaired")


class CollectionHealth(BaseModel):
    last_collection_time: str | None = None
    interval_seconds: float = Field(default=5.0, gt=0.0)
    consecutive_failures: int = Field(default=0, ge=0)
    loop_duration_ms: float = Field(default=0.0, ge=0.0)


class StorageHealth(BaseModel):
    status: str = "HEALTHY"
    backend: str = "sqlite"
    journal_mode: str = "wal"
    total_events: int = Field(default=0, ge=0)
    db_size_bytes: int = Field(default=0, ge=0)
    wal_size_bytes: int = Field(default=0, ge=0)
    last_write_time: str | None = None


class DetectionHealth(BaseModel):
    model_status: str = "READY"
    model_version: str = "1.0.0"
    feature_schema_version: int = 1
    features: list[str] = Field(default_factory=lambda: ["CPU", "Net", "Cam"])
    training_samples: int = Field(default=30, ge=0)
    last_inference_time: str | None = None


class SensorHealthItem(BaseModel):
    name: str
    status: SensorStatus
    value: str
    detail: str
    last_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DiagnosticsHealth(BaseModel):
    error_count: int = Field(default=0, ge=0)
    degraded_components: list[str] = Field(default_factory=list)


class AgentHealthResponse(BaseModel):
    agent: AgentStatus
    collection: CollectionHealth
    storage: StorageHealth
    detection: DetectionHealth
    sensors: list[SensorHealthItem] = Field(default_factory=list)
    diagnostics: DiagnosticsHealth
