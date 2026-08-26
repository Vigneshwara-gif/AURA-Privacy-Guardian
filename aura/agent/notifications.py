"""
Windows Native Notification Dispatcher and Incident-Aware Deduplication Tracker.

Guarantees:
  - Strict incident-aware deduplication (at most 1 notification per incident per severity).
  - Escalation-triggered notifications (LOW -> MEDIUM, MEDIUM -> HIGH, HIGH -> CRITICAL).
  - Incident resolution and fresh occurrence lifecycle tracking.
  - Safe, local-only Windows native Toast notification delivery.
  - Zero sensitive payload leakage (sanitized and redacted).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import html
import logging
import os
import platform
import re
import subprocess
import sys
import threading
from typing import Any

from aura.models.types import SecurityEvent

logger = logging.getLogger(__name__)

SEVERITY_LEVELS: dict[str, int] = {
    "NORMAL": 0,
    "INFO": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


@dataclass
class IncidentState:
    """Tracks state of an active or resolved security incident."""

    incident_id: str
    first_seen: str
    last_seen: str
    current_severity: str
    notified_severity: str | None = None
    is_resolved: bool = False
    occurrence_count: int = 1
    last_event_id: str = ""


class IncidentNotificationTracker:
    """
    Evaluates security events against an incident lifecycle model to prevent alert fatigue.
    """

    def __init__(self, min_severity: str = "MEDIUM", enabled: bool = True) -> None:
        self.min_severity = min_severity.upper()
        self.enabled = enabled
        self._incidents: dict[str, IncidentState] = {}
        self._lock = threading.Lock()

    @property
    def active_incidents_count(self) -> int:
        with self._lock:
            return sum(1 for inc in self._incidents.values() if not inc.is_resolved)

    def get_incident_state(self, incident_id: str) -> IncidentState | None:
        with self._lock:
            return self._incidents.get(incident_id)

    def evaluate_event(self, event: SecurityEvent) -> tuple[bool, str]:
        """
        Evaluate an event to determine whether a user notification should be dispatched.

        Returns:
            (should_notify, decision_reason)
        """
        if not self.enabled:
            return False, "notifications_disabled"

        incident_id = event.incident_id or f"inc_{event.event_type.lower()}"
        event_severity = event.severity.upper()
        event_level = SEVERITY_LEVELS.get(event_severity, 0)
        min_level = SEVERITY_LEVELS.get(self.min_severity, 2)

        with self._lock:
            existing = self._incidents.get(incident_id)

            # 1. Normal / Info / Resolved event handling
            if event_level <= 0 or event.is_resolved:
                if existing and not existing.is_resolved:
                    existing.is_resolved = True
                    existing.current_severity = event_severity
                    existing.notified_severity = None
                    existing.last_seen = event.timestamp
                    return False, "incident_resolved"
                return False, "severity_nominal"

            # 2. Check if severity meets the minimum threshold
            if event_level < min_level:
                if existing:
                    existing.current_severity = event_severity
                    existing.last_seen = event.timestamp
                return False, "below_minimum_severity"

            # 3. New Incident or Re-occurrence after resolution
            if existing is None or existing.is_resolved:
                state = IncidentState(
                    incident_id=incident_id,
                    first_seen=event.timestamp,
                    last_seen=event.timestamp,
                    current_severity=event_severity,
                    notified_severity=event_severity,
                    is_resolved=False,
                    occurrence_count=1,
                    last_event_id=event.event_id,
                )
                self._incidents[incident_id] = state
                return True, "new_incident"

            # 4. Existing Active Incident - Check for Severity Escalation
            notified_level = SEVERITY_LEVELS.get(existing.notified_severity or "NORMAL", 0)

            if event_level > notified_level:
                # Severity Escalation (e.g. MEDIUM -> HIGH, HIGH -> CRITICAL)
                existing.notified_severity = event_severity
                existing.current_severity = event_severity
                existing.last_seen = event.timestamp
                existing.occurrence_count += 1
                existing.last_event_id = event.event_id
                return True, "severity_escalation"

            # 5. Same severity or minor variation - Deduplicate
            existing.current_severity = event_severity
            existing.last_seen = event.timestamp
            existing.occurrence_count += 1
            existing.last_event_id = event.event_id
            return False, "deduplicated_same_severity"

    def reset(self) -> None:
        """Clear all tracked incidents."""
        with self._lock:
            self._incidents.clear()


class WindowsToastNotifier:
    """
    Local-first Windows Toast notification dispatcher using WinRT PowerShell.
    """

    def __init__(self, app_id: str = "AURA Privacy Guardian") -> None:
        self.app_id = app_id
        self.is_windows = platform.system().lower() == "windows"

    @staticmethod
    def sanitize_text(text: str, max_len: int = 140) -> str:
        """Sanitize and redact any potential tokens or credentials."""
        # Redact bearer tokens / hashes / credentials
        redacted = re.sub(r"[A-Fa-f0-9]{32,}", "[REDACTED_HASH]", text)
        redacted = re.sub(r"(bearer\s+)[^\s]+", r"\1[REDACTED_TOKEN]", redacted, flags=re.IGNORECASE)
        redacted = re.sub(r"(password\s*=\s*)[^\s]+", r"\1[REDACTED]", redacted, flags=re.IGNORECASE)
        # Escape XML entities
        escaped = html.escape(redacted)
        if len(escaped) > max_len:
            escaped = escaped[: max_len - 3] + "..."
        return escaped

    def notify(self, title: str, message: str, severity: str = "MEDIUM") -> bool:
        """
        Dispatch a native Windows Toast notification synchronously.
        """
        if not self.is_windows:
            logger.debug("Windows toast suppressed on non-Windows platform (%s)", platform.system())
            return False

        clean_title = self.sanitize_text(f"[{severity.upper()}] {title}", max_len=64)
        clean_msg = self.sanitize_text(message, max_len=160)

        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        $template = @"
        <toast>
            <visual>
                <binding template="ToastGeneric">
                    <text>{clean_title}</text>
                    <text>{clean_msg}</text>
                </binding>
            </visual>
        </toast>
"@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{self.app_id}").Show($toast)
        """

        try:
            # Execute with creationflags to hide console window and bounded timeout
            creationflags = 0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                timeout=2.0,
                creationflags=creationflags,
            )
            return res.returncode == 0
        except Exception as exc:
            logger.warning("Native Windows toast delivery failed: %s", exc)
            return False

    async def notify_async(self, title: str, message: str, severity: str = "MEDIUM") -> bool:
        """Dispatch native toast in worker thread to avoid blocking event loop."""
        return await asyncio.to_thread(self.notify, title, message, severity)
