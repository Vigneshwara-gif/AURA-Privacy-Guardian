"""
Windows Startup Management for AURA Background Agent.

Guarantees:
  - Registers auto-start in user session via HKCU Run Key or Windows Task Scheduler.
  - Enforces LeastPrivilege (runs in interactive user session, NOT elevated SYSTEM).
  - Safe subprocess execution with argument lists (NEVER shell=True).
  - Dynamic resolution of installed executable vs development environment.
  - Idempotent installation and uninstallation.
  - Integrity verification / tampering detection.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from aura.core.paths import get_paths

logger = logging.getLogger(__name__)

DEFAULT_TASK_NAME = "AURA_Privacy_Guardian_Agent"
REG_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_KEY_NAME = "AURA_Privacy_Guardian"


class WindowsStartupManager:
    """
    Manages Windows auto-start lifecycle for AURA Privacy Guardian (Registry Run Key & Task Scheduler).
    """

    def __init__(self, task_name: str = DEFAULT_TASK_NAME, reg_name: str = REG_KEY_NAME) -> None:
        self.task_name = task_name
        self.reg_name = reg_name

    def resolve_executable_target(self) -> tuple[Path, list[str]]:
        """
        Determine the appropriate executable path and arguments for the current runtime.
        Returns (executable_path, argument_list).
        """
        paths = get_paths()
        installed_bin = paths.install_root / "bin" / "aura-agent.exe"
        if getattr(sys, "frozen", False):
            # Running as compiled PyInstaller executable
            return Path(sys.executable), []
        elif installed_bin.exists():
            return installed_bin, []
        else:
            # Running from Python development / source environment
            python_exe = Path(sys.executable)
            return python_exe, ["-m", "aura.cli.agent_cli", "start"]

    def _get_registry_command(self) -> str | None:
        if sys.platform != "win32":
            return None
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, self.reg_name)
                return str(val)
        except Exception:
            return None

    def _set_registry_command(self, cmd: str) -> bool:
        if sys.platform != "win32":
            return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, self.reg_name, 0, winreg.REG_SZ, cmd)
                return True
        except Exception as exc:
            logger.error("Failed to write to HKCU Run Key: %s", exc)
            return False

    def _delete_registry_command(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, self.reg_name)
                return True
        except FileNotFoundError:
            return True
        except Exception as exc:
            logger.error("Failed to delete HKCU Run Key: %s", exc)
            return False

    def is_installed(self) -> bool:
        """Check if the AURA startup entry is registered in Registry or Task Scheduler."""
        if sys.platform != "win32":
            return False

        # 1. Check HKCU Run Key
        if self._get_registry_command() is not None:
            return True

        # 2. Check Task Scheduler
        cmd = ["schtasks.exe", "/Query", "/TN", self.task_name, "/FO", "CSV", "/NH"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0, check=False)
            return res.returncode == 0
        except Exception:
            return False

    def get_status(self) -> dict[str, Any]:
        """Retrieve detailed status of the registered startup entry."""
        if sys.platform != "win32":
            return {
                "installed": False,
                "platform": sys.platform,
                "detail": "Windows startup management is only available on Windows.",
            }

        # 1. Check Registry
        reg_cmd = self._get_registry_command()
        if reg_cmd is not None:
            return {
                "installed": True,
                "mechanism": "HKCU_REGISTRY_RUN_KEY",
                "registry_key": f"HKCU\\{REG_RUN_KEY_PATH}\\{self.reg_name}",
                "target": reg_cmd,
                "privilege": "LeastPrivilege (User Session)",
            }

        # 2. Check Task Scheduler
        cmd = ["schtasks.exe", "/Query", "/TN", self.task_name, "/FO", "LIST", "/V"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0, check=False)
            if res.returncode == 0:
                info: dict[str, Any] = {
                    "installed": True,
                    "mechanism": "TASK_SCHEDULER",
                    "task_name": self.task_name,
                }
                for line in res.stdout.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        info[k.strip()] = v.strip()
                return info
        except Exception:
            pass

        return {
            "installed": False,
            "task_name": self.task_name,
            "reg_name": self.reg_name,
            "detail": "No auto-start registration found.",
        }

    def install_startup(self, method: str = "auto", delay_seconds: int = 5) -> dict[str, Any]:
        """
        Register AURA to start automatically on user logon.
        method: "auto" (prefers Task Scheduler, falls back to HKCU Run Key), "registry", or "task_scheduler".
        """
        if sys.platform != "win32":
            return {
                "success": False,
                "error": "Startup registration is only supported on Windows.",
            }

        exe_path, args = self.resolve_executable_target()
        if not exe_path.exists():
            return {
                "success": False,
                "error": f"Executable target not found: {exe_path}",
            }

        task_cmd = str(exe_path)
        if args:
            task_cmd = f'"{exe_path}" ' + " ".join(args)

        # 1. Try Task Scheduler if requested
        if method in {"auto", "task_scheduler"}:
            delay_formatted = f"0000:{max(1, min(60, delay_seconds)):02d}"
            cmd = [
                "schtasks.exe",
                "/Create",
                "/TN",
                self.task_name,
                "/TR",
                task_cmd,
                "/SC",
                "ONLOGON",
                "/DELAY",
                delay_formatted,
                "/RL",
                "LIMITED",
                "/F",
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10.0, check=False)
                if res.returncode == 0:
                    logger.info("Registered AURA Task Scheduler startup: %s", self.task_name)
                    return {
                        "success": True,
                        "mechanism": "TASK_SCHEDULER",
                        "task_name": self.task_name,
                        "target": task_cmd,
                        "trigger": "ONLOGON",
                        "privilege": "LIMITED (LeastPrivilege)",
                    }
                elif method == "task_scheduler":
                    return {"success": False, "error": res.stderr.strip() or res.stdout.strip()}
            except Exception as exc:
                if method == "task_scheduler":
                    return {"success": False, "error": str(exc)}

        # 2. Register via HKCU Run Key (Native Windows User-Session Mechanism)
        if self._set_registry_command(task_cmd):
            logger.info("Registered AURA HKCU Run Key startup: %s", self.reg_name)
            return {
                "success": True,
                "mechanism": "HKCU_REGISTRY_RUN_KEY",
                "registry_key": f"HKCU\\{REG_RUN_KEY_PATH}\\{self.reg_name}",
                "target": task_cmd,
                "privilege": "LeastPrivilege (User Session)",
            }

        return {"success": False, "error": "Could not register startup via Task Scheduler or Registry."}

    def uninstall_startup(self) -> dict[str, Any]:
        """
        Unregister AURA startup entries from both Registry and Task Scheduler.
        Idempotent.
        """
        if sys.platform != "win32":
            return {
                "success": False,
                "error": "Startup uninstallation is only supported on Windows.",
            }

        # 1. Clean Registry
        self._delete_registry_command()

        # 2. Clean Task Scheduler
        cmd = ["schtasks.exe", "/Delete", "/TN", self.task_name, "/F"]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=10.0, check=False)
        except Exception:
            pass

        logger.info("Uninstalled AURA startup registration.")
        return {"success": True, "detail": "Startup entries removed."}

    def verify_integrity(self) -> dict[str, Any]:
        """
        Verify that the registered startup entry points to the expected executable.
        Detects tampering or misconfiguration.
        """
        status = self.get_status()
        if not status.get("installed"):
            return {
                "valid": False,
                "tampered": False,
                "detail": "Startup is not installed.",
            }

        expected_exe, _ = self.resolve_executable_target()
        target_str = status.get("target", "") or status.get("Task To Run", "")
        discrepancies: list[str] = []

        if str(expected_exe).lower() not in target_str.lower():
            discrepancies.append(
                f"Executable mismatch: Expected {expected_exe}, configured target is {target_str!r}"
            )

        return {
            "valid": len(discrepancies) == 0,
            "tampered": len(discrepancies) > 0,
            "discrepancies": discrepancies,
            "mechanism": status.get("mechanism"),
        }
