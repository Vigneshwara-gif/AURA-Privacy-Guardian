"""
Configuration settings for AURA Cloud Service.
"""

from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CloudConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AURA_CLOUD_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=int(os.environ.get("PORT", "8000")), ge=1, le=65535)
    database_path: str = Field(default=str(Path("data/aura_cloud.db").resolve()))
    jwt_secret: str = Field(default="aura_cloud_dev_secret_change_in_production")
    pairing_ttl_seconds: int = Field(default=600, ge=60, le=3600)
    session_ttl_hours: float = Field(default=72.0, ge=1.0)
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "*",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            "https://aura-privacy-guardian.vercel.app",
        ]
    )


_cloud_config_instance: CloudConfig | None = None


def get_cloud_config() -> CloudConfig:
    global _cloud_config_instance
    if _cloud_config_instance is None:
        _cloud_config_instance = CloudConfig()
    return _cloud_config_instance
