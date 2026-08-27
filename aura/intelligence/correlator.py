"""
Multi-Signal Security Correlation Engine for AURA.

Correlates observations across Process, Network, Persistence, Privacy,
Security Posture, and ML Anomaly signals into unified investigation chains.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from aura.intelligence.evidence import EvidenceCategory, EvidenceObservationState, SecurityEvidence
from aura.intelligence.findings import DetailedSecurityFinding, FindingSeverity, FindingStatus

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CorrelatedChain:
    chain_id: str
    title: str
    primary_entity: str
    severity: FindingSeverity
    confidence: float
    started_at: str
    updated_at: str
    evidence_items: list[dict[str, Any]]
    signals_count: int
    summary: str


class AdvancedCorrelationEngine:
    """Combines disparate technical signals into high-confidence correlated findings."""

    @classmethod
    def correlate_signals(cls, evidences: list[SecurityEvidence]) -> list[CorrelatedChain]:
        """Group evidence by entity (PID, remote IP, or host) and construct correlated chains."""
        now_iso = datetime.now(timezone.utc).isoformat()
        chains: list[CorrelatedChain] = []

        # Group by PID
        pid_groups: dict[int, list[SecurityEvidence]] = {}
        for ev in evidences:
            for pid in ev.related_pids:
                pid_groups.setdefault(pid, []).append(ev)

        for pid, ev_list in pid_groups.items():
            if len(ev_list) >= 2:
                # Multi-signal correlation found for this PID
                categories = {e.category for e in ev_list}
                chain_id = f"CHN-{uuid.uuid4().hex[:8].upper()}"

                # Calculate composite severity
                has_privacy = EvidenceCategory.PRIVACY in categories
                has_network = EvidenceCategory.NETWORK in categories
                has_ml = EvidenceCategory.ML_ANOMALY in categories

                if has_privacy and has_network:
                    sev = FindingSeverity.CRITICAL
                    title = f"Correlated Privacy Media Capture & Outbound Network Flow (PID {pid})"
                elif has_ml and (has_network or has_privacy):
                    sev = FindingSeverity.HIGH
                    title = f"Correlated ML Anomaly & Network Activity (PID {pid})"
                else:
                    sev = FindingSeverity.MEDIUM
                    title = f"Multi-Signal Behavioral Cluster for Process (PID {pid})"

                avg_conf = round(sum(e.confidence for e in ev_list) / len(ev_list), 2)

                chains.append(
                    CorrelatedChain(
                        chain_id=chain_id,
                        title=title,
                        primary_entity=f"Process PID {pid}",
                        severity=sev,
                        confidence=avg_conf,
                        started_at=min(e.timestamp for e in ev_list),
                        updated_at=now_iso,
                        evidence_items=[e.to_dict() for e in ev_list],
                        signals_count=len(ev_list),
                        summary=f"Correlated {len(ev_list)} evidence signals across {len(categories)} distinct categories for PID {pid}.",
                    )
                )

        return chains
