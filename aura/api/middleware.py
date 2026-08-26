"""
Security middleware for Host header protection, correlation IDs, and origin validation.
"""

from __future__ import annotations

import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

ALLOWED_LOOPBACK_HOSTS = frozenset({
    "127.0.0.1",
    "localhost",
    "127.0.0.1:8787",
    "localhost:8787",
    "[::1]",
    "[::1]:8787",
    "testserver",  # Starlette TestClient default
})


class HostHeaderGuardMiddleware(BaseHTTPMiddleware):
    """
    Guards against DNS Rebinding attacks by rejecting any request
    whose Host header does not match authorized loopback hostnames.
    """

    def __init__(self, app: Any, allowed_hosts: set[str] | frozenset[str] = ALLOWED_LOOPBACK_HOSTS) -> None:
        super().__init__(app)
        self.allowed_hosts = allowed_hosts

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        host = request.headers.get("host", "").strip().lower()
        base_host = host.split(":", 1)[0].strip("[]")
        is_allowed = (
            host in self.allowed_hosts
            or base_host in {"127.0.0.1", "localhost", "::1", "testserver"}
        )
        if not host or not is_allowed:
            logger.warning("Rejected suspicious Host header: %r from client: %s", host, request.client)
            return JSONResponse(
                status_code=400,
                content={
                    "code": "INVALID_REQUEST",
                    "message": f"Invalid Host header: {host!r}. Only local loopback connections are permitted.",
                },
            )

        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response
