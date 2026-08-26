"""
FastAPI application factory and server startup configuration for AURA Local API.
"""

from __future__ import annotations

import logging
import mimetypes
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

# Explicitly register standard MIME types to prevent Windows Registry from serving .js as text/plain
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")

from aura.api.auth import SessionManager
from aura.api.errors import (
    AuraApiException,
    aura_api_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from aura.api.middleware import HostHeaderGuardMiddleware
from aura.api.ratelimit import RateLimiter
from aura.api.router import router
from aura.api.stream import StreamManager
from aura.core.config import Settings, get_settings
from aura.engine.service import AuraEngineService
from aura.storage.sqlite import StorageEngine

logger = logging.getLogger(__name__)


def create_app(
    engine: AuraEngineService,
    storage: StorageEngine,
    settings: Settings | None = None,
    session_manager: SessionManager | None = None,
    stream_manager: StreamManager | None = None,
    rate_limiter: RateLimiter | None = None,
) -> FastAPI:
    """
    Construct and configure the FastAPI application for AURA Local API.
    """
    cfg = settings or get_settings()

    app = FastAPI(
        title="AURA Local API Gateway",
        version="1.0.0",
        description="Localhost authenticated REST & WebSocket API for AURA Privacy Guardian",
        docs_url="/docs" if cfg.docs_are_enabled() else None,
        redoc_url=None,
    )

    # Injected state instances
    app.state.engine = engine
    app.state.storage = storage
    app.state.settings = cfg
    app.state.session_manager = session_manager or SessionManager()
    app.state.stream_manager = stream_manager or StreamManager()
    app.state.rate_limiter = rate_limiter or RateLimiter()

    # 1. Host Header Guard (DNS Rebinding mitigation)
    app.add_middleware(HostHeaderGuardMiddleware)

    # 2. Strict CORS policy
    allowed_origins = list(cfg.api.cors_origins) or ["http://127.0.0.1:5173", "http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # 3. Exception handlers mapping to ApiErrorResponse
    app.add_exception_handler(AuraApiException, aura_api_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 4. Mount API Routes
    app.include_router(router)

    # 5. Mount Static Web Dashboard (Local Delivery)
    from aura.core.paths import get_paths
    paths = get_paths()
    if paths.web_dir.exists() and (paths.web_dir / "index.html").exists():
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=str(paths.web_dir), html=True), name="web_dashboard")

    return app
