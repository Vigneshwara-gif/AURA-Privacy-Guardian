"""
Non-intrusive Windows camera hardware capability probe.

Replaces OpenCV VideoCapture locks with safe OS device capability queries.
Guarantees:
  - Zero camera hardware locks.
  - Zero LED activity flashes.
  - Zero frame capture, decoding, or storage.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import NamedTuple

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore[assignment]

from aura.models.types import PrivacyHardwareStatus

logger = logging.getLogger(__name__)


class CameraProbeResult(NamedTuple):
    status: PrivacyHardwareStatus
    device_count: int
    detail: str
    is_active: bool = False


def probe_camera_capability() -> CameraProbeResult:
    """
    Non-intrusively probe camera presence on Windows via device registry enumeration.

    What this proves:
      - Checks whether imaging / camera class devices ({6bdd1fc6-810f-11d0-bec7-08002be2092f}
        or {ca3e7ab9-b4c3-4ae6-8251-579ef933890f}) are registered in the hardware tree.
      - Does NOT open the camera stream.
      - Does NOT turn on the webcam indicator light.
    """
    if sys.platform != "win32":
        return CameraProbeResult(
            status=PrivacyHardwareStatus.UNAVAILABLE,
            device_count=0,
            detail="Windows device registry probe only supported on win32 platform.",
        )

    device_count = 0
    # Camera Device Class GUIDs in Windows Registry
    # 1. Image devices: {6bdd1fc6-810f-11d0-bec7-08002be2092f}
    # 2. Camera devices (Win10+): {ca3e7ab9-b4c3-4ae6-8251-579ef933890f}
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
                            # Device instances are formatted as 4-digit numbers (e.g. 0000, 0001)
                            if subkey_name.isdigit() and len(subkey_name) == 4:
                                with winreg.OpenKey(key, subkey_name, 0, winreg.KEY_READ) as dev_key:
                                    try:
                                        # Verify DriverDesc or ProviderName exists
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
                detail=f"{device_count} camera device(s) registered in hardware tree (non-intrusive probe).",
            )
        else:
            return CameraProbeResult(
                status=PrivacyHardwareStatus.NOT_DETECTED,
                device_count=0,
                detail="No camera hardware devices detected in Windows device tree.",
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
