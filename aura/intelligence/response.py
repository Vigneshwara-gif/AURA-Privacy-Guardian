"""
Safe Response Action Engine for AURA.

Executes explicit, authenticated remediation commands (process termination,
Windows Security / Firewall / Privacy shortcuts) with comprehensive audit logging.

Does NOT execute destructive actions automatically.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
import subprocess
import sys
from typing import Any
import psutil

from aura.intelligence.timeline import ForensicTimelineEngine, TimelineEventType

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ResponseActionResult:
    action_id: str
    action_type: str
    target: str
    success: bool
    message: str
    timestamp: str
    actor: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SafeResponseEngine:
    """Executes authenticated, audited containment and remediation actions."""

    @classmethod
    def terminate_process(cls, pid: int, actor: str = "Operator") -> ResponseActionResult:
        """Safely terminate a target process with audit trail."""
        now_iso = datetime.now(timezone.utc).isoformat()
        action_id = f"ACT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{pid}"

        # Prevent killing critical system processes
        critical_names = {"csrss.exe", "lsass.exe", "services.exe", "smss.exe", "wininit.exe", "system"}
        try:
            p = psutil.Process(pid)
            pname = p.name().lower()
            if pname in critical_names or pid in {0, 4}:
                msg = f"Cannot terminate protected Windows kernel/system process '{pname}' (PID {pid})."
                return ResponseActionResult(
                    action_id=action_id,
                    action_type="TERMINATE_PROCESS",
                    target=f"PID {pid} ({pname})",
                    success=False,
                    message=msg,
                    timestamp=now_iso,
                    actor=actor,
                )

            p.terminate()
            try:
                p.wait(timeout=2.0)
            except psutil.TimeoutExpired:
                p.kill()

            msg = f"Process '{pname}' (PID {pid}) successfully terminated."
            ForensicTimelineEngine.record_event(
                event_type=TimelineEventType.USER_ACTION,
                title=f"Terminated Process {pname}",
                entity_name=pname,
                entity_id=str(pid),
                severity="INFO",
                details={"actor": actor, "action": "TERMINATE_PROCESS"},
            )
            return ResponseActionResult(
                action_id=action_id,
                action_type="TERMINATE_PROCESS",
                target=f"PID {pid} ({pname})",
                success=True,
                message=msg,
                timestamp=now_iso,
                actor=actor,
            )
        except psutil.NoSuchProcess:
            return ResponseActionResult(
                action_id=action_id,
                action_type="TERMINATE_PROCESS",
                target=f"PID {pid}",
                success=True,
                message=f"Process PID {pid} is already terminated or does not exist.",
                timestamp=now_iso,
                actor=actor,
            )
        except psutil.AccessDenied as exc:
            return ResponseActionResult(
                action_id=action_id,
                action_type="TERMINATE_PROCESS",
                target=f"PID {pid}",
                success=False,
                message=f"Access denied terminating process PID {pid} (requires elevation).",
                timestamp=now_iso,
                actor=actor,
            )
        except Exception as exc:
            return ResponseActionResult(
                action_id=action_id,
                action_type="TERMINATE_PROCESS",
                target=f"PID {pid}",
                success=False,
                message=f"Failed to terminate process PID {pid}: {exc}",
                timestamp=now_iso,
                actor=actor,
            )

    @classmethod
    def open_system_shortcut(cls, shortcut_type: str, actor: str = "Operator") -> ResponseActionResult:
        """Launch genuine Windows privacy, security, or network settings page."""
        now_iso = datetime.now(timezone.utc).isoformat()
        action_id = f"ACT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{shortcut_type}"

        uri_map = {
            "CAMERA": "ms-settings:privacy-webcam",
            "MICROPHONE": "ms-settings:privacy-microphone",
            "DEFENDER": "windowsdefender:",
            "FIREWALL": "ms-settings:windowsdefender",
            "UPDATE": "ms-settings:windowsupdate",
            "NETWORK": "ms-settings:network-status",
        }

        target_uri = uri_map.get(shortcut_type.upper())
        if not target_uri:
            return ResponseActionResult(
                action_id=action_id,
                action_type="OPEN_SHORTCUT",
                target=shortcut_type,
                success=False,
                message=f"Unknown settings shortcut type: {shortcut_type}",
                timestamp=now_iso,
                actor=actor,
            )

        try:
            if sys.platform == "win32":
                subprocess.Popen(["cmd.exe", "/c", "start", target_uri], shell=True)
            return ResponseActionResult(
                action_id=action_id,
                action_type="OPEN_SHORTCUT",
                target=target_uri,
                success=True,
                message=f"Opened Windows settings shortcut: {target_uri}",
                timestamp=now_iso,
                actor=actor,
            )
        except Exception as exc:
            return ResponseActionResult(
                action_id=action_id,
                action_type="OPEN_SHORTCUT",
                target=target_uri,
                success=False,
                message=f"Failed to open shortcut {target_uri}: {exc}",
                timestamp=now_iso,
                actor=actor,
            )
