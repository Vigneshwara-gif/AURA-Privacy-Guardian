"""
Tests for AI Explainability and Threat Hunting Engines.
"""

import pytest
from aura.engine.features import FeatureExtractionPipeline
from aura.intelligence.explainability import AIExplainabilityEngine, AnomalyExplanationReport
from aura.intelligence.threat_hunter import ThreatHuntingEngine, ThreatHuntResult
from aura.models.types import TelemetrySnapshot


def test_ai_explainability_engine_nominal():
    telem = TelemetrySnapshot(
        cpu_percent=20.0,
        memory_percent=45.0,
        net_upload_kbps=50.0,
        net_download_kbps=150.0,
        established_connections=25,
        remote_connections=5,
        process_count=150,
    )
    exp = AIExplainabilityEngine.explain(telemetry=telem)
    assert isinstance(exp, AnomalyExplanationReport)
    assert 0.0 <= exp.combined_score <= 1.0
    assert len(exp.feature_explanations) == 10
    assert len(exp.narrative) > 0
    d = exp.to_dict()
    assert "feature_explanations" in d
    assert "narrative" in d


def test_threat_hunting_engine():
    res = ThreatHuntingEngine.execute_hunts()
    assert isinstance(res, ThreatHuntResult)
    assert res.hunts_executed == len(ThreatHuntingEngine.HUNT_QUERIES)
    assert isinstance(res.matches, list)
    assert len(res.summary) > 0
    d = res.to_dict()
    assert "matches" in d
