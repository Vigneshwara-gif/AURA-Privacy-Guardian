from __future__ import annotations

import time
from statistics import median
from typing import Any

import pandas as pd

from logger import (
    append_log,
    load_baseline,
    load_logs,
    save_baseline,
)

from model import (
    FEATURES,
    detect,
    train_model,
)

from privacy_monitor import (
    get_connection_snapshot,
    get_process_snapshot,
    privacy_risk,
    sensitive_files_in_common_locations,
)

from sensors import (
    get_data,
    get_full_sensor_snapshot,
)


# ============================================================
# AURA PRIVACY GUARDIAN
# CORE INTELLIGENCE ENGINE
# ============================================================
#
# Pipeline:
#
# Sensors
#    ↓
# System telemetry
#    ↓
# ML detection
#    ↓
# Process intelligence
#    ↓
# Network intelligence
#    ↓
# Privacy risk engine
#    ↓
# Unified 0–100 risk score
#    ↓
# Logging + Dashboard
#
# Current ML features:
#     CPU
#     Net
#     Cam
#
# Additional telemetry is used as contextual intelligence.
#
# AURA is a behavioural triage system.
# It does NOT claim proof of malware, spyware, theft,
# or unauthorized access.
# ============================================================


DEFAULT_SAMPLES = 30
DEFAULT_BASELINE_INTERVAL = 0.5


# ============================================================
# SAFE CONVERSION HELPERS
# ============================================================

def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """Safely convert a value to float."""

    try:
        if value is None or pd.isna(value):
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def _safe_int(
    value: Any,
    default: int = 0,
) -> int:
    """Safely convert a value to integer."""

    try:
        if value is None or pd.isna(value):
            return default

        return int(float(value))

    except (TypeError, ValueError):
        return default


def _safe_text(
    value: Any,
    default: str = "",
) -> str:
    """Safely convert a value to text."""

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default

    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    return text if text else default


# ============================================================
# BASELINE COLLECTION
# ============================================================

def collect_baseline(
    samples: int = DEFAULT_SAMPLES,
    interval: float = DEFAULT_BASELINE_INTERVAL,
    probe_camera: bool = False,
) -> pd.DataFrame:
    """
    Collect the normal behavioural baseline used by the
    current AURA ML model.

    ML features:
        CPU
        Net
        Cam
    """

    if samples < 10:
        raise ValueError(
            "AURA requires at least 10 baseline samples."
        )

    readings: list[list[float | int]] = []

    print()
    print("=" * 70)
    print(" AURA PRIVACY GUARDIAN")
    print(" BASELINE COLLECTION")
    print("=" * 70)
    print(
        f" Collecting {samples} normal-operation samples..."
    )
    print(
        " Keep the computer in normal everyday use."
    )
    print()

    for index in range(samples):

        cpu, net, cam = get_data(
            probe_camera=probe_camera
        )

        cpu = _safe_float(cpu)
        net = _safe_float(net)
        cam = _safe_int(cam)

        readings.append(
            [
                cpu,
                net,
                cam,
            ]
        )

        print(
            f" Sample {index + 1:02d}/{samples:02d}"
            f" | CPU {cpu:6.2f}%"
            f" | Upload {net:9.3f} KB/s"
            f" | Camera {cam}"
        )

        if index < samples - 1:

            time.sleep(
                max(
                    _safe_float(
                        interval,
                        0.5,
                    ),
                    0.05,
                )
            )

    baseline = pd.DataFrame(
        readings,
        columns=FEATURES,
    )

    save_baseline(readings)

    print()
    print(" Baseline saved successfully.")
    print("=" * 70)
    print()

    return baseline


# ============================================================
# LOAD OR CREATE BASELINE
# ============================================================

def get_or_create_baseline(
    samples: int = DEFAULT_SAMPLES,
) -> pd.DataFrame:
    """Load a valid baseline or create one if required."""

    baseline = load_baseline()

    if baseline.empty:

        return collect_baseline(
            samples=samples
        )

    missing_features = [
        feature
        for feature in FEATURES
        if feature not in baseline.columns
    ]

    if missing_features:

        print(
            "Existing baseline is missing required "
            "features. Creating a new baseline."
        )

        return collect_baseline(
            samples=samples
        )

    clean = (
        baseline[FEATURES]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
        .dropna()
    )

    if len(clean) >= 10:

        return clean.reset_index(
            drop=True
        )

    print(
        "Existing baseline contains insufficient "
        "valid samples. Creating a new baseline."
    )

    return collect_baseline(
        samples=samples
    )


# ============================================================
# MODEL TRAINING
# ============================================================

def train_aura_model(
    baseline: pd.DataFrame | None = None,
):
    """Train the AURA ML detection engine."""

    if baseline is None:

        baseline = get_or_create_baseline()

    if not isinstance(
        baseline,
        pd.DataFrame,
    ):

        baseline = pd.DataFrame(
            baseline,
            columns=FEATURES,
        )

    missing_features = [
        feature
        for feature in FEATURES
        if feature not in baseline.columns
    ]

    if missing_features:

        raise ValueError(
            "Missing required ML features: "
            f"{missing_features}"
        )

    clean = (
        baseline[FEATURES]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
        .dropna()
    )

    if len(clean) < 10:

        raise ValueError(
            "At least 10 valid baseline samples "
            "are required for AURA training."
        )

    return train_model(clean)


# ============================================================
# PROCESS BASELINE
# ============================================================

def _get_process_baseline() -> float | None:
    """
    Estimate normal process count from recent AURA history.

    A minimum of five valid observations is required.
    """

    try:

        logs = load_logs()

        if logs.empty:
            return None

        if "Process_Count" not in logs.columns:
            return None

        values = pd.to_numeric(
            logs["Process_Count"],
            errors="coerce",
        ).dropna()

        values = values[
            values >= 0
        ]

        if len(values) < 5:
            return None

        recent = values.tail(50)

        return float(
            median(
                recent.tolist()
            )
        )

    except Exception:

        return None


# ============================================================
# CONNECTION STATE COUNTS
# ============================================================

def _connection_state_counts(
    snapshot: dict,
) -> tuple[int, int]:
    """Calculate established and listening connections."""

    established = 0
    listening = 0

    connections = snapshot.get(
        "connections",
        [],
    )

    if not isinstance(
        connections,
        list,
    ):
        return established, listening

    for connection in connections:

        if not isinstance(
            connection,
            dict,
        ):
            continue

        status = _safe_text(
            connection.get(
                "status",
                "",
            )
        ).upper()

        if status == "ESTABLISHED":
            established += 1

        elif status == "LISTEN":
            listening += 1

    return established, listening


# ============================================================
# SENSOR SNAPSHOT FLATTENER
# ============================================================

def _flatten_sensor_snapshot(
    snapshot: dict,
) -> dict[str, Any]:
    """Convert sensor telemetry into stable AURA fields."""

    if not isinstance(
        snapshot,
        dict,
    ):
        snapshot = {}

    cpu = snapshot.get("cpu", {})
    memory = snapshot.get("memory", {})
    disk = snapshot.get("disk", {})
    disk_io = snapshot.get("disk_io", {})
    network = snapshot.get("network", {})
    battery = snapshot.get("battery", {})
    uptime = snapshot.get("uptime", {})
    health = snapshot.get("sensor_health", {})

    if not isinstance(cpu, dict):
        cpu = {}

    if not isinstance(memory, dict):
        memory = {}

    if not isinstance(disk, dict):
        disk = {}

    if not isinstance(disk_io, dict):
        disk_io = {}

    if not isinstance(network, dict):
        network = {}

    if not isinstance(battery, dict):
        battery = {}

    if not isinstance(uptime, dict):
        uptime = {}

    if not isinstance(health, dict):
        health = {}

    return {

        # ----------------------------------------------------
        # ML FEATURES
        # ----------------------------------------------------

        "CPU": _safe_float(
            cpu.get(
                "usage_percent",
                0.0,
            )
        ),

        "Net": _safe_float(
            network.get(
                "upload_kbps",
                0.0,
            )
        ),

        "Cam": _safe_int(
            snapshot.get(
                "camera_available",
                0,
            )
        ),

        # ----------------------------------------------------
        # MEMORY
        # ----------------------------------------------------

        "Memory": _safe_float(
            memory.get(
                "usage_percent",
                0.0,
            )
        ),

        "Memory_Available": _safe_float(
            memory.get(
                "available_gb",
                0.0,
            )
        ),

        # ----------------------------------------------------
        # DISK
        # ----------------------------------------------------

        "Disk": _safe_float(
            disk.get(
                "usage_percent",
                0.0,
            )
        ),

        "Disk_Read": _safe_float(
            disk_io.get(
                "read_mbps",
                0.0,
            )
        ),

        "Disk_Write": _safe_float(
            disk_io.get(
                "write_mbps",
                0.0,
            )
        ),

        # ----------------------------------------------------
        # CPU
        # ----------------------------------------------------

        "CPU_Frequency": _safe_float(
            cpu.get(
                "frequency_mhz",
                0.0,
            )
        ),

        # ----------------------------------------------------
        # NETWORK
        # ----------------------------------------------------

        "Network_Download": _safe_float(
            network.get(
                "download_kbps",
                0.0,
            )
        ),

        "Network_Upload": _safe_float(
            network.get(
                "upload_kbps",
                0.0,
            )
        ),

        # ----------------------------------------------------
        # BATTERY
        # ----------------------------------------------------

        "Battery_Percent":
            battery.get("percent"),

        "Battery_Status":
            _safe_text(
                battery.get(
                    "status",
                    "NOT_AVAILABLE",
                )
            ),

        # ----------------------------------------------------
        # UPTIME
        # ----------------------------------------------------

        "Uptime":
            _safe_text(
                uptime.get(
                    "uptime_text",
                    "UNKNOWN",
                )
            ),

        # ----------------------------------------------------
        # SENSOR HEALTH
        # ----------------------------------------------------

        "Sensor_Health":
            _safe_float(
                health.get(
                    "health_percent",
                    0.0,
                )
            ),

        "Sensors_Available":
            _safe_int(
                health.get(
                    "available_sensors",
                    0,
                )
            ),

        "Sensors_Total":
            _safe_int(
                health.get(
                    "total_sensors",
                    0,
                )
            ),
    }


# ============================================================
# ML METRICS
# ============================================================

def _calculate_anomaly_metrics(
    result: dict,
) -> dict[str, float]:
    """
    Provide explainable ML metrics.

    IF and LOF decision scores are model margins,
    not probabilities.
    """

    if_score = _safe_float(
        result.get(
            "if_score",
            0.0,
        )
    )

    lof_score = _safe_float(
        result.get(
            "lof_score",
            0.0,
        )
    )

    if_anomaly = _safe_int(
        result.get(
            "if_anomaly",
            0,
        )
    )

    lof_anomaly = _safe_int(
        result.get(
            "lof_anomaly",
            0,
        )
    )

    if_intensity = round(
        min(
            abs(if_score) * 100.0,
            100.0,
        ),
        2,
    )

    lof_intensity = round(
        min(
            abs(lof_score) * 100.0,
            100.0,
        ),
        2,
    )

    if (
        if_anomaly
        and lof_anomaly
    ):
        confidence = 100.0

    elif (
        if_anomaly
        or lof_anomaly
    ):
        confidence = 60.0

    else:
        confidence = 0.0

    return {
        "IF_Anomaly_Intensity": if_intensity,
        "LOF_Anomaly_Intensity": lof_intensity,
        "Anomaly_Confidence": confidence,
    }


# ============================================================
# ONE COMPLETE AURA SCAN
# ============================================================

def scan_once(
    model,
    probe_camera: bool = False,
    synthetic: dict | None = None,
    persist: bool = True,
) -> dict:
    """
    Run one complete AURA scan.

    Live mode:
        Uses actual Windows telemetry.

    Synthetic mode:
        Uses safe abnormal values for demonstration only.

    When ``persist`` is False the scan result is not written
    to the monitoring log, so demonstration or test scans
    cannot contaminate production history.
    """

    # ========================================================
    # 1. SENSOR COLLECTION
    # ========================================================

    sensor_snapshot = get_full_sensor_snapshot(
        probe_camera=(
            probe_camera
            if synthetic is None
            else False
        )
    )

    telemetry = _flatten_sensor_snapshot(
        sensor_snapshot
    )

    # ========================================================
    # 2. SYNTHETIC DEMONSTRATION OVERRIDE
    # ========================================================

    is_demo = synthetic is not None

    if synthetic is not None:

        if not isinstance(
            synthetic,
            dict,
        ):
            raise TypeError(
                "synthetic must be a dictionary."
            )

        telemetry["CPU"] = _safe_float(
            synthetic.get(
                "CPU",
                telemetry["CPU"],
            ),
            telemetry["CPU"],
        )

        telemetry["Net"] = _safe_float(
            synthetic.get(
                "Net",
                telemetry["Net"],
            ),
            telemetry["Net"],
        )

        telemetry["Cam"] = _safe_int(
            synthetic.get(
                "Cam",
                telemetry["Cam"],
            ),
            telemetry["Cam"],
        )

    cpu = telemetry["CPU"]
    net = telemetry["Net"]
    cam = telemetry["Cam"]

    # ========================================================
    # 3. ML DETECTION
    # ========================================================

    ml_result = detect(
        model,
        [
            cpu,
            net,
            cam,
        ],
    )

    anomaly_metrics = (
        _calculate_anomaly_metrics(
            ml_result
        )
    )

    # ========================================================
    # 4. PROCESS INTELLIGENCE
    # ========================================================

    processes = get_process_snapshot()

    process_count = _safe_int(
        processes.get(
            "process_count",
            0,
        )
    )

    process_baseline = (
        _get_process_baseline()
    )

    # ========================================================
    # 5. NETWORK INTELLIGENCE
    # ========================================================

    connections = get_connection_snapshot()

    connection_count = _safe_int(
        connections.get(
            "connection_count",
            0,
        )
    )

    remote_connections = _safe_int(
        connections.get(
            "remote_connection_count",
            0,
        )
    )

    (
        established_connections,
        listening_connections,
    ) = _connection_state_counts(
        connections
    )

    # ========================================================
    # 6. SENSITIVE FILE INVENTORY
    # ========================================================

    sensitive_paths = (
        sensitive_files_in_common_locations()
    )

    sensitive_count = len(
        sensitive_paths
    )

    # ========================================================
    # 7. UNIFIED PRIVACY RISK
    # ========================================================

    privacy = privacy_risk(
        ml_anomaly=_safe_int(
            ml_result.get(
                "anomaly",
                0,
            )
        ),
        net_kbps=net,
        process_count=process_count,
        baseline_process_count=process_baseline,
        remote_connection_count=remote_connections,
        camera_available=cam,
    )

    # ========================================================
    # 8. CAMERA SAFETY
    # ========================================================

    reasons = privacy.get(
        "reasons",
        [],
    )

    if isinstance(
        reasons,
        str,
    ):
        reasons = [reasons]

    privacy["reasons"] = [
        reason
        for reason in reasons
        if "camera" not in str(
            reason
        ).lower()
    ]

    if not privacy["reasons"]:

        privacy["reasons"] = [
            (
                "No significant privacy-related "
                "deviation detected."
            )
        ]

    # ========================================================
    # 9. MODEL HEALTH
    # ========================================================

    try:

        baseline = load_baseline()

        training_samples = len(
            baseline
        )

        if training_samples >= 30:
            model_health = "HEALTHY"

        elif training_samples >= 10:
            model_health = "LIMITED"

        else:
            model_health = "INSUFFICIENT"

    except Exception:

        training_samples = 0
        model_health = "UNKNOWN"

    # ========================================================
    # 10. AUTHORITATIVE RISK RESULT
    # ========================================================
    #
    # IMPORTANT:
    #
    # privacy_monitor.py is now the SINGLE source of truth.
    #
    # We DO NOT downgrade LOW to NORMAL.
    # We DO NOT downgrade CRITICAL to HIGH.
    #
    # The exact 0–100 score and severity are preserved.
    # ========================================================

    risk_score = max(
        0,
        min(
            _safe_int(
                privacy.get(
                    "risk_score",
                    0,
                )
            ),
            100,
        ),
    )

    risk = _safe_text(
        privacy.get(
            "risk",
            "NORMAL",
        ),
        "NORMAL",
    ).upper()

    valid_levels = {
        "NORMAL",
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }

    if risk not in valid_levels:

        # Defensive fallback only.
        if risk_score >= 80:
            risk = "CRITICAL"

        elif risk_score >= 55:
            risk = "HIGH"

        elif risk_score >= 25:
            risk = "MEDIUM"

        elif risk_score >= 10:
            risk = "LOW"

        else:
            risk = "NORMAL"

    # ========================================================
    # 11. SEVERITY
    # ========================================================

    severity_map = {
        "NORMAL": "INFO",
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
        "CRITICAL": "CRITICAL",
    }

    severity = severity_map.get(
        risk,
        "INFO",
    )

    # ========================================================
    # 12. STATUS TEXT
    # ========================================================

    if risk == "CRITICAL":

        status = "CRITICAL"

        status_message = (
            "Multiple high-severity indicators "
            "require immediate investigation."
        )

    elif risk == "HIGH":

        status = "HIGH RISK"

        status_message = (
            "Significant abnormal behaviour detected. "
            "Review the security evidence."
        )

    elif risk == "MEDIUM":

        status = "ATTENTION"

        status_message = (
            "Unusual activity detected. "
            "Review the available evidence."
        )

    elif risk == "LOW":

        status = "MONITORING"

        status_message = (
            "Minor behavioural deviation detected."
        )

    else:

        status = "PROTECTED"

        status_message = (
            "No significant privacy-related "
            "deviation detected."
        )

    # ========================================================
    # 13. LOGGING
    # ========================================================

    append_log(
        cpu=cpu,
        net=net,
        cam=cam,

        if_anomaly=_safe_int(
            ml_result.get(
                "if_anomaly",
                0,
            )
        ),

        lof_anomaly=_safe_int(
            ml_result.get(
                "lof_anomaly",
                0,
            )
        ),

        anomaly=_safe_int(
            ml_result.get(
                "anomaly",
                0,
            )
        ),

        risk=risk,

        process_count=process_count,

        remote_connections=remote_connections,

        sensitive_files=sensitive_count,

        risk_score=risk_score,

        network_level=_safe_text(
            privacy.get(
                "network_label",
                "NORMAL",
            ),
            "NORMAL",
        ),

        privacy_event=_safe_int(
            privacy.get(
                "privacy_event",
                0,
            )
        ),

        potential_data_exfiltration=int(
            bool(
                privacy.get(
                    "potential_data_exfiltration",
                    False,
                )
            )
        ),

        # ------------------------------------------------
        # Extended telemetry (F9 fix — these 20 fields
        # were computed but not passed, so every row after
        # 2026-08-19 20:39:46 recorded them as 0.0 or
        # "UNKNOWN").
        # ------------------------------------------------

        memory=_safe_float(
            telemetry.get("Memory", 0.0)
        ),

        disk=_safe_float(
            telemetry.get("Disk", 0.0)
        ),

        disk_read=_safe_float(
            telemetry.get("Disk_Read", 0.0)
        ),

        disk_write=_safe_float(
            telemetry.get("Disk_Write", 0.0)
        ),

        cpu_frequency=_safe_float(
            telemetry.get("CPU_Frequency", 0.0)
        ),

        network_download=_safe_float(
            telemetry.get(
                "Network_Download", 0.0
            )
        ),

        network_upload=_safe_float(
            telemetry.get(
                "Network_Upload", 0.0
            )
        ),

        established_connections=(
            established_connections
        ),

        listening_connections=(
            listening_connections
        ),

        # AI intelligence

        if_score=_safe_float(
            ml_result.get("if_score", 0.0)
        ),

        lof_score=_safe_float(
            ml_result.get("lof_score", 0.0)
        ),

        if_anomaly_intensity=_safe_float(
            ml_result.get(
                "if_anomaly_intensity", 0.0
            )
        ),

        lof_anomaly_intensity=_safe_float(
            ml_result.get(
                "lof_anomaly_intensity", 0.0
            )
        ),

        anomaly_confidence=_safe_float(
            ml_result.get(
                "anomaly_confidence", 0.0
            )
        ),

        strongest_feature=_safe_text(
            ml_result.get(
                "strongest_feature", ""
            ),
            "",
        ),

        strongest_feature_deviation=_safe_float(
            ml_result.get(
                "strongest_feature_deviation",
                0.0,
            )
        ),

        # Risk intelligence

        severity=severity,

        process_level=_safe_text(
            privacy.get(
                "process_label",
                "NORMAL",
            ),
            "NORMAL",
        ),

        potential_camera_risk=int(
            bool(
                privacy.get(
                    "potential_camera_risk",
                    False,
                )
            )
        ),

        behavioral_adjustment=0,

        # Model information

        model_health=model_health,

        training_samples=training_samples,
    )

    # ========================================================
    # 14. FINAL RESULT
    # ========================================================

    return {

        # ----------------------------------------------------
        # Core ML inputs
        # ----------------------------------------------------

        "CPU": cpu,
        "Net": net,
        "Cam": cam,

        # ----------------------------------------------------
        # Complete telemetry
        # ----------------------------------------------------

        **telemetry,

        # ----------------------------------------------------
        # Process intelligence
        # ----------------------------------------------------

        "Process_Count":
            process_count,

        "Process_Baseline":
            process_baseline,

        "Process_Names":
            sorted(
                list(
                    processes.get(
                        "process_names",
                        set(),
                    )
                )
            )[:100],

        # ----------------------------------------------------
        # Network intelligence
        # ----------------------------------------------------

        "Connection_Count":
            connection_count,

        "Remote_Connections":
            remote_connections,

        "Established_Connections":
            established_connections,

        "Listening_Connections":
            listening_connections,

        "Remote_Endpoints":
            connections.get(
                "remote_endpoints",
                [],
            ),

        # ----------------------------------------------------
        # Privacy inventory
        # ----------------------------------------------------

        "Sensitive_Files":
            sensitive_count,

        "Sensitive_File_Paths":
            sensitive_paths,

        # ----------------------------------------------------
        # ML results
        # ----------------------------------------------------

        **ml_result,

        **anomaly_metrics,

        # ----------------------------------------------------
        # Privacy risk
        # ----------------------------------------------------

        **privacy,

        # ----------------------------------------------------
        # Authoritative risk information
        # ----------------------------------------------------

        "Risk_Score": risk_score,

        "Risk_Level": risk,

        "Severity": severity,

        "Status": status,

        "Status_Message": status_message,

        # ----------------------------------------------------
        # Model metadata
        # ----------------------------------------------------

        "Model_Health":
            model_health,

        "Training_Samples":
            training_samples,

        "Is_Demo":
            is_demo,

        # ----------------------------------------------------
        # Explicit ML feature declaration
        # ----------------------------------------------------

        "ML_Features": {
            "CPU": cpu,
            "Net": net,
            "Cam": cam,
        },

        # ----------------------------------------------------
        # Raw sensor snapshot
        # ----------------------------------------------------

        "Sensor_Snapshot":
            sensor_snapshot,
    }


# ============================================================
# TERMINAL MONITORING
# ============================================================

def run_terminal_monitoring(
    samples: int = DEFAULT_SAMPLES,
    interval: float = 1.0,
    probe_camera: bool = False,
):
    """Run continuous AURA monitoring in the terminal."""

    baseline = get_or_create_baseline(
        samples
    )

    model = train_model(
        baseline
    )

    print()
    print("=" * 90)
    print(" AURA PRIVACY GUARDIAN")
    print(" PROFESSIONAL LIVE MONITORING")
    print("=" * 90)
    print(" Press Ctrl+C to stop.")
    print()

    try:

        while True:

            result = scan_once(
                model,
                probe_camera=probe_camera,
            )

            risk = _safe_text(
                result.get(
                    "Risk_Level",
                    result.get(
                        "risk",
                        "NORMAL",
                    ),
                ),
                "NORMAL",
            ).upper()

            anomaly = _safe_int(
                result.get(
                    "anomaly",
                    0,
                )
            )

            icon = (
                "⚠️"
                if anomaly
                else "✅"
            )

            print(
                f"{icon} {risk:8s}"
                f" | CPU {result['CPU']:6.2f}%"
                f" | RAM {result.get('Memory', 0):6.2f}%"
                f" | UP {result['Net']:9.3f} KB/s"
                f" | DOWN "
                f"{result.get('Network_Download', 0):9.3f} KB/s"
                f" | PROC "
                f"{result['Process_Count']:4d}"
                f" | REMOTE "
                f"{result['Remote_Connections']:3d}"
                f" | SCORE "
                f"{result['Risk_Score']:3d}/100"
            )

            time.sleep(
                max(
                    _safe_float(
                        interval,
                        1.0,
                    ),
                    0.1,
                )
            )

    except KeyboardInterrupt:

        print()
        print("=" * 90)
        print(" AURA MONITORING STOPPED")
        print("=" * 90)


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    run_terminal_monitoring()