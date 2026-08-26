"""
Non-intrusive Windows microphone presence and activity capability probe.

Guarantees:
  - Zero audio recording.
  - Zero audio buffer decoding or transmission.
  - Explicit capability boundary based on Windows Core Audio endpoints.
"""

from __future__ import annotations

import logging
import sys
from typing import NamedTuple

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore[assignment]

from aura.models.types import PrivacyHardwareStatus

logger = logging.getLogger(__name__)


class MicrophoneProbeResult(NamedTuple):
    status: PrivacyHardwareStatus
    device_count: int
    detail: str
    is_active: bool = False


def probe_microphone_capability() -> MicrophoneProbeResult:
    """
    Non-intrusively check for microphone hardware on Windows.

    What this proves:
      - Checks whether audio capture endpoints exist in Windows Audio Class registry.
      - Does NOT record or stream audio data.
    """
    if sys.platform != "win32":
        return MicrophoneProbeResult(
            status=PrivacyHardwareStatus.UNAVAILABLE,
            device_count=0,
            detail="Windows CoreAudio device registry probe only supported on win32 platform.",
        )

    device_count = 0
    # Media/Audio Device Class GUID: {4d36e96c-e325-11ce-bfc1-08002be10318}
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
                detail=f"{device_count} audio input/output endpoint device(s) registered in Windows tree.",
            )
        else:
            return MicrophoneProbeResult(
                status=PrivacyHardwareStatus.NOT_DETECTED,
                device_count=0,
                detail="No audio capture hardware devices detected.",
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
