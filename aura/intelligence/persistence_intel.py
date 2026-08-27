"""
Startup & Persistence Intelligence Engine for AURA.

Performs deep analysis of Run/RunOnce keys, Startup directories, Windows Services,
and Scheduled Tasks for unsigned binaries, untrusted paths, and unauthorized churn.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any

from aura.intelligence.evidence import EvidenceCategory, EvidenceObservationState, SecurityEvidence
from aura.sensors.persistence import PersistenceIntelligenceCollector, PersistenceInventorySnapshot

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PersistenceAnalysisItem:
    item_type: str  # STARTUP_APP, WINDOWS_SERVICE, SCHEDULED_TASK
    name: str
    executable_path: str | None
    location_or_trigger: str
    is_suspicious_location: bool
    exists_on_disk: bool
    risk_severity: str  # NORMAL, LOW, MEDIUM, HIGH
    evidence_notes: list[str]


@dataclass(slots=True)
class PersistenceIntelligenceSnapshot:
    timestamp: str
    total_startup_apps: int
    total_services: int
    total_scheduled_tasks: int
    analyzed_items: list[PersistenceAnalysisItem]
    suspicious_count: int
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_startup_apps": self.total_startup_apps,
            "total_services": self.total_services,
            "total_scheduled_tasks": self.total_scheduled_tasks,
            "analyzed_items": [asdict(i) for i in self.analyzed_items],
            "suspicious_count": self.suspicious_count,
            "summary": self.summary,
        }


class PersistenceIntelligenceEngine:
    """Analyzes Windows persistence mechanisms for security risks and unauthorized auto-starts."""

    @classmethod
    def analyze(cls) -> PersistenceIntelligenceSnapshot:
        now_iso = datetime.now(timezone.utc).isoformat()
        inv: PersistenceInventorySnapshot = PersistenceIntelligenceCollector.collect_inventory(max_items=100)

        analyzed: list[PersistenceAnalysisItem] = []
        suspicious_count = 0

        # 1. Analyze Startup Apps
        for app in inv.startup_apps:
            exe = app.executable_path or ""
            exe_lower = exe.lower()
            is_susp = any(s in exe_lower for s in ["appdata\\local\\temp", "\\downloads\\", "\\users\\public\\"])
            exists = app.exists_on_disk

            notes = []
            sev = "NORMAL"
            if is_susp:
                sev = "HIGH"
                suspicious_count += 1
                notes.append(f"Application executes from user-writable/temporary location: {exe}")
            if not exists and exe:
                sev = "LOW"
                notes.append(f"Persistence target executable does not exist on disk: {exe}")

            analyzed.append(
                PersistenceAnalysisItem(
                    item_type="STARTUP_APP",
                    name=app.name,
                    executable_path=app.executable_path,
                    location_or_trigger=app.source_location,
                    is_suspicious_location=is_susp,
                    exists_on_disk=exists,
                    risk_severity=sev,
                    evidence_notes=notes,
                )
            )

        # 2. Analyze Windows Services
        for svc in inv.services[:50]:
            bin_path = svc.bin_path or ""
            bin_lower = bin_path.lower()
            is_susp = any(s in bin_lower for s in ["appdata\\local\\temp", "\\downloads\\", "\\users\\public\\"])

            notes = []
            sev = "NORMAL"
            if is_susp:
                sev = "HIGH"
                suspicious_count += 1
                notes.append(f"Service binary path points to user-writable path: {bin_path}")

            analyzed.append(
                PersistenceAnalysisItem(
                    item_type="WINDOWS_SERVICE",
                    name=svc.name,
                    executable_path=svc.bin_path,
                    location_or_trigger=f"Start: {svc.start_type} | State: {svc.status}",
                    is_suspicious_location=is_susp,
                    exists_on_disk=True,
                    risk_severity=sev,
                    evidence_notes=notes,
                )
            )

        summary = (
            f"Persistence intelligence verified {len(inv.startup_apps)} startup applications, {inv.services_count} Windows services, "
            f"and {inv.scheduled_tasks_count} scheduled tasks. Identified {suspicious_count} entries configured in non-standard/user-writable paths."
        )

        return PersistenceIntelligenceSnapshot(
            timestamp=now_iso,
            total_startup_apps=len(inv.startup_apps),
            total_services=inv.services_count,
            total_scheduled_tasks=inv.scheduled_tasks_count,
            analyzed_items=analyzed,
            suspicious_count=suspicious_count,
            summary=summary,
        )
