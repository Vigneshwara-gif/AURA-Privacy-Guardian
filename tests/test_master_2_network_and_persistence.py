"""
Tests for Network Investigation and Persistence Intelligence Engines.
"""

import pytest
from aura.intelligence.network_intel import NetworkInvestigationEngine, NetworkInvestigationSnapshot
from aura.intelligence.persistence_intel import PersistenceIntelligenceEngine, PersistenceIntelligenceSnapshot


def test_network_investigation_engine():
    snap = NetworkInvestigationEngine.investigate(limit=50)
    assert isinstance(snap, NetworkInvestigationSnapshot)
    assert snap.total_connections >= 0
    assert snap.established_count >= 0
    assert snap.listening_count >= 0
    assert isinstance(snap.active_endpoints, list)
    assert isinstance(snap.exposure_findings, list)
    d = snap.to_dict()
    assert "active_endpoints" in d
    assert "exposure_findings" in d


def test_persistence_intelligence_engine():
    snap = PersistenceIntelligenceEngine.analyze()
    assert isinstance(snap, PersistenceIntelligenceSnapshot)
    assert snap.total_startup_apps >= 0
    assert snap.total_services >= 0
    assert snap.total_scheduled_tasks >= 0
    assert isinstance(snap.analyzed_items, list)
    d = snap.to_dict()
    assert "analyzed_items" in d
    assert "suspicious_count" in d
