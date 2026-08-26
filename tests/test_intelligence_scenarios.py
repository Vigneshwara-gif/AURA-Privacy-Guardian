"""
Comprehensive Security Intelligence, Behavioral Baselines, Multi-Signal Correlation,
and Adversarial Scenario Tests for AURA Phase 4.
"""

from __future__ import annotations

import math
from pathlib import Path
import pytest

from aura.engine.baseline import BaselineState, HostBehaviorBaseline, MetricBaseline
from aura.engine.correlation import CorrelationCategory, MultiSignalCorrelator
from aura.engine.risk_hardened import HardenedRiskEngine
from aura.engine.service import AuraEngineService
from aura.models.types import PrivacyHardwareStatus, SensorHealthRecord, SensorStatus, TelemetrySnapshot
from aura.sensors.network_intel import NetworkIntelligenceCollector, SocketCategory
from aura.sensors.process_intel import ConfidenceLevel, ProcessIntelligenceCollector


# ======================================================================
# 1. Behavioral Baselines & Anomaly Detection Tests (Stage 2)
# ======================================================================

def test_metric_baseline_warmup_and_states() -> None:
    """Verify warm-up period correctly outputs INSUFFICIENT_DATA and transitions to NORMAL."""
    b = MetricBaseline("CPU", warmup_samples=5, anomaly_z_threshold=3.0, min_std=2.0)

    # First 4 samples should be in warm-up
    for i in range(4):
        res = b.assess(20.0 + i)
        assert res.state == BaselineState.INSUFFICIENT_DATA
        assert not res.is_anomaly

    # 5th sample completes warm-up
    res5 = b.assess(22.0)
    assert res5.sample_count >= 5

    # 6th sample should be evaluated as NORMAL
    res6 = b.assess(23.0)
    assert res6.state == BaselineState.NORMAL
    assert not res6.is_anomaly


def test_metric_baseline_anomaly_detection() -> None:
    """Verify extreme deviation triggers ANOMALOUS state with high z-score."""
    b = MetricBaseline("Upload", warmup_samples=5, anomaly_z_threshold=2.5, min_std=10.0)

    for _ in range(10):
        b.update(100.0)  # Establish baseline at 100 KB/s

    # Normal sample
    res_norm = b.assess(110.0, update_after=False)
    assert res_norm.state == BaselineState.NORMAL

    # Extreme spike: 5000 KB/s
    res_spike = b.assess(5000.0, update_after=False)
    assert res_spike.state == BaselineState.ANOMALOUS
    assert res_spike.is_anomaly
    assert res_spike.z_score is not None and res_spike.z_score > 2.5


def test_baseline_reset_and_nan_resilience() -> None:
    """Verify baseline reset and resilience against NaN / Inf values."""
    b = MetricBaseline("Memory", warmup_samples=5)
    b.update(40.0)
    b.update(42.0)
    assert b.count == 2

    # NaN / Inf should be silently ignored without crashing or corrupting
    b.update(float("nan"))
    b.update(float("inf"))
    assert b.count == 2

    b.reset()
    assert b.count == 0
    assert b.mean == 0.0


# ======================================================================
# 2. Process & Network Intelligence Tests (Stage 4)
# ======================================================================

def test_process_intelligence_collector() -> None:
    """Verify safe process enumeration with confidence metadata."""
    procs = ProcessIntelligenceCollector.get_top_processes(limit=5)
    assert isinstance(procs, list)
    if procs:
        p = procs[0]
        assert p.pid >= 0
        assert p.name
        assert p.confidence == ConfidenceLevel.OBSERVED


def test_network_intelligence_ip_classification() -> None:
    """Verify loopback, private subnet, and public WAN IP classification."""
    assert NetworkIntelligenceCollector.classify_ip("127.0.0.1") == SocketCategory.LOOPBACK
    assert NetworkIntelligenceCollector.classify_ip("::1") == SocketCategory.LOOPBACK
    assert NetworkIntelligenceCollector.classify_ip("192.168.1.100") == SocketCategory.LOCAL_SUBNET
    assert NetworkIntelligenceCollector.classify_ip("10.0.0.5") == SocketCategory.LOCAL_SUBNET
    assert NetworkIntelligenceCollector.classify_ip("8.8.8.8") == SocketCategory.REMOTE_PUBLIC
    assert NetworkIntelligenceCollector.classify_ip("invalid_ip") == SocketCategory.UNKNOWN


# ======================================================================
# 3. Multi-Signal Correlation & Privacy Threats (Stages 3 & 5)
# ======================================================================

def test_privacy_threat_correlation() -> None:
    """Verify Camera Active + Outbound Network Spike generates PRIVACY_ANOMALY insight."""
    correlator = MultiSignalCorrelator()
    baseline = HostBehaviorBaseline(warmup_samples=5)

    # Establish baseline
    for _ in range(10):
        baseline.assess_snapshot(
            TelemetrySnapshot(
                timestamp="2026-08-25T12:00:00Z",
                cpu_percent=15.0,
                net_upload_kbps=50.0,
                process_count=150,
            )
        )

    # Suspicious snapshot: Camera AVAILABLE + 2500 KB/s upload
    suspicious_snap = TelemetrySnapshot(
        timestamp="2026-08-25T12:05:00Z",
        cpu_percent=20.0,
        net_upload_kbps=2500.0,
        process_count=155,
        camera_status=PrivacyHardwareStatus.AVAILABLE,
    )

    assessments = baseline.assess_snapshot(suspicious_snap, update=False)
    insights = correlator.correlate(suspicious_snap, assessments)

    assert len(insights) >= 1
    privacy_insight = next(i for i in insights if i.category == CorrelationCategory.PRIVACY_ANOMALY)
    assert privacy_insight.severity == "HIGH"
    assert privacy_insight.is_compound
    assert len(privacy_insight.evidence_chain) >= 2


# ======================================================================
# 4. Hardened Explainable Risk Engine Tests (Stage 6)
# ======================================================================

def test_hardened_risk_engine_bounds_and_explainability() -> None:
    """Verify deterministic 0-100 bounded risk score with structured contributors."""
    correlator = MultiSignalCorrelator()
    baseline = HostBehaviorBaseline(warmup_samples=5)

    for _ in range(10):
        baseline.assess_snapshot(
            TelemetrySnapshot(timestamp="2026-08-25T12:00:00Z", cpu_percent=10.0, net_upload_kbps=20.0)
        )

    nominal_snap = TelemetrySnapshot(timestamp="2026-08-25T12:01:00Z", cpu_percent=12.0, net_upload_kbps=25.0)
    assessments = baseline.assess_snapshot(nominal_snap, update=False)
    insights = correlator.correlate(nominal_snap, assessments)

    res_nominal = HardenedRiskEngine.evaluate(nominal_snap, assessments, insights)
    assert res_nominal.risk_score == 0.0
    assert res_nominal.severity == "NORMAL"
    assert len(res_nominal.reasons) > 0


def test_risk_engine_degraded_sensor_awareness() -> None:
    """Verify sensor degradation is reported and transparently noted."""
    baseline = HostBehaviorBaseline()
    degraded_snap = TelemetrySnapshot(
        timestamp="2026-08-25T12:00:00Z",
        sensor_health=[
            SensorHealthRecord(
                name="Camera Hardware",
                status=SensorStatus.ERROR,
                value="—",
                detail="DirectShow COM exception.",
            )
        ],
    )
    assessments = baseline.assess_snapshot(degraded_snap)
    res = HardenedRiskEngine.evaluate(degraded_snap, assessments, [])
    assert res.is_degraded
    assert any("Camera Hardware" in r for r in res.reasons)


# ======================================================================
# 5. Full Engine Service Integration (Stage 8)
# ======================================================================

def test_engine_service_scan_once_integration(tmp_path: Path) -> None:
    """Verify AuraEngineService.scan_once integrates baselines, correlation, and risk."""
    from aura.storage.sqlite import StorageEngine
    from aura.core.config import Settings
    from aura.core.paths import AuraPaths

    db_path = tmp_path / "intel_test.db"
    storage = StorageEngine(db_path)
    workspace_root = Path(__file__).resolve().parent.parent
    paths = AuraPaths(install_root=workspace_root, user_root=tmp_path, user_root_origin="test")

    engine = AuraEngineService(settings=Settings(), paths=paths, storage=storage)
    scan_res = engine.scan_once(probe_camera=False, probe_microphone=False)

    assert scan_res.scan_id
    assert scan_res.event.event_id
    assert scan_res.event.risk_score >= 0.0
    assert scan_res.event.severity in ("NORMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert isinstance(scan_res.event.evidence, list)

    status = engine.get_status()
    assert "baselines" in status
    assert "cpu_percent" in status["baselines"]
    storage.close()
