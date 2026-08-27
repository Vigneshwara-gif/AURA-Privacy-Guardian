"""
Windows Microphone Intelligence & Audio Privacy Sentinel Collector.

Collects genuine Windows audio capture endpoints, system permission state,
real-time recording session attribution (via CapabilityAccessManager ConsentStore
and live process correlation), recent usage history, and state transitions.

Does NOT record or store audio.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
import sys
from typing import Any
import psutil

try:
    import winreg
except ImportError:
    winreg = None

from aura.models.types import PrivacyHardwareStatus

logger = logging.getLogger(__name__)


def _filetime_to_iso(ft: int | None) -> str | None:
    """Convert Windows 64-bit FILETIME to ISO-8601 UTC string."""
    if not ft or ft <= 0:
        return None
    try:
        epoch_seconds = (ft - 116444736000000000) / 10_000_000.0
        return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()
    except Exception:
        return None


@dataclass(slots=True)
class MicrophoneDevice:
    """Physical or virtual audio capture endpoint enumerated from Windows CoreAudio registry."""
    index: str
    name: str
    provider: str
    driver_date: str
    driver_version: str
    matching_id: str
    is_present: bool = True
    is_enabled: bool = True


@dataclass(slots=True)
class RecentMicrophoneAppUsage:
    """Historical application microphone access record from Windows ConsentStore."""
    app_name: str
    raw_target: str
    is_packaged: bool
    last_used_start: str | None
    last_used_stop: str | None
    is_currently_active: bool
    active_pids: list[int] = field(default_factory=list)


@dataclass(slots=True)
class MicrophoneStateTransition:
    """State transition record when microphone status changes."""
    previous_status: str
    new_status: str
    timestamp: str
    trigger_process: str | None


@dataclass(slots=True)
class MicrophoneIntelligenceSnapshot:
    """Comprehensive microphone hardware, privacy permission, and live session snapshot."""
    timestamp: str
    status: PrivacyHardwareStatus
    device_count: int
    devices: list[MicrophoneDevice]
    system_permission: str  # ALLOWED, DENIED, UNKNOWN
    is_active: bool
    active_process_name: str | None
    active_pids: list[int]
    recent_usage: list[RecentMicrophoneAppUsage]
    last_transition: MicrophoneStateTransition | None
    confidence: float
    source: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "status": self.status.value,
            "device_count": self.device_count,
            "devices": [asdict(d) for d in self.devices],
            "system_permission": self.system_permission,
            "is_active": self.is_active,
            "active_process_name": self.active_process_name,
            "active_pids": self.active_pids,
            "recent_usage": [asdict(u) for u in self.recent_usage],
            "last_transition": asdict(self.last_transition) if self.last_transition else None,
            "confidence": self.confidence,
            "source": self.source,
            "detail": self.detail,
        }


# Backwards-compatible NamedTuple alias for earlier probes
class MicrophoneProbeResult:
    def __init__(
        self,
        status: PrivacyHardwareStatus,
        device_count: int,
        detail: str,
        is_active: bool = False,
        active_process_name: str | None = None,
        active_pids: list[int] | None = None,
    ) -> None:
        self.status = status
        self.device_count = device_count
        self.detail = detail
        self.is_active = is_active
        self.active_process_name = active_process_name
        self.active_pids = active_pids or []


class MicrophoneIntelligenceCollector:
    """Orchestrates genuine Windows microphone discovery and live session tracking."""

    _last_status: PrivacyHardwareStatus | None = None
    _last_transition: MicrophoneStateTransition | None = None

    @classmethod
    def collect_snapshot(cls) -> MicrophoneIntelligenceSnapshot:
        now_iso = datetime.now(timezone.utc).isoformat()

        if sys.platform != "win32" or winreg is None:
            return MicrophoneIntelligenceSnapshot(
                timestamp=now_iso,
                status=PrivacyHardwareStatus.UNAVAILABLE,
                device_count=0,
                devices=[],
                system_permission="UNKNOWN",
                is_active=False,
                active_process_name=None,
                active_pids=[],
                recent_usage=[],
                last_transition=None,
                confidence=1.0,
                source="Non-Windows OS Platform",
                detail="Microphone intelligence collection is only supported on Windows host platforms.",
            )

        # 1. Enumerate Audio Capture Devices from Registry Media Classes
        devices: list[MicrophoneDevice] = []
        audio_class_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e96c-e325-11ce-bfc1-08002be10318}"

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, audio_class_path, 0, winreg.KEY_READ) as key:
                subkeys_count, _, _ = winreg.QueryInfoKey(key)
                for i in range(subkeys_count):
                    sk_name = winreg.EnumKey(key, i)
                    if sk_name.isdigit() and len(sk_name) == 4:
                        with winreg.OpenKey(key, sk_name, 0, winreg.KEY_READ) as dev_key:
                            vals: dict[str, Any] = {}
                            for j in range(winreg.QueryInfoKey(dev_key)[1]):
                                vname, vval, _ = winreg.EnumValue(dev_key, j)
                                vals[vname] = vval
                            dname = vals.get("DriverDesc") or vals.get("FriendlyName") or vals.get("DeviceDesc")
                            if dname:
                                devices.append(
                                    MicrophoneDevice(
                                        index=sk_name,
                                        name=str(dname),
                                        provider=str(vals.get("ProviderName", "Microsoft")),
                                        driver_date=str(vals.get("DriverDate", "")),
                                        driver_version=str(vals.get("DriverVersion", "")),
                                        matching_id=str(vals.get("MatchingDeviceId", "")),
                                        is_present=True,
                                        is_enabled=True,
                                    )
                                )
        except Exception:
            pass

        # 2. Query Root Privacy Permission State
        sys_perm = "UNKNOWN"
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone",
                0,
                winreg.KEY_READ,
            ) as perm_key:
                val, _ = winreg.QueryValueEx(perm_key, "Value")
                sys_perm = "ALLOWED" if str(val).lower() == "allow" else "DENIED"
        except Exception:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone",
                    0,
                    winreg.KEY_READ,
                ) as perm_key:
                    val, _ = winreg.QueryValueEx(perm_key, "Value")
                    sys_perm = "ALLOWED" if str(val).lower() == "allow" else "DENIED"
            except Exception:
                sys_perm = "UNKNOWN"

        # 3. Read Live Usage & Recent Usage from ConsentStore
        running_procs_map: dict[str, list[psutil.Process]] = {}
        for p in psutil.process_iter(["name", "exe"]):
            try:
                pname = p.info.get("name")
                if pname:
                    running_procs_map.setdefault(pname.lower(), []).append(p)
            except Exception:
                pass

        recent_usage: list[RecentMicrophoneAppUsage] = []
        active_app: str | None = None
        active_pids: list[int] = []

        consent_bases = [
            r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone",
            r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone\NonPackaged",
        ]

        for base_path in consent_bases:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base_path, 0, winreg.KEY_READ) as key:
                    subkeys_count, _, _ = winreg.QueryInfoKey(key)
                    for i in range(subkeys_count):
                        sk_name = winreg.EnumKey(key, i)
                        if sk_name == "NonPackaged":
                            continue
                        app_path = f"{base_path}\\{sk_name}"
                        try:
                            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, app_path, 0, winreg.KEY_READ) as app_key:
                                num_values = winreg.QueryInfoKey(app_key)[1]
                                val_dict = dict(winreg.EnumValue(app_key, k)[:2] for k in range(num_values))
                                start = val_dict.get("LastUsedTimeStart", 0)
                                stop = val_dict.get("LastUsedTimeStop", 0)

                                is_flagged = start > 0 and (start > stop or stop == 0)
                                decoded = sk_name.replace("#", "\\")
                                exe_name = decoded.split("\\")[-1]

                                matching_procs = running_procs_map.get(exe_name.lower(), [])
                                is_genuinely_active = is_flagged and len(matching_procs) > 0
                                pids = [p.pid for p in matching_procs] if is_genuinely_active else []

                                start_iso = _filetime_to_iso(start)
                                stop_iso = _filetime_to_iso(stop)

                                if start > 0 or stop > 0:
                                    recent_usage.append(
                                        RecentMicrophoneAppUsage(
                                            app_name=sk_name if "#" not in sk_name else exe_name,
                                            raw_target=decoded,
                                            is_packaged="#" not in sk_name,
                                            last_used_start=start_iso,
                                            last_used_stop=stop_iso,
                                            is_currently_active=is_genuinely_active,
                                            active_pids=pids,
                                        )
                                    )

                                if is_genuinely_active and not active_app:
                                    active_app = exe_name
                                    active_pids = pids
                        except Exception:
                            pass
            except Exception:
                pass

        recent_usage.sort(key=lambda u: u.last_used_start or "", reverse=True)

        is_active = active_app is not None and len(active_pids) > 0
        device_count = len(devices)

        if is_active:
            status = PrivacyHardwareStatus.ACTIVE
            detail = f"Active audio capture session detected in process '{active_app}' (PID: {', '.join(map(str, active_pids))})."
        elif device_count > 0:
            status = PrivacyHardwareStatus.AVAILABLE
            detail = f"{device_count} audio input endpoint(s) enumerated; verified zero active recording sessions."
        else:
            status = PrivacyHardwareStatus.NOT_DETECTED
            detail = "No audio capture hardware devices detected."

        if cls._last_status is not None and cls._last_status != status:
            cls._last_transition = MicrophoneStateTransition(
                previous_status=cls._last_status.value,
                new_status=status.value,
                timestamp=now_iso,
                trigger_process=active_app,
            )
        cls._last_status = status

        return MicrophoneIntelligenceSnapshot(
            timestamp=now_iso,
            status=status,
            device_count=device_count,
            devices=devices,
            system_permission=sys_perm,
            is_active=is_active,
            active_process_name=active_app,
            active_pids=active_pids,
            recent_usage=recent_usage[:15],
            last_transition=cls._last_transition,
            confidence=0.95,
            source="Windows CapabilityAccessManager ConsentStore + CoreAudio Setup Class Registry",
            detail=detail,
        )


def probe_microphone_capability() -> MicrophoneProbeResult:
    """Backwards-compatible wrapper returning MicrophoneProbeResult."""
    snap = MicrophoneIntelligenceCollector.collect_snapshot()
    return MicrophoneProbeResult(
        status=snap.status,
        device_count=snap.device_count,
        detail=snap.detail,
        is_active=snap.is_active,
        active_process_name=snap.active_process_name,
        active_pids=snap.active_pids,
    )
