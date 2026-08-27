"""
Tests for Feature Extraction Pipeline and ML Anomaly Detection Ensemble.
"""

import pytest
from aura.engine.features import FeatureExtractionPipeline, FeatureVector
from aura.engine.anomaly_ensemble import AnomalyDetectionEnsemble
from aura.models.types import TelemetrySnapshot, PrivacyHardwareStatus


def test_feature_extraction_pipeline():
    telem = TelemetrySnapshot(
        cpu_percent=45.0,
        memory_percent=60.0,
        net_upload_kbps=1200.0,
        net_download_kbps=4500.0,
        established_connections=35,
        remote_connections=12,
        process_count=180,
        camera_status=PrivacyHardwareStatus.INACTIVE,
        microphone_status=PrivacyHardwareStatus.INACTIVE,
    )
    vec = FeatureExtractionPipeline.extract_features(telem)
    assert len(vec.raw_values) == 10
    assert len(vec.normalized_values) == 10
    for val in vec.normalized_values:
        assert 0.0 <= val <= 1.0
    arr = vec.to_numpy()
    assert arr.shape == (1, 10)


def test_anomaly_detection_ensemble():
    ensemble = AnomalyDetectionEnsemble(random_state=42)
    
    # Nominal vector
    nominal_telem = TelemetrySnapshot(
        cpu_percent=15.0,
        memory_percent=40.0,
        net_upload_kbps=10.0,
        net_download_kbps=20.0,
        established_connections=15,
        remote_connections=3,
        process_count=120,
    )
    vec_nom = FeatureExtractionPipeline.extract_features(nominal_telem)
    res_nom = ensemble.evaluate(vec_nom)
    assert isinstance(res_nom.is_anomaly, bool)
    assert 0.0 <= res_nom.combined_anomaly_score <= 1.0

    # Severe outlier vector (100% CPU, 100% RAM, massive upload)
    outlier_telem = TelemetrySnapshot(
        cpu_percent=100.0,
        memory_percent=99.0,
        net_upload_kbps=45000.0,
        net_download_kbps=90000.0,
        established_connections=450,
        remote_connections=200,
        process_count=900,
    )
    vec_out = FeatureExtractionPipeline.extract_features(outlier_telem)
    res_out = ensemble.evaluate(vec_out)
    assert res_out.combined_anomaly_score > res_nom.combined_anomaly_score
