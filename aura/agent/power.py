"""
Power Transition & Sleep/Resume Detector for AURA Background Agent.

Guarantees:
  - Uses high-resolution monotonic time to accurately detect system suspension.
  - Distinguishes between normal loop jitter vs sleep/hibernate/resume.
  - Triggers sensor delta baseline resets to prevent fabricated traffic spikes.
  - Structured POWER_RESUME event dispatch.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PowerTransitionEvent:
    """Record describing a detected power/sleep suspension gap."""

    gap_seconds: float
    expected_interval_seconds: float
    detected_at: str
    transition_type: str = "POWER_RESUME"


class PowerTransitionDetector:
    """
    Monitors timing cadence to detect OS sleep, hibernate, and modern standby resume events.
    """

    def __init__(self, gap_multiplier_threshold: float = 3.0, min_gap_seconds: float = 12.0) -> None:
        self.gap_multiplier = max(2.0, gap_multiplier_threshold)
        self.min_gap_seconds = max(1.0, min_gap_seconds)
        self._last_cycle_monotonic: float | None = None
        self._resume_count = 0

    @property
    def resume_count(self) -> int:
        return self._resume_count

    def check_transition(self, expected_interval: float) -> PowerTransitionEvent | None:
        """
        Check if the elapsed monotonic time since last cycle indicates an OS suspension gap.
        Returns a PowerTransitionEvent if a sleep/resume gap occurred, else None.
        """
        now_mono = time.monotonic()
        threshold = max(self.min_gap_seconds, expected_interval * self.gap_multiplier)

        if self._last_cycle_monotonic is None:
            self._last_cycle_monotonic = now_mono
            return None

        elapsed = now_mono - self._last_cycle_monotonic
        self._last_cycle_monotonic = now_mono

        if elapsed >= threshold:
            self._resume_count += 1
            now_iso = datetime.now(timezone.utc).isoformat()
            logger.info(
                "Power transition / sleep gap detected: elapsed %.2fs (threshold: %.2fs)",
                elapsed,
                threshold,
            )
            return PowerTransitionEvent(
                gap_seconds=elapsed,
                expected_interval_seconds=expected_interval,
                detected_at=now_iso,
            )

        return None

    def reset(self) -> None:
        """Reset internal monotonic baseline reference."""
        self._last_cycle_monotonic = time.monotonic()
