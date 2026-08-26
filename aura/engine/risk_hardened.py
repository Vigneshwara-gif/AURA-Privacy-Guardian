"""
Hardened, Explainable Risk Assessment Engine for AURA.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any

from aura.engine.baseline import BaselineState, MetricAssessment
from aura.engine.correlation import CorrelatedInsight, CorrelationCategory
from aura.models.types import PrivacyHardwareStatus, TelemetrySnapshot

logger = logging.getLogger(__name__)


@dataclass
class RiskContributor:
    signal: str
    source: str
    points: int
    severity: str
    reason: str
    observed_value: Any
    baseline_reference: Any | None
    reliability: float


@dataclass
class HardenedRiskResult:
    risk_score: float
    severity: str
    is_degraded: bool
    reasons: list[str]
    contributors: list[RiskContributor]
    privacy_flags: list[str]
    compound_exfiltration_flag: bool
    summary: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HardenedRiskEngine:
    @staticmethod
    def evaluate(
        snapshot: TelemetrySnapshot,
        assessments: dict[str, MetricAssessment],
        insights: list[CorrelatedInsight],
        ml_anomaly: bool = False,
        ml_intensity: float = 0.0,
    ) -> HardenedRiskResult:
        contributors: list[RiskContributor] = []
        reasons: list[str] = []
        privacy_flags: list[str] = []
        compound_exfiltration = False
        is_degraded = False

        # 1. Sensor degradation check
        degraded_sensors = [
            r.name for r in snapshot.sensor_health if r.status.value in ("DEGRADED", "ERROR", "PERMISSION_LIMITED")
        ]
        if degraded_sensors:
            is_degraded = True
            reasons.append(f"Sensors operating with reduced fidelity: {', '.join(degraded_sensors)}.")

        # 2. Correlated insights
        for ins in insights:
            contributors.append(
                RiskContributor(
                    signal=ins.title,
                    source="MultiSignalCorrelator",
                    points=ins.total_risk_contribution,
                    severity=ins.severity,
                    reason=ins.explanation,
                    observed_value=ins.primary_signal,
                    baseline_reference="Host Behavioral Baseline",
                    reliability=0.95,
                )
            )
            reasons.append(ins.explanation)
            if ins.category == CorrelationCategory.PRIVACY_ANOMALY:
                privacy_flags.append("potential_privacy_anomaly")
                compound_exfiltration = True

        # 3. Direct Camera & Microphone Active Usage Evaluation
        if snapshot.camera_status == PrivacyHardwareStatus.ACTIVE:
            cam_points = 35
            contributors.append(
                RiskContributor(
                    signal="Active Camera Capture",
                    source="Windows CapabilityAccessManager",
                    points=cam_points,
                    severity="HIGH",
                    reason="Camera video capture session currently active.",
                    observed_value="ACTIVE",
                    baseline_reference="INACTIVE",
                    reliability=1.0,
                )
            )
            reasons.append("Camera video stream is currently active.")
            privacy_flags.append("camera_active")

        if snapshot.microphone_status == PrivacyHardwareStatus.ACTIVE:
            mic_points = 30
            contributors.append(
                RiskContributor(
                    signal="Active Microphone Recording",
                    source="Windows CapabilityAccessManager",
                    points=mic_points,
                    severity="MEDIUM",
                    reason="Microphone audio capture session currently active.",
                    observed_value="ACTIVE",
                    baseline_reference="INACTIVE",
                    reliability=1.0,
                )
            )
            reasons.append("Microphone audio stream is currently active.")
            privacy_flags.append("microphone_active")

        # 4. ML Anomaly Model Evaluation (Isolation Forest + LOF)
        if ml_anomaly:
            ml_points = int(min(30, 15 + ml_intensity * 20))
            contributors.append(
                RiskContributor(
                    signal="Unsupervised Statistical Anomaly",
                    source="IsolationForest + LOF Ensemble",
                    points=ml_points,
                    severity="HIGH" if ml_intensity > 0.5 else "MEDIUM",
                    reason="Multi-dimensional telemetry vector deviates from trained baseline distribution.",
                    observed_value=f"Anomaly (intensity {ml_intensity:.2f})",
                    baseline_reference="Normal Distribution",
                    reliability=0.90,
                )
            )
            reasons.append("ML models detected unusual behavioral clustering.")

        # 5. Compound Data Exfiltration Flag
        if (snapshot.camera_status in {PrivacyHardwareStatus.AVAILABLE, PrivacyHardwareStatus.ACTIVE} or snapshot.microphone_status in {PrivacyHardwareStatus.AVAILABLE, PrivacyHardwareStatus.ACTIVE}) and snapshot.net_upload_kbps > 500.0:
            compound_exfiltration = True
            privacy_flags.append("potential_data_exfiltration")
            contributors.append(
                RiskContributor(
                    signal="Compound Privacy Exfiltration Vector",
                    source="AuraEngineService",
                    points=25,
                    severity="CRITICAL",
                    reason=f"Active hardware sensor concurrent with elevated outbound network bandwidth ({snapshot.net_upload_kbps:.1f} KB/s).",
                    observed_value=f"{snapshot.net_upload_kbps:.1f} KB/s",
                    baseline_reference="Baseline Network Threshold",
                    reliability=0.98,
                )
            )
            reasons.append("High-volume network transfer concurrent with active sensor session.")

        # Calculate Total Deterministic Risk Score
        total_points = sum(c.points for c in contributors)
        risk_score = float(max(0.0, min(100.0, total_points)))

        # Determine Severity Band
        if risk_score >= 90.0:
            severity = "CRITICAL"
        elif risk_score >= 70.0:
            severity = "HIGH"
        elif risk_score >= 45.0:
            severity = "MEDIUM"
        elif risk_score >= 15.0:
            severity = "LOW"
        else:
            severity = "NORMAL"

        if not reasons:
            reasons = ["Host behavior is within nominal baselines. No anomalous contributors detected."]
            summary = reasons[0]
        else:
            summary = f"Risk evaluated as {severity} ({risk_score:.0f}/100): {'; '.join(reasons[:2])}"

        return HardenedRiskResult(
            risk_score=risk_score,
            severity=severity,
            is_degraded=is_degraded,
            reasons=reasons,
            contributors=contributors,
            privacy_flags=privacy_flags,
            compound_exfiltration_flag=compound_exfiltration,
            summary=summary,
        )
