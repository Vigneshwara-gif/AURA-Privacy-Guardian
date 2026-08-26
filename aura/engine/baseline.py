"""
Dynamic Behavioral Baselines and Statistical Anomaly Detection Engine for AURA.

Implements online statistical tracking (Welford's streaming algorithm + EWMA)
with warm-up periods, outlier resistance, bounded memory, and explicit baseline states.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any
import logging

logger = logging.getLogger(__name__)


class BaselineState(str, Enum):
    """Explicit operational state of a behavioral baseline."""

    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NORMAL = "NORMAL"
    ANOMALOUS = "ANOMALOUS"
    DEGRADED = "DEGRADED"


@dataclass
class MetricAssessment:
    """Assessment result for a single telemetry metric against its baseline."""

    name: str
    state: BaselineState
    observed_value: float
    baseline_mean: float | None
    baseline_std: float | None
    z_score: float | None
    sample_count: int
    is_anomaly: bool
    deviation_factor: float
    detail: str


class MetricBaseline:
    """
    Online statistical baseline for a single numeric metric.
    Maintains streaming mean, variance (Welford's algorithm), and exponential moving average (EMA).
    Memory complexity is strictly O(1).
    """

    def __init__(
        self,
        name: str,
        warmup_samples: int = 10,
        anomaly_z_threshold: float = 3.0,
        ema_alpha: float = 0.1,
        min_std: float = 1.0,
    ) -> None:
        self.name = name
        self.warmup_samples = max(3, warmup_samples)
        self.anomaly_z_threshold = max(1.5, anomaly_z_threshold)
        self.ema_alpha = max(0.01, min(0.5, ema_alpha))
        self.min_std = max(0.001, min_std)

        self.count: int = 0
        self.mean: float = 0.0
        self.m2: float = 0.0
        self.ema: float = 0.0
        self.min_observed: float = float("inf")
        self.max_observed: float = float("-inf")
        self._is_degraded: bool = False

    def reset(self) -> None:
        """Reset baseline state (e.g. after sleep/resume or user configuration change)."""
        self.count = 0
        self.mean = 0.0
        self.m2 = 0.0
        self.ema = 0.0
        self.min_observed = float("inf")
        self.max_observed = float("-inf")
        self._is_degraded = False

    def mark_degraded(self, degraded: bool = True) -> None:
        """Mark sensor or data source as degraded."""
        self._is_degraded = degraded

    @property
    def variance(self) -> float:
        """Calculate sample variance."""
        return self.m2 / (self.count - 1) if self.count > 1 else 0.0

    @property
    def std_dev(self) -> float:
        """Calculate standard deviation with a minimum floor to avoid zero-division."""
        return max(self.min_std, math.sqrt(self.variance))

    def update(self, value: float) -> None:
        """
        Incorporate a new observation using Welford's streaming algorithm.
        """
        if math.isnan(value) or math.isinf(value):
            return

        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2

        if self.count == 1:
            self.ema = value
            self.min_observed = value
            self.max_observed = value
        else:
            self.ema = (self.ema_alpha * value) + ((1.0 - self.ema_alpha) * self.ema)
            self.min_observed = min(self.min_observed, value)
            self.max_observed = max(self.max_observed, value)

    def assess(self, value: float, update_after: bool = True) -> MetricAssessment:
        """
        Evaluate an observation against the current baseline without falsely flagging
        insufficient data as anomalous.
        """
        if self._is_degraded:
            return MetricAssessment(
                name=self.name,
                state=BaselineState.DEGRADED,
                observed_value=value,
                baseline_mean=self.mean if self.count > 0 else None,
                baseline_std=self.std_dev if self.count > 1 else None,
                z_score=None,
                sample_count=self.count,
                is_anomaly=False,
                deviation_factor=0.0,
                detail=f"{self.name} sensor is currently in a degraded state.",
            )

        if self.count < self.warmup_samples:
            if update_after:
                self.update(value)
            return MetricAssessment(
                name=self.name,
                state=BaselineState.INSUFFICIENT_DATA,
                observed_value=value,
                baseline_mean=self.mean if self.count > 0 else None,
                baseline_std=None,
                z_score=None,
                sample_count=self.count,
                is_anomaly=False,
                deviation_factor=0.0,
                detail=f"Warming up baseline ({self.count}/{self.warmup_samples} samples collected).",
            )

        std = self.std_dev
        z_score = (value - self.mean) / std
        deviation_factor = abs(value - self.mean) / max(1.0, abs(self.mean))
        is_anom = bool(z_score >= self.anomaly_z_threshold)

        state = BaselineState.ANOMALOUS if is_anom else BaselineState.NORMAL
        detail = (
            f"Observed {value:.1f} is {z_score:+.2f}σ from baseline mean {self.mean:.1f} (std: {std:.1f})"
            if is_anom
            else f"Within normal baseline envelope (mean: {self.mean:.1f}, std: {std:.1f})"
        )

        if update_after:
            if z_score < 4.0:
                self.update(value)

        return MetricAssessment(
            name=self.name,
            state=state,
            observed_value=value,
            baseline_mean=self.mean,
            baseline_std=std,
            z_score=z_score,
            sample_count=self.count,
            is_anomaly=is_anom,
            deviation_factor=deviation_factor,
            detail=detail,
        )


class HostBehaviorBaseline:
    """
    Comprehensive multi-metric behavioral baseline manager for host telemetry.
    """

    def __init__(self, warmup_samples: int = 10) -> None:
        self.warmup_samples = warmup_samples
        self.metrics: dict[str, MetricBaseline] = {
            "cpu_percent": MetricBaseline("CPU Utilization", warmup_samples=warmup_samples, anomaly_z_threshold=2.8, min_std=5.0),
            "memory_percent": MetricBaseline("Memory Utilization", warmup_samples=warmup_samples, anomaly_z_threshold=2.5, min_std=3.0),
            "net_upload_kbps": MetricBaseline("Network Upload Rate", warmup_samples=warmup_samples, anomaly_z_threshold=3.0, min_std=50.0),
            "net_download_kbps": MetricBaseline("Network Download Rate", warmup_samples=warmup_samples, anomaly_z_threshold=3.0, min_std=100.0),
            "process_count": MetricBaseline("Active Process Count", warmup_samples=warmup_samples, anomaly_z_threshold=3.0, min_std=15.0),
            "established_connections": MetricBaseline("Established Sockets", warmup_samples=warmup_samples, anomaly_z_threshold=3.0, min_std=10.0),
            "remote_connections": MetricBaseline("Remote Sockets", warmup_samples=warmup_samples, anomaly_z_threshold=3.0, min_std=5.0),
        }

    def reset_all(self) -> None:
        """Reset all metric baselines (e.g. after sleep/resume)."""
        for b in self.metrics.values():
            b.reset()
        logger.info("All host behavioral baselines reset.")

    def assess_snapshot(self, snapshot: Any, update: bool = True) -> dict[str, MetricAssessment]:
        """Assess all telemetry snapshot fields against their respective baselines."""
        assessments: dict[str, MetricAssessment] = {}

        field_map = {
            "cpu_percent": getattr(snapshot, "cpu_percent", 0.0),
            "memory_percent": getattr(snapshot, "memory_percent", 0.0),
            "net_upload_kbps": getattr(snapshot, "net_upload_kbps", 0.0),
            "net_download_kbps": getattr(snapshot, "net_download_kbps", 0.0),
            "process_count": float(getattr(snapshot, "process_count", 0)),
            "established_connections": float(getattr(snapshot, "established_connections", 0)),
            "remote_connections": float(getattr(snapshot, "remote_connections", 0)),
        }

        for key, val in field_map.items():
            baseline = self.metrics.get(key)
            if baseline:
                assessments[key] = baseline.assess(val, update_after=update)

        return assessments

    def get_summary(self) -> dict[str, Any]:
        """Return summary of all active baselines."""
        return {
            name: {
                "count": b.count,
                "mean": round(b.mean, 2) if b.count > 0 else None,
                "std_dev": round(b.std_dev, 2) if b.count > 1 else None,
                "state": BaselineState.INSUFFICIENT_DATA.value if b.count < self.warmup_samples else BaselineState.NORMAL.value,
            }
            for name, b in self.metrics.items()
        }
