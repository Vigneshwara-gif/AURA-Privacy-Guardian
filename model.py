from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler


# ============================================================
# AURA AI DETECTION ENGINE
# ============================================================
#
# Current model features:
#   CPU  -> CPU utilisation
#   Net  -> outbound network rate
#   Cam  -> camera availability indicator
#
# The model combines:
#
#   1. Isolation Forest
#   2. Local Outlier Factor
#   3. Ensemble decision
#   4. Anomaly confidence
#   5. Explainable detection metadata
#
# IMPORTANT:
# Anomaly detection identifies behaviour that differs from
# the learned baseline. It does NOT prove malware, spyware,
# compromise, or data theft.
#
# ============================================================


FEATURES = [
    "CPU",
    "Net",
    "Cam",
]


# ============================================================
# MODEL CONFIGURATION
# ============================================================

DEFAULT_CONTAMINATION = 0.10

MIN_BASELINE_SAMPLES = 10

ISOLATION_TREES = 300

MIN_LOF_NEIGHBORS = 2

MAX_LOF_NEIGHBORS = 20


# ============================================================
# MODEL DATA STRUCTURE
# ============================================================

@dataclass
class AURAModel:
    """
    Complete trained AURA anomaly-detection model.

    The original three model components are preserved for
    compatibility with the existing AURA project.
    """

    scaler: StandardScaler

    isolation_forest: IsolationForest

    lof: LocalOutlierFactor

    feature_names: tuple[str, ...]

    training_samples: int

    contamination: float

    lof_neighbors: int

    baseline_mean: np.ndarray

    baseline_std: np.ndarray

    # Model decision statistics.
    if_training_scores: np.ndarray

    lof_training_scores: np.ndarray


# ============================================================
# INPUT VALIDATION
# ============================================================

def _prepare(X: Any) -> np.ndarray:
    """
    Convert input data into a validated numeric matrix.

    Accepted inputs:
        - pandas DataFrame
        - numpy array
        - list of rows
        - single feature row

    The function always returns:

        shape = (samples, 3)
    """

    if isinstance(X, pd.DataFrame):

        missing = [
            feature
            for feature in FEATURES
            if feature not in X.columns
        ]

        if missing:
            raise ValueError(
                "Missing required AURA features: "
                + ", ".join(missing)
            )

        X = X[FEATURES].to_numpy(
            dtype=float
        )

    else:

        X = np.asarray(
            X,
            dtype=float,
        )

    # Handle one-dimensional input.
    if X.ndim == 1:

        if X.size != len(FEATURES):
            raise ValueError(
                f"Expected {len(FEATURES)} features "
                f"({FEATURES}), received {X.size}."
            )

        X = X.reshape(
            1,
            -1,
        )

    if X.ndim != 2:

        raise ValueError(
            "AURA model input must be a 2-dimensional "
            "feature matrix."
        )

    if X.shape[1] != len(FEATURES):

        raise ValueError(
            f"AURA expects {len(FEATURES)} features: "
            f"{FEATURES}. Received {X.shape[1]}."
        )

    if not np.isfinite(X).all():

        raise ValueError(
            "AURA received NaN or infinite sensor values."
        )

    return X


# ============================================================
# CONTAMINATION VALIDATION
# ============================================================

def _validate_contamination(
    contamination: float,
) -> float:
    """
    Validate Isolation Forest / LOF contamination.
    """

    try:
        contamination = float(
            contamination
        )
    except (TypeError, ValueError):

        raise ValueError(
            "Contamination must be a numeric value."
        )

    if not (
        0.0 < contamination <= 0.5
    ):

        raise ValueError(
            "Contamination must be between "
            "0 and 0.5."
        )

    return contamination


# ============================================================
# MODEL TRAINING
# ============================================================

def train_model(
    X,
    contamination: float = DEFAULT_CONTAMINATION,
) -> AURAModel:
    """
    Train the AURA anomaly-detection ensemble.

    Models:
        - StandardScaler
        - Isolation Forest
        - Local Outlier Factor

    The baseline represents normal behaviour observed
    during the AURA baseline-collection phase.
    """

    X = _prepare(X)

    contamination = _validate_contamination(
        contamination
    )

    if len(X) < MIN_BASELINE_SAMPLES:

        raise ValueError(
            f"At least {MIN_BASELINE_SAMPLES} "
            "baseline samples are required."
        )

    # --------------------------------------------------------
    # SCALE FEATURES
    # --------------------------------------------------------

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(
        X
    )

    # --------------------------------------------------------
    # ISOLATION FOREST
    # --------------------------------------------------------

    isolation_forest = IsolationForest(
        n_estimators=ISOLATION_TREES,
        contamination=contamination,
        max_samples="auto",
        max_features=1.0,
        bootstrap=False,
        n_jobs=-1,
        random_state=42,
    )

    isolation_forest.fit(
        X_scaled
    )

    # --------------------------------------------------------
    # LOCAL OUTLIER FACTOR
    # --------------------------------------------------------

    neighbors = max(
        MIN_LOF_NEIGHBORS,
        min(
            MAX_LOF_NEIGHBORS,
            len(X_scaled) - 1,
        ),
    )

    lof = LocalOutlierFactor(
        n_neighbors=neighbors,
        contamination=contamination,
        novelty=True,
        metric="minkowski",
        p=2,
    )

    lof.fit(
        X_scaled
    )

    # --------------------------------------------------------
    # TRAINING SCORE DISTRIBUTIONS
    # --------------------------------------------------------

    if_training_scores = (
        isolation_forest
        .decision_function(
            X_scaled
        )
    )

    lof_training_scores = (
        lof
        .decision_function(
            X_scaled
        )
    )

    # --------------------------------------------------------
    # BASELINE STATISTICS
    # --------------------------------------------------------

    baseline_mean = np.mean(
        X,
        axis=0,
    )

    baseline_std = np.std(
        X,
        axis=0,
    )

    # Prevent zero standard deviation from causing
    # problems in future distance calculations.
    baseline_std = np.where(
        baseline_std < 1e-9,
        1e-9,
        baseline_std,
    )

    return AURAModel(
        scaler=scaler,
        isolation_forest=isolation_forest,
        lof=lof,
        feature_names=tuple(FEATURES),
        training_samples=len(X),
        contamination=contamination,
        lof_neighbors=neighbors,
        baseline_mean=baseline_mean,
        baseline_std=baseline_std,
        if_training_scores=if_training_scores,
        lof_training_scores=lof_training_scores,
    )


# ============================================================
# FEATURE DEVIATION
# ============================================================

def _feature_deviation(
    model: AURAModel,
    X_scaled: np.ndarray,
) -> dict[str, float]:
    """
    Calculate how far the observation is from the learned
    standardized baseline.

    This is useful for explaining WHY an event is unusual.
    """

    values = np.abs(
        X_scaled[0]
    )

    return {
        feature: round(
            float(value),
            3,
        )
        for feature, value in zip(
            FEATURES,
            values,
        )
    }


# ============================================================
# SCORE NORMALIZATION
# ============================================================

def _normalize_if_score(
    score: float,
) -> float:
    """
    Convert Isolation Forest's decision score into a
    dashboard-friendly anomaly intensity.

    Higher value = more anomalous.
    """

    # Isolation Forest decision_function:
    # higher = more normal
    #
    # Convert it into:
    # higher = more anomalous

    anomaly_intensity = 0.5 - float(
        score
    )

    # Typical decision values are around -0.5 to +0.5.
    # Map approximately into 0-100.
    normalized = (
        anomaly_intensity + 0.5
    ) * 100

    return float(
        np.clip(
            normalized,
            0,
            100,
        )
    )


def _normalize_lof_score(
    score: float,
) -> float:
    """
    Convert LOF novelty score into an approximate
    anomaly-intensity scale.

    Higher value = more anomalous.
    """

    # LOF decision_function:
    # higher = more normal
    #
    # A score around 0 generally represents the decision
    # boundary for the fitted model.

    anomaly_intensity = 0.5 - float(
        score
    )

    normalized = (
        anomaly_intensity + 0.5
    ) * 100

    return float(
        np.clip(
            normalized,
            0,
            100,
        )
    )


# ============================================================
# ENSEMBLE CONFIDENCE
# ============================================================

def _ensemble_confidence(
    if_anomaly: int,
    lof_anomaly: int,
    if_intensity: float,
    lof_intensity: float,
) -> float:
    """
    Produce an explainable ensemble confidence value.

    This is NOT a probability of malware.

    It represents agreement/strength of the anomaly detectors.
    """

    detector_agreement = 0.0

    if if_anomaly and lof_anomaly:

        detector_agreement = 1.0

    elif if_anomaly or lof_anomaly:

        detector_agreement = 0.55

    else:

        detector_agreement = 0.0

    intensity = (
        if_intensity
        + lof_intensity
    ) / 2.0

    confidence = (
        detector_agreement * 60
        + intensity * 0.40
    )

    return round(
        float(
            np.clip(
                confidence,
                0,
                100,
            )
        ),
        2,
    )


# ============================================================
# ENSEMBLE RISK
# ============================================================

def _ensemble_risk(
    if_anomaly: int,
    lof_anomaly: int,
    anomaly_confidence: float,
) -> str:
    """
    Convert detector agreement into a simple model-level
    anomaly classification.
    """

    if (
        if_anomaly
        and lof_anomaly
        and anomaly_confidence >= 70
    ):

        return "HIGH"

    if (
        if_anomaly
        or lof_anomaly
    ):

        return "MEDIUM"

    return "NORMAL"


# ============================================================
# DETECTION
# ============================================================

def detect(
    model: AURAModel,
    data,
) -> dict[str, Any]:
    """
    Run the AURA AI anomaly-detection ensemble.

    Returns:
        Isolation Forest result
        LOF result
        combined anomaly
        anomaly intensity
        confidence
        feature deviations
        model metadata
    """

    # --------------------------------------------------------
    # PREPARE INPUT
    # --------------------------------------------------------

    X = _prepare(
        data
        if isinstance(
            data,
            pd.DataFrame,
        )
        else [data]
    )

    # --------------------------------------------------------
    # SCALE
    # --------------------------------------------------------

    X_scaled = (
        model.scaler.transform(
            X
        )
    )

    # --------------------------------------------------------
    # ISOLATION FOREST
    # --------------------------------------------------------

    if_raw = int(
        model.isolation_forest.predict(
            X_scaled
        )[0]
    )

    if_anomaly = int(
        if_raw == -1
    )

    if_score = float(
        model.isolation_forest
        .decision_function(
            X_scaled
        )[0]
    )

    if_intensity = (
        _normalize_if_score(
            if_score
        )
    )

    # --------------------------------------------------------
    # LOF
    # --------------------------------------------------------

    lof_raw = int(
        model.lof.predict(
            X_scaled
        )[0]
    )

    lof_anomaly = int(
        lof_raw == -1
    )

    lof_score = float(
        model.lof.decision_function(
            X_scaled
        )[0]
    )

    lof_intensity = (
        _normalize_lof_score(
            lof_score
        )
    )

    # --------------------------------------------------------
    # ENSEMBLE
    # --------------------------------------------------------

    anomaly = int(
        if_anomaly
        or lof_anomaly
    )

    confidence = (
        _ensemble_confidence(
            if_anomaly=if_anomaly,
            lof_anomaly=lof_anomaly,
            if_intensity=if_intensity,
            lof_intensity=lof_intensity,
        )
    )

    risk = _ensemble_risk(
        if_anomaly=if_anomaly,
        lof_anomaly=lof_anomaly,
        anomaly_confidence=confidence,
    )

    # --------------------------------------------------------
    # FEATURE DEVIATIONS
    # --------------------------------------------------------

    deviations = _feature_deviation(
        model,
        X_scaled,
    )

    # --------------------------------------------------------
    # PRIMARY ANOMALY SIGNAL
    # --------------------------------------------------------

    strongest_feature = max(
        deviations,
        key=deviations.get,
    )

    strongest_deviation = deviations[
        strongest_feature
    ]

    # --------------------------------------------------------
    # EXPLANATION
    # --------------------------------------------------------

    reasons: list[str] = []

    if if_anomaly:

        reasons.append(
            "Isolation Forest identified the "
            "observation as anomalous."
        )

    if lof_anomaly:

        reasons.append(
            "Local Outlier Factor identified "
            "the observation as anomalous."
        )

    if (
        if_anomaly
        and lof_anomaly
    ):

        reasons.append(
            "Both AI detectors agree that the "
            "observation differs from the learned baseline."
        )

    if strongest_deviation >= 3:

        reasons.append(
            f"{strongest_feature} shows a strong "
            "deviation from the learned baseline."
        )

    elif strongest_deviation >= 2:

        reasons.append(
            f"{strongest_feature} shows a noticeable "
            "deviation from the learned baseline."
        )

    if not reasons:

        reasons.append(
            "AI detectors found the current observation "
            "consistent with the learned baseline."
        )

    # --------------------------------------------------------
    # MODEL STATUS
    # --------------------------------------------------------

    model_health = "READY"

    if model.training_samples < MIN_BASELINE_SAMPLES:

        model_health = "INSUFFICIENT_BASELINE"

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {
        # Basic compatibility
        "if_anomaly": if_anomaly,
        "lof_anomaly": lof_anomaly,
        "anomaly": anomaly,

        # Raw model scores
        "if_score": round(
            if_score,
            4,
        ),
        "lof_score": round(
            lof_score,
            4,
        ),

        # Normalized intelligence
        "if_anomaly_intensity": round(
            if_intensity,
            2,
        ),
        "lof_anomaly_intensity": round(
            lof_intensity,
            2,
        ),

        "anomaly_confidence": confidence,

        # Model-level risk
        "risk": risk,

        # Explainability
        "feature_deviations": deviations,

        "strongest_feature": (
            strongest_feature
        ),

        "strongest_feature_deviation": round(
            strongest_deviation,
            3,
        ),

        "reasons": reasons,

        # Metadata
        "model_health": model_health,

        "training_samples": (
            model.training_samples
        ),

        "contamination": (
            model.contamination
        ),

        "lof_neighbors": (
            model.lof_neighbors
        ),

        "features": list(
            model.feature_names
        ),
    }


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def predict(
    model: AURAModel,
    data,
):
    """
    Backward-compatible anomaly prediction.

    Returns:
        1 -> anomaly
        0 -> normal
    """

    return int(
        detect(
            model,
            data,
        )["anomaly"]
    )


# ============================================================
# MODEL INFORMATION
# ============================================================

def get_model_info(
    model: AURAModel,
) -> dict[str, Any]:
    """
    Return model metadata for the AURA dashboard.
    """

    return {
        "status": "READY",

        "algorithms": [
            "Isolation Forest",
            "Local Outlier Factor",
        ],

        "features": list(
            model.feature_names
        ),

        "training_samples": (
            model.training_samples
        ),

        "contamination": (
            model.contamination
        ),

        "lof_neighbors": (
            model.lof_neighbors
        ),

        "isolation_trees": (
            ISOLATION_TREES
        ),
    }


# ============================================================
# ARTIFACT PERSISTENCE HELPERS
# ============================================================

def save_model(
    model: AURAModel,
    dest_path: Path | str,
) -> Path:
    """Serialize AURAModel artifact to disk."""
    from aura.models.persistence import save_model_artifact
    return save_model_artifact(model, dest_path)


def load_model(
    artifact_path: Path | str,
) -> AURAModel:
    """Load persisted AURAModel artifact from disk without retraining."""
    from aura.models.persistence import load_model_artifact
    return load_model_artifact(artifact_path)