"""
Real-Time Alert Engine for AURA.

Manages severity-based alert dispatching, deduplication, cooldown intervals,
acknowledgement state, and WebSocket broadcast triggers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from aura.intelligence.findings import FindingSeverity

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SecurityAlert:
    alert_id: str = field(default_factory=lambda: f"ALT-{uuid.uuid4().hex[:8].upper()}")
    title: str = ""
    severity: FindingSeverity = FindingSeverity.INFO
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "AuraAlertEngine"
    summary: str = ""
    entity_id: str = ""
    finding_id: str | None = None
    incident_id: str | None = None
    is_acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


class AlertEngine:
    """Coordinates deduplicated real-time alert dispatching."""

    _alerts: list[SecurityAlert] = []
    _cooldown_tracker: dict[str, float] = {}  # alert_key -> last_dispatched_ts
    COOLDOWN_SECONDS = 30.0

    @classmethod
    def dispatch_alert(
        cls,
        title: str,
        severity: FindingSeverity,
        summary: str,
        entity_id: str = "",
        finding_id: str | None = None,
        incident_id: str | None = None,
    ) -> SecurityAlert | None:
        now = datetime.now(timezone.utc)
        now_ts = now.timestamp()
        key = f"{severity.value}:{title}:{entity_id}"

        last_time = cls._cooldown_tracker.get(key, 0.0)
        if now_ts - last_time < cls.COOLDOWN_SECONDS:
            # In cooldown, suppress duplicate spam
            return None

        cls._cooldown_tracker[key] = now_ts
        alert = SecurityAlert(
            title=title,
            severity=severity,
            timestamp=now.isoformat(),
            summary=summary,
            entity_id=entity_id,
            finding_id=finding_id,
            incident_id=incident_id,
        )
        cls._alerts.append(alert)
        if len(cls._alerts) > 500:
            cls._alerts = cls._alerts[-500:]
        return alert

    @classmethod
    def get_alerts(cls, limit: int = 50, severity: FindingSeverity | None = None) -> list[SecurityAlert]:
        res = cls._alerts
        if severity:
            res = [a for a in res if a.severity == severity]
        return list(reversed(res[-limit:]))

    @classmethod
    def acknowledge_alert(cls, alert_id: str, actor: str = "Operator") -> bool:
        for a in cls._alerts:
            if a.alert_id == alert_id:
                a.is_acknowledged = True
                a.acknowledged_by = actor
                a.acknowledged_at = datetime.now(timezone.utc).isoformat()
                return True
        return False
