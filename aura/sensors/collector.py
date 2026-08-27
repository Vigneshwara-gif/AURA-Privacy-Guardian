"""
Isolated hardware & OS sensor collector for AURA.

Enforces sensor fault isolation: an exception in one sensor does NOT terminate
the collection cycle or corrupt remaining sensors.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
import sys
import time
from typing import Any
import psutil

from aura.models.types import (
    PrivacyHardwareStatus,
    SensorHealthRecord,
    SensorStatus,
    TelemetrySnapshot,
)
from aura.sensors.camera import probe_camera_capability
from aura.sensors.microphone import probe_microphone_capability

logger = logging.getLogger(__name__)


class SensorCollector:
    """Isolated sensor collector with independent error handling per probe."""

    def __init__(self, sample_interval: float = 0.2) -> None:
        self.sample_interval = max(0.05, min(2.0, sample_interval))
        self._last_net_bytes: tuple[int, int, float] | None = None

    def reset_baselines(self) -> None:
        """Reset historical delta baselines (e.g. after system resume from sleep/hibernation)."""
        self._last_net_bytes = None
        logger.info("Sensor delta baselines reset successfully.")

    def collect_snapshot(
        self,
        probe_camera: bool = False,
        probe_microphone: bool = False,
    ) -> TelemetrySnapshot:
        """
        Collect a full host telemetry snapshot with total sensor isolation.
        """
        return self._collect_internal(probe_camera=probe_camera, probe_microphone=probe_microphone)

    collect = collect_snapshot

    def _collect_internal(
        self,
        probe_camera: bool = False,
        probe_microphone: bool = False,
    ) -> TelemetrySnapshot:
        now_iso = datetime.now(timezone.utc).isoformat()
        health_records: list[SensorHealthRecord] = []
        raw_payload: dict[str, Any] = {}

        # ----------------------------------------------------
        # 1. CPU Sensor
        # ----------------------------------------------------
        cpu_percent = 0.0
        cpu_cores = 0
        cpu_freq_mhz = 0.0
        try:
            cpu_percent = float(psutil.cpu_percent(interval=self.sample_interval))
            cpu_cores = int(psutil.cpu_count(logical=True) or 0)
            freq_info = psutil.cpu_freq()
            if freq_info and freq_info.current:
                cpu_freq_mhz = float(freq_info.current)

            if cpu_cores > 0 and 0.0 <= cpu_percent <= 100.0:
                health_records.append(
                    SensorHealthRecord(
                        name="Processor (CPU)",
                        status=SensorStatus.HEALTHY,
                        value=f"{cpu_percent:.1f}%",
                        detail=f"{cpu_cores} logical cores @ {cpu_freq_mhz:.0f} MHz",
                    )
                )
            else:
                health_records.append(
                    SensorHealthRecord(
                        name="Processor (CPU)",
                        status=SensorStatus.DEGRADED,
                        value=f"{cpu_percent:.1f}%",
                        detail="CPU core count query returned non-positive value.",
                    )
                )
        except PermissionError:
            health_records.append(
                SensorHealthRecord(
                    name="Processor (CPU)",
                    status=SensorStatus.PERMISSION_LIMITED,
                    value="—",
                    detail="Permission denied querying CPU metrics.",
                )
            )
        except Exception as exc:
            logger.warning("CPU sensor probe failed: %s", exc)
            health_records.append(
                SensorHealthRecord(
                    name="Processor (CPU)",
                    status=SensorStatus.ERROR,
                    value="—",
                    detail=f"Sensor probe failed: {exc}",
                )
            )

        # ----------------------------------------------------
        # 2. Memory Sensor
        # ----------------------------------------------------
        mem_percent = 0.0
        mem_used_gb = 0.0
        mem_total_gb = 0.0
        try:
            vmem = psutil.virtual_memory()
            mem_percent = float(vmem.percent)
            mem_used_gb = float(vmem.used / (1024**3))
            mem_total_gb = float(vmem.total / (1024**3))

            if mem_total_gb > 0.0:
                health_records.append(
                    SensorHealthRecord(
                        name="Physical Memory (RAM)",
                        status=SensorStatus.HEALTHY,
                        value=f"{mem_percent:.1f}%",
                        detail=f"{mem_used_gb:.1f} of {mem_total_gb:.1f} GB utilized",
                    )
                )
            else:
                health_records.append(
                    SensorHealthRecord(
                        name="Physical Memory (RAM)",
                        status=SensorStatus.DEGRADED,
                        value=f"{mem_percent:.1f}%",
                        detail="Virtual memory total capacity reported as 0 GB.",
                    )
                )
        except Exception as exc:
            logger.warning("Memory sensor probe failed: %s", exc)
            health_records.append(
                SensorHealthRecord(
                    name="Physical Memory (RAM)",
                    status=SensorStatus.ERROR,
                    value="—",
                    detail=f"Memory query failed: {exc}",
                )
            )

        # ----------------------------------------------------
        # 3. Disk Volume & I/O
        # ----------------------------------------------------
        disk_percent = 0.0
        disk_free_gb = 0.0
        disk_total_gb = 0.0
        disk_path = os.environ.get("SystemDrive", "C:") + ("\\" if not os.environ.get("SystemDrive", "C:").endswith("\\") else "")
        try:
            du = psutil.disk_usage(disk_path)
            disk_percent = float(du.percent)
            disk_free_gb = float(du.free / (1024**3))
            disk_total_gb = float(du.total / (1024**3))

            health_records.append(
                SensorHealthRecord(
                    name="Storage Volume",
                    status=SensorStatus.HEALTHY,
                    value=f"{disk_percent:.1f}%",
                    detail=f"{disk_free_gb:.1f} GB free of {disk_total_gb:.1f} GB ({disk_path})",
                )
            )
        except Exception as exc:
            logger.warning("Disk sensor probe failed: %s", exc)
            health_records.append(
                SensorHealthRecord(
                    name="Storage Volume",
                    status=SensorStatus.ERROR,
                    value="—",
                    detail=f"Disk usage query failed for {disk_path}: {exc}",
                )
            )

        # ----------------------------------------------------
        # 4. Network Throughput & Sockets
        # ----------------------------------------------------
        net_upload_kbps = 0.0
        net_download_kbps = 0.0
        established_conns = 0
        listening_conns = 0
        remote_conns = 0
        try:
            curr_io = psutil.net_io_counters()
            now_t = time.time()
            if self._last_net_bytes is not None:
                last_sent, last_recv, last_t = self._last_net_bytes
                dt = max(0.001, now_t - last_t)
                net_upload_kbps = max(0.0, float((curr_io.bytes_sent - last_sent) / 1024.0 / dt))
                net_download_kbps = max(0.0, float((curr_io.bytes_recv - last_recv) / 1024.0 / dt))
            self._last_net_bytes = (curr_io.bytes_sent, curr_io.bytes_recv, now_t)

            health_records.append(
                SensorHealthRecord(
                    name="Network Interface",
                    status=SensorStatus.HEALTHY,
                    value=f"{net_upload_kbps:.1f} KB/s",
                    detail=f"Up: {net_upload_kbps:.1f} KB/s, Down: {net_download_kbps:.1f} KB/s",
                )
            )
        except Exception as exc:
            logger.warning("Network I/O query failed: %s", exc)
            health_records.append(
                SensorHealthRecord(
                    name="Network Interface",
                    status=SensorStatus.ERROR,
                    value="—",
                    detail=f"Network I/O query error: {exc}",
                )
            )

        try:
            conns = psutil.net_connections(kind="inet")
            for c in conns:
                status = getattr(c, "status", "")
                if status == "ESTABLISHED":
                    established_conns += 1
                    if getattr(c, "raddr", None):
                        remote_conns += 1
                elif status == "LISTEN":
                    listening_conns += 1

            health_records.append(
                SensorHealthRecord(
                    name="Network Sockets",
                    status=SensorStatus.HEALTHY,
                    value=f"{len(conns)} sockets",
                    detail=f"{established_conns} established ({remote_conns} remote), {listening_conns} listening",
                )
            )
        except (psutil.AccessDenied, PermissionError):
            health_records.append(
                SensorHealthRecord(
                    name="Network Sockets",
                    status=SensorStatus.PERMISSION_LIMITED,
                    value="—",
                    detail="Windows withheld socket table for other user accounts (elevation required).",
                )
            )
        except Exception as exc:
            logger.warning("Network sockets query failed: %s", exc)
            health_records.append(
                SensorHealthRecord(
                    name="Network Sockets",
                    status=SensorStatus.ERROR,
                    value="—",
                    detail=f"Socket enumeration error: {exc}",
                )
            )

        # ----------------------------------------------------
        # 5. Process Table
        # ----------------------------------------------------
        process_count = 0
        try:
            pids = psutil.pids()
            process_count = len(pids)
            health_records.append(
                SensorHealthRecord(
                    name="Process Table",
                    status=SensorStatus.HEALTHY,
                    value=str(process_count),
                    detail=f"{process_count} running processes visible to AURA",
                )
            )
        except Exception as exc:
            logger.warning("Process table query failed: %s", exc)
            health_records.append(
                SensorHealthRecord(
                    name="Process Table",
                    status=SensorStatus.ERROR,
                    value="—",
                    detail=f"Process table probe error: {exc}",
                )
            )

        # ----------------------------------------------------
        # 6. Privacy Hardware (Non-Intrusive)
        # ----------------------------------------------------
        cam_status = PrivacyHardwareStatus.NOT_PROBED
        if probe_camera:
            cam_res = probe_camera_capability()
            cam_status = cam_res.status
            health_records.append(
                SensorHealthRecord(
                    name="Camera Hardware",
                    status=SensorStatus.HEALTHY if cam_status == PrivacyHardwareStatus.AVAILABLE else SensorStatus.UNAVAILABLE,
                    value=cam_status.value,
                    detail=cam_res.detail,
                )
            )

        mic_status = PrivacyHardwareStatus.NOT_PROBED
        if probe_microphone:
            mic_res = probe_microphone_capability()
            mic_status = mic_res.status
            health_records.append(
                SensorHealthRecord(
                    name="Microphone Hardware",
                    status=SensorStatus.HEALTHY if mic_status == PrivacyHardwareStatus.AVAILABLE else SensorStatus.UNAVAILABLE,
                    value=mic_status.value,
                    detail=mic_res.detail,
                )
            )

        return TelemetrySnapshot(
            timestamp=now_iso,
            cpu_percent=cpu_percent,
            cpu_cores=cpu_cores,
            cpu_frequency_mhz=cpu_freq_mhz,
            memory_percent=mem_percent,
            memory_used_gb=mem_used_gb,
            memory_total_gb=mem_total_gb,
            disk_percent=disk_percent,
            disk_free_gb=disk_free_gb,
            disk_total_gb=disk_total_gb,
            disk_path=disk_path,
            net_upload_kbps=net_upload_kbps,
            net_download_kbps=net_download_kbps,
            process_count=process_count,
            established_connections=established_conns,
            listening_connections=listening_conns,
            remote_connections=remote_conns,
            camera_status=cam_status,
            microphone_status=mic_status,
            sensor_health=health_records,
            raw_payload=raw_payload,
        )
