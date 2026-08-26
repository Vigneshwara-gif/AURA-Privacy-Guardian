"""
Multi-Signal Correlation and Privacy Threat Intelligence Engine for AURA.

Combines independent observations across hardware sentinels, process trees,
network connections, and statistical behavioral baselines into an explainable,
anti-double-counting correlation graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any
import uuid

from aura.engine.baseline import BaselineState, MetricAssessment
from aura.models.types import PrivacyHardwareStatus, TelemetrySnapshot
from aura.sensors.network_intel import ConnectionInfo, SocketCategory
from aura.sensors.process_intel import ConfidenceLevel, ProcessInfo

logger = logging.getLogger(__name__)


class CorrelationCategory(str, Enum):
    """Categorization of correlated security signals."""

    PRIVACY_ANOMALY = "PRIVACY_ANOMALY"
    RESOURCE_BURST = "RESOURCE_BURST"
    NETWORK_EXFILTRATION_RISK = "NETWORK_EXFILTRATION_RISK"
    HOST_ANOMALY = "HOST_ANOMALY"
    NOMINAL = "NOMINAL"


@dataclass
class EvidenceSignal:
    """Individual measured evidence signal within a correlation chain."""

    signal_name: str
    observed_value: Any
    baseline_value: Any | None
    unit: str | None
    weight: int
    severity: str
    confidence: ConfidenceLevel
    provenance_detail: str


@dataclass
class CorrelatedInsight:
    """Strongly typed multi-signal correlated security insight."""

    correlation_id: str
    category: CorrelationCategory
    title: str
    severity: str
    total_risk_contribution: int
    primary_signal: str
    contributing_signals: list[str]
    evidence_chain: list[EvidenceSignal]
    explanation: str
    recommendation: str
    is_compound: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MultiSignalCorrelator:
    """
    Evaluates telemetry snapshots, baseline assessments, process lists,
    and socket tables to produce correlated, explainable security insights.
    """

    def __init__(self, time_window_seconds: int = 60) -> None:
        self.time_window_seconds = time_window_seconds
        self._recent_anomalies: list[dict[str, Any]] = []

    def correlate(
        self,
        snapshot: TelemetrySnapshot,
        assessments: dict[str, MetricAssessment],
        top_processes: list[ProcessInfo] | None = None,
        connections: list[ConnectionInfo] | None = None,
    ) -> list[CorrelatedInsight]:
        """
        Perform multi-signal correlation with strict anti-double-counting.
        """
        insights: list[CorrelatedInsight] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # Extract primary signals
        cpu_ass = assessments.get("cpu_percent")
        net_up_ass = assessments.get("net_upload_kbps")
        proc_ass = assessments.get("process_count")
        sock_ass = assessments.get("remote_connections")

        cam_active = snapshot.camera_status == PrivacyHardwareStatus.AVAILABLE
        mic_active = snapshot.microphone_status == PrivacyHardwareStatus.AVAILABLE

        net_upload_anom = net_up_ass.is_anomaly if net_up_ass else False
        cpu_anom = cpu_ass.is_anomaly if cpu_ass else False
        proc_anom = proc_ass.is_anomaly if proc_ass else False
        sock_anom = sock_ass.is_anomaly if sock_ass else False

        # Count active remote WAN public connections
        remote_wan_count = 0
        if connections:
            remote_wan_count = sum(1 for c in connections if c.category == SocketCategory.REMOTE_PUBLIC)

        # ----------------------------------------------------
        # Rule 1: Privacy Hardware + High Outbound WAN Burst (Compound)
        # ----------------------------------------------------
        if (cam_active or mic_active) and (net_upload_anom or snapshot.net_upload_kbps > 800.0):
            sensor_name = "Camera and Microphone" if (cam_active and mic_active) else "Camera" if cam_active else "Microphone"
            evidence = [
                EvidenceSignal(
                    signal_name=f"{sensor_name} Active",
                    observed_value="STREAMING / RECORDING",
                    baseline_value="INACTIVE / IDLE",
                    unit=None,
                    weight=20,
                    severity="HIGH",
                    confidence=ConfidenceLevel.OBSERVED,
                    provenance_detail=f"Windows endpoint probe verified active {sensor_name.lower()} state.",
                ),
                EvidenceSignal(
                    signal_name="Outbound Network Burst",
                    observed_value=round(snapshot.net_upload_kbps, 1),
                    baseline_value=round(net_up_ass.baseline_mean, 1) if net_up_ass and net_up_ass.baseline_mean else None,
                    unit="KB/s",
                    weight=15,
                    severity="HIGH",
                    confidence=ConfidenceLevel.OBSERVED,
                    provenance_detail=f"Measured outbound rate of {snapshot.net_upload_kbps:.1f} KB/s exceeds host baseline envelope.",
                ),
            ]

            insights.append(
                CorrelatedInsight(
                    correlation_id=str(uuid.uuid4()),
                    category=CorrelationCategory.PRIVACY_ANOMALY,
                    title="Potential Privacy-Related Anomaly",
                    severity="HIGH",
                    total_risk_contribution=35,
                    primary_signal=f"{sensor_name} Active + Outbound Network Spike",
                    contributing_signals=["Privacy Hardware Sentinel", "Network Throughput Sentinel"],
                    evidence_chain=evidence,
                    explanation=(
                        f"Active {sensor_name.lower()} stream correlated with a contemporaneous "
                        f"outbound network throughput spike of {snapshot.net_upload_kbps:.1f} KB/s."
                    ),
                    recommendation="Inspect recently active conferencing or background applications in Task Manager.",
                    is_compound=True,
                    timestamp=now_iso,
                )
            )

        # ----------------------------------------------------
        # Rule 2: Multi-Resource Compute + Network Anomaly (Compound)
        # ----------------------------------------------------
        elif cpu_anom and net_upload_anom and not (cam_active or mic_active):
            evidence = [
                EvidenceSignal(
                    signal_name="CPU Anomaly",
                    observed_value=round(snapshot.cpu_percent, 1),
                    baseline_value=round(cpu_ass.baseline_mean, 1) if cpu_ass and cpu_ass.baseline_mean else None,
                    unit="%",
                    weight=12,
                    severity="MEDIUM",
                    confidence=ConfidenceLevel.OBSERVED,
                    provenance_detail=f"CPU load ({snapshot.cpu_percent:.1f}%) is {cpu_ass.z_score:+.1f}σ from mean." if cpu_ass and cpu_ass.z_score else "",
                ),
                EvidenceSignal(
                    signal_name="Network Upload Anomaly",
                    observed_value=round(snapshot.net_upload_kbps, 1),
                    baseline_value=round(net_up_ass.baseline_mean, 1) if net_up_ass and net_up_ass.baseline_mean else None,
                    unit="KB/s",
                    weight=13,
                    severity="MEDIUM",
                    confidence=ConfidenceLevel.OBSERVED,
                    provenance_detail=f"Upload rate ({snapshot.net_upload_kbps:.1f} KB/s) is {net_up_ass.z_score:+.1f}σ from mean." if net_up_ass and net_up_ass.z_score else "",
                ),
            ]

            insights.append(
                CorrelatedInsight(
                    correlation_id=str(uuid.uuid4()),
                    category=CorrelationCategory.RESOURCE_BURST,
                    title="Correlated Compute & Network Anomaly",
                    severity="MEDIUM",
                    total_risk_contribution=25,
                    primary_signal="Simultaneous High CPU & Network Upload",
                    contributing_signals=["CPU Utilization", "Network Upload Rate"],
                    evidence_chain=evidence,
                    explanation="Host experienced concurrent spikes in compute processing and outbound network traffic.",
                    recommendation="Review high-CPU processes in the System Activity tab.",
                    is_compound=True,
                    timestamp=now_iso,
                )
            )

        # ----------------------------------------------------
        # Rule 3: Single-Signal Outbound Network Surge (Isolated)
        # ----------------------------------------------------
        elif net_upload_anom and not (cam_active or mic_active):
            evidence = [
                EvidenceSignal(
                    signal_name="Network Upload Spike",
                    observed_value=round(snapshot.net_upload_kbps, 1),
                    baseline_value=round(net_up_ass.baseline_mean, 1) if net_up_ass and net_up_ass.baseline_mean else None,
                    unit="KB/s",
                    weight=18,
                    severity="LOW" if snapshot.net_upload_kbps < 2000 else "MEDIUM",
                    confidence=ConfidenceLevel.OBSERVED,
                    provenance_detail=f"Upload rate ({snapshot.net_upload_kbps:.1f} KB/s) deviates significantly from learned baseline.",
                )
            ]

            insights.append(
                CorrelatedInsight(
                    correlation_id=str(uuid.uuid4()),
                    category=CorrelationCategory.NETWORK_EXFILTRATION_RISK,
                    title="Elevated Outbound Network Activity",
                    severity="LOW" if snapshot.net_upload_kbps < 2000 else "MEDIUM",
                    total_risk_contribution=18,
                    primary_signal="Outbound Network Throughput",
                    contributing_signals=["Network Interface Sentinel"],
                    evidence_chain=evidence,
                    explanation=f"Outbound network throughput reached {snapshot.net_upload_kbps:.1f} KB/s without associated privacy hardware activity.",
                    recommendation="Verify active cloud backup, file sync, or browser upload tasks.",
                    is_compound=False,
                    timestamp=now_iso,
                )
            )

        # ----------------------------------------------------
        # Rule 4: Process Table Anomaly (Rapid Expansion)
        # ----------------------------------------------------
        if proc_anom:
            evidence = [
                EvidenceSignal(
                    signal_name="Process Count Anomaly",
                    observed_value=snapshot.process_count,
                    baseline_value=round(proc_ass.baseline_mean, 0) if proc_ass and proc_ass.baseline_mean else None,
                    unit="processes",
                    weight=12,
                    severity="LOW",
                    confidence=ConfidenceLevel.OBSERVED,
                    provenance_detail=f"Total running processes ({snapshot.process_count}) is {proc_ass.z_score:+.1f}σ above baseline." if proc_ass and proc_ass.z_score else "",
                )
            ]

            insights.append(
                CorrelatedInsight(
                    correlation_id=str(uuid.uuid4()),
                    category=CorrelationCategory.HOST_ANOMALY,
                    title="Process Count Expansion",
                    severity="LOW",
                    total_risk_contribution=12,
                    primary_signal="Process Table Expansion",
                    contributing_signals=["Process Table Sentinel"],
                    evidence_chain=evidence,
                    explanation=f"Active process count ({snapshot.process_count}) is significantly higher than typical baseline.",
                    recommendation="Review newly launched applications.",
                    is_compound=False,
                    timestamp=now_iso,
                )
            )

        return insights
