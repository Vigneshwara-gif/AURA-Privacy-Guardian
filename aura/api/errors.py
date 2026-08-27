"""
Exception classes and FastAPI error handlers for AURA API.

Guarantees:
  - Zero raw tracebacks, internal file paths, or DB query errors leaked to clients.
  - Uniform ApiErrorResponse schemas across all failure modes.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from aura.contracts.errors import ApiErrorResponse, ErrorCode

logger = logging.getLogger(__name__)


class AuraApiException(Exception):
    """Base exception for all AURA API errors."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class AuthenticationError(AuraApiException):
    def __init__(self, message: str = "Authentication required or credentials invalid", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationError(AuraApiException):
    def __init__(self, message: str = "Insufficient permissions for this operation", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class NotFoundError(AuraApiException):
    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class RateLimitError(AuraApiException):
    def __init__(self, message: str = "Rate limit exceeded. Please retry later.", retry_after: int = 60) -> None:
        super().__init__(
            code=ErrorCode.RATE_LIMITED,
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after_seconds": retry_after},
        )


class StorageUnavailableError(AuraApiException):
    def __init__(self, message: str = "Storage subsystem is temporarily unavailable", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code=ErrorCode.STORAGE_ERROR,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


async def aura_api_exception_handler(request: Request, exc: AuraApiException) -> JSONResponse:
    """Handle explicit AURA API exceptions."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    payload = ApiErrorResponse(
        code=exc.code,
        message=exc.message,
        timestamp=datetime.now(timezone.utc).isoformat(),
        correlation_id=correlation_id,
        details=exc.details,
    )
    headers = {}
    if exc.code == ErrorCode.RATE_LIMITED and exc.details and "retry_after_seconds" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after_seconds"])
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump(), headers=headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle schema validation failures with clean sanitization."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    sanitized_errors = []
    for err in exc.errors():
        loc = " -> ".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        sanitized_errors.append(f"{loc}: {msg}")

    payload = ApiErrorResponse(
        code=ErrorCode.INVALID_REQUEST,
        message="Request validation failed",
        timestamp=datetime.now(timezone.utc).isoformat(),
        correlation_id=correlation_id,
        details={"validation_errors": sanitized_errors},
    )
    return JSONResponse(status_code=422, content=payload.model_dump())


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle generic Starlette/FastAPI HTTP exceptions."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    code_map = {
        400: ErrorCode.INVALID_REQUEST,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        405: ErrorCode.INVALID_REQUEST,
        429: ErrorCode.RATE_LIMITED,
        500: ErrorCode.INTERNAL_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE,
    }
    error_code = code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    payload = ApiErrorResponse(
        code=error_code,
        message=str(exc.detail) if exc.detail else "HTTP error occurred",
        timestamp=datetime.now(timezone.utc).isoformat(),
        correlation_id=correlation_id,
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled server exceptions to prevent traceback leakage."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    logger.exception("Unhandled server exception [correlation_id=%s]: %s", correlation_id, exc)
    payload = ApiErrorResponse(
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal server error occurred. Diagnostics logged with correlation ID.",
        timestamp=datetime.now(timezone.utc).isoformat(),
        correlation_id=correlation_id,
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload.model_dump())
