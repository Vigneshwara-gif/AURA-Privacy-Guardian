"""
Windows Network Intelligence Collector for AURA.

Categorizes active socket endpoints (Loopback, Local LAN, WAN Public),
correlates socket PIDs to processes, and tracks connection velocity without sniffing packet contents.
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
    """Network connection scope category."""

    LOOPBACK = "LOOPBACK"
    LOCAL_SUBNET = "LOCAL_SUBNET"
    REMOTE_PUBLIC = "REMOTE_PUBLIC"
    UNKNOWN = "UNKNOWN"


@dataclass
class ConnectionInfo:
    """Strongly typed metadata for an active network socket."""

    local_ip: str
    local_port: int
    remote_ip: str | None
    remote_port: int | None
    status: str
    pid: int | None
    process_name: str | None
    category: SocketCategory
    confidence: ConfidenceLevel = ConfidenceLevel.OBSERVED


class NetworkIntelligenceCollector:
    """Inspects and categorizes active socket endpoints on Windows."""

    @staticmethod
    def classify_ip(ip_str: str | None) -> SocketCategory:
        """Classify an IP string into Loopback, Local Subnet, or Remote Public."""
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
        """Collect and categorize active network connections with bounded lookup overhead."""
        connections: list[ConnectionInfo] = []
        try:
            raw_conns = psutil.net_connections(kind="inet")
            sliced_conns = raw_conns[:limit]

            # Cache unique PID lookups in bulk
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
        except (psutil.AccessDenied, PermissionError):
            logger.debug("Socket enumeration requires elevation on Windows.")
        except Exception as exc:
            logger.warning("Error querying network connections: %s", exc)

        return connections
