"""
Behavioral Baseline & Explainable AI Anomaly Engine.

Provides transparent, evidence-backed explanations for Isolation Forest
and Local Outlier Factor (LOF) multi-model anomaly scoring without black-box metrics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any

from aura.engine.anomaly_ensemble import AnomalyDetectionEnsemble, AnomalyEnsembleResult
from aura.engine.features import FeatureExtractionPipeline, FeatureVector
from aura.models.types import TelemetryData
from aura.sensors.security_posture import WindowsSecurityPostureSnapshot

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FeatureExplanation:
    feature_name: str
    observed_raw: float
    observed_normalized: float
    nominal_range_min: float
    nominal_range_max: float
    is_outlier: bool
    contribution_weight: float
    explanation_text: str


@dataclass(slots=True)
class AnomalyExplanationReport:
    timestamp: str
    is_anomaly: bool
    combined_score: float
    isolation_forest_score: float
    lof_score: float
    confidence: float
    primary_signal: str | None
    feature_explanations: list[FeatureExplanation]
    narrative: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "is_anomaly": self.is_anomaly,
            "combined_score": self.combined_score,
            "isolation_forest_score": self.isolation_forest_score,
            "lof_score": self.lof_score,
            "confidence": self.confidence,
            "primary_signal": self.primary_signal,
            "feature_explanations": [asdict(f) for f in self.feature_explanations],
            "narrative": self.narrative,
        }


class AIExplainabilityEngine:
    """Synthesizes human-interpretable technical explanations for ML anomaly decisions."""

    NOMINAL_BOUNDS = {
        "cpu_percent": (5.0, 75.0),
        "memory_percent": (20.0, 85.0),
        "net_upload_kbps": (0.0, 3000.0),
        "net_download_kbps": (0.0, 10000.0),
        "established_connections": (1, 150),
        "remote_connections": (0, 75),
        "process_count": (50, 400),
        "camera_active": (0.0, 0.0),
        "microphone_active": (0.0, 0.0),
        "security_posture_score": (80.0, 100.0),
    }

    @classmethod
    def explain(
        cls,
        telemetry: TelemetryData,
        ensemble: AnomalyDetectionEnsemble | None = None,
        posture: WindowsSecurityPostureSnapshot | None = None,
    ) -> AnomalyExplanationReport:
        ens = ensemble or AnomalyDetectionEnsemble()
        feat_vec = FeatureExtractionPipeline.extract_features(telemetry=telemetry, security_posture=posture)
        ml_res = ens.evaluate(feat_vec)

        explanations: list[FeatureExplanation] = []
        outlier_reasons: list[str] = []

        for name, raw_val, norm_val in zip(feat_vec.feature_names, feat_vec.raw_values, feat_vec.normalized_values):
            n_min, n_max = cls.NOMINAL_BOUNDS.get(name, (0.0, 100.0))
            is_outlier = raw_val > n_max or raw_val < n_min

            if is_outlier:
                if raw_val > n_max:
                    text = f"Observed {raw_val:.1f} exceeds upper nominal threshold ({n_max:.1f})"
                else:
                    text = f"Observed {raw_val:.1f} is below lower nominal threshold ({n_min:.1f})"
                outlier_reasons.append(f"{name.replace('_', ' ').title()} ({text})")
            else:
                text = f"Observed {raw_val:.1f} within expected host baseline envelope ({n_min:.1f} - {n_max:.1f})"

            explanations.append(
                FeatureExplanation(
                    feature_name=name,
                    observed_raw=raw_val,
                    observed_normalized=round(norm_val, 3),
                    nominal_range_min=n_min,
                    nominal_range_max=n_max,
                    is_outlier=is_outlier,
                    contribution_weight=round(norm_val * 0.1, 3),
                    explanation_text=text,
                )
            )

        if ml_res.is_anomaly:
            narrative = (
                f"Multi-model ML Ensemble classified this observation as ANOMALOUS (Ensemble Score: {ml_res.combined_anomaly_score:.2f}, "
                f"Isolation Forest: {ml_res.isolation_forest_score:.2f}, LOF: {ml_res.lof_score:.2f}). "
                f"Primary contributing signals: {', '.join(outlier_reasons) if outlier_reasons else 'Multi-signal compound vector divergence'}."
            )
        else:
            narrative = (
                f"Multi-model ML Ensemble classified this observation as NOMINAL (Ensemble Score: {ml_res.combined_anomaly_score:.2f}). "
                f"Host telemetry aligns with baseline behavioral envelope."
            )

        return AnomalyExplanationReport(
            timestamp=feat_vec.timestamp,
            is_anomaly=ml_res.is_anomaly,
            combined_score=ml_res.combined_anomaly_score,
            isolation_forest_score=ml_res.isolation_forest_score,
            lof_score=ml_res.lof_score,
            confidence=ml_res.confidence,
            primary_signal=ml_res.primary_outlier_signal,
            feature_explanations=explanations,
            narrative=narrative,
        )
