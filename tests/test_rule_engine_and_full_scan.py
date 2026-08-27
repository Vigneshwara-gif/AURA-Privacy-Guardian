"""
Tests for Security Rule Engine and Full PC Security Scan.
"""

import pytest
from aura.engine.rules import SecurityRuleEngine
from aura.engine.scan_engine import FullSecurityScanEngine, FullScanResult
from aura.models.types import TelemetrySnapshot, PrivacyHardwareStatus
from aura.sensors.security_posture import SecurityPostureCollector, DefenderStatus, FirewallProfileStatus, WindowsUpdatePosture, WindowsSecurityPostureSnapshot


def test_security_rule_engine_exfiltration():
    telem = TelemetrySnapshot(
        camera_status=PrivacyHardwareStatus.ACTIVE,
        net_upload_kbps=5000.0,
    )
    findings = SecurityRuleEngine.evaluate_rules(telemetry=telem)
    assert any(f.rule_id == "RUL-001" for f in findings)


def test_full_security_scan_execution():
    scanner = FullSecurityScanEngine()
    result = scanner.execute_full_scan()
    assert isinstance(result, FullScanResult)
    assert len(result.scan_id) > 0
    assert result.duration_seconds >= 0.0
    assert result.total_checks_performed > 0
    assert len(result.categories_scanned) == 16
    assert 0 <= result.overall_security_score <= 100
    assert 0 <= result.privacy_health_score <= 100
    assert 0 <= result.composite_risk_score <= 100
    assert result.risk_severity in {"NORMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert len(result.summary_narrative) > 0
