from __future__ import annotations

import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

import psutil


# ============================================================
# AURA PRIVACY GUARDIAN
# PRIVACY INTELLIGENCE ENGINE
# ============================================================
#
# Purpose:
#   • Real Windows process telemetry
#   • Real network connection telemetry
#   • Sensitive-file inventory
#   • Behavioural classification
#   • Explainable 0–100 privacy risk scoring
#
# IMPORTANT:
# AURA is a behavioural triage system.
# It does NOT prove malware, spyware, data theft,
# unauthorized access, or system compromise.
#
# Every telemetry value collected here comes from the
# local Windows system through psutil / filesystem APIs.
# ============================================================


# ============================================================
# FILE INTELLIGENCE CONFIGURATION
# ============================================================

SENSITIVE_EXTENSIONS = {
    # Documents
    ".doc",
    ".docx",
    ".pdf",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".rtf",
    ".txt",
    ".md",

    # Structured data
    ".csv",
    ".json",
    ".xml",
    ".yaml",
    ".yml",

    # Databases
    ".db",
    ".sqlite",
    ".sqlite3",
    ".sql",

    # Configuration / secrets
    ".env",
    ".ini",
    ".cfg",
    ".conf",
    ".config",

    # Cryptographic / credential material
    ".key",
    ".pem",
    ".crt",
    ".cer",
    ".p12",
    ".pfx",

    # Source code
    ".py",
    ".java",
    ".js",
    ".ts",
    ".cpp",
    ".c",
    ".h",
}


SENSITIVE_CATEGORIES = {
    "documents": {
        ".doc",
        ".docx",
        ".pdf",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".rtf",
    },

    "data": {
        ".csv",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".txt",
        ".md",
    },

    "database": {
        ".db",
        ".sqlite",
        ".sqlite3",
        ".sql",
    },

    "credentials": {
        ".env",
        ".key",
        ".pem",
        ".p12",
        ".pfx",
    },

    "source_code": {
        ".py",
        ".java",
        ".js",
        ".ts",
        ".cpp",
        ".c",
        ".h",
    },
}


COMMON_SENSITIVE_DIRS = {
    "documents",
    "desktop",
    "downloads",
    "pictures",
}


MAX_FILES_SCANNED = 2500
MAX_FILE_RESULTS = 250
MAX_ENDPOINTS = 100
MAX_CONNECTION_RECORDS = 150


# ============================================================
# NETWORK & CONNECTION THRESHOLDS (CONSOLIDATED)
# ============================================================
#
# Sourced from structured configuration (aura/core/config.py).
# ============================================================

try:
    from aura.core.config import get_settings
    _cfg = get_settings()
    NETWORK_ELEVATED = float(_cfg.risk.network.elevated_kbps)
    NETWORK_HIGH = float(_cfg.risk.network.high_kbps)
    NETWORK_VERY_HIGH = float(_cfg.risk.network.very_high_kbps)

    REMOTE_CONNECTION_WATCH = int(_cfg.risk.connections.watch)
    REMOTE_CONNECTION_HIGH = int(_cfg.risk.connections.high)
    REMOTE_CONNECTION_VERY_HIGH = int(_cfg.risk.connections.very_high)
except Exception:
    NETWORK_ELEVATED = 100.0
    NETWORK_HIGH = 1000.0
    NETWORK_VERY_HIGH = 5000.0

    REMOTE_CONNECTION_WATCH = 30
    REMOTE_CONNECTION_HIGH = 75
    REMOTE_CONNECTION_VERY_HIGH = 150



# ============================================================
# PROCESS MONITORING
# ============================================================

def get_process_snapshot() -> dict[str, Any]:
    """
    Collect a real-time snapshot of running processes.

    Uses psutil to query Windows process information.

    Access-denied, terminated, and protected processes are
    safely skipped.
    """

    processes: list[dict[str, Any]] = []
    names: set[str] = set()

    aggregate_cpu = 0.0
    aggregate_memory = 0.0

    try:
        iterator = psutil.process_iter(
            [
                "pid",
                "name",
                "username",
                "status",
                "cpu_percent",
                "memory_percent",
                "create_time",
            ]
        )

        for proc in iterator:

            try:
                info = proc.info

                pid = info.get("pid")
                name = (
                    info.get("name")
                    or "unknown"
                )

                username = info.get(
                    "username"
                )

                status = (
                    info.get("status")
                    or "unknown"
                )

                cpu = float(
                    info.get("cpu_percent")
                    or 0.0
                )

                memory = float(
                    info.get("memory_percent")
                    or 0.0
                )

                aggregate_cpu += cpu
                aggregate_memory += memory

                names.add(
                    str(name).lower()
                )

                processes.append(
                    {
                        "pid": pid,
                        "name": name,
                        "username": username,
                        "status": status,
                        "cpu_percent": round(
                            cpu,
                            2,
                        ),
                        "memory_percent": round(
                            memory,
                            2,
                        ),
                        "create_time": info.get(
                            "create_time"
                        ),
                    }
                )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

            except Exception:
                continue

    except Exception:
        pass

    top_cpu = sorted(
        processes,
        key=lambda item: item.get(
            "cpu_percent",
            0.0,
        ),
        reverse=True,
    )[:10]

    top_memory = sorted(
        processes,
        key=lambda item: item.get(
            "memory_percent",
            0.0,
        ),
        reverse=True,
    )[:10]

    return {
        "process_count": len(
            processes
        ),

        "process_names": names,

        "processes": processes,

        "top_cpu_processes": top_cpu,

        "top_memory_processes": top_memory,

        "aggregate_cpu_percent": round(
            aggregate_cpu,
            2,
        ),

        "aggregate_memory_percent": round(
            aggregate_memory,
            2,
        ),
    }


def get_process_summary() -> dict[str, Any]:
    """Return a compact process intelligence summary."""

    snapshot = get_process_snapshot()

    return {
        "process_count":
            snapshot["process_count"],

        "unique_processes":
            len(
                snapshot["process_names"]
            ),

        "top_cpu_processes":
            snapshot["top_cpu_processes"],

        "top_memory_processes":
            snapshot["top_memory_processes"],
    }


# ============================================================
# NETWORK CONNECTION INTELLIGENCE
# ============================================================

def get_connection_snapshot() -> dict[str, Any]:
    """
    Collect real network connection information.

    A remote endpoint is NOT considered malicious merely
    because a connection exists.
    """

    total = 0
    remote = 0
    established = 0
    listening = 0
    time_wait = 0
    other_states = 0

    endpoints: list[str] = []
    endpoint_counter: Counter[str] = Counter()

    connection_records: list[
        dict[str, Any]
    ] = []

    try:
        connections = psutil.net_connections(
            kind="inet"
        )

    except (
        psutil.AccessDenied,
        OSError,
    ):
        connections = []

    except Exception:
        connections = []

    for conn in connections:

        try:
            status = str(
                conn.status
                or "NONE"
            ).upper()

            if conn.status:
                total += 1

            if status == "ESTABLISHED":
                established += 1

            elif status == "LISTEN":
                listening += 1

            elif status == "TIME_WAIT":
                time_wait += 1

            else:
                other_states += 1

            endpoint = None

            if conn.raddr:

                try:
                    ip = conn.raddr.ip
                    port = conn.raddr.port

                    endpoint = (
                        f"{ip}:{port}"
                    )

                    remote += 1
                    endpoint_counter[
                        endpoint
                    ] += 1

                    if (
                        endpoint
                        not in endpoints
                    ):
                        endpoints.append(
                            endpoint
                        )

                except AttributeError:
                    pass

            process_name = None

            if conn.pid:

                try:
                    process_name = (
                        psutil.Process(
                            conn.pid
                        ).name()
                    )

                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                ):
                    process_name = None

                except Exception:
                    process_name = None

            connection_records.append(
                {
                    "pid": conn.pid,

                    "process":
                        process_name,

                    "status":
                        status,

                    "local":
                        (
                            str(conn.laddr)
                            if conn.laddr
                            else None
                        ),

                    "remote":
                        (
                            str(conn.raddr)
                            if conn.raddr
                            else None
                        ),
                }
            )

        except Exception:
            continue

    top_endpoints = [
        {
            "endpoint": endpoint,
            "connections": count,
        }
        for endpoint, count
        in endpoint_counter.most_common(
            MAX_ENDPOINTS
        )
    ]

    return {
        "connection_count":
            total,

        "remote_connection_count":
            remote,

        "established_connections":
            established,

        "listening_connections":
            listening,

        "time_wait_connections":
            time_wait,

        "other_connections":
            other_states,

        "remote_endpoints":
            endpoints[
                :MAX_ENDPOINTS
            ],

        "top_remote_endpoints":
            top_endpoints,

        "connections":
            connection_records[
                :MAX_CONNECTION_RECORDS
            ],
    }


# ============================================================
# NETWORK CLASSIFICATION
# ============================================================

def classify_network_activity(
    net_kbps: float,
) -> str:
    """Classify actual outbound network throughput."""

    try:
        value = float(
            net_kbps
        )

    except (
        TypeError,
        ValueError,
    ):
        value = 0.0

    if value >= NETWORK_VERY_HIGH:
        return "VERY_HIGH"

    if value >= NETWORK_HIGH:
        return "HIGH"

    if value >= NETWORK_ELEVATED:
        return "ELEVATED"

    return "NORMAL"


def classify_connection_activity(
    remote_connection_count: int,
) -> str:
    """
    Classify remote connection volume.

    Connection count alone is weak evidence.
    """

    try:
        count = int(
            remote_connection_count
        )

    except (
        TypeError,
        ValueError,
    ):
        count = 0

    if count >= REMOTE_CONNECTION_VERY_HIGH:
        return "VERY_HIGH"

    if count >= REMOTE_CONNECTION_HIGH:
        return "HIGH"

    if count >= REMOTE_CONNECTION_WATCH:
        return "WATCH"

    return "NORMAL"


# ============================================================
# PROCESS BASELINE
# ============================================================

def classify_process_activity(
    process_count: int,
    baseline_count: float | None,
) -> str:
    """
    Compare current process count against AURA's baseline.

    If no valid baseline exists, AURA does not invent an
    anomaly.
    """

    if baseline_count is None:
        return "NORMAL"

    try:
        current = float(
            process_count
        )

        baseline = float(
            baseline_count
        )

    except (
        TypeError,
        ValueError,
    ):
        return "NORMAL"

    if baseline <= 0:
        return "NORMAL"

    ratio = (
        current / baseline
    )

    if ratio >= 2.0:
        return "VERY_HIGH"

    if ratio >= 1.75:
        return "ELEVATED"

    if ratio >= 1.35:
        return "WATCH"

    return "NORMAL"


# ============================================================
# SENSITIVE FILE INTELLIGENCE
# ============================================================

def _categorize_extension(
    extension: str,
) -> str:
    """Map an extension to a privacy category."""

    extension = str(
        extension
    ).lower()

    for category, extensions in (
        SENSITIVE_CATEGORIES.items()
    ):

        if extension in extensions:
            return category

    return "other"


def sensitive_files_in_common_locations() -> list[str]:
    """
    Inventory sensitive-looking files in common user folders.

    IMPORTANT:
    AURA reads file paths and extensions only.

    It does NOT:
        • open files
        • read file contents
        • upload files
        • modify files
        • delete files
    """

    home = Path.home()

    results: list[str] = []

    scanned_files = 0

    for dirname in (
        COMMON_SENSITIVE_DIRS
    ):

        folder = (
            home / dirname
        )

        if (
            not folder.exists()
            or not folder.is_dir()
        ):
            continue

        try:

            for root, dirs, files in os.walk(
                folder,
                topdown=True,
            ):

                # Avoid hidden directories.
                dirs[:] = [
                    directory
                    for directory in dirs
                    if not directory.startswith(
                        "."
                    )
                ]

                for filename in files:

                    scanned_files += 1

                    if (
                        scanned_files
                        > MAX_FILES_SCANNED
                    ):
                        return results

                    try:

                        extension = (
                            Path(filename)
                            .suffix
                            .lower()
                        )

                        if (
                            extension
                            in SENSITIVE_EXTENSIONS
                        ):

                            results.append(
                                str(
                                    Path(root)
                                    / filename
                                )
                            )

                            if (
                                len(results)
                                >= MAX_FILE_RESULTS
                            ):
                                return results

                    except (
                        PermissionError,
                        OSError,
                    ):
                        continue

                if (
                    scanned_files
                    > MAX_FILES_SCANNED
                ):
                    return results

        except (
            PermissionError,
            OSError,
        ):
            continue

        except Exception:
            continue

    return results


def get_sensitive_file_inventory() -> dict[str, Any]:
    """Return structured sensitive-file metadata."""

    paths = (
        sensitive_files_in_common_locations()
    )

    categories: Counter[str] = Counter()
    extensions: Counter[str] = Counter()

    for path in paths:

        try:

            extension = (
                Path(path)
                .suffix
                .lower()
            )

            extensions[
                extension
            ] += 1

            categories[
                _categorize_extension(
                    extension
                )
            ] += 1

        except Exception:
            continue

    return {
        "total":
            len(paths),

        "paths":
            paths,

        "categories":
            dict(categories),

        "extensions":
            dict(extensions),
    }


# ============================================================
# UNIFIED RISK ENGINE
# ============================================================

def privacy_risk(
    ml_anomaly: int,
    net_kbps: float,
    process_count: int,
    baseline_process_count: float | None,
    remote_connection_count: int,
    camera_available: int,
) -> dict[str, Any]:
    """
    Calculate AURA's unified 0–100 behavioural risk score.

    Severity:

        0–9     NORMAL
        10–24   LOW
        25–54   MEDIUM
        55–79   HIGH
        80–100  CRITICAL

    The score is a triage indicator.

    It is NOT a probability of infection and does not
    represent forensic proof of compromise.
    """

    reasons: list[str] = []
    evidence: list[dict[str, Any]] = []

    score = 0

    # ========================================================
    # 1. AI ANOMALY
    # ========================================================

    if int(ml_anomaly):

        score += 30

        reasons.append(
            "AI anomaly detection identified behaviour "
            "outside the learned baseline."
        )

        evidence.append(
            {
                "signal":
                    "AI anomaly",

                "severity":
                    "HIGH",

                "weight":
                    30,
            }
        )

    # ========================================================
    # 2. OUTBOUND NETWORK ACTIVITY
    # ========================================================

    network_label = (
        classify_network_activity(
            net_kbps
        )
    )

    if network_label == "VERY_HIGH":

        score += 30

        reasons.append(
            "Very high outbound network activity detected."
        )

        evidence.append(
            {
                "signal":
                    "Outbound network",

                "severity":
                    "HIGH",

                "value":
                    round(
                        float(net_kbps),
                        2,
                    ),

                "unit":
                    "KB/s",

                "weight":
                    30,
            }
        )

    elif network_label == "HIGH":

        score += 22

        reasons.append(
            "High outbound network activity detected."
        )

        evidence.append(
            {
                "signal":
                    "Outbound network",

                "severity":
                    "MEDIUM",

                "value":
                    round(
                        float(net_kbps),
                        2,
                    ),

                "unit":
                    "KB/s",

                "weight":
                    22,
            }
        )

    elif network_label == "ELEVATED":

        score += 10

        reasons.append(
            "Outbound network activity is above "
            "the normal monitoring threshold."
        )

        evidence.append(
            {
                "signal":
                    "Outbound network",

                "severity":
                    "LOW",

                "value":
                    round(
                        float(net_kbps),
                        2,
                    ),

                "unit":
                    "KB/s",

                "weight":
                    10,
            }
        )

    # ========================================================
    # 3. PROCESS BEHAVIOUR
    # ========================================================

    process_label = (
        classify_process_activity(
            process_count,
            baseline_process_count,
        )
    )

    if process_label == "VERY_HIGH":

        score += 20

        reasons.append(
            "Process activity is significantly above "
            "the learned baseline."
        )

        evidence.append(
            {
                "signal":
                    "Process behaviour",

                "severity":
                    "HIGH",

                "value":
                    process_count,

                "weight":
                    20,
            }
        )

    elif process_label == "ELEVATED":

        score += 15

        reasons.append(
            "Process activity is substantially above "
            "the learned baseline."
        )

        evidence.append(
            {
                "signal":
                    "Process behaviour",

                "severity":
                    "MEDIUM",

                "value":
                    process_count,

                "weight":
                    15,
            }
        )

    elif process_label == "WATCH":

        score += 7

        reasons.append(
            "Process activity is above the normal baseline."
        )

        evidence.append(
            {
                "signal":
                    "Process behaviour",

                "severity":
                    "LOW",

                "value":
                    process_count,

                "weight":
                    7,
            }
        )

    # ========================================================
    # 4. REMOTE CONNECTIONS
    # ========================================================
    #
    # IMPORTANT:
    #
    # A normal Windows system can easily have dozens of
    # remote connections.
    #
    # Therefore this signal has deliberately LOW weight.
    # ========================================================

    connection_label = (
        classify_connection_activity(
            remote_connection_count
        )
    )

    if connection_label == "VERY_HIGH":

        score += 8

        reasons.append(
            "Remote connection volume is unusually high "
            "and should be reviewed with other indicators."
        )

        evidence.append(
            {
                "signal":
                    "Remote connections",

                "severity":
                    "MEDIUM",

                "value":
                    remote_connection_count,

                "weight":
                    8,
            }
        )

    elif connection_label == "HIGH":

        score += 5

        reasons.append(
            "Remote connection volume is elevated."
        )

        evidence.append(
            {
                "signal":
                    "Remote connections",

                "severity":
                    "LOW",

                "value":
                    remote_connection_count,

                "weight":
                    5,
            }
        )

    elif connection_label == "WATCH":

        score += 2

        # Deliberately informational.
        reasons.append(
            "A higher-than-usual number of remote "
            "connections is currently active."
        )

        evidence.append(
            {
                "signal":
                    "Remote connections",

                "severity":
                    "INFO",

                "value":
                    remote_connection_count,

                "weight":
                    2,
            }
        )

    # ========================================================
    # 5. CAMERA
    # ========================================================
    #
    # Camera availability is informational.
    #
    # AURA NEVER treats camera availability alone as
    # evidence of unauthorized camera access.
    # ========================================================

    camera_status = (
        "AVAILABLE"
        if int(camera_available)
        else "NOT_DETECTED"
    )

    # ========================================================
    # 6. NORMALIZE SCORE
    # ========================================================

    score = max(
        0,
        min(
            int(score),
            100,
        ),
    )

    # ========================================================
    # 7. SEVERITY
    # ========================================================

    if score >= 80:

        risk = "CRITICAL"

    elif score >= 55:

        risk = "HIGH"

    elif score >= 25:

        risk = "MEDIUM"

    elif score >= 10:

        risk = "LOW"

    else:

        risk = "NORMAL"

    # ========================================================
    # 8. PRIVACY EVENT
    # ========================================================

    privacy_event = bool(
        score >= 25
        and (
            bool(ml_anomaly)

            or network_label
            in {
                "HIGH",
                "VERY_HIGH",
            }

            or process_label
            in {
                "WATCH",
                "ELEVATED",
                "VERY_HIGH",
            }

            or connection_label
            in {
                "HIGH",
                "VERY_HIGH",
            }
        )
    )

    # ========================================================
    # 9. POTENTIAL EXFILTRATION
    # ========================================================
    #
    # AURA requires:
    #
    #   suspicious outbound traffic
    #       +
    #   another behavioural indicator
    #
    # A high connection count alone is NOT enough.
    # ========================================================

    network_suspicious = (
        network_label
        in {
            "HIGH",
            "VERY_HIGH",
        }
    )

    behaviour_suspicious = (
        bool(ml_anomaly)

        or process_label
        in {
            "WATCH",
            "ELEVATED",
            "VERY_HIGH",
        }

        or connection_label
        in {
            "HIGH",
            "VERY_HIGH",
        }
    )

    potential_data_exfiltration = bool(
        network_suspicious
        and behaviour_suspicious
    )

    if potential_data_exfiltration:

        reasons.append(
            "Multiple independent indicators form a "
            "potential data-exfiltration pattern."
        )

        evidence.append(
            {
                "signal":
                    "Potential exfiltration pattern",

                "severity":
                    "HIGH",

                "weight":
                    0,
            }
        )

    # ========================================================
    # 10. DEFAULT EXPLANATION
    # ========================================================

    if not reasons:

        reasons.append(
            "No significant privacy-related deviation "
            "was detected."
        )

    # ========================================================
    # 11. FINAL RESULT
    # ========================================================

    return {
        "risk_score":
            score,

        "risk":
            risk,

        "risk_level":
            risk,

        "reasons":
            reasons,

        "evidence":
            evidence,

        "network_label":
            network_label,

        "process_label":
            process_label,

        "connection_label":
            connection_label,

        "camera_status":
            camera_status,

        "potential_data_exfiltration":
            potential_data_exfiltration,

        "potential_camera_risk":
            False,

        "privacy_event":
            privacy_event,
    }


# ============================================================
# COMPLETE PRIVACY CONTEXT
# ============================================================

def snapshot_privacy_context(
    net_kbps: float,
    camera_available: int,
) -> dict[str, Any]:
    """Collect complete privacy intelligence."""

    processes = (
        get_process_snapshot()
    )

    connections = (
        get_connection_snapshot()
    )

    files = (
        get_sensitive_file_inventory()
    )

    return {
        "timestamp":
            time.time(),

        # ----------------------------------------------------
        # PROCESS
        # ----------------------------------------------------

        "process_count":
            processes["process_count"],

        "process_names":
            sorted(
                processes["process_names"]
            )[:100],

        "top_cpu_processes":
            processes[
                "top_cpu_processes"
            ],

        "top_memory_processes":
            processes[
                "top_memory_processes"
            ],

        # ----------------------------------------------------
        # NETWORK
        # ----------------------------------------------------

        "connection_count":
            connections[
                "connection_count"
            ],

        "remote_connection_count":
            connections[
                "remote_connection_count"
            ],

        "established_connections":
            connections[
                "established_connections"
            ],

        "listening_connections":
            connections[
                "listening_connections"
            ],

        "time_wait_connections":
            connections[
                "time_wait_connections"
            ],

        "remote_endpoints":
            connections[
                "remote_endpoints"
            ],

        "top_remote_endpoints":
            connections[
                "top_remote_endpoints"
            ],

        # ----------------------------------------------------
        # FILES
        # ----------------------------------------------------

        "sensitive_file_count":
            files["total"],

        "sensitive_files":
            files["paths"],

        "sensitive_file_categories":
            files["categories"],

        "sensitive_file_extensions":
            files["extensions"],

        # ----------------------------------------------------
        # CLASSIFICATION
        # ----------------------------------------------------

        "network_label":
            classify_network_activity(
                net_kbps
            ),

        "connection_label":
            classify_connection_activity(
                connections[
                    "remote_connection_count"
                ]
            ),

        # ----------------------------------------------------
        # CAMERA
        # ----------------------------------------------------

        "camera_available":
            int(
                camera_available
            ),
    }


# ============================================================
# DASHBOARD HEALTH SUMMARY
# ============================================================

def get_privacy_health_summary(
    risk_score: int,
    risk_level: str,
) -> dict[str, Any]:
    """
    Convert AURA's numerical risk score into dashboard
    status information.

    The numerical score is authoritative.
    """

    try:

        score = max(
            0,
            min(
                int(risk_score),
                100,
            ),
        )

    except (
        TypeError,
        ValueError,
    ):

        score = 0

    # Always derive severity from the actual score.
    if score >= 80:
        level = "CRITICAL"

    elif score >= 55:
        level = "HIGH"

    elif score >= 25:
        level = "MEDIUM"

    elif score >= 10:
        level = "LOW"

    else:
        level = "NORMAL"

    if level == "CRITICAL":

        return {
            "status":
                "CRITICAL",

            "icon":
                "🔴",

            "message":
                (
                    "Multiple high-severity indicators "
                    "require immediate investigation."
                ),
        }

    if level == "HIGH":

        return {
            "status":
                "HIGH RISK",

            "icon":
                "🔴",

            "message":
                (
                    "Significant abnormal behaviour detected. "
                    "Review the available security evidence."
                ),
        }

    if level == "MEDIUM":

        return {
            "status":
                "ATTENTION",

            "icon":
                "🟠",

            "message":
                (
                    "Unusual activity was detected. "
                    "Continue monitoring and review the evidence."
                ),
        }

    if level == "LOW":

        return {
            "status":
                "MONITORING",

            "icon":
                "🟡",

            "message":
                (
                    "Minor behavioural deviation detected."
                ),
        }

    return {
        "status":
            "PROTECTED",

        "icon":
            "🟢",

        "message":
            (
                "No significant privacy-related "
                "deviation was detected."
            ),
    }