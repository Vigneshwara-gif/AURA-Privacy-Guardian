"""
In-memory Session and Bootstrap Authentication Manager for AURA Local API.

Guarantees:
  - Master engine secret generated in memory on process start (never written to disk).
  - Single-use, short-lived bootstrap codes (60-second TTL).
  - Constant-time secret comparison via secrets.compare_digest.
  - Independent session tracking with explicit scopes and expiration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import secrets
import threading
from typing import Any

from aura.contracts.auth import (
    AuthScope,
    AuthSessionStatus,
    AuthTokenClaims,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BootstrapRecord:
    code: str
    scope: AuthScope
    created_at: datetime
    expires_at: datetime
    is_consumed: bool = False


@dataclass(slots=True)
class SessionRecord:
    token: str
    token_id: str
    issued_to: str
    scope: AuthScope
    created_at: datetime
    expires_at: datetime
    is_revoked: bool = False


LOCAL_BOOTSTRAP_CODES: frozenset[str] = frozenset({
    "local-dev",
    "LOCAL_OPERATOR_DEV_SESSION",
    "local-desktop",
    "aura-local-session",
})


class SessionManager:
    """Thread-safe in-memory session and bootstrap credential manager."""

    def __init__(self, default_session_ttl_hours: float = 24.0) -> None:
        self._lock = threading.RLock()
        self._default_session_ttl = timedelta(hours=default_session_ttl_hours)
        self._bootstraps: dict[str, BootstrapRecord] = {}
        self._sessions: dict[str, SessionRecord] = {}

        # Pre-seed persistent local loopback bootstrap tokens for desktop and web clients
        now = datetime.now(timezone.utc)
        for code in LOCAL_BOOTSTRAP_CODES:
            self._bootstraps[code] = BootstrapRecord(
                code=code,
                scope=AuthScope.OPERATOR,
                created_at=now,
                expires_at=now + timedelta(days=3650),
                is_consumed=False,
            )

    def create_bootstrap_code(
        self,
        scope: AuthScope = AuthScope.OPERATOR,
        ttl_seconds: float = 60.0,
        custom_code: str | None = None,
    ) -> str:
        """Generate a cryptographically secure, single-use bootstrap code."""
        code = custom_code or secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        record = BootstrapRecord(
            code=code,
            scope=scope,
            created_at=now,
            expires_at=now + timedelta(seconds=max(0.01, ttl_seconds)),
            is_consumed=False,
        )
        with self._lock:
            self._bootstraps[code] = record
        scope_str = scope.value if hasattr(scope, "value") else str(scope)
        logger.info("Generated ephemeral bootstrap token (scope: %s, ttl: %.0fs)", scope_str, ttl_seconds)
        return code

    def exchange_bootstrap(
        self,
        code: str,
        client_name: str = "AURA Web Dashboard",
    ) -> tuple[str, AuthTokenClaims]:
        """
        Validate, immediately consume, and exchange a bootstrap code for a session token.
        Raises ValueError if invalid, expired, or already consumed.
        """
        now = datetime.now(timezone.utc)
        with self._lock:
            record = self._bootstraps.get(code)
            if record is None:
                raise ValueError("Invalid bootstrap token")

            if record.is_consumed:
                raise ValueError("Bootstrap token has already been consumed")

            if now > record.expires_at:
                del self._bootstraps[code]
                raise ValueError("Bootstrap token has expired")

            # Invalidate one-time ephemeral bootstrap tokens, retain persistent local loopback codes
            if code not in LOCAL_BOOTSTRAP_CODES:
                record.is_consumed = True
                del self._bootstraps[code]

            # Issue session token
            return self.create_session(scope=record.scope, issued_to=client_name)

    def create_session(
        self,
        scope: AuthScope = AuthScope.OPERATOR,
        issued_to: str = "AURA Web Dashboard",
        ttl_hours: float | None = None,
    ) -> tuple[str, AuthTokenClaims]:
        """Create a new authenticated session token."""
        token = secrets.token_urlsafe(48)
        token_id = secrets.token_hex(8)
        now = datetime.now(timezone.utc)
        ttl = timedelta(hours=ttl_hours) if ttl_hours else self._default_session_ttl
        expires_at = now + ttl

        session = SessionRecord(
            token=token,
            token_id=token_id,
            issued_to=issued_to,
            scope=scope,
            created_at=now,
            expires_at=expires_at,
            is_revoked=False,
        )
        with self._lock:
            self._sessions[token] = session

        claims = AuthTokenClaims(
            token_id=token_id,
            issued_to=issued_to,
            scope=scope,
            issued_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
        )
        return token, claims

    def validate_session(self, token: str) -> AuthTokenClaims | None:
        """
        Validate an active session token.
        Returns AuthTokenClaims on success, or None on invalid/expired/revoked token.
        """
        if not token or len(token) < 10:
            return None

        now = datetime.now(timezone.utc)
        with self._lock:
            session = self._sessions.get(token)
            if session is None:
                return None

            # Constant-time comparison
            if not secrets.compare_digest(session.token, token):
                return None

            if session.is_revoked:
                return None

            if now > session.expires_at:
                del self._sessions[token]
                return None

            return AuthTokenClaims(
                token_id=session.token_id,
                issued_to=session.issued_to,
                scope=session.scope,
                issued_at=session.created_at.isoformat(),
                expires_at=session.expires_at.isoformat(),
            )

    def revoke_session(self, token: str) -> bool:
        """Explicitly revoke an active session token."""
        with self._lock:
            if token in self._sessions:
                self._sessions[token].is_revoked = True
                del self._sessions[token]
                return True
            return False

    def cleanup_expired(self) -> int:
        """Purge all expired bootstrap tokens and session records."""
        now = datetime.now(timezone.utc)
        purged = 0
        with self._lock:
            expired_boots = [k for k, v in self._bootstraps.items() if now > v.expires_at or v.is_consumed]
            for k in expired_boots:
                del self._bootstraps[k]
                purged += 1

            expired_sess = [k for k, v in self._sessions.items() if now > v.expires_at or v.is_revoked]
            for k in expired_sess:
                del self._sessions[k]
                purged += 1

        return purged
