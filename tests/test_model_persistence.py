"""
Tests for ML model artifact serialization, deserialization, integrity checks, and schema validation.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from aura.models.persistence import (
    load_model_artifact,
    load_or_train_model,
    save_model_artifact,
)
from model import AURAModel, detect, train_model


@pytest.fixture
def trained_model() -> AURAModel:
    data = pd.DataFrame(
        {
            "CPU": np.random.uniform(5.0, 30.0, size=50),
            "Net": np.random.uniform(10.0, 150.0, size=50),
            "Cam": np.zeros(50),
        }
    )
    return train_model(data, contamination=0.10)


def test_model_save_and_load(trained_model: AURAModel, tmp_path: Path) -> None:
    """Verify saving model to artifact and loading back without loss."""
    art_path = tmp_path / "test_model.joblib"
    save_model_artifact(trained_model, art_path)
    assert art_path.exists()
    assert art_path.stat().st_size > 0

    loaded_model = load_model_artifact(art_path)
    assert loaded_model.training_samples == trained_model.training_samples
    assert loaded_model.contamination == trained_model.contamination
    assert loaded_model.feature_names == trained_model.feature_names


def test_model_inference_equivalence_after_reload(trained_model: AURAModel, tmp_path: Path) -> None:
    """Verify that anomaly inference produces identical scores before and after load."""
    art_path = tmp_path / "test_model.joblib"
    save_model_artifact(trained_model, art_path)
    loaded_model = load_model_artifact(art_path)

    sample_input = [25.0, 80.0, 0.0]
    res_orig = detect(trained_model, sample_input)
    res_loaded = detect(loaded_model, sample_input)

    assert float(res_orig["if_score"]) == pytest.approx(float(res_loaded["if_score"]), rel=1e-5)
    assert float(res_orig["lof_score"]) == pytest.approx(float(res_loaded["lof_score"]), rel=1e-5)
    assert int(res_orig["anomaly"]) == int(res_loaded["anomaly"])


def test_corrupted_artifact_rejection(tmp_path: Path) -> None:
    """Verify that a corrupted artifact file raises ValueError."""
    art_path = tmp_path / "corrupt.joblib"
    art_path.write_bytes(b"NOT_A_VALID_JOBLIB_FILE_CORRUPT_BYTES")

    with pytest.raises(ValueError, match="Corrupted model artifact"):
        load_model_artifact(art_path)


def test_incompatible_feature_schema(trained_model: AURAModel, tmp_path: Path) -> None:
    """Verify that schema mismatch raises ValueError."""
    art_path = tmp_path / "schema_mismatch.joblib"
    save_model_artifact(trained_model, art_path)

    with pytest.raises(ValueError, match="Feature schema mismatch"):
        load_model_artifact(art_path, expected_features=("CPU", "Net", "Disk", "Memory"))
