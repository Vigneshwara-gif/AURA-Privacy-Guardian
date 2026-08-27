"""
Tests for Unified Security Evidence and Process DNA Service.
"""

import os
import pytest
from aura.intelligence.evidence import EvidenceCategory, EvidenceObservationState, SecurityEvidence
from aura.intelligence.process_dna import ProcessDNAService, ProcessDNAProfile


def test_unified_security_evidence_model():
    ev = SecurityEvidence(
        source="TestHunter",
        category=EvidenceCategory.PROCESS,
        observation_state=EvidenceObservationState.OBSERVED,
        entity_type="process",
        entity_id="1234",
        observed_value=r"C:\temp\malicious.exe",
        expected_value=r"C:\Program Files\app.exe",
        deviation=0.85,
        confidence=0.98,
        summary="Process running from temporary path",
    )
    assert ev.evidence_id.startswith("EVD-")
    d = ev.to_dict()
    assert d["category"] == "PROCESS"
    assert d["observation_state"] == "OBSERVED"
    assert d["confidence"] == 0.98


def test_process_dna_service_self():
    current_pid = os.getpid()
    dna = ProcessDNAService.get_process_dna(current_pid)
    assert dna is not None
    assert isinstance(dna, ProcessDNAProfile)
    assert dna.pid == current_pid
    assert dna.identity.name != ""
    assert dna.identity.exe_exists is True
    assert dna.execution.cpu_percent >= 0.0
    assert dna.execution.memory_mb >= 0.0
    assert 0 <= dna.security.risk_score <= 100
    d = dna.to_dict()
    assert "identity" in d
    assert "execution" in d
    assert "network" in d
    assert "privacy" in d
    assert "security" in d


def test_process_dna_service_invalid_pid():
    dna = ProcessDNAService.get_process_dna(99999999)
    assert dna is None
