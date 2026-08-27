"""
Unified Security Findings Engine for AURA.

Defines rich, evidence-traceable security findings with strict separation
between Severity (Impact) and Confidence (Certainty), and remediation lifecycle.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

from aura.intelligence.evidence import EvidenceCategory, EvidenceObservationState, SecurityEvidence


class FindingSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


@dataclass(slots=True)
class DetailedSecurityFinding:
    """Rich security finding with provenance evidence, ML signals, and remediation path."""
    finding_id: str = field(default_factory=lambda: f"FND-{uuid.uuid4().hex[:8].upper()}")
    title: str = ""
    category: EvidenceCategory = EvidenceCategory.PROCESS
    severity: FindingSeverity = FindingSeverity.INFO
    confidence: float = 0.95  # 0.0 to 1.0 (Certainty)
    status: FindingStatus = FindingStatus.OPEN
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    affected_entity_type: str = "host"
    affected_entity_id: str = "Host OS"
    summary: str = ""
    technical_explanation: str = ""
    recommendation: str = ""
    rule_ids: list[str] = field(default_factory=list)
    evidences: list[dict[str, Any]] = field(default_factory=list)
    related_pids: list[int] = field(default_factory=list)
    related_endpoints: list[str] = field(default_factory=list)
    incident_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["severity"] = self.severity.value
        d["status"] = self.status.value
        return d
