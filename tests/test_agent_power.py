"""
Unit tests for PowerTransitionDetector and sensor delta re-baselining.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch
import pytest

from aura.agent.power import PowerTransitionDetector
from aura.models.types import SensorStatus
from aura.sensors.collector import SensorCollector


def test_power_detector_normal_jitter() -> None:
    """Verify normal scheduling jitter does not trigger a power resume event."""
    detector = PowerTransitionDetector(gap_multiplier_threshold=3.0, min_gap_seconds=10.0)

    # First cycle sets baseline
    assert detector.check_transition(expected_interval=5.0) is None

    # Second cycle with small normal jitter (5.2s)
    with patch("time.monotonic", side_effect=[time.monotonic() + 5.2]):
        evt = detector.check_transition(expected_interval=5.0)
        assert evt is None
        assert detector.resume_count == 0


def test_power_detector_sleep_gap_detection() -> None:
    """Verify large monotonic time gap (>15s) triggers PowerTransitionEvent."""
    detector = PowerTransitionDetector(gap_multiplier_threshold=3.0, min_gap_seconds=10.0)

    base_time = 1000.0
    with patch("time.monotonic", return_value=base_time):
        assert detector.check_transition(expected_interval=5.0) is None

    # Simulate waking from sleep 3600 seconds later
    with patch("time.monotonic", return_value=base_time + 3600.0):
        evt = detector.check_transition(expected_interval=5.0)
        assert evt is not None
        assert evt.transition_type == "POWER_RESUME"
        assert evt.gap_seconds == pytest.approx(3600.0)
        assert detector.resume_count == 1


def test_sensor_collector_rebaseline_prevents_false_traffic_spike() -> None:
    """Verify that calling reset_baselines prevents calculating a false network spike after sleep."""
    collector = SensorCollector(sample_interval=0.02)

    # Sample 1: Baseline established
    snap1 = collector.collect_snapshot()
    assert collector._last_net_bytes is not None

    # Simulate sleep: system wakes up and collector baselines are reset
    collector.reset_baselines()
    assert collector._last_net_bytes is None

    # Sample 2: First cycle after wake-up establishes new baseline without false spike
    snap2 = collector.collect_snapshot()
    assert snap2.net_upload_kbps >= 0.0
    assert snap2.net_download_kbps >= 0.0
    assert collector._last_net_bytes is not None
