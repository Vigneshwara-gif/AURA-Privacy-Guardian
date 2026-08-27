"""
Real Windows Startup & Persistence Telemetry Collector for AURA.

Inspects legitimate Windows persistence mechanisms:
  - HKCU & HKLM Run / RunOnce registry keys
  - User and System Startup directories
  - Windows Services (active and disabled)
  - Windows Scheduled Tasks
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
import io
import logging
import os
import subprocess
from typing import Any
import psutil

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class StartupAppItem:
    """Startup application entry from Registry or Startup folders."""
    name: str
    command: str
    source_location: str
    user_context: str
    is_enabled: bool = True
    executable_path: str | None = None
    exists_on_disk: bool = True


@dataclass(slots=True)
class WindowsServiceItem:
    """Windows background service snapshot."""
    name: str
    display_name: str
    status: str
    start_type: str
    bin_path: str | None
    username: str | None


@dataclass(slots=True)
class ScheduledTaskItem:
    """Windows Task Scheduler task item."""
    task_name: str
    next_run_time: str
    status: str
    author: str | None = None
    action_command: str | None = None


@dataclass(slots=True)
class PersistenceInventorySnapshot:
    """Consolidated persistence telemetry snapshot."""
    timestamp: str
    startup_apps: list[StartupAppItem] = field(default_factory=list)
    services_count: int = 0
    running_services_count: int = 0
    services: list[WindowsServiceItem] = field(default_factory=list)
    scheduled_tasks_count: int = 0
    scheduled_tasks: list[ScheduledTaskItem] = field(default_factory=list)


class PersistenceIntelligenceCollector:
    """Safely interrogates Windows persistence layers."""

    RUN_KEYS = [
        (r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU Run", "CURRENT_USER"),
        (r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU RunOnce", "CURRENT_USER"),
        (r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM Run", "SYSTEM"),
        (r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM RunOnce", "SYSTEM"),
        (r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM WOW6432 Run", "SYSTEM"),
    ]

    @staticmethod
    def _extract_exe_path(command: str) -> str:
        """Extract clean executable path from a command string with arguments/quotes."""
        cleaned = command.strip()
        if cleaned.startswith('"'):
            end_idx = cleaned.find('"', 1)
            if end_idx != -1:
                return cleaned[1:end_idx]
        parts = cleaned.split()
        return parts[0] if parts else cleaned

    @classmethod
    def collect_startup_apps(cls) -> list[StartupAppItem]:
        """Collect startup applications from Registry Run keys and Startup folders."""
        items: list[StartupAppItem] = []

        # 1. Registry Run Keys
        if winreg is not None:
            for subkey, loc_name, user_ctx in cls.RUN_KEYS:
                root_hive = winreg.HKEY_CURRENT_USER if user_ctx == "CURRENT_USER" else winreg.HKEY_LOCAL_MACHINE
                try:
                    with winreg.OpenKey(root_hive, subkey) as key:
                        val_count = winreg.QueryInfoKey(key)[1]
                        for i in range(val_count):
                            try:
                                name, cmd, _ = winreg.EnumValue(key, i)
                                exe = cls._extract_exe_path(str(cmd))
                                exists = os.path.exists(os.path.expandvars(exe))
                                items.append(
                                    StartupAppItem(
                                        name=str(name),
                                        command=str(cmd),
                                        source_location=loc_name,
                                        user_context=user_ctx,
                                        is_enabled=True,
                                        executable_path=exe,
                                        exists_on_disk=exists,
                                    )
                                )
                            except Exception:
                                continue
                except Exception:
                    continue

        # 2. Startup Folders
        startup_dirs = [
            (os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"), "User Startup Folder", "CURRENT_USER"),
            (os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Startup"), "Common Startup Folder", "SYSTEM"),
        ]
        for folder_path, loc_name, user_ctx in startup_dirs:
            if os.path.isdir(folder_path):
                try:
                    for entry in os.scandir(folder_path):
                        if entry.is_file() and not entry.name.lower().endswith(".ini"):
                            items.append(
                                StartupAppItem(
                                    name=entry.name,
                                    command=entry.path,
                                    source_location=loc_name,
                                    user_context=user_ctx,
                                    is_enabled=True,
                                    executable_path=entry.path,
                                    exists_on_disk=True,
                                )
                            )
                except Exception as exc:
                    logger.debug("Error scanning startup directory %s: %s", folder_path, exc)

        return items

    @classmethod
    def collect_services(cls, limit: int | None = None) -> list[WindowsServiceItem]:
        """Collect real Windows Services via psutil."""
        services: list[WindowsServiceItem] = []
        try:
            for s in psutil.win_service_iter():
                try:
                    info = s.as_dict()
                    services.append(
                        WindowsServiceItem(
                            name=str(info.get("name") or ""),
                            display_name=str(info.get("display_name") or ""),
                            status=str(info.get("status") or "unknown"),
                            start_type=str(info.get("start_type") or "unknown"),
                            bin_path=info.get("binpath"),
                            username=info.get("username"),
                        )
                    )
                except Exception:
                    continue
        except Exception as exc:
            logger.debug("Error enumerating Windows services: %s", exc)

        if limit is not None:
            return services[:limit]
        return services

    @classmethod
    def collect_scheduled_tasks(cls, limit: int | None = None) -> list[ScheduledTaskItem]:
        """Collect Windows Scheduled Tasks via schtasks.exe."""
        tasks: list[ScheduledTaskItem] = []
        try:
            p = subprocess.run(
                ["schtasks.exe", "/query", "/fo", "CSV", "/nh"],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            if p.returncode == 0 and p.stdout:
                reader = csv.reader(io.StringIO(p.stdout))
                for row in reader:
                    if len(row) >= 3:
                        task_name = row[0].strip()
                        next_run = row[1].strip()
                        status = row[2].strip()
                        tasks.append(
                            ScheduledTaskItem(
                                task_name=task_name,
                                next_run_time=next_run,
                                status=status,
                            )
                        )
        except Exception as exc:
            logger.debug("Error querying scheduled tasks: %s", exc)

        if limit is not None:
            return tasks[:limit]
        return tasks

    @classmethod
    def collect_inventory(cls, max_items: int = 100) -> PersistenceInventorySnapshot:
        """Capture consolidated persistence inventory."""
        now_iso = datetime.now(timezone.utc).isoformat()
        startups = cls.collect_startup_apps()
        services = cls.collect_services()
        running_svcs = sum(1 for s in services if s.status.lower() == "running")
        tasks = cls.collect_scheduled_tasks()

        return PersistenceInventorySnapshot(
            timestamp=now_iso,
            startup_apps=startups,
            services_count=len(services),
            running_services_count=running_svcs,
            services=services[:max_items],
            scheduled_tasks_count=len(tasks),
            scheduled_tasks=tasks[:max_items],
        )
