"""
Comprehensive tests for genuine Windows Camera & Microphone Intelligence Collectors.
"""

from __future__ import annotations

from unittest.mock import patch
import pytest

from aura.models.types import PrivacyHardwareStatus, SensorStatus
from aura.sensors.camera import (
    CameraIntelligenceCollector,
    CameraIntelligenceSnapshot,
    CameraProbeResult,
    probe_camera_capability,
)
from aura.sensors.collector import SensorCollector
from aura.sensors.microphone import (
    MicrophoneIntelligenceCollector,
    MicrophoneIntelligenceSnapshot,
    MicrophoneProbeResult,
    probe_microphone_capability,
)
from aura.contracts.system import (
    CameraIntelligenceResponse,
    MicrophoneIntelligenceResponse,
    PrivacySentinelSummaryResponse,
)


def test_camera_intelligence_collector_snapshot():
    """Verify CameraIntelligenceCollector collects genuine hardware, permission, and usage."""
    snap = CameraIntelligenceCollector.collect_snapshot()
    assert isinstance(snap, CameraIntelligenceSnapshot)
    assert isinstance(snap.status, PrivacyHardwareStatus)
    assert snap.status in {
        PrivacyHardwareStatus.AVAILABLE,
        PrivacyHardwareStatus.ACTIVE,
        PrivacyHardwareStatus.NOT_DETECTED,
        PrivacyHardwareStatus.PERMISSION_LIMITED,
        PrivacyHardwareStatus.UNAVAILABLE,
        PrivacyHardwareStatus.UNKNOWN,
    }
    assert snap.system_permission in {"ALLOWED", "DENIED", "UNKNOWN"}
    assert snap.device_count >= 0
    assert isinstance(snap.devices, list)
    assert isinstance(snap.recent_usage, list)
    assert 0.0 <= snap.confidence <= 1.0
    assert len(snap.source) > 0

    # Test serialization
    d = snap.to_dict()
    assert "status" in d
    assert "devices" in d
    assert "recent_usage" in d
    resp_model = CameraIntelligenceResponse(**d)
    assert resp_model.status == snap.status.value


def test_microphone_intelligence_collector_snapshot():
    """Verify MicrophoneIntelligenceCollector collects genuine hardware, permission, and usage."""
    snap = MicrophoneIntelligenceCollector.collect_snapshot()
    assert isinstance(snap, MicrophoneIntelligenceSnapshot)
    assert isinstance(snap.status, PrivacyHardwareStatus)
    assert snap.status in {
        PrivacyHardwareStatus.AVAILABLE,
        PrivacyHardwareStatus.ACTIVE,
        PrivacyHardwareStatus.NOT_DETECTED,
        PrivacyHardwareStatus.PERMISSION_LIMITED,
        PrivacyHardwareStatus.UNAVAILABLE,
        PrivacyHardwareStatus.UNKNOWN,
    }
    assert snap.system_permission in {"ALLOWED", "DENIED", "UNKNOWN"}
    assert snap.device_count >= 0
    assert isinstance(snap.devices, list)
    assert isinstance(snap.recent_usage, list)
    assert 0.0 <= snap.confidence <= 1.0
    assert len(snap.source) > 0

    # Test serialization
    d = snap.to_dict()
    assert "status" in d
    assert "devices" in d
    assert "recent_usage" in d
    resp_model = MicrophoneIntelligenceResponse(**d)
    assert resp_model.status == snap.status.value


def test_camera_probe_backwards_compatible():
    """Verify backwards-compatible camera probe wrapper."""
    result = probe_camera_capability()
    assert isinstance(result, CameraProbeResult)
    assert isinstance(result.status, PrivacyHardwareStatus)
    assert isinstance(result.detail, str)


def test_microphone_probe_backwards_compatible():
    """Verify backwards-compatible microphone probe wrapper."""
    result = probe_microphone_capability()
    assert isinstance(result, MicrophoneProbeResult)
    assert isinstance(result.status, PrivacyHardwareStatus)


def test_sensor_collector_isolated_on_error():
    """Verify that a failing sensor probe does not crash collector or taint other metrics."""
    collector = SensorCollector(sample_interval=0.05)

    with patch("psutil.virtual_memory", side_effect=RuntimeError("Simulated memory driver failure")):
        snapshot = collector.collect_snapshot(probe_camera=False)

    assert snapshot.cpu_percent >= 0.0
    assert snapshot.memory_percent == 0.0

    ram_record = next((h for h in snapshot.sensor_health if "Memory" in h.name), None)
    assert ram_record is not None
    assert ram_record.status == SensorStatus.ERROR
    assert "Simulated memory driver failure" in ram_record.detail


def test_sensor_permission_limited():
    """Verify PERMISSION_LIMITED sensor health status when permission is denied."""
    collector = SensorCollector(sample_interval=0.05)

    with patch("psutil.cpu_percent", side_effect=PermissionError("Simulated access denial")):
        snapshot = collector.collect_snapshot(probe_camera=False)

    cpu_record = next((h for h in snapshot.sensor_health if "Processor" in h.name), None)
    assert cpu_record is not None
    assert cpu_record.status == SensorStatus.PERMISSION_LIMITED
