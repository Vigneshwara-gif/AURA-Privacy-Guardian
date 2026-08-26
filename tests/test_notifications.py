"""
Comprehensive unit and integration tests for IncidentNotificationTracker and WindowsToastNotifier.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from aura.agent.notifications import IncidentNotificationTracker, WindowsToastNotifier
from aura.models.types import SecurityEvent


def test_normal_event_does_not_notify() -> None:
    """TEST 1: NORMAL / INFO events do not trigger notification."""
    tracker = IncidentNotificationTracker(min_severity="MEDIUM")
    event = SecurityEvent(
        event_id="evt-1",
        event_type="SECURITY_ASSESSMENT",
        severity="NORMAL",
        risk_score=0.0,
        incident_id="inc_baseline_nominal",
        summary="All systems normal",
    )
    should_notify, reason = tracker.evaluate_event(event)
    assert should_notify is False
    assert reason in ("severity_nominal", "below_minimum_severity")


def test_medium_incident_notifies_once() -> None:
    """TEST 2: MEDIUM incident first detected notifies exactly once."""
    tracker = IncidentNotificationTracker(min_severity="MEDIUM")
    event = SecurityEvent(
        event_id="evt-med-1",
        event_type="SECURITY_ASSESSMENT",
        severity="MEDIUM",
        risk_score=45.0,
        incident_id="inc_unsupervised_ml_anomaly",
        summary="Unusual CPU + Net anomaly detected",
    )
    should_notify, reason = tracker.evaluate_event(event)
    assert should_notify is True
    assert reason == "new_incident"


def test_same_incident_repeated_100_times_notifies_once() -> None:
    """TEST 3 & 4: Same MEDIUM incident repeated 100 times notifies only once total."""
    tracker = IncidentNotificationTracker(min_severity="MEDIUM")
    event = SecurityEvent(
        event_id="evt-med-1",
        event_type="SECURITY_ASSESSMENT",
        severity="MEDIUM",
        risk_score=45.0,
        incident_id="inc_unsupervised_ml_anomaly",
        summary="Unusual CPU + Net anomaly detected",
    )

    # First occurrence
    should_notify, reason = tracker.evaluate_event(event)
    assert should_notify is True

    # 100 subsequent identical cycles
    for i in range(100):
        subsequent_event = SecurityEvent(
            event_id=f"evt-med-sub-{i}",
            event_type="SECURITY_ASSESSMENT",
            severity="MEDIUM",
            risk_score=46.0 + (i % 3),  # Minor risk score fluctuation within MEDIUM
            incident_id="inc_unsupervised_ml_anomaly",
            summary="Unusual CPU + Net anomaly detected",
        )
        sub_notify, sub_reason = tracker.evaluate_event(subsequent_event)
        assert sub_notify is False
        assert sub_reason == "deduplicated_same_severity"

    state = tracker.get_incident_state("inc_unsupervised_ml_anomaly")
    assert state is not None
    assert state.occurrence_count == 101
    assert state.notified_severity == "MEDIUM"


def test_severity_escalation_lifecycle() -> None:
    """TEST 5, 6, 7: Escalation from MEDIUM -> HIGH -> CRITICAL triggers exactly 1 alert per tier."""
    tracker = IncidentNotificationTracker(min_severity="MEDIUM")
    inc_id = "inc_privacy_compound_exfiltration"

    # Step 1: Initial MEDIUM event -> Notify
    evt_med = SecurityEvent(
        event_id="evt-1",
        severity="MEDIUM",
        risk_score=45.0,
        incident_id=inc_id,
        summary="Camera active with elevated outbound traffic",
    )
    n1, r1 = tracker.evaluate_event(evt_med)
    assert n1 is True
    assert r1 == "new_incident"

    # Step 2: Repeat MEDIUM -> Deduplicated
    n2, r2 = tracker.evaluate_event(evt_med)
    assert n2 is False
    assert r2 == "deduplicated_same_severity"

    # Step 3: Escalates to HIGH -> Notify exactly once
    evt_high = SecurityEvent(
        event_id="evt-2",
        severity="HIGH",
        risk_score=78.0,
        incident_id=inc_id,
        summary="Camera active and outbound burst to unknown remote ASN",
    )
    n3, r3 = tracker.evaluate_event(evt_high)
    assert n3 is True
    assert r3 == "severity_escalation"

    # Step 4: Repeat HIGH -> Deduplicated
    n4, r4 = tracker.evaluate_event(evt_high)
    assert n4 is False
    assert r4 == "deduplicated_same_severity"

    # Step 5: Escalates to CRITICAL -> Notify exactly once
    evt_crit = SecurityEvent(
        event_id="evt-3",
        severity="CRITICAL",
        risk_score=95.0,
        incident_id=inc_id,
        summary="Active unauthorized exfiltration in progress",
    )
    n5, r5 = tracker.evaluate_event(evt_crit)
    assert n5 is True
    assert r5 == "severity_escalation"

    # Step 6: Repeat CRITICAL -> Deduplicated
    n6, r6 = tracker.evaluate_event(evt_crit)
    assert n6 is False
    assert r6 == "deduplicated_same_severity"


def test_incident_resolution_and_reoccurrence() -> None:
    """TEST 8 & 9: Incident resolution resets state; subsequent threat notifies as new incident."""
    tracker = IncidentNotificationTracker(min_severity="MEDIUM")
    inc_id = "inc_camera_hijack"

    # 1. Threat occurs -> Alert
    evt = SecurityEvent(event_id="e1", severity="HIGH", risk_score=80.0, incident_id=inc_id, summary="Camera anomaly")
    n1, _ = tracker.evaluate_event(evt)
    assert n1 is True

    # 2. Threat resolves (baseline returns to normal) -> Marked resolved
    resolve_evt = SecurityEvent(
        event_id="e2",
        severity="NORMAL",
        risk_score=5.0,
        incident_id=inc_id,
        summary="Camera released, traffic normal",
        is_resolved=True,
    )
    n2, r2 = tracker.evaluate_event(resolve_evt)
    assert n2 is False
    assert r2 == "incident_resolved"

    state = tracker.get_incident_state(inc_id)
    assert state is not None
    assert state.is_resolved is True
    assert state.notified_severity is None

    # 3. Same threat reappears later -> Notifies as NEW incident!
    evt_new = SecurityEvent(event_id="e3", severity="HIGH", risk_score=82.0, incident_id=inc_id, summary="Camera anomaly reappeared")
    n3, r3 = tracker.evaluate_event(evt_new)
    assert n3 is True
    assert r3 == "new_incident"


def test_notifications_disabled() -> None:
    """TEST 13: When notifications are disabled, tracker returns False but records state."""
    tracker = IncidentNotificationTracker(min_severity="MEDIUM", enabled=False)
    evt = SecurityEvent(event_id="e1", severity="CRITICAL", risk_score=99.0, incident_id="inc_critical")
    should_notify, reason = tracker.evaluate_event(evt)
    assert should_notify is False
    assert reason == "notifications_disabled"


def test_toast_sanitization_and_redaction() -> None:
    """TEST 15: WindowsToastNotifier sanitizes HTML entities and redacts tokens/passwords."""
    notifier = WindowsToastNotifier()
    raw = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID & <script>alert(1)</script> password=SecretPass123"
    sanitized = notifier.sanitize_text(raw)

    assert "eyJhbGciOi" not in sanitized
    assert "[REDACTED_TOKEN]" in sanitized
    assert "SecretPass123" not in sanitized
    assert "[REDACTED]" in sanitized
    assert "<script>" not in sanitized
    assert "&lt;script&gt;" in sanitized
