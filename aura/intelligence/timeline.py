"""
Forensic Chronological Timeline Engine for AURA.

Aggregates process lifecycles, network socket events, persistence alterations,
privacy sensor state transitions, security findings, and user responses into a unified timeline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


class TimelineEventType(str, Enum):
    PROCESS_START = "PROCESS_START"
    PROCESS_STOP = "PROCESS_STOP"
    SOCKET_CONNECT = "SOCKET_CONNECT"
    PERSISTENCE_ADD = "PERSISTENCE_ADD"
    PRIVACY_TRANSITION = "PRIVACY_TRANSITION"
    SECURITY_POSTURE_CHANGE = "SECURITY_POSTURE_CHANGE"
    SECURITY_FINDING = "SECURITY_FINDING"
    INCIDENT_CREATED = "INCIDENT_CREATED"
    USER_ACTION = "USER_ACTION"
    SYSTEM_LOG = "SYSTEM_LOG"


@dataclass(slots=True)
class TimelineItem:
    item_id: str = field(default_factory=lambda: f"TLM-{uuid.uuid4().hex[:8].upper()}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: TimelineEventType = TimelineEventType.SYSTEM_LOG
    severity: str = "INFO"
    title: str = ""
    entity_name: str = ""
    entity_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d


class ForensicTimelineEngine:
    """Maintains chronological security timeline with search and filtering."""

    _events: list[TimelineItem] = []

    @classmethod
    def record_event(
        cls,
        event_type: TimelineEventType,
        title: str,
        entity_name: str,
        entity_id: str = "",
        severity: str = "INFO",
        details: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> TimelineItem:
        item = TimelineItem(
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            severity=severity,
            title=title,
            entity_name=entity_name,
            entity_id=entity_id,
            details=details or {},
        )
        cls._events.append(item)
        if len(cls._events) > 1000:
            cls._events = cls._events[-1000:]
        return item

    @classmethod
    def get_timeline(
        cls,
        limit: int = 50,
        event_type: TimelineEventType | None = None,
        severity: str | None = None,
    ) -> list[TimelineItem]:
        filtered = cls._events
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        if severity:
            filtered = [e for e in filtered if e.severity.upper() == severity.upper()]
        return list(reversed(filtered[-limit:]))
