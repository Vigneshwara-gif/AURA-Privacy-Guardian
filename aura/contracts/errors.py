"""
Standard error schemas and error codes for AURA API.

Guarantees:
  - Zero raw tracebacks, internal file paths, or DB errors leaked to clients.
  - Consistent machine-readable codes and structured payloads.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SENSOR_UNAVAILABLE = "SENSOR_UNAVAILABLE"
    STORAGE_ERROR = "STORAGE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ApiErrorResponse(BaseModel):
    code: ErrorCode = Field(..., description="Machine-readable error category")
    message: str = Field(..., description="Sanitized human-readable explanation")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of error event",
    )
    correlation_id: str | None = Field(default=None, description="Request tracking ID")
    details: dict[str, Any] | None = Field(default=None, description="Non-sensitive structured details")
