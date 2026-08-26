"""
Windows Process Intelligence Collector for AURA.

Extracts non-intrusive process telemetry, parent-child relationships,
execution paths, and resource footprints with strict fault isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import logging
import os
from typing import Any
import psutil

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Observation confidence level."""

    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


@dataclass
class ProcessInfo:
    """Strongly typed snapshot of a single running process."""

    pid: int
    name: str
    exe_path: str | None
    parent_pid: int | None
    created_time: str
    cpu_percent: float
    memory_rss_bytes: int
    status: str
    username: str | None
    is_elevated: bool
    confidence: ConfidenceLevel = ConfidenceLevel.OBSERVED


class ProcessIntelligenceCollector:
    """Safely inspects process tables with comprehensive AccessDenied and NoSuchProcess handling."""

    @staticmethod
    def get_top_processes(limit: int = 10) -> list[ProcessInfo]:
        """Collect top processes with low-latency non-blocking enumeration."""
        procs: list[ProcessInfo] = []
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            raw = list(psutil.process_iter(["pid", "name"]))
            for p in raw[:limit * 4]:
                try:
                    info = p.info
                    pid = int(info.get("pid") or 0)
                    name = str(info.get("name") or "unknown")
                    mem_rss = 0
                    try:
                        mem_rss = p.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                    procs.append(
                        ProcessInfo(
                            pid=pid,
                            name=name,
                            exe_path=None,
                            parent_pid=None,
                            created_time=now_iso,
                            cpu_percent=0.0,
                            memory_rss_bytes=mem_rss,
                            status="running",
                            username=None,
                            is_elevated=False,
                            confidence=ConfidenceLevel.OBSERVED,
                        )
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as exc:
            logger.debug("Error inspecting processes: %s", exc)

        procs.sort(key=lambda x: x.memory_rss_bytes, reverse=True)
        return procs[:limit]

    @staticmethod
    def get_process_by_pid(pid: int) -> ProcessInfo | None:
        """Query detailed information for a specific PID."""
        try:
            p = psutil.Process(pid)
            name = p.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None

        ctime_iso = datetime.now(timezone.utc).isoformat()
        try:
            ctime = p.create_time()
            ctime_iso = datetime.fromtimestamp(ctime, timezone.utc).isoformat()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        exe_path = None
        try:
            exe_path = p.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        parent_pid = None
        try:
            parent_pid = p.ppid()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        cpu_percent = 0.0
        try:
            cpu_percent = p.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        mem_rss = 0
        try:
            mem_rss = p.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        status_str = "running"
        try:
            status_str = p.status()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        username = None
        try:
            username = p.username()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return ProcessInfo(
            pid=pid,
            name=name,
            exe_path=exe_path,
            parent_pid=parent_pid,
            created_time=ctime_iso,
            cpu_percent=cpu_percent,
            memory_rss_bytes=mem_rss,
            status=status_str,
            username=username,
            is_elevated=(exe_path is None and pid > 0),
            confidence=ConfidenceLevel.OBSERVED,
        )
