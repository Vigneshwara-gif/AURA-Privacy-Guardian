"""
Reliable, non-intrusive Windows microphone presence and active usage capability probe.
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


class MicrophoneProbeResult(NamedTuple):
    status: PrivacyHardwareStatus
    device_count: int
    detail: str
    is_active: bool = False
    active_process_name: str | None = None
    active_pids: list[int] = []


def _check_consent_store_active(capability: str = "microphone") -> tuple[bool, str | None, list[int]]:
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


def probe_microphone_capability() -> MicrophoneProbeResult:
    if sys.platform != "win32" or winreg is None:
        return MicrophoneProbeResult(
            status=PrivacyHardwareStatus.UNAVAILABLE,
            device_count=0,
            detail="Windows CoreAudio device registry probe only supported on win32 platform.",
        )

    is_active, active_app, active_pids = _check_consent_store_active("microphone")
    if is_active and active_app:
        pid_str = f" (PID: {', '.join(map(str, active_pids))})" if active_pids else ""
        return MicrophoneProbeResult(
            status=PrivacyHardwareStatus.ACTIVE,
            device_count=1,
            detail=f"Active audio capture session detected in process '{active_app}'{pid_str}.",
            is_active=True,
            active_process_name=active_app,
            active_pids=active_pids,
        )

    device_count = 0
    audio_class_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e96c-e325-11ce-bfc1-08002be10318}"

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, audio_class_path, 0, winreg.KEY_READ) as key:
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

        if device_count > 0:
            return MicrophoneProbeResult(
                status=PrivacyHardwareStatus.AVAILABLE,
                device_count=device_count,
                detail=f"{device_count} audio input endpoint(s) enumerated; verified zero active recording sessions.",
                is_active=False,
            )
        else:
            return MicrophoneProbeResult(
                status=PrivacyHardwareStatus.NOT_DETECTED,
                device_count=0,
                detail="No audio capture hardware devices detected.",
                is_active=False,
            )

    except PermissionError:
        return MicrophoneProbeResult(
            status=PrivacyHardwareStatus.PERMISSION_LIMITED,
            device_count=0,
            detail="Windows permissions limited access to audio hardware enumeration.",
        )
    except Exception as exc:
        logger.debug("Unexpected error during microphone capability probe: %s", exc)
        return MicrophoneProbeResult(
            status=PrivacyHardwareStatus.UNKNOWN,
            device_count=0,
            detail=f"Microphone capability query encountered error: {exc}",
        )
