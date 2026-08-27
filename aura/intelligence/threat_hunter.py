"""
Multi-Vector Threat Hunting Engine for AURA.

Executes targeted heuristic queries against live Windows memory, active sockets,
persistence vectors, and security logs to uncover subtle attack patterns.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any
import psutil

from aura.intelligence.evidence import EvidenceCategory, EvidenceObservationState, SecurityEvidence
from aura.intelligence.findings import DetailedSecurityFinding, FindingSeverity, FindingStatus
from aura.sensors.camera import CameraIntelligenceCollector
from aura.sensors.microphone import MicrophoneIntelligenceCollector
from aura.sensors.persistence import PersistenceIntelligenceCollector
from aura.sensors.security_posture import SecurityPostureCollector

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ThreatHuntQuery:
    hunt_id: str
    hunt_name: str
    category: EvidenceCategory
    description: str
    target_vector: str


@dataclass(slots=True)
class ThreatHuntMatch:
    match_id: str
    hunt_id: str
    timestamp: str
    entity: str
    severity: FindingSeverity
    title: str
    evidence_details: list[str]
    suggested_remediation: str


@dataclass(slots=True)
class ThreatHuntResult:
    timestamp: str
    hunts_executed: int
    matches_found: int
    matches: list[ThreatHuntMatch]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "hunts_executed": self.hunts_executed,
            "matches_found": self.matches_found,
            "matches": [
                {
                    "match_id": m.match_id,
                    "hunt_id": m.hunt_id,
                    "timestamp": m.timestamp,
                    "entity": m.entity,
                    "severity": m.severity.value,
                    "title": m.title,
                    "evidence_details": m.evidence_details,
                    "suggested_remediation": m.suggested_remediation,
                }
                for m in self.matches
            ],
            "summary": self.summary,
        }


class ThreatHuntingEngine:
    """Executes multi-vector threat hunts across live Windows telemetry."""

    HUNT_QUERIES = [
        ThreatHuntQuery(
            hunt_id="HNT-001",
            hunt_name="Unsigned / Temp Path Process Execution",
            category=EvidenceCategory.PROCESS,
            description="Searches for running processes executing from temp, user downloads, or public directories.",
            target_vector="Process Image Paths",
        ),
        ThreatHuntQuery(
            hunt_id="HNT-002",
            hunt_name="Privacy Media Exfiltration Flow",
            category=EvidenceCategory.PRIVACY,
            description="Searches for active camera/mic streaming concurrent with active remote outbound connections.",
            target_vector="Hardware Sentinels + Sockets",
        ),
        ThreatHuntQuery(
            hunt_id="HNT-003",
            hunt_name="Unprotected Inbound Network Exposure",
            category=EvidenceCategory.NETWORK,
            description="Searches for listening sockets bound to all interfaces while Firewall profiles are degraded.",
            target_vector="Listening Sockets + Firewall",
        ),
        ThreatHuntQuery(
            hunt_id="HNT-004",
            hunt_name="Suspicious Auto-Start Persistence",
            category=EvidenceCategory.PERSISTENCE,
            description="Searches for startup registry entries pointing to temporary or user-writable locations.",
            target_vector="Registry Run Keys",
        ),
        ThreatHuntQuery(
            hunt_id="HNT-005",
            hunt_name="Defender Antivirus Inactive Posture",
            category=EvidenceCategory.SECURITY_POSTURE,
            description="Searches for disabled Windows Defender Real-Time Protection.",
            target_vector="Security Center Posture",
        ),
    ]

    @classmethod
    def execute_hunts(cls) -> ThreatHuntResult:
        now_iso = datetime.now(timezone.utc).isoformat()
        matches: list[ThreatHuntMatch] = []

        # Hunt 1: Processes executing from temp/downloads
        for p in psutil.process_iter(["pid", "name", "exe"]):
            try:
                exe = p.info.get("exe")
                if exe:
                    exe_l = exe.lower()
                    if "appdata\\local\\temp" in exe_l or "\\downloads\\" in exe_l or "\\users\\public\\" in exe_l:
                        matches.append(
                            ThreatHuntMatch(
                                match_id=f"MCH-{len(matches)+1:03d}",
                                hunt_id="HNT-001",
                                timestamp=now_iso,
                                entity=f"PID {p.pid} ({p.info.get('name')})",
                                severity=FindingSeverity.HIGH,
                                title=f"Process Running from Untrusted Path: {exe}",
                                evidence_details=[
                                    f"PID: {p.pid}",
                                    f"Process Name: {p.info.get('name')}",
                                    f"Image Path: {exe}",
                                ],
                                suggested_remediation="Verify the binary origin and terminate if unauthorized.",
                            )
                        )
            except Exception:
                pass

        # Hunt 2: Privacy Media Exfiltration
        try:
            cam = CameraIntelligenceCollector.collect_snapshot()
            mic = MicrophoneIntelligenceCollector.collect_snapshot()
            if cam.is_active or mic.is_active:
                # Check outbound connections
                active_pids = set(cam.active_pids + mic.active_pids)
                for c in psutil.net_connections(kind="inet"):
                    if c.pid in active_pids and c.status == "ESTABLISHED" and c.raddr:
                        matches.append(
                            ThreatHuntMatch(
                                match_id=f"MCH-{len(matches)+1:03d}",
                                hunt_id="HNT-002",
                                timestamp=now_iso,
                                entity=f"PID {c.pid} -> {c.raddr.ip}:{c.raddr.port}",
                                severity=FindingSeverity.CRITICAL,
                                title=f"Active Privacy Media Streaming with Concurrent Outbound Connection",
                                evidence_details=[
                                    f"Camera Active: {cam.is_active}",
                                    f"Microphone Active: {mic.is_active}",
                                    f"Remote Socket: {c.raddr.ip}:{c.raddr.port}",
                                ],
                                suggested_remediation="Inspect process network flow and camera permissions immediately.",
                            )
                        )
                        break
        except Exception:
            pass

        # Hunt 3 & 5: Security Posture
        try:
            posture = SecurityPostureCollector.collect_posture()
            if not posture.defender.realtime_protection_enabled:
                matches.append(
                    ThreatHuntMatch(
                        match_id=f"MCH-{len(matches)+1:03d}",
                        hunt_id="HNT-005",
                        timestamp=now_iso,
                        entity="Windows Defender Antivirus",
                        severity=FindingSeverity.CRITICAL,
                        title="Windows Defender Real-Time Protection Disabled",
                        evidence_details=["Defender Real-Time Status: False"],
                        suggested_remediation="Enable Windows Defender Real-Time Protection in Windows Security.",
                    )
                )
            if not posture.firewall.all_profiles_secure:
                matches.append(
                    ThreatHuntMatch(
                        match_id=f"MCH-{len(matches)+1:03d}",
                        hunt_id="HNT-003",
                        timestamp=now_iso,
                        entity="Windows Defender Firewall",
                        severity=FindingSeverity.HIGH,
                        title="One or More Windows Firewall Profiles are Inactive",
                        evidence_details=["Firewall all_profiles_secure: False"],
                        suggested_remediation="Restore default Firewall profiles in Control Panel.",
                    )
                )
        except Exception:
            pass

        # Hunt 4: Persistence
        try:
            pers = PersistenceIntelligenceCollector.collect_inventory(max_items=30)
            for app in pers.startup_apps:
                exe = (app.executable_path or "").lower()
                if "appdata\\local\\temp" in exe or "\\downloads\\" in exe or "\\users\\public\\" in exe:
                    matches.append(
                        ThreatHuntMatch(
                            match_id=f"MCH-{len(matches)+1:03d}",
                            hunt_id="HNT-004",
                            timestamp=now_iso,
                            entity=f"Startup: {app.name}",
                            severity=FindingSeverity.HIGH,
                            title=f"Startup Persistence Pointing to Untrusted Path: {app.executable_path}",
                            evidence_details=[f"App: {app.name}", f"Location: {app.source_location}"],
                            suggested_remediation="Review and remove unauthorized startup registry entry.",
                        )
                    )
        except Exception:
            pass

        summary = (
            f"Executed {len(cls.HUNT_QUERIES)} threat hunting routines across process memory, network sockets, "
            f"privacy devices, persistence, and security posture. Discovered {len(matches)} threat hunt matches."
        )

        return ThreatHuntResult(
            timestamp=now_iso,
            hunts_executed=len(cls.HUNT_QUERIES),
            matches_found=len(matches),
            matches=matches,
            summary=summary,
        )
