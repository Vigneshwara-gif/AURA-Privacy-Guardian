from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "system_logs.csv"
BASELINE_FILE = DATA_DIR / "baseline.csv"

COLUMNS = [
    "Timestamp", "CPU", "Net", "Cam",
    "Process_Count", "Remote_Connections", "Sensitive_Files",
    "IF_Anomaly", "LOF_Anomaly", "Anomaly",
    "Risk", "Risk_Score", "Network_Level", "Privacy_Event",
    "Potential_Data_Exfiltration",
]


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_baseline(data, filename: Optional[str] = None) -> Path:
    _ensure_data_dir()
    path = Path(filename) if filename else BASELINE_FILE
    rows = list(data)
    pd.DataFrame(rows, columns=["CPU", "Net", "Cam"]).to_csv(path, index=False)
    return path


def load_baseline(filename: Optional[str] = None) -> pd.DataFrame:
    path = Path(filename) if filename else BASELINE_FILE
    if not path.exists():
        return pd.DataFrame(columns=["CPU", "Net", "Cam"])
    return pd.read_csv(path)


def append_log(
    cpu: float,
    net: float,
    cam: int,
    if_anomaly: int = 0,
    lof_anomaly: int = 0,
    anomaly: int = 0,
    risk: str = "NORMAL",
    process_count: int = 0,
    remote_connections: int = 0,
    sensitive_files: int = 0,
    risk_score: int = 0,
    network_level: str = "NORMAL",
    privacy_event: int = 0,
    potential_data_exfiltration: int = 0,
    filename: Optional[str] = None,
) -> Path:
    _ensure_data_dir()
    path = Path(filename) if filename else LOG_FILE

    row = pd.DataFrame([{
        "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "CPU": cpu,
        "Net": net,
        "Cam": cam,
        "Process_Count": process_count,
        "Remote_Connections": remote_connections,
        "Sensitive_Files": sensitive_files,
        "IF_Anomaly": if_anomaly,
        "LOF_Anomaly": lof_anomaly,
        "Anomaly": anomaly,
        "Risk": risk,
        "Risk_Score": risk_score,
        "Network_Level": network_level,
        "Privacy_Event": privacy_event,
        "Potential_Data_Exfiltration": potential_data_exfiltration,
    }])

    if path.exists():
        row.to_csv(path, mode="a", header=False, index=False)
    else:
        row.to_csv(path, index=False)

    return path


def load_logs(filename: Optional[str] = None) -> pd.DataFrame:
    path = Path(filename) if filename else LOG_FILE
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(path)
    # Older logs are still readable; missing new fields get safe defaults.
    defaults = {
        "Process_Count": 0, "Remote_Connections": 0, "Sensitive_Files": 0,
        "Risk_Score": 0, "Network_Level": "NORMAL", "Privacy_Event": 0,
        "Potential_Data_Exfiltration": 0,
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    return df


def save_data(data, filename="data/system_logs.csv"):
    _ensure_data_dir()
    df = pd.DataFrame(data, columns=["CPU", "Net", "Cam"])
    df.to_csv(filename, index=False)
