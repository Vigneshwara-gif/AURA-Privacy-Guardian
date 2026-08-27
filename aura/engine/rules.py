"""
Deterministic Security Rule Engine for AURA.

Executes transparent, evidence-backed security rules against live telemetry,
process tables, network flows, persistence items, and security posture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any

from aura.models.types import TelemetryData
from aura.sensors.persistence import PersistenceInventorySnapshot
from aura.sensors.security_posture import WindowsSecurityPostureSnapshot

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RuleFinding:
    """Structured result of a triggered security rule."""
    rule_id: str
    rule_name: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    category: str  # "PRIVACY", "SECURITY_POSTURE", "PERSISTENCE", "NETWORK", "PROCESS"
    title: str
    explanation: str
    evidence: list[str]
    recommendation: str
    risk_points: int


class SecurityRuleEngine:
    """Evaluates deterministic Windows threat and privacy rules."""

    @classmethod
    def evaluate_rules(
        cls,
        telemetry: TelemetryData,
        posture: WindowsSecurityPostureSnapshot | None = None,
        persistence: PersistenceInventorySnapshot | None = None,
    ) -> list[RuleFinding]:
        """Execute all active security rules against current observation."""
        findings: list[RuleFinding] = []

        # Rule RUL-001: Active Camera Exfiltration
        cam_status = telemetry.camera_status.value if hasattr(telemetry.camera_status, "value") else str(telemetry.camera_status)
        mic_status = telemetry.microphone_status.value if hasattr(telemetry.microphone_status, "value") else str(telemetry.microphone_status)

        if cam_status.upper() == "ACTIVE" and telemetry.net_upload_kbps > 2500.0:
            findings.append(
                RuleFinding(
                    rule_id="RUL-001",
                    rule_name="Active Camera Exfiltration",
                    severity="CRITICAL",
                    category="PRIVACY",
                    title="Camera Capture Active with High-Speed Outbound Network Flow",
                    explanation="Camera device is actively streaming video frames concurrently with elevated outbound network throughput.",
                    evidence=[
                        "Camera status: ACTIVE",
                        f"Outbound transfer rate: {telemetry.net_upload_kbps:.1f} KB/s (threshold: >2500 KB/s)",
                        f"Active remote sockets: {telemetry.remote_connections}",
                    ],
                    recommendation="Inspect open applications utilizing the camera in Windows Privacy Settings.",
                    risk_points=40,
                )
            )

        # Rule RUL-002: Active Microphone Exfiltration
        if mic_status.upper() == "ACTIVE" and telemetry.net_upload_kbps > 1500.0:
            findings.append(
                RuleFinding(
                    rule_id="RUL-002",
                    rule_name="Active Microphone Exfiltration",
                    severity="HIGH",
                    category="PRIVACY",
                    title="Microphone Audio Capture Active with Concurrent Outbound Flow",
                    explanation="Microphone audio recording session is active concurrent with outbound data transmission.",
                    evidence=[
                        "Microphone status: ACTIVE",
                        f"Outbound transfer rate: {telemetry.net_upload_kbps:.1f} KB/s",
                    ],
                    recommendation="Review microphone permission grants under Windows Settings > Privacy & Security > Microphone.",
                    risk_points=30,
                )
            )

        # Rule RUL-003: Windows Defender Real-Time Protection Disabled
        if posture and not posture.defender.realtime_protection_enabled:
            findings.append(
                RuleFinding(
                    rule_id="RUL-003",
                    rule_name="Defender Real-Time Protection Inactive",
                    severity="CRITICAL",
                    category="SECURITY_POSTURE",
                    title="Windows Defender Real-Time Protection is Disabled",
                    explanation="The host system's primary real-time antivirus inspection engine is currently disabled.",
                    evidence=[
                        "Windows Defender Real-Time Monitoring: False",
                        f"Antivirus engine enabled: {posture.defender.antivirus_enabled}",
                    ],
                    recommendation="Enable Windows Defender Real-Time Protection in Windows Security Center immediately.",
                    risk_points=35,
                )
            )

        # Rule RUL-004: Windows Firewall Profile Inactive
        if posture and not posture.firewall.all_profiles_secure:
            insecure_profiles = []
            if not posture.firewall.domain_profile_enabled:
                insecure_profiles.append("Domain")
            if not posture.firewall.private_profile_enabled:
                insecure_profiles.append("Private")
            if not posture.firewall.public_profile_enabled:
                insecure_profiles.append("Public")

            findings.append(
                RuleFinding(
                    rule_id="RUL-004",
                    rule_name="Windows Firewall Profile Disabled",
                    severity="HIGH",
                    category="SECURITY_POSTURE",
                    title="One or More Windows Firewall Profiles are Disabled",
                    explanation=f"Windows Firewall protection is inactive for profiles: {', '.join(insecure_profiles)}.",
                    evidence=[f"Disabled profiles: {', '.join(insecure_profiles)}"],
                    recommendation="Restore default Windows Defender Firewall profile settings.",
                    risk_points=25,
                )
            )

        # Rule RUL-005: Suspicious Persistence from Temp/Downloads
        if persistence:
            for app in persistence.startup_apps:
                exe_lower = (app.executable_path or "").lower()
                if "appdata\\local\\temp" in exe_lower or "\\downloads\\" in exe_lower or "\\users\\public\\" in exe_lower:
                    findings.append(
                        RuleFinding(
                            rule_id="RUL-005",
                            rule_name="Suspicious Startup Application Path",
                            severity="HIGH",
                            category="PERSISTENCE",
                            title=f"Startup Application Executing from Untrusted Path ({app.name})",
                            explanation=f"Application '{app.name}' is configured to run at startup from an untrusted temporary or user-writable location.",
                            evidence=[
                                f"Application name: {app.name}",
                                f"Target path: {app.executable_path}",
                                f"Registry/Location: {app.source_location}",
                            ],
                            recommendation="Investigate and remove the persistence entry if unauthorized.",
                            risk_points=30,
                        )
                    )

        # Rule RUL-006: High Resource Saturation
        if telemetry.cpu_percent > 95.0 and telemetry.memory_percent > 95.0:
            findings.append(
                RuleFinding(
                    rule_id="RUL-006",
                    rule_name="Extreme Host Resource Saturation",
                    severity="MEDIUM",
                    category="PROCESS",
                    title="Severe Host CPU and Memory Saturation",
                    explanation="Host processor and RAM utilization both exceed 95%, which may indicate resource exhaustion or runaway process activity.",
                    evidence=[
                        f"CPU utilization: {telemetry.cpu_percent:.1f}%",
                        f"Memory utilization: {telemetry.memory_percent:.1f}%",
                    ],
                    recommendation="Review top resource-consuming processes in Incident Studio.",
                    risk_points=15,
                )
            )

        return findings
