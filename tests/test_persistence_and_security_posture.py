"""
Tests for Persistence and Security Posture Collectors.
"""

import pytest
from aura.sensors.persistence import PersistenceIntelligenceCollector
from aura.sensors.security_posture import SecurityPostureCollector
from aura.sensors.event_log import WindowsEventLogCollector


def test_persistence_inventory_collection():
    inventory = PersistenceIntelligenceCollector.collect_inventory(max_items=20)
    assert isinstance(inventory.startup_apps, list)
    assert inventory.services_count >= 0
    assert inventory.scheduled_tasks_count >= 0
    assert isinstance(inventory.services, list)
    assert isinstance(inventory.scheduled_tasks, list)


def test_security_posture_collection():
    posture = SecurityPostureCollector.collect_posture()
    assert 0 <= posture.overall_posture_score <= 100
    assert isinstance(posture.defender.realtime_protection_enabled, bool)
    assert isinstance(posture.firewall.all_profiles_secure, bool)
    assert isinstance(posture.update_posture.is_reboot_pending, bool)


def test_windows_event_log_collection():
    events = WindowsEventLogCollector.get_recent_system_events(count=5)
    assert isinstance(events, list)
