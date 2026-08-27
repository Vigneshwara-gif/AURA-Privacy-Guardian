"""
Authentication and session handshake contracts for AURA Local API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


class AuthScope(str, Enum):
    READ_ONLY = "READ_ONLY"
    VIEWER = "READ_ONLY"
    OPERATOR = "OPERATOR"
    ADMIN = "ADMIN"


class AuthSessionStatus(str, Enum):
    UNAUTHENTICATED = "UNAUTHENTICATED"
    AUTHENTICATED = "AUTHENTICATED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class SessionHandshakeRequest(BaseModel):
    client_name: str = Field(default="AURA Web Dashboard", description="Client identifier")
    client_version: str = Field(default="1.0.0")
    requested_scope: AuthScope = Field(default=AuthScope.OPERATOR)


class SessionHandshakeResponse(BaseModel):
    status: AuthSessionStatus
    session_id: str
    scope: AuthScope
    expires_at: str | None = None
    server_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuthTokenClaims(BaseModel):
    token_id: str
    issued_to: str
    scope: AuthScope
    issued_at: str
    expires_at: str | None = None
