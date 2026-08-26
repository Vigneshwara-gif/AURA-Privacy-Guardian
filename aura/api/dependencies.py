"""
FastAPI dependency injection providers for engine, storage, auth, and rate limiting.
"""

from __future__ import annotations

from typing import Callable
from fastapi import Depends, Header, Query
from starlette.requests import HTTPConnection, Request

from aura.api.auth import SessionManager
from aura.api.errors import AuthenticationError, AuthorizationError, RateLimitError
from aura.api.ratelimit import RateLimiter
from aura.api.stream import StreamManager
from aura.contracts.auth import AuthScope, AuthTokenClaims
from aura.engine.service import AuraEngineService
from aura.storage.sqlite import StorageEngine


async def get_engine(conn: HTTPConnection) -> AuraEngineService:
    """Retrieve injected AuraEngineService from application state."""
    return conn.app.state.engine


async def get_storage(conn: HTTPConnection) -> StorageEngine:
    """Retrieve injected StorageEngine from application state."""
    return conn.app.state.storage


async def get_session_manager(conn: HTTPConnection) -> SessionManager:
    """Retrieve injected SessionManager from application state."""
    return conn.app.state.session_manager


async def get_stream_manager(conn: HTTPConnection) -> StreamManager:
    """Retrieve injected StreamManager from application state."""
    return conn.app.state.stream_manager


async def get_rate_limiter(conn: HTTPConnection) -> RateLimiter:
    """Retrieve injected RateLimiter from application state."""
    return conn.app.state.rate_limiter


async def get_current_claims(
    conn: HTTPConnection,
    authorization: str | None = Header(default=None),
    token_query: str | None = Query(default=None, alias="token"),
    session_manager: SessionManager = Depends(get_session_manager),
) -> AuthTokenClaims:
    """
    Extract and validate Bearer session token from Authorization header or ?token= query.
    """
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization[7:].strip()
    elif token_query:
        raw_token = token_query.strip()

    if not raw_token:
        raise AuthenticationError("Authorization header with Bearer token is required")

    claims = session_manager.validate_session(raw_token)
    if claims is None:
        raise AuthenticationError("Session token is invalid or has expired")

    if hasattr(conn, "state"):
        conn.state.claims = claims
    return claims


def require_scope(required_scope: AuthScope) -> Callable[[AuthTokenClaims], AuthTokenClaims]:
    """
    FastAPI dependency enforcing RBAC hierarchy: ADMIN >= OPERATOR >= READ_ONLY.
    """
    scope_hierarchy = {
        AuthScope.READ_ONLY: 1,
        AuthScope.OPERATOR: 2,
        AuthScope.ADMIN: 3,
    }

    async def scope_checker(claims: AuthTokenClaims = Depends(get_current_claims)) -> AuthTokenClaims:
        user_level = scope_hierarchy.get(claims.scope, 0)
        req_level = scope_hierarchy.get(required_scope, 99)

        if user_level < req_level:
            raise AuthorizationError(
                f"Operation requires scope '{required_scope.value}', but token has scope '{claims.scope.value}'"
            )
        return claims

    return scope_checker
