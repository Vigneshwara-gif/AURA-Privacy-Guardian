from __future__ import annotations

import platform
import time
from typing import Optional

import psutil

try:
    import cv2
except ImportError:
    cv2 = None


# ============================================================
# AURA PRIVACY GUARDIAN
# SENSOR & TELEMETRY ENGINE
# ============================================================
#
# Purpose:
#   Collect real local Windows system telemetry for AURA.
#
# Design principles:
#   - Real measurements only
#   - No fabricated security events
#   - Safe failure handling
#   - Low overhead
#   - Windows compatible
#   - Privacy aware
#   - Backward compatible with existing AURA core
#   - Ready for future ML feature engineering
#
# Sensors:
#   CPU
#   Memory / RAM
#   Disk capacity
#   Disk I/O
#   Network upload/download
#   Network interfaces
#   Running processes
#   Battery
#   System uptime
#   Camera availability
#   Platform information
#
# ============================================================


# ============================================================
# SAMPLING STATE
# ============================================================

_net_sent: Optional[int] = None
_net_received: Optional[int] = None
_net_timestamp: Optional[float] = None

_disk_read: Optional[int] = None
_disk_write: Optional[int] = None
_disk_timestamp: Optional[float] = None


# ============================================================
# SAFE CONVERSION HELPERS
# ============================================================

def _float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# CPU TELEMETRY
# ============================================================

def get_cpu_usage(interval: float = 0.2) -> float:
    """
    Return total CPU utilisation percentage.
    """

    try:
        return round(
            psutil.cpu_percent(interval=interval),
            2,
        )
    except Exception:
        return 0.0


def get_cpu_per_core() -> list[float]:
    """
    Return utilisation for individual logical CPUs.
    """

    try:
        values = psutil.cpu_percent(
            interval=0.1,
            percpu=True,
        )

        return [
            round(float(value), 2)
            for value in values
        ]

    except Exception:
        return []


def get_cpu_frequency() -> float:
    """
    Return current CPU frequency in MHz.
    """

    try:
        frequency = psutil.cpu_freq()

        if frequency is None:
            return 0.0

        return round(
            float(frequency.current),
            2,
        )

    except Exception:
        return 0.0


def get_cpu_info() -> dict:
    """
    Return complete CPU telemetry.
    """

    try:
        physical = psutil.cpu_count(
            logical=False
        ) or 0

        logical = psutil.cpu_count(
            logical=True
        ) or 0

    except Exception:
        physical = 0
        logical = 0

    return {
        "usage_percent": get_cpu_usage(),
        "physical_cores": physical,
        "logical_cores": logical,
        "frequency_mhz": get_cpu_frequency(),
        "per_core_usage": get_cpu_per_core(),
    }


# ============================================================
# MEMORY / RAM TELEMETRY
# ============================================================

def get_memory_info() -> dict:
    """
    Return RAM and swap utilisation.
    """

    try:
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "usage_percent": round(
                memory.percent,
                2,
            ),
            "total_gb": round(
                memory.total / (1024 ** 3),
                2,
            ),
            "used_gb": round(
                memory.used / (1024 ** 3),
                2,
            ),
            "available_gb": round(
                memory.available / (1024 ** 3),
                2,
            ),
            "swap_percent": round(
                swap.percent,
                2,
            ),
            "swap_used_gb": round(
                swap.used / (1024 ** 3),
                2,
            ),
        }

    except Exception:
        return {
            "usage_percent": 0.0,
            "total_gb": 0.0,
            "used_gb": 0.0,
            "available_gb": 0.0,
            "swap_percent": 0.0,
            "swap_used_gb": 0.0,
        }


def get_memory_usage() -> float:
    """
    Backward-compatible RAM usage function.
    """

    return get_memory_info()["usage_percent"]


# ============================================================
# DISK CAPACITY TELEMETRY
# ============================================================

def get_disk_info(
    path: str = "C:\\",
) -> dict:
    """
    Return disk capacity information.
    """

    try:
        disk = psutil.disk_usage(path)

        return {
            "path": path,
            "usage_percent": round(
                disk.percent,
                2,
            ),
            "total_gb": round(
                disk.total / (1024 ** 3),
                2,
            ),
            "used_gb": round(
                disk.used / (1024 ** 3),
                2,
            ),
            "free_gb": round(
                disk.free / (1024 ** 3),
                2,
            ),
        }

    except Exception:
        return {
            "path": path,
            "usage_percent": 0.0,
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
        }


def get_disk_usage(
    path: str = "C:\\",
) -> float:
    """
    Backward-compatible disk usage function.
    """

    return get_disk_info(path)["usage_percent"]


# ============================================================
# DISK I/O TELEMETRY
# ============================================================

def get_disk_io_rate() -> dict:
    """
    Calculate real disk read/write rates in MB/s.

    Uses differences between consecutive psutil
    disk I/O counter readings.
    """

    global _disk_read
    global _disk_write
    global _disk_timestamp

    try:
        counters = psutil.disk_io_counters()

        if counters is None:
            return {
                "read_mbps": 0.0,
                "write_mbps": 0.0,
            }

        now = time.time()

        current_read = counters.read_bytes
        current_write = counters.write_bytes

        if (
            _disk_read is None
            or _disk_write is None
            or _disk_timestamp is None
        ):
            _disk_read = current_read
            _disk_write = current_write
            _disk_timestamp = now

            return {
                "read_mbps": 0.0,
                "write_mbps": 0.0,
            }

        elapsed = max(
            now - _disk_timestamp,
            0.001,
        )

        read_mbps = (
            max(
                current_read - _disk_read,
                0,
            )
            / (1024 ** 2)
            / elapsed
        )

        write_mbps = (
            max(
                current_write - _disk_write,
                0,
            )
            / (1024 ** 2)
            / elapsed
        )

        _disk_read = current_read
        _disk_write = current_write
        _disk_timestamp = now

        return {
            "read_mbps": round(
                read_mbps,
                3,
            ),
            "write_mbps": round(
                write_mbps,
                3,
            ),
        }

    except Exception:
        return {
            "read_mbps": 0.0,
            "write_mbps": 0.0,
        }


# ============================================================
# NETWORK TELEMETRY
# ============================================================

def _sample_network() -> dict:
    """
    Internal network sampler.

    IMPORTANT:
    All network rate calculations go through this function
    so that the counters are updated only once per sample.
    """

    global _net_sent
    global _net_received
    global _net_timestamp

    try:
        counters = psutil.net_io_counters()

        if counters is None:
            return {
                "upload_kbps": 0.0,
                "download_kbps": 0.0,
                "bytes_sent": 0,
                "bytes_received": 0,
                "packets_sent": 0,
                "packets_received": 0,
            }

        now = time.time()

        current_sent = counters.bytes_sent
        current_received = counters.bytes_recv

        upload_kbps = 0.0
        download_kbps = 0.0

        if (
            _net_sent is not None
            and _net_received is not None
            and _net_timestamp is not None
        ):

            elapsed = max(
                now - _net_timestamp,
                0.001,
            )

            upload_kbps = (
                max(
                    current_sent - _net_sent,
                    0,
                )
                / 1024
                / elapsed
            )

            download_kbps = (
                max(
                    current_received - _net_received,
                    0,
                )
                / 1024
                / elapsed
            )

        _net_sent = current_sent
        _net_received = current_received
        _net_timestamp = now

        return {
            "upload_kbps": round(
                upload_kbps,
                3,
            ),
            "download_kbps": round(
                download_kbps,
                3,
            ),
            "bytes_sent": current_sent,
            "bytes_received": current_received,
            "packets_sent": counters.packets_sent,
            "packets_received": counters.packets_recv,
        }

    except Exception:
        return {
            "upload_kbps": 0.0,
            "download_kbps": 0.0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "packets_sent": 0,
            "packets_received": 0,
        }


def get_network_info() -> dict:
    """
    Return complete network telemetry.
    """

    data = _sample_network()

    interfaces = []

    try:
        stats = psutil.net_if_stats()

        for name, info in stats.items():
            if info.isup:
                interfaces.append(name)

    except Exception:
        pass

    return {
        **data,
        "active_interfaces": interfaces,
    }


def get_network_rate() -> float:
    """
    Backward-compatible AURA network sensor.

    Returns outbound/upload rate in KB/s.
    """

    return get_network_info()[
        "upload_kbps"
    ]


# ============================================================
# NETWORK INTERFACE INFORMATION
# ============================================================

def get_network_interfaces() -> list[dict]:
    """
    Return active network interface information.

    Only interface metadata is collected.
    """

    results = []

    try:
        addresses = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for interface, addr_list in addresses.items():

            if (
                interface not in stats
                or not stats[interface].isup
            ):
                continue

            ipv4 = None
            ipv6 = None
            mac = None

            for address in addr_list:

                family = str(
                    address.family
                )

                if (
                    address.family
                    == psutil.AF_LINK
                ):
                    mac = address.address

                elif "AF_INET6" in family:
                    ipv6 = address.address

                elif "AF_INET" in family:
                    ipv4 = address.address

            results.append(
                {
                    "interface": interface,
                    "ipv4": ipv4,
                    "ipv6": ipv6,
                    "mac": mac,
                    "up": True,
                }
            )

    except Exception:
        pass

    return results


# ============================================================
# PROCESS TELEMETRY
# ============================================================

def get_process_count() -> int:
    """
    Return number of currently running processes.
    """

    try:
        return len(
            psutil.pids()
        )

    except Exception:
        return 0


# ============================================================
# BATTERY TELEMETRY
# ============================================================

def get_battery_info() -> dict:
    """
    Return battery information.

    Desktop systems without batteries are reported
    as unavailable.
    """

    try:
        battery = psutil.sensors_battery()

        if battery is None:
            return {
                "available": False,
                "percent": None,
                "charging": None,
                "seconds_left": None,
                "status": "NOT_AVAILABLE",
            }

        charging = bool(
            battery.power_plugged
        )

        if charging:
            status = "CHARGING"
        else:
            status = "ON_BATTERY"

        seconds_left = battery.secsleft

        if (
            seconds_left
            == psutil.POWER_TIME_UNLIMITED
        ):
            seconds_left = None

        return {
            "available": True,
            "percent": round(
                battery.percent,
                1,
            ),
            "charging": charging,
            "seconds_left": seconds_left,
            "status": status,
        }

    except Exception:
        return {
            "available": False,
            "percent": None,
            "charging": None,
            "seconds_left": None,
            "status": "NOT_AVAILABLE",
        }


# ============================================================
# SYSTEM UPTIME
# ============================================================

def get_system_uptime() -> dict:
    """
    Return system boot time and uptime.
    """

    try:
        boot_time = psutil.boot_time()
        now = time.time()

        seconds = max(
            now - boot_time,
            0,
        )

        days = int(
            seconds // 86400
        )

        hours = int(
            (seconds % 86400) // 3600
        )

        minutes = int(
            (seconds % 3600) // 60
        )

        return {
            "boot_timestamp": boot_time,
            "uptime_seconds": int(
                seconds
            ),
            "uptime_text": (
                f"{days}d "
                f"{hours}h "
                f"{minutes}m"
            ),
        }

    except Exception:
        return {
            "boot_timestamp": 0,
            "uptime_seconds": 0,
            "uptime_text": "UNKNOWN",
        }


# ============================================================
# CAMERA PRIVACY SENSOR (NON-INTRUSIVE)
# ============================================================

def get_camera_status(
    enabled: bool = False,
) -> int:
    """
    Non-intrusively probe whether a camera device is present on Windows.

    1 = camera device present and available in hardware tree
    0 = not detected, unavailable, or probe disabled

    IMPORTANT:
    This probe uses device registry enumeration. It NEVER opens video capture
    streams and NEVER illuminates webcam hardware LEDs.
    """
    if not enabled:
        return 0

    from aura.models.types import PrivacyHardwareStatus
    from aura.sensors.camera import probe_camera_capability

    try:
        res = probe_camera_capability()
        return 1 if res.status == PrivacyHardwareStatus.AVAILABLE else 0
    except Exception:
        return 0


# ============================================================
# PLATFORM INFORMATION
# ============================================================

def get_platform_info() -> dict:
    """
    Return non-sensitive platform information.
    """

    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
    }


# ============================================================
# SENSOR HEALTH
# ============================================================

def get_sensor_health(
    snapshot: dict,
) -> dict:
    """
    Evaluate whether AURA sensors returned usable data.

    This is useful for the professional dashboard because
    AURA should distinguish:

        NORMAL SYSTEM
    from
        SENSOR UNAVAILABLE
    """

    checks = {
        "cpu": (
            "cpu" in snapshot
            and snapshot["cpu"] is not None
        ),

        "memory": (
            "memory" in snapshot
            and snapshot["memory"] is not None
        ),

        "disk": (
            "disk" in snapshot
            and snapshot["disk"] is not None
        ),

        "disk_io": (
            "disk_io" in snapshot
            and snapshot["disk_io"] is not None
        ),

        "network": (
            "network" in snapshot
            and snapshot["network"] is not None
        ),

        "processes": (
            "process_count" in snapshot
        ),

        "battery": (
            "battery" in snapshot
        ),

        "uptime": (
            "uptime" in snapshot
        ),
    }

    available = sum(
        1
        for value in checks.values()
        if value
    )

    total = len(checks)

    health_percent = round(
        available / total * 100,
        1,
    )

    return {
        "healthy": health_percent >= 75,
        "health_percent": health_percent,
        "available_sensors": available,
        "total_sensors": total,
        "checks": checks,
    }


# ============================================================
# COMPLETE AURA TELEMETRY SNAPSHOT
# ============================================================

def get_full_sensor_snapshot(
    probe_camera: bool = False,
) -> dict:
    """
    Collect the complete AURA telemetry snapshot.

    This is the main interface for the future
    AURA intelligence / feature-engineering layer.
    """

    snapshot = {
        "timestamp": time.time(),

        # --------------------------------------------
        # CPU
        # --------------------------------------------
        "cpu": get_cpu_info(),

        # --------------------------------------------
        # MEMORY
        # --------------------------------------------
        "memory": get_memory_info(),

        # --------------------------------------------
        # STORAGE
        # --------------------------------------------
        "disk": get_disk_info(),
        "disk_io": get_disk_io_rate(),

        # --------------------------------------------
        # NETWORK
        # --------------------------------------------
        "network": get_network_info(),
        "network_interfaces":
            get_network_interfaces(),

        # --------------------------------------------
        # PROCESSES
        # --------------------------------------------
        "process_count":
            get_process_count(),

        # --------------------------------------------
        # POWER
        # --------------------------------------------
        "battery":
            get_battery_info(),

        # --------------------------------------------
        # UPTIME
        # --------------------------------------------
        "uptime":
            get_system_uptime(),

        # --------------------------------------------
        # PRIVACY HARDWARE
        # --------------------------------------------
        "camera_available":
            get_camera_status(
                enabled=probe_camera
            ),

        # --------------------------------------------
        # PLATFORM
        # --------------------------------------------
        "platform":
            get_platform_info(),
    }

    # Sensor health is calculated after
    # the snapshot exists.
    snapshot["sensor_health"] = (
        get_sensor_health(snapshot)
    )

    return snapshot


# ============================================================
# BACKWARD-COMPATIBLE AURA INTERFACE
# ============================================================

def get_data(
    probe_camera: bool = False,
) -> tuple[float, float, int]:
    """
    Existing AURA interface.

    Returns:

        CPU
        Network Upload Rate
        Camera Status

    This keeps the existing aura_core.py and model.py
    working while the richer telemetry engine is available
    for the next AURA intelligence upgrade.
    """

    cpu = get_cpu_usage(
        interval=0.5
    )

    network = get_network_info()

    upload_rate = network[
        "upload_kbps"
    ]

    camera = get_camera_status(
        enabled=probe_camera
    )

    return (
        cpu,
        upload_rate,
        camera,
    )