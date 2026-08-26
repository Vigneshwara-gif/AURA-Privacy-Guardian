"""
Hardened, Explainable Risk Assessment Engine for AURA.

Computes bounded (0–100), deterministic risk scores with full data provenance,
structured contributor attribution, anti-double-counting guards, and explicit
sensor degradation accounting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any

from aura.engine.baseline import BaselineState, MetricAssessment
from aura.engine.correlation import CorrelatedInsight, CorrelationCategory
from aura.models.types import PrivacyHardwareStatus, TelemetrySnapshot

logger = logging.getLogger(__name__)


@dataclass
class RiskContributor:
    """Individual explainable contributor to the overall risk score."""

    signal: str
    source: str
    points: int
    severity: str
    reason: str
    observed_value: Any
    baseline_reference: Any | None
    reliability: float  # 0.0 to 1.0


@dataclass
class HardenedRiskResult:
    """Complete, transparent risk evaluation result."""

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
    """Deterministic, explainable risk calculation engine."""

    @staticmethod
    def evaluate(
        snapshot: TelemetrySnapshot,
        assessments: dict[str, MetricAssessment],
        insights: list[CorrelatedInsight],
        ml_anomaly: bool = False,
        ml_intensity: float = 0.0,
    ) -> HardenedRiskResult:
        """
        Evaluate composite risk with strict attribution and anti-double-counting.
        """
        contributors: list[RiskContributor] = []
        reasons: list[str] = []
        privacy_flags: list[str] = []
        compound_exfiltration = False
        is_degraded = False

        # 1. Check for sensor degradation
        degraded_sensors = [
            r.name for r in snapshot.sensor_health if r.status.value in ("DEGRADED", "ERROR", "PERMISSION_LIMITED")
        ]
        if degraded_sensors:
            is_degraded = True
            reasons.append(f"Sensors operating with reduced fidelity: {', '.join(degraded_sensors)}.")

        # 2. Process Correlated Insights
        covered_metrics = set()
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
            elif ins.category == CorrelationCategory.NETWORK_EXFILTRATION_RISK:
                privacy_flags.append("elevated_outbound_network")

            for ev in ins.evidence_chain:
                covered_metrics.add(ev.signal_name.lower())

        # 3. Process ML Anomaly (with Anti-Double-Counting Dampening)
        if ml_anomaly:
            # If correlated insights already covered the anomaly, dampen the raw ML weight to avoid double counting
            ml_points = 10 if ("network upload burst" in covered_metrics or "cpu anomaly" in covered_metrics) else 25
            contributors.append(
                RiskContributor(
                    signal="Isolation Forest Anomaly",
                    source="AURAModel (Unsupervised ML)",
                    points=ml_points,
                    severity="MEDIUM",
                    reason="Multi-dimensional host feature vector falls outside the baseline isolation envelope.",
                    observed_value=f"Intensity: {ml_intensity:.2f}",
                    baseline_reference="Trained Isolation Forest Baseline",
                    reliability=0.80,
                )
            )
            reasons.append("Unsupervised ML detected a multi-feature anomaly.")

        # 4. Aggregate Score
        raw_score = sum(c.points for c in contributors)
        bounded_score = max(0.0, min(100.0, float(raw_score)))

        # 5. Determine Severity
        if bounded_score >= 80.0:
            severity = "CRITICAL"
        elif bounded_score >= 55.0:
            severity = "HIGH"
        elif bounded_score >= 25.0:
            severity = "MEDIUM"
        elif bounded_score >= 10.0:
            severity = "LOW"
        else:
            severity = "NORMAL"

        summary = (
            f"{severity} Risk ({bounded_score:.0f}/100) — "
            + (reasons[0] if reasons else "Nominal host telemetry within baseline.")
        )

        return HardenedRiskResult(
            risk_score=bounded_score,
            severity=severity,
            is_degraded=is_degraded,
            reasons=reasons if reasons else ["System telemetry operating within learned baseline."],
            contributors=contributors,
            privacy_flags=privacy_flags,
            compound_exfiltration_flag=compound_exfiltration,
            summary=summary,
        )
