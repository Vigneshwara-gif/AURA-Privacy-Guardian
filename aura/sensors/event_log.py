"""
Real Windows Security Event Log Ingestion for AURA.

Extracts structured Windows Security, System, and Defender event logs
using fast native wevtutil queries without high CPU overhead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WindowsLogEvent:
    """Normalized Windows Event Log entry."""
    event_id: int
    log_name: str
    provider: str
    timestamp: str
    level: str
    user_name: str | None
    computer: str
    description: str


class WindowsEventLogCollector:
    """Safely extracts security-relevant events from Windows Event Log."""

    @staticmethod
    def _parse_wevtutil_text(raw_text: str) -> list[WindowsLogEvent]:
        """Parse wevtutil /f:text output into structured WindowsLogEvent items."""
        events: list[WindowsLogEvent] = []
        current_event: dict[str, str] = {}

        for line in raw_text.splitlines():
            line_str = line.strip()
            if line_str.startswith("Event[") or line_str.startswith("Event:"):
                if current_event and "event_id" in current_event:
                    try:
                        events.append(
                            WindowsLogEvent(
                                event_id=int(current_event.get("event_id", 0)),
                                log_name=current_event.get("log_name", "System"),
                                provider=current_event.get("provider", "Unknown"),
                                timestamp=current_event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                                level=current_event.get("level", "Information"),
                                user_name=current_event.get("user_name"),
                                computer=current_event.get("computer", "LocalHost"),
                                description=current_event.get("description", "").strip(),
                            )
                        )
                    except Exception:
                        pass
                current_event = {}
                continue

            if ":" in line_str:
                k, _, v = line_str.partition(":")
                k_norm = k.strip().lower()
                v_clean = v.strip()

                if k_norm == "event id":
                    current_event["event_id"] = v_clean
                elif k_norm == "log name":
                    current_event["log_name"] = v_clean
                elif k_norm == "source":
                    current_event["provider"] = v_clean
                elif k_norm == "date":
                    current_event["timestamp"] = v_clean
                elif k_norm == "level":
                    current_event["level"] = v_clean
                elif k_norm == "user name":
                    current_event["user_name"] = v_clean
                elif k_norm == "computer":
                    current_event["computer"] = v_clean
                elif k_norm == "description":
                    current_event["description"] = v_clean
            else:
                if "description" in current_event and line_str:
                    current_event["description"] += " " + line_str

        if current_event and "event_id" in current_event:
            try:
                events.append(
                    WindowsLogEvent(
                        event_id=int(current_event.get("event_id", 0)),
                        log_name=current_event.get("log_name", "System"),
                        provider=current_event.get("provider", "Unknown"),
                        timestamp=current_event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        level=current_event.get("level", "Information"),
                        user_name=current_event.get("user_name"),
                        computer=current_event.get("computer", "LocalHost"),
                        description=current_event.get("description", "").strip(),
                    )
                )
            except Exception:
                pass

        return events

    @classmethod
    def get_recent_system_events(cls, count: int = 10) -> list[WindowsLogEvent]:
        """Fetch recent System log events."""
        try:
            p = subprocess.run(
                ["wevtutil", "qe", "System", f"/c:{count}", "/rd:true", "/f:text"],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            if p.returncode == 0 and p.stdout:
                return cls._parse_wevtutil_text(p.stdout)
        except Exception as exc:
            logger.debug("Error querying System event log: %s", exc)
        return []

    @classmethod
    def get_recent_defender_events(cls, count: int = 10) -> list[WindowsLogEvent]:
        """Fetch recent Windows Defender Operational log events."""
        try:
            p = subprocess.run(
                ["wevtutil", "qe", "Microsoft-Windows-Windows Defender/Operational", f"/c:{count}", "/rd:true", "/f:text"],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            if p.returncode == 0 and p.stdout:
                return cls._parse_wevtutil_text(p.stdout)
        except Exception as exc:
            logger.debug("Error querying Defender event log: %s", exc)
        return []
