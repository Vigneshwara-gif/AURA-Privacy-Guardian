"""
Tests for non-intrusive camera & microphone capability probes and isolated collection.
"""

from __future__ import annotations

from unittest.mock import patch
import pytest

from aura.models.types import PrivacyHardwareStatus, SensorStatus
from aura.sensors.camera import CameraProbeResult, probe_camera_capability
from aura.sensors.collector import SensorCollector
from aura.sensors.microphone import MicrophoneProbeResult, probe_microphone_capability


def test_camera_probe_returns_valid_result() -> None:
    """Verify camera probe produces structured result without throwing exceptions."""
    result = probe_camera_capability()
    assert isinstance(result, CameraProbeResult)
    assert isinstance(result.status, PrivacyHardwareStatus)
    assert result.status in {
        PrivacyHardwareStatus.AVAILABLE,
        PrivacyHardwareStatus.NOT_DETECTED,
        PrivacyHardwareStatus.PERMISSION_LIMITED,
        PrivacyHardwareStatus.UNAVAILABLE,
        PrivacyHardwareStatus.UNKNOWN,
    }
    assert isinstance(result.detail, str)


def test_microphone_probe_returns_valid_result() -> None:
    """Verify microphone probe produces structured result without throwing exceptions."""
    result = probe_microphone_capability()
    assert isinstance(result, MicrophoneProbeResult)
    assert isinstance(result.status, PrivacyHardwareStatus)
    assert result.status in {
        PrivacyHardwareStatus.AVAILABLE,
        PrivacyHardwareStatus.NOT_DETECTED,
        PrivacyHardwareStatus.PERMISSION_LIMITED,
        PrivacyHardwareStatus.UNAVAILABLE,
        PrivacyHardwareStatus.UNKNOWN,
    }


def test_sensor_collector_isolated_on_error() -> None:
    """Verify that a failing sensor probe does not crash collector or taint other metrics."""
    collector = SensorCollector(sample_interval=0.05)

    with patch("psutil.virtual_memory", side_effect=RuntimeError("Simulated memory driver failure")):
        snapshot = collector.collect_snapshot(probe_camera=False)

    assert snapshot.cpu_percent >= 0.0
    assert snapshot.memory_percent == 0.0  # Safe default on error

    # Verify sensor health reports error on RAM probe
    ram_record = next((h for h in snapshot.sensor_health if "Memory" in h.name), None)
    assert ram_record is not None
    assert ram_record.status == SensorStatus.ERROR
    assert "Simulated memory driver failure" in ram_record.detail

    # Verify CPU sensor completed normally
    cpu_record = next((h for h in snapshot.sensor_health if "Processor" in h.name), None)
    assert cpu_record is not None
    assert cpu_record.status in {SensorStatus.HEALTHY, SensorStatus.DEGRADED}


def test_sensor_permission_limited() -> None:
    """Verify that AccessDenied is mapped to PERMISSION_LIMITED."""
    collector = SensorCollector(sample_interval=0.05)

    with patch("psutil.net_connections", side_effect=PermissionError("Admin elevation required")):
        snapshot = collector.collect_snapshot(probe_camera=False)

    socket_record = next((h for h in snapshot.sensor_health if "Sockets" in h.name), None)
    assert socket_record is not None
    assert socket_record.status == SensorStatus.PERMISSION_LIMITED
