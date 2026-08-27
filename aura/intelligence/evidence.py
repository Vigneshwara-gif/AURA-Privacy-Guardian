"""
Unified Security Evidence Architecture for AURA.

Every observation is structured with evidence ID, timestamp, source, entity,
observed/expected values, deviation, confidence, and provenance relationships.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


class EvidenceCategory(str, Enum):
    PROCESS = "PROCESS"
    NETWORK = "NETWORK"
    PERSISTENCE = "PERSISTENCE"
    PRIVACY = "PRIVACY"
    SECURITY_POSTURE = "SECURITY_POSTURE"
    BEHAVIORAL_BASELINE = "BEHAVIORAL_BASELINE"
    ML_ANOMALY = "ML_ANOMALY"
    RULE_MATCH = "RULE_MATCH"
    SYSTEM_EVENT = "SYSTEM_EVENT"


class EvidenceObservationState(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    SUSPECTED = "SUSPECTED"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class SecurityEvidence:
    """Atomic evidence record representing an observed or inferred technical fact."""
    evidence_id: str = field(default_factory=lambda: f"EVD-{uuid.uuid4().hex[:10].upper()}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "AuraIntelligenceEngine"
    category: EvidenceCategory = EvidenceCategory.PROCESS
    observation_state: EvidenceObservationState = EvidenceObservationState.OBSERVED
    entity_type: str = "process"  # process, socket, registry, file, driver, event_log
    entity_id: str = ""           # PID, endpoint, key_path, rule_id
    observed_value: Any = None
    expected_value: Any = None
    deviation: float | None = None
    confidence: float = 0.95      # 0.0 to 1.0
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    parent_evidence_ids: list[str] = field(default_factory=list)
    related_pids: list[int] = field(default_factory=list)
    related_endpoints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["observation_state"] = self.observation_state.value
        return d
