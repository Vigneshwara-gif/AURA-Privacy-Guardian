"""
Feature Extraction Pipeline for AURA Multi-Signal ML & Behavioral Scoring.

Extracts normalized, inspectable numerical feature vectors across:
  - Host & Process CPU/Memory dynamics
  - Network throughput & remote socket diversity
  - Hardware privacy sentinel states (Camera/Microphone)
  - Security posture & persistence churn
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any
import numpy as np

from aura.models.types import TelemetryData
from aura.sensors.security_posture import WindowsSecurityPostureSnapshot

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "cpu_percent",
    "memory_percent",
    "net_upload_kbps",
    "net_download_kbps",
    "established_connections",
    "remote_connections",
    "process_count",
    "camera_active",
    "microphone_active",
    "security_posture_score",
]


@dataclass(slots=True)
class FeatureVector:
    """Extracted normalized numerical feature vector with provenance metadata."""
    timestamp: str
    feature_names: list[str]
    raw_values: list[float]
    normalized_values: list[float]

    def to_numpy(self) -> np.ndarray:
        """Return 2D numpy array suitable for scikit-learn estimators [1, n_features]."""
        return np.array([self.normalized_values], dtype=np.float64)

    def to_dict(self) -> dict[str, Any]:
        """Convert to inspectable dictionary mapping feature names to values."""
        return {
            "timestamp": self.timestamp,
            "features": dict(zip(self.feature_names, self.raw_values)),
            "normalized": dict(zip(self.feature_names, self.normalized_values)),
        }


class FeatureExtractionPipeline:
    """Transforms raw system telemetry into scaled, deterministic feature representations."""

    # Nominal maximum scale bounds for min-max normalization
    MAX_SCALES = {
        "cpu_percent": 100.0,
        "memory_percent": 100.0,
        "net_upload_kbps": 50000.0,  # 50 MB/s
        "net_download_kbps": 100000.0,  # 100 MB/s
        "established_connections": 500.0,
        "remote_connections": 250.0,
        "process_count": 1000.0,
        "camera_active": 1.0,
        "microphone_active": 1.0,
        "security_posture_score": 100.0,
    }

    @classmethod
    def extract_features(
        cls,
        telemetry: TelemetryData,
        security_posture: WindowsSecurityPostureSnapshot | None = None,
    ) -> FeatureVector:
        """Extract deterministic feature vector from live telemetry and posture."""
        now_iso = datetime.now(timezone.utc).isoformat()

        cam_active = 1.0 if str(telemetry.camera_status).upper() == "ACTIVE" else 0.0
        mic_active = 1.0 if str(telemetry.microphone_status).upper() == "ACTIVE" else 0.0

        posture_score = float(security_posture.overall_posture_score) if security_posture else 100.0

        raw_map: dict[str, float] = {
            "cpu_percent": float(telemetry.cpu_percent),
            "memory_percent": float(telemetry.memory_percent),
            "net_upload_kbps": float(telemetry.net_upload_kbps),
            "net_download_kbps": float(telemetry.net_download_kbps),
            "established_connections": float(telemetry.established_connections),
            "remote_connections": float(telemetry.remote_connections),
            "process_count": float(telemetry.process_count),
            "camera_active": cam_active,
            "microphone_active": mic_active,
            "security_posture_score": posture_score,
        }

        raw_values = [raw_map[name] for name in FEATURE_NAMES]
        norm_values = [
            max(0.0, min(1.0, raw_map[name] / cls.MAX_SCALES.get(name, 1.0)))
            for name in FEATURE_NAMES
        ]

        return FeatureVector(
            timestamp=now_iso,
            feature_names=list(FEATURE_NAMES),
            raw_values=raw_values,
            normalized_values=norm_values,
        )
