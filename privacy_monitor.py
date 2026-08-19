from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import psutil


SENSITIVE_EXTENSIONS = {
    ".doc", ".docx", ".pdf", ".xls", ".xlsx", ".csv", ".txt",
    ".ppt", ".pptx", ".sql", ".db", ".sqlite", ".json",
    ".key", ".pem", ".env",
}

COMMON_SENSITIVE_DIRS = {
    "documents", "desktop", "downloads", "pictures",
}


def get_process_snapshot() -> dict[str, Any]:
    """Return a lightweight snapshot of running processes."""
    processes = []
    names = set()

    for proc in psutil.process_iter(["pid", "name", "username"]):
        try:
            info = proc.info
            name = info.get("name") or "unknown"
            names.add(name.lower())
            processes.append({
                "pid": info.get("pid"),
                "name": name,
                "username": info.get("username"),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {
        "process_count": len(processes),
        "process_names": names,
        "processes": processes,
    }


def get_connection_snapshot() -> dict[str, Any]:
    """Return current network connection counts and remote endpoints."""
    total = 0
    remote = 0
    endpoints = []

    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, OSError):
        connections = []

    for conn in connections:
        if conn.status:
            total += 1
        if conn.raddr:
            remote += 1
            try:
                ip = conn.raddr.ip
                port = conn.raddr.port
                endpoints.append(f"{ip}:{port}")
            except AttributeError:
                pass

    return {
        "connection_count": total,
        "remote_connection_count": remote,
        "remote_endpoints": endpoints[:50],
    }


def classify_network_activity(net_kbps: float) -> str:
    """Heuristic label; thresholds are demo-oriented, not forensic proof."""
    if net_kbps >= 5000:
        return "VERY_HIGH"
    if net_kbps >= 1000:
        return "HIGH"
    if net_kbps >= 100:
        return "ELEVATED"
    return "NORMAL"


def classify_process_activity(process_count: int, baseline_count: float | None) -> str:
    if baseline_count is None:
        return "NORMAL"
    if process_count > baseline_count * 1.75:
        return "ELEVATED"
    if process_count > baseline_count * 1.35:
        return "WATCH"
    return "NORMAL"


def privacy_risk(
    ml_anomaly: int,
    net_kbps: float,
    process_count: int,
    baseline_process_count: float | None,
    remote_connection_count: int,
    camera_available: int,
) -> dict[str, Any]:
    """
    Combine ML and privacy-relevant runtime indicators.

    This produces a triage signal, not a forensic/security verdict.
    """
    reasons = []
    score = 0

    if ml_anomaly:
        score += 2
        reasons.append("ML anomaly detected")

    network_label = classify_network_activity(net_kbps)
    if network_label == "VERY_HIGH":
        score += 3
        reasons.append("very high outbound network activity")
    elif network_label == "HIGH":
        score += 2
        reasons.append("high outbound network activity")
    elif network_label == "ELEVATED":
        score += 1
        reasons.append("elevated outbound network activity")

    process_label = classify_process_activity(process_count, baseline_process_count)
    if process_label == "ELEVATED":
        score += 2
        reasons.append("unusual process-count increase")
    elif process_label == "WATCH":
        score += 1
        reasons.append("process-count increase")

    if remote_connection_count >= 30:
        score += 1
        reasons.append("many active remote connections")

    # Camera availability is informational; it is NOT treated as evidence
    # of unauthorized camera access.
    camera_status = "AVAILABLE" if camera_available else "NOT_DETECTED"

    if score >= 5:
        risk = "HIGH"
    elif score >= 2:
        risk = "MEDIUM"
    else:
        risk = "NORMAL"

    privacy_event = (
        score >= 2
        and (
            network_label in {"HIGH", "VERY_HIGH"}
            or process_label in {"WATCH", "ELEVATED"}
            or ml_anomaly
        )
    )

    return {
        "risk_score": score,
        "risk": risk,
        "reasons": reasons or ["no significant privacy-related deviation"],
        "network_label": network_label,
        "process_label": process_label,
        "camera_status": camera_status,
        "potential_data_exfiltration": bool(
            net_kbps >= 1000 and (ml_anomaly or process_label != "NORMAL")
        ),
        "potential_camera_risk": False,
        "privacy_event": privacy_event,
    }


def sensitive_files_in_common_locations() -> list[str]:
    """
    Return existing sensitive-looking file paths in common user folders.

    This is inventory only. It does not read file contents and does not
    claim that a file has been leaked.
    """
    home = Path.home()
    results = []

    for dirname in COMMON_SENSITIVE_DIRS:
        folder = home / dirname
        if not folder.exists():
            continue

        try:
            for path in folder.iterdir():
                if path.is_file() and path.suffix.lower() in SENSITIVE_EXTENSIONS:
                    results.append(str(path))
        except (PermissionError, OSError):
            continue

    return results[:100]


def snapshot_privacy_context(net_kbps: float, camera_available: int) -> dict[str, Any]:
    processes = get_process_snapshot()
    connections = get_connection_snapshot()

    return {
        "process_count": processes["process_count"],
        "process_names": sorted(processes["process_names"])[:100],
        "connection_count": connections["connection_count"],
        "remote_connection_count": connections["remote_connection_count"],
        "remote_endpoints": connections["remote_endpoints"],
        "sensitive_file_count": len(sensitive_files_in_common_locations()),
        "camera_available": camera_available,
    }
