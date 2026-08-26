"""
Reliable, non-intrusive Windows camera hardware capability and active usage probe.
"""

from __future__ import annotations

import logging
import sys
from typing import NamedTuple
import psutil

try:
    import winreg
except ImportError:
    winreg = None

from aura.models.types import PrivacyHardwareStatus

logger = logging.getLogger(__name__)


class CameraProbeResult(NamedTuple):
    status: PrivacyHardwareStatus
    device_count: int
    detail: str
    is_active: bool = False
    active_process_name: str | None = None
    active_pids: list[int] = []


def _check_consent_store_active(capability: str = "webcam") -> tuple[bool, str | None, list[int]]:
    if winreg is None:
        return False, None, []

    base_paths = [
        rf"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\{capability}",
        rf"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\{capability}\NonPackaged",
    ]

    for base_path in base_paths:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base_path, 0, winreg.KEY_READ) as key:
                subkeys_count, _, _ = winreg.QueryInfoKey(key)
                for i in range(subkeys_count):
                    app_name = winreg.EnumKey(key, i)
                    if app_name == "NonPackaged":
                        continue
                    app_path = f"{base_path}\\{app_name}"
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, app_path, 0, winreg.KEY_READ) as app_key:
                            try:
                                last_stop, _ = winreg.QueryValueEx(app_key, "LastUsedTimeStop")
                                last_start, _ = winreg.QueryValueEx(app_key, "LastUsedTimeStart")
                                if last_start > 0 and (last_start > last_stop or last_stop == 0):
                                    decoded_path = app_name.replace("#", "\\")
                                    exe_name = decoded_path.split("\\")[-1]
                                    matched_pids = []
                                    for p in psutil.process_iter(["name"]):
                                        try:
                                            pname = p.info.get("name")
                                            if pname and pname.lower() == exe_name.lower():
                                                matched_pids.append(p.pid)
                                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                                            pass
                                    if matched_pids:
                                        return True, exe_name, matched_pids
                            except OSError:
                                pass
                    except OSError:
                        pass
        except Exception:
            pass

    return False, None, []


def probe_camera_capability() -> CameraProbeResult:
    if sys.platform != "win32" or winreg is None:
        return CameraProbeResult(
            status=PrivacyHardwareStatus.UNAVAILABLE,
            device_count=0,
            detail="Windows device registry probe only supported on win32 platform.",
        )

    # 1. Active usage check
    is_active, active_app, active_pids = _check_consent_store_active("webcam")
    if is_active and active_app:
        pid_str = f" (PID: {', '.join(map(str, active_pids))})" if active_pids else ""
        return CameraProbeResult(
            status=PrivacyHardwareStatus.ACTIVE,
            device_count=1,
            detail=f"Active camera video stream session detected in process '{active_app}'{pid_str}.",
            is_active=True,
            active_process_name=active_app,
            active_pids=active_pids,
        )

    # 2. Hardware enumeration check
    device_count = 0
    guid_paths = [
        r"SYSTEM\CurrentControlSet\Control\Class\{ca3e7ab9-b4c3-4ae6-8251-579ef933890f}",
        r"SYSTEM\CurrentControlSet\Control\Class\{6bdd1fc6-810f-11d0-bec7-08002be2092f}",
    ]

    try:
        for rel_path in guid_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rel_path, 0, winreg.KEY_READ) as key:
                    subkeys_count, _, _ = winreg.QueryInfoKey(key)
                    for i in range(subkeys_count):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            if subkey_name.isdigit() and len(subkey_name) == 4:
                                with winreg.OpenKey(key, subkey_name, 0, winreg.KEY_READ) as dev_key:
                                    try:
                                        desc, _ = winreg.QueryValueEx(dev_key, "DriverDesc")
                                        if desc:
                                            device_count += 1
                                    except OSError:
                                        pass
                        except OSError:
                            continue
            except FileNotFoundError:
                continue
            except PermissionError:
                return CameraProbeResult(
                    status=PrivacyHardwareStatus.PERMISSION_LIMITED,
                    device_count=0,
                    detail="Access denied reading hardware device registry.",
                )

        if device_count > 0:
            return CameraProbeResult(
                status=PrivacyHardwareStatus.AVAILABLE,
                device_count=device_count,
                detail=f"{device_count} camera device(s) enumerated; verified zero active capture sessions.",
                is_active=False,
            )
        else:
            return CameraProbeResult(
                status=PrivacyHardwareStatus.NOT_DETECTED,
                device_count=0,
                detail="No camera hardware devices detected in Windows device tree.",
                is_active=False,
            )

    except PermissionError:
        return CameraProbeResult(
            status=PrivacyHardwareStatus.PERMISSION_LIMITED,
            device_count=0,
            detail="Windows permissions limited access to device enumeration.",
        )
    except Exception as exc:
        logger.debug("Unexpected error during camera capability probe: %s", exc)
        return CameraProbeResult(
            status=PrivacyHardwareStatus.UNKNOWN,
            device_count=0,
            detail=f"Camera capability query encountered error: {exc}",
        )
