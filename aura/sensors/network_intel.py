"""
Windows Network Intelligence Collector for AURA.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import ipaddress
import logging
from typing import Any
import psutil

from aura.sensors.process_intel import ConfidenceLevel

logger = logging.getLogger(__name__)


class SocketCategory(str, Enum):
    LOOPBACK = "LOOPBACK"
    LOCAL_SUBNET = "LOCAL_SUBNET"
    REMOTE_PUBLIC = "REMOTE_PUBLIC"
    UNKNOWN = "UNKNOWN"


@dataclass
class ConnectionInfo:
    local_ip: str
    local_port: int
    remote_ip: str | None
    remote_port: int | None
    status: str
    pid: int | None
    process_name: str | None
    category: SocketCategory
    confidence: ConfidenceLevel = ConfidenceLevel.OBSERVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_ip": self.local_ip,
            "local_port": self.local_port,
            "remote_ip": self.remote_ip,
            "remote_port": self.remote_port,
            "status": self.status,
            "pid": self.pid,
            "process_name": self.process_name,
            "category": self.category.value,
            "confidence": self.confidence.value,
        }


class NetworkIntelligenceCollector:
    @staticmethod
    def classify_ip(ip_str: str | None) -> SocketCategory:
        if not ip_str:
            return SocketCategory.UNKNOWN
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_loopback:
                return SocketCategory.LOOPBACK
            if ip.is_private or ip.is_link_local:
                return SocketCategory.LOCAL_SUBNET
            return SocketCategory.REMOTE_PUBLIC
        except ValueError:
            return SocketCategory.UNKNOWN

    @classmethod
    def get_active_connections(cls, limit: int = 50) -> list[ConnectionInfo]:
        connections: list[ConnectionInfo] = []
        try:
            raw_conns = psutil.net_connections(kind="inet")
            sliced_conns = raw_conns[:limit]

            pid_names: dict[int, str] = {}
            unique_pids = {c.pid for c in sliced_conns if c.pid}
            for pid in unique_pids:
                try:
                    pid_names[pid] = psutil.Process(pid).name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pid_names[pid] = "inaccessible"

            for c in sliced_conns:
                local_ip = c.laddr.ip if c.laddr else "0.0.0.0"
                local_port = c.laddr.port if c.laddr else 0
                remote_ip = c.raddr.ip if c.raddr else None
                remote_port = c.raddr.port if c.raddr else None
                category = cls.classify_ip(remote_ip) if remote_ip else SocketCategory.LOOPBACK

                pname = pid_names.get(c.pid) if c.pid else None

                connections.append(
                    ConnectionInfo(
                        local_ip=local_ip,
                        local_port=local_port,
                        remote_ip=remote_ip,
                        remote_port=remote_port,
                        status=getattr(c, "status", "UNKNOWN"),
                        pid=c.pid,
                        process_name=pname,
                        category=category,
                        confidence=ConfidenceLevel.OBSERVED,
                    )
                )
        except Exception as exc:
            logger.debug("Error retrieving network connections: %s", exc)

        return connections

    @classmethod
    def analyze_network_anomalies(
        cls,
        connections: list[ConnectionInfo],
        current_net_upload_kbps: float = 0.0,
        baseline_upload_kbps: float = 50.0,
    ) -> list[dict[str, Any]]:
        anomalies: list[dict[str, Any]] = []

        if current_net_upload_kbps > max(500.0, baseline_upload_kbps * 4.0):
            anomalies.append({
                "type": "OUTBOUND_TRAFFIC_SPIKE",
                "severity": "HIGH",
                "detail": f"Outbound network throughput ({current_net_upload_kbps:.1f} KB/s) is 4x above baseline.",
                "observed_value": current_net_upload_kbps,
                "baseline_value": baseline_upload_kbps,
            })

        remote_public_conns = [c for c in connections if c.category == SocketCategory.REMOTE_PUBLIC and c.status == "ESTABLISHED"]
        if len(remote_public_conns) > 25:
            anomalies.append({
                "type": "HIGH_REMOTE_CONNECTION_COUNT",
                "severity": "MEDIUM",
                "detail": f"{len(remote_public_conns)} concurrent public remote socket connections active.",
                "observed_value": len(remote_public_conns),
            })

        return anomalies
