"""
FastAPI application factory for AURA Cloud Service.
"""

from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aura.cloud.config import CloudConfig, get_cloud_config
from aura.cloud.storage import CloudStorage
from aura.cloud.relay import CloudTelemetryRelay
from aura.cloud.router import cloud_router

logger = logging.getLogger(__name__)


def create_cloud_app(
    config: CloudConfig | None = None,
    storage: CloudStorage | None = None,
    relay: CloudTelemetryRelay | None = None,
) -> FastAPI:
    cfg = config or get_cloud_config()
    db = storage or CloudStorage(cfg.database_path)
    tel_relay = relay or CloudTelemetryRelay()

    app = FastAPI(
        title="AURA Cloud API",
        version="2.0.0",
        description="Production Multi-Tenant Cloud Platform for AURA Privacy Guardian",
        docs_url="/docs",
        redoc_url=None,
    )

    app.state.cloud_config = cfg
    app.state.cloud_storage = db
    app.state.telemetry_relay = tel_relay

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(cloud_router)

    return app


app = create_cloud_app()
