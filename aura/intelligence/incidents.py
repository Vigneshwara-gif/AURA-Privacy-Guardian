"""
Security Incident Management Engine for AURA.

Orchestrates multi-finding incident lifecycle (NEW -> INVESTIGATING -> ACKNOWLEDGED -> CONTAINED -> RESOLVED).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

from aura.intelligence.findings import DetailedSecurityFinding, FindingSeverity


class IncidentState(str, Enum):
    NEW = "NEW"
    INVESTIGATING = "INVESTIGATING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


@dataclass(slots=True)
class SecurityIncident:
    incident_id: str = field(default_factory=lambda: f"INC-{uuid.uuid4().hex[:8].upper()}")
    title: str = ""
    severity: FindingSeverity = FindingSeverity.MEDIUM
    state: IncidentState = IncidentState.NEW
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    summary: str = ""
    affected_entities: list[str] = field(default_factory=list)
    findings_count: int = 0
    findings: list[dict[str, Any]] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    action_history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["state"] = self.state.value
        return d


class IncidentManager:
    """Manages active and historical security incidents."""

    _incidents: dict[str, SecurityIncident] = {}

    @classmethod
    def create_incident(
        cls,
        title: str,
        severity: FindingSeverity,
        summary: str,
        affected_entities: list[str],
        findings: list[DetailedSecurityFinding] | None = None,
        recommended_actions: list[str] | None = None,
    ) -> SecurityIncident:
        now_iso = datetime.now(timezone.utc).isoformat()
        findings_dicts = [f.to_dict() for f in (findings or [])]
        inc = SecurityIncident(
            title=title,
            severity=severity,
            state=IncidentState.NEW,
            created_at=now_iso,
            updated_at=now_iso,
            summary=summary,
            affected_entities=affected_entities,
            findings_count=len(findings_dicts),
            findings=findings_dicts,
            recommended_actions=recommended_actions or ["Investigate associated processes and network flows."],
        )
        cls._incidents[inc.incident_id] = inc
        return inc

    @classmethod
    def get_incidents(
        cls,
        limit: int = 50,
        state: IncidentState | None = None,
        severity: FindingSeverity | None = None,
    ) -> list[SecurityIncident]:
        res = list(cls._incidents.values())
        if state:
            res = [i for i in res if i.state == state]
        if severity:
            res = [i for i in res if i.severity == severity]
        res.sort(key=lambda x: x.created_at, reverse=True)
        return res[:limit]

    @classmethod
    def get_incident_by_id(cls, incident_id: str) -> SecurityIncident | None:
        return cls._incidents.get(incident_id)

    @classmethod
    def update_incident_state(
        cls,
        incident_id: str,
        new_state: IncidentState,
        actor: str = "Administrator",
        note: str = "",
    ) -> bool:
        inc = cls._incidents.get(incident_id)
        if not inc:
            return False
        inc.state = new_state
        inc.updated_at = datetime.now(timezone.utc).isoformat()
        inc.action_history.append({
            "timestamp": inc.updated_at,
            "action": f"STATE_CHANGED_TO_{new_state.value}",
            "actor": actor,
            "note": note,
        })
        return True
