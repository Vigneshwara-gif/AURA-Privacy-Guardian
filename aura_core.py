from __future__ import annotations

import time

import pandas as pd

from logger import append_log, load_baseline, save_baseline
from model import FEATURES, detect, train_model
from privacy_monitor import (
    get_connection_snapshot,
    get_process_snapshot,
    privacy_risk,
    sensitive_files_in_common_locations,
)
from sensors import get_data


DEFAULT_SAMPLES = 30


def collect_baseline(samples: int = DEFAULT_SAMPLES, interval: float = 0.5, probe_camera: bool = False):
    readings = []

    print("=== AURA BASELINE COLLECTION ===")
    print(f"Collecting {samples} samples...")

    for i in range(samples):
        cpu, net, cam = get_data(probe_camera=probe_camera)
        readings.append([cpu, net, cam])
        print(
            f"Sample {i + 1:02d}/{samples} | "
            f"CPU: {cpu:6.2f}% | Net: {net:8.3f} KB/s | Cam: {cam}"
        )
        time.sleep(interval)

    df = pd.DataFrame(readings, columns=FEATURES)
    save_baseline(readings)
    return df


def get_or_create_baseline(samples: int = DEFAULT_SAMPLES):
    baseline = load_baseline()
    if len(baseline) >= 10:
        return baseline[FEATURES]
    return collect_baseline(samples=samples)


def train_aura_model(baseline=None):
    if baseline is None:
        baseline = get_or_create_baseline()
    return train_model(baseline[FEATURES])


def scan_once(model, probe_camera: bool = False, synthetic: dict | None = None) -> dict:
    """
    Run one AURA scan.

    `synthetic` is intentionally supported for a safe demonstration/testing
    mode; it lets the dashboard test detection without changing the machine.
    """
    if synthetic:
        cpu = float(synthetic.get("CPU", 95.0))
        net = float(synthetic.get("Net", 5000.0))
        cam = int(synthetic.get("Cam", 0))
    else:
        cpu, net, cam = get_data(probe_camera=probe_camera)

    result = detect(model, [cpu, net, cam])

    processes = get_process_snapshot()
    connections = get_connection_snapshot()
    sensitive_count = len(sensitive_files_in_common_locations())

    baseline_process_count = None
    privacy = privacy_risk(
        ml_anomaly=result["anomaly"],
        net_kbps=net,
        process_count=processes["process_count"],
        baseline_process_count=baseline_process_count,
        remote_connection_count=connections["remote_connection_count"],
        camera_available=cam,
    )

    # For live runs, avoid calling camera availability itself a privacy threat.
    if cam:
        privacy["reasons"] = [
            r for r in privacy["reasons"] if "camera" not in r.lower()
        ] or privacy["reasons"]

    append_log(
        cpu=cpu,
        net=net,
        cam=cam,
        if_anomaly=result["if_anomaly"],
        lof_anomaly=result["lof_anomaly"],
        anomaly=result["anomaly"],
        risk=privacy["risk"],
        process_count=processes["process_count"],
        remote_connections=connections["remote_connection_count"],
        sensitive_files=sensitive_count,
        risk_score=privacy["risk_score"],
        network_level=privacy["network_label"],
        privacy_event=int(privacy["privacy_event"]),
        potential_data_exfiltration=int(privacy["potential_data_exfiltration"]),
    )

    return {
        "CPU": cpu,
        "Net": net,
        "Cam": cam,
        "Process_Count": processes["process_count"],
        "Remote_Connections": connections["remote_connection_count"],
        "Sensitive_Files": sensitive_count,
        "Remote_Endpoints": connections["remote_endpoints"],
        **result,
        **privacy,
    }


def run_terminal_monitoring(samples: int = DEFAULT_SAMPLES, interval: float = 1.0, probe_camera: bool = False):
    baseline = get_or_create_baseline(samples)
    model = train_model(baseline)

    print("\n=== AURA LIVE MONITORING STARTED ===")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            result = scan_once(model, probe_camera=probe_camera)
            icon = "⚠️" if result["anomaly"] else "✅"
            print(
                f"{icon} {result['risk']:6s} | "
                f"CPU:{result['CPU']:6.2f}% | "
                f"Net:{result['Net']:8.3f} KB/s | "
                f"Processes:{result['Process_Count']} | "
                f"Remote:{result['Remote_Connections']} | "
                f"Risk score:{result['risk_score']}"
            )
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n=== AURA MONITORING STOPPED ===")


if __name__ == "__main__":
    run_terminal_monitoring()
