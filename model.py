from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler


FEATURES = ["CPU", "Net", "Cam"]


@dataclass
class AURAModel:
    scaler: StandardScaler
    isolation_forest: IsolationForest
    lof: LocalOutlierFactor


def _prepare(X) -> np.ndarray:
    if isinstance(X, pd.DataFrame):
        X = X[FEATURES]
    return np.asarray(X, dtype=float)


def train_model(X, contamination: float = 0.10) -> AURAModel:
    """Train Isolation Forest and LOF on baseline sensor data."""
    X = _prepare(X)

    if len(X) < 10:
        raise ValueError("At least 10 baseline samples are required.")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    isolation_forest = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )
    isolation_forest.fit(X_scaled)

    neighbors = max(2, min(20, len(X_scaled) - 1))
    lof = LocalOutlierFactor(
        n_neighbors=neighbors,
        contamination=contamination,
        novelty=True,
    )
    lof.fit(X_scaled)

    return AURAModel(scaler, isolation_forest, lof)


def detect(model: AURAModel, data) -> dict:
    """Run Isolation Forest and LOF and return a combined decision."""
    X = _prepare([data]) if not isinstance(data, pd.DataFrame) else _prepare(data)
    X_scaled = model.scaler.transform(X)

    if_raw = int(model.isolation_forest.predict(X_scaled)[0])
    lof_raw = int(model.lof.predict(X_scaled)[0])

    if_anomaly = int(if_raw == -1)
    lof_anomaly = int(lof_raw == -1)
    anomaly = int(if_anomaly or lof_anomaly)

    if_score = float(model.isolation_forest.decision_function(X_scaled)[0])
    lof_score = float(model.lof.decision_function(X_scaled)[0])

    if if_anomaly and lof_anomaly:
        risk = "HIGH"
    elif anomaly:
        risk = "MEDIUM"
    else:
        risk = "NORMAL"

    return {
        "if_anomaly": if_anomaly,
        "lof_anomaly": lof_anomaly,
        "anomaly": anomaly,
        "if_score": round(if_score, 4),
        "lof_score": round(lof_score, 4),
        "risk": risk,
    }


def predict(model: AURAModel, data):
    """Backward-compatible anomaly prediction."""
    return detect(model, data)["anomaly"]
