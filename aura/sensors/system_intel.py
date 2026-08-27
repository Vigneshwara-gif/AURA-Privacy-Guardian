"""
Real Windows System Telemetry & Posture Collector for AURA.

Extracts hardware configuration, OS kernel details, CPU topology,
memory allocation, disk partition metrics, and boot/uptime state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
import os
import platform
from typing import Any
import psutil

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CpuCoreInfo:
    """Per-core CPU performance metrics."""
    core_index: int
    utilization_percent: float


@dataclass(slots=True)
class DiskPartitionInfo:
    """Disk partition usage statistics."""
    mountpoint: str
    device: str
    fstype: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


@dataclass(slots=True)
class SystemTelemetrySnapshot:
    """Comprehensive real Windows host system snapshot."""
    timestamp: str
    os_name: str
    os_version: str
    os_build: str
    os_display_version: str
    architecture: str
    hostname: str
    logged_in_user: str
    boot_time_iso: str
    uptime_seconds: float
    cpu_model: str
    cpu_physical_cores: int
    cpu_logical_cores: int
    cpu_frequency_current_mhz: float
    cpu_frequency_max_mhz: float
    cpu_overall_percent: float
    cpu_cores: list[CpuCoreInfo] = field(default_factory=list)
    memory_total_gb: float = 0.0
    memory_used_gb: float = 0.0
    memory_available_gb: float = 0.0
    memory_percent: float = 0.0
    swap_total_gb: float = 0.0
    swap_used_gb: float = 0.0
    partitions: list[DiskPartitionInfo] = field(default_factory=list)


class SystemIntelligenceCollector:
    """Safely extracts real Windows host kernel, CPU, memory, and storage metrics."""

    @staticmethod
    def _get_windows_release_info() -> tuple[str, str, str]:
        """Query precise Windows ProductName, DisplayVersion, and Build number from registry."""
        os_name = "Windows"
        display_version = "Unknown"
        build_str = platform.version()

        if winreg is None:
            return os_name, display_version, build_str

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
                info_count = winreg.QueryInfoKey(key)[1]
                val_names = {winreg.EnumValue(key, i)[0] for i in range(info_count)}

                if "ProductName" in val_names:
                    os_name = str(winreg.QueryValueEx(key, "ProductName")[0])
                if "DisplayVersion" in val_names:
                    display_version = str(winreg.QueryValueEx(key, "DisplayVersion")[0])
                elif "ReleaseId" in val_names:
                    display_version = str(winreg.QueryValueEx(key, "ReleaseId")[0])

                current_build = winreg.QueryValueEx(key, "CurrentBuild")[0] if "CurrentBuild" in val_names else ""
                ubr = winreg.QueryValueEx(key, "UBR")[0] if "UBR" in val_names else ""
                if current_build:
                    build_str = f"{current_build}.{ubr}" if ubr != "" else str(current_build)
        except Exception as exc:
            logger.debug("Error reading Windows NT CurrentVersion registry: %s", exc)

        return os_name, display_version, build_str

    @classmethod
    def collect_snapshot(cls) -> SystemTelemetrySnapshot:
        """Capture complete real system telemetry snapshot."""
        now_iso = datetime.now(timezone.utc).isoformat()
        os_name, display_ver, build_str = cls._get_windows_release_info()

        # Uptime & Boot time
        boot_ts = psutil.boot_time()
        boot_iso = datetime.fromtimestamp(boot_ts, timezone.utc).isoformat()
        uptime = max(0.0, datetime.now(timezone.utc).timestamp() - boot_ts)

        # CPU info
        phys_cores = psutil.cpu_count(logical=False) or 1
        log_cores = psutil.cpu_count(logical=True) or 1
        overall_cpu = psutil.cpu_percent(interval=None)
        per_core = psutil.cpu_percent(percpu=True, interval=None)

        cores_list = [
            CpuCoreInfo(core_index=idx, utilization_percent=float(val))
            for idx, val in enumerate(per_core)
        ]

        freq = psutil.cpu_freq()
        freq_cur = freq.current if freq else 0.0
        freq_max = freq.max if freq else 0.0

        # Memory
        vmem = psutil.virtual_memory()
        total_gb = round(vmem.total / (1024 ** 3), 2)
        used_gb = round(vmem.used / (1024 ** 3), 2)
        avail_gb = round(vmem.available / (1024 ** 3), 2)
        mem_pct = float(vmem.percent)

        swap = psutil.swap_memory()
        swap_total_gb = round(swap.total / (1024 ** 3), 2)
        swap_used_gb = round(swap.used / (1024 ** 3), 2)

        # Disks
        partitions_list: list[DiskPartitionInfo] = []
        try:
            for p in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    partitions_list.append(
                        DiskPartitionInfo(
                            mountpoint=p.mountpoint,
                            device=p.device,
                            fstype=p.fstype,
                            total_gb=round(usage.total / (1024 ** 3), 2),
                            used_gb=round(usage.used / (1024 ** 3), 2),
                            free_gb=round(usage.free / (1024 ** 3), 2),
                            percent=float(usage.percent),
                        )
                    )
                except (PermissionError, OSError):
                    continue
        except Exception as exc:
            logger.debug("Error querying disk partitions: %s", exc)

        # User identity
        user = "SYSTEM"
        try:
            user = os.getlogin()
        except Exception:
            user = os.environ.get("USERNAME", "SYSTEM")

        return SystemTelemetrySnapshot(
            timestamp=now_iso,
            os_name=os_name,
            os_version=platform.version(),
            os_build=build_str,
            os_display_version=display_ver,
            architecture=platform.machine(),
            hostname=platform.node(),
            logged_in_user=user,
            boot_time_iso=boot_iso,
            uptime_seconds=uptime,
            cpu_model=platform.processor() or "Unknown CPU",
            cpu_physical_cores=phys_cores,
            cpu_logical_cores=log_cores,
            cpu_frequency_current_mhz=freq_cur,
            cpu_frequency_max_mhz=freq_max,
            cpu_overall_percent=overall_cpu,
            cpu_cores=cores_list,
            memory_total_gb=total_gb,
            memory_used_gb=used_gb,
            memory_available_gb=avail_gb,
            memory_percent=mem_pct,
            swap_total_gb=swap_total_gb,
            swap_used_gb=swap_used_gb,
            partitions=partitions_list,
        )
