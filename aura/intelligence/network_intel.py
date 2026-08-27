"""
Network Investigation & Exposure Analysis Engine for AURA.

Analyzes active socket topologies, listening endpoints, private vs public routing,
newly observed destinations, and firewall profile alignment.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import ipaddress
import logging
from typing import Any
import psutil

from aura.intelligence.evidence import EvidenceCategory, EvidenceObservationState, SecurityEvidence
from aura.sensors.security_posture import SecurityPostureCollector

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NetworkEndpointRecord:
    ip: str
    port: int
    classification: str  # LOOPBACK, PRIVATE, PUBLIC_INTERNET, MULTICAST, LINK_LOCAL
    protocol: str        # TCP, UDP
    state: str           # ESTABLISHED, LISTEN, TIME_WAIT, CLOSE_WAIT, etc.
    pid: int | None
    process_name: str | None
    first_observed: str
    last_observed: str
    reputation_status: str  # "Reputation intelligence not configured" or "TRUSTED", etc.


@dataclass(slots=True)
class NetworkExposureFinding:
    port: int
    protocol: str
    bind_address: str
    pid: int | None
    process_name: str | None
    service_name: str | None
    is_public_exposure: bool
    firewall_profile_active: bool
    severity: str        # INFO, LOW, MEDIUM, HIGH
    title: str
    recommendation: str


@dataclass(slots=True)
class NetworkInvestigationSnapshot:
    timestamp: str
    total_connections: int
    established_count: int
    listening_count: int
    remote_public_count: int
    active_endpoints: list[NetworkEndpointRecord]
    exposure_findings: list[NetworkExposureFinding]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_connections": self.total_connections,
            "established_count": self.established_count,
            "listening_count": self.listening_count,
            "remote_public_count": self.remote_public_count,
            "active_endpoints": [asdict(e) for e in self.active_endpoints],
            "exposure_findings": [asdict(f) for f in self.exposure_findings],
            "summary": self.summary,
        }


class NetworkInvestigationEngine:
    """Investigates socket flows and evaluates local attack surface exposures."""

    _endpoint_history: dict[str, str] = {}  # ip:port -> first_observed_iso

    @classmethod
    def _classify_ip(cls, ip_str: str) -> str:
        if not ip_str:
            return "UNKNOWN"
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if ip_obj.is_loopback:
                return "LOOPBACK"
            if ip_obj.is_private:
                return "PRIVATE"
            if ip_obj.is_multicast:
                return "MULTICAST"
            if ip_obj.is_link_local:
                return "LINK_LOCAL"
            return "PUBLIC_INTERNET"
        except ValueError:
            return "HOSTNAME"

    @classmethod
    def investigate(cls, limit: int = 150) -> NetworkInvestigationSnapshot:
        now_iso = datetime.now(timezone.utc).isoformat()

        # Cache running processes by PID
        proc_names: dict[int, str] = {}
        for p in psutil.process_iter(["name"]):
            try:
                pname = p.info.get("name")
                if pname:
                    proc_names[p.pid] = pname
            except Exception:
                pass

        endpoints: list[NetworkEndpointRecord] = []
        exposure_findings: list[NetworkExposureFinding] = []

        established = 0
        listening = 0
        public_count = 0

        # Query firewall state
        fw_secure = True
        try:
            posture = SecurityPostureCollector.collect_posture()
            fw_secure = posture.firewall.all_profiles_secure
        except Exception:
            pass

        try:
            conns = psutil.net_connections(kind="inet")
        except Exception:
            conns = []

        for c in conns[:limit]:
            proto = "TCP" if c.type == 1 else "UDP"
            laddr = c.laddr
            raddr = c.raddr
            pid = c.pid
            pname = proc_names.get(pid, "unknown") if pid else None

            if c.status == "ESTABLISHED":
                established += 1
            elif c.status == "LISTEN":
                listening += 1

            if raddr:
                remote_ip = raddr.ip
                remote_port = raddr.port
                classification = cls._classify_ip(remote_ip)
                if classification == "PUBLIC_INTERNET":
                    public_count += 1

                ep_key = f"{remote_ip}:{remote_port}"
                if ep_key not in cls._endpoint_history:
                    cls._endpoint_history[ep_key] = now_iso

                endpoints.append(
                    NetworkEndpointRecord(
                        ip=remote_ip,
                        port=remote_port,
                        classification=classification,
                        protocol=proto,
                        state=c.status or "ESTABLISHED",
                        pid=pid,
                        process_name=pname,
                        first_observed=cls._endpoint_history[ep_key],
                        last_observed=now_iso,
                        reputation_status="Reputation intelligence not configured",
                    )
                )

            # Exposure Analysis on Listening Sockets
            if c.status == "LISTEN" and laddr:
                bind_ip = laddr.ip
                port = laddr.port
                is_pub = bind_ip in {"0.0.0.0", "::"}

                # Check if unexpected public exposure
                if is_pub and port not in {80, 443, 8787}:  # 8787 is AURA local API
                    sev = "MEDIUM" if not fw_secure else "LOW"
                    exposure_findings.append(
                        NetworkExposureFinding(
                            port=port,
                            protocol=proto,
                            bind_address=bind_ip,
                            pid=pid,
                            process_name=pname,
                            service_name=None,
                            is_public_exposure=True,
                            firewall_profile_active=fw_secure,
                            severity=sev,
                            title=f"Open Inbound Port {port} Bound to All Interfaces ({pname or 'PID ' + str(pid)})",
                            recommendation=f"Review if process '{pname or pid}' requires unconstrained inbound network binding.",
                        )
                    )

        summary = (
            f"Network investigation analyzed {len(conns)} active socket descriptors: "
            f"{established} established flows, {listening} listening endpoints, and {public_count} public remote destinations. "
            f"Identified {len(exposure_findings)} exposure checkpoints requiring operational review."
        )

        return NetworkInvestigationSnapshot(
            timestamp=now_iso,
            total_connections=len(conns),
            established_count=established,
            listening_count=listening,
            remote_public_count=public_count,
            active_endpoints=endpoints[:100],
            exposure_findings=exposure_findings,
            summary=summary,
        )
