"""
Tests for Incident Management, Safe Response Actions, and Alert Engine.
"""

import os
import pytest
from aura.intelligence.alerts import AlertEngine, SecurityAlert
from aura.intelligence.findings import FindingSeverity
from aura.intelligence.incidents import IncidentManager, IncidentState, SecurityIncident
from aura.intelligence.response import SafeResponseEngine, ResponseActionResult
from aura.intelligence.timeline import ForensicTimelineEngine, TimelineEventType


def test_forensic_timeline_engine():
    item = ForensicTimelineEngine.record_event(
        event_type=TimelineEventType.PROCESS_START,
        title="Started test process",
        entity_name="test.exe",
        entity_id="1234",
        severity="INFO",
    )
    assert item.item_id.startswith("TLM-")
    events = ForensicTimelineEngine.get_timeline(limit=10)
    assert any(e.item_id == item.item_id for e in events)


def test_incident_manager_lifecycle():
    inc = IncidentManager.create_incident(
        title="Test Multi-Vector Exfiltration Incident",
        severity=FindingSeverity.HIGH,
        summary="High egress rate with active camera stream",
        affected_entities=["PID 1234"],
    )
    assert inc.incident_id.startswith("INC-")
    assert inc.state == IncidentState.NEW

    # Update state
    updated = IncidentManager.update_incident_state(
        incident_id=inc.incident_id,
        new_state=IncidentState.INVESTIGATING,
        actor="SecOps",
        note="Investigating host flow",
    )
    assert updated is True
    fetched = IncidentManager.get_incident_by_id(inc.incident_id)
    assert fetched is not None
    assert fetched.state == IncidentState.INVESTIGATING
    assert len(fetched.action_history) == 1


def test_safe_response_engine_critical_protection():
    # Attempting to kill PID 0 or PID 4 (System) must be rejected safely
    res = SafeResponseEngine.terminate_process(pid=4, actor="SecOps")
    assert res.success is False
    assert "Cannot terminate protected" in res.message


def test_safe_response_engine_shortcut():
    res = SafeResponseEngine.open_system_shortcut("CAMERA", actor="SecOps")
    assert res.action_type == "OPEN_SHORTCUT"
    assert res.success is True


def test_alert_engine_dispatch_and_acknowledge():
    alert = AlertEngine.dispatch_alert(
        title="Test Unique Alert",
        severity=FindingSeverity.CRITICAL,
        summary="Critical security test alert",
        entity_id="test_host",
    )
    assert alert is not None
    assert alert.alert_id.startswith("ALT-")
    assert alert.is_acknowledged is False

    # Acknowledge
    ack = AlertEngine.acknowledge_alert(alert.alert_id, actor="SecOps")
    assert ack is True
    alerts = AlertEngine.get_alerts(limit=10)
    matched = next((a for a in alerts if a.alert_id == alert.alert_id), None)
    assert matched is not None
    assert matched.is_acknowledged is True
