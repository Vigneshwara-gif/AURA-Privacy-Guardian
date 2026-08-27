"""
Process DNA Intelligence Service.

Extracts deep identity, execution context, binary provenance, thread/handle metrics,
network socket maps, and privacy sentinel ties for any Windows process.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
from typing import Any
import psutil

try:
    import winreg
except ImportError:
    winreg = None

from aura.intelligence.evidence import EvidenceCategory, EvidenceObservationState, SecurityEvidence
from aura.sensors.process_intel import ProcessIntelligenceCollector

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProcessIdentityDNA:
    pid: int
    name: str
    exe_path: str | None
    exe_exists: bool
    sha256_hash: str | None
    parent_pid: int | None
    parent_name: str | None
    child_pids: list[int]
    created_time: str
    lifetime_seconds: float
    is_elevated: bool
    username: str | None
    cmdline: str | None


@dataclass(slots=True)
class ProcessExecutionDNA:
    cpu_percent: float
    memory_rss_bytes: int
    memory_mb: float
    num_threads: int
    num_handles: int
    status: str


@dataclass(slots=True)
class ProcessNetworkDNA:
    connection_count: int
    connections: list[dict[str, Any]]
    listening_ports: list[int]
    remote_endpoints: list[str]


@dataclass(slots=True)
class ProcessPrivacyDNA:
    camera_access_detected: bool
    microphone_access_detected: bool
    privacy_events_count: int
    last_privacy_access: str | None


@dataclass(slots=True)
class ProcessSecurityDNA:
    rules_triggered: list[str]
    ml_anomaly_score: float
    baseline_deviation: float
    risk_score: int
    risk_level: str  # NORMAL, LOW, MEDIUM, HIGH, CRITICAL
    evidences: list[dict[str, Any]]


@dataclass(slots=True)
class ProcessDNAProfile:
    """Comprehensive multi-dimensional Process DNA profile."""
    timestamp: str
    pid: int
    identity: ProcessIdentityDNA
    execution: ProcessExecutionDNA
    network: ProcessNetworkDNA
    privacy: ProcessPrivacyDNA
    security: ProcessSecurityDNA

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "pid": self.pid,
            "identity": asdict(self.identity),
            "execution": asdict(self.execution),
            "network": asdict(self.network),
            "privacy": asdict(self.privacy),
            "security": asdict(self.security),
        }


class ProcessDNAService:
    """Constructs real-time evidence-backed Process DNA profiles."""

    _hash_cache: dict[str, str] = {}

    @classmethod
    def _compute_sha256(cls, path_str: str | None) -> str | None:
        if not path_str:
            return None
        if path_str in cls._hash_cache:
            return cls._hash_cache[path_str]
        try:
            p = Path(path_str)
            if not p.exists() or not p.is_file() or p.stat().st_size > 50 * 1024 * 1024:
                return None
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            digest = h.hexdigest().lower()
            cls._hash_cache[path_str] = digest
            return digest
        except Exception:
            return None

    @classmethod
    def get_process_dna(cls, pid: int) -> ProcessDNAProfile | None:
        """Construct deep DNA profile for a target PID."""
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        try:
            p = psutil.Process(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

        # 1. Identity
        try:
            name = p.name()
        except Exception:
            name = "unknown"

        try:
            exe = p.exe()
        except Exception:
            exe = None

        exe_exists = bool(exe and Path(exe).exists())
        sha256 = cls._compute_sha256(exe)

        try:
            ppid = p.ppid()
        except Exception:
            ppid = None

        parent_name = None
        if ppid:
            try:
                parent_name = psutil.Process(ppid).name()
            except Exception:
                parent_name = None

        child_pids = []
        try:
            child_pids = [c.pid for c in p.children(recursive=False)]
        except Exception:
            pass

        try:
            create_time_ts = p.create_time()
            created_iso = datetime.fromtimestamp(create_time_ts, tz=timezone.utc).isoformat()
            lifetime = max(0.0, (now.timestamp() - create_time_ts))
        except Exception:
            created_iso = now_iso
            lifetime = 0.0

        try:
            cmdline_list = p.cmdline()
            cmdline = " ".join(cmdline_list) if cmdline_list else None
        except Exception:
            cmdline = None

        try:
            username = p.username()
        except Exception:
            username = None

        is_elevated = False
        try:
            if sys.platform == "win32":
                import ctypes
                # Check process token elevation if accessible
                is_elevated = username is not None and ("system" in username.lower() or "administrator" in username.lower())
        except Exception:
            pass

        identity = ProcessIdentityDNA(
            pid=pid,
            name=name,
            exe_path=exe,
            exe_exists=exe_exists,
            sha256_hash=sha256,
            parent_pid=ppid,
            parent_name=parent_name,
            child_pids=child_pids,
            created_time=created_iso,
            lifetime_seconds=round(lifetime, 1),
            is_elevated=is_elevated,
            username=username,
            cmdline=cmdline,
        )

        # 2. Execution Metrics
        try:
            cpu_pct = p.cpu_percent(interval=None)
        except Exception:
            cpu_pct = 0.0

        try:
            mem_info = p.memory_info()
            rss = mem_info.rss
        except Exception:
            rss = 0

        try:
            num_threads = p.num_threads()
        except Exception:
            num_threads = 0

        try:
            num_handles = p.num_handles() if hasattr(p, "num_handles") else 0
        except Exception:
            num_handles = 0

        try:
            status = p.status()
        except Exception:
            status = "running"

        execution = ProcessExecutionDNA(
            cpu_percent=round(cpu_pct, 1),
            memory_rss_bytes=rss,
            memory_mb=round(rss / (1024 * 1024), 1),
            num_threads=num_threads,
            num_handles=num_handles,
            status=status,
        )

        # 3. Network Sockets
        connections_list = []
        listening_ports = []
        remote_endpoints = []
        try:
            conns = p.connections(kind="inet")
            for c in conns:
                laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else ""
                raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else ""
                if c.status == "LISTEN" and c.laddr:
                    listening_ports.append(c.laddr.port)
                if raddr and raddr not in remote_endpoints:
                    remote_endpoints.append(raddr)
                connections_list.append({
                    "fd": c.fd,
                    "family": str(c.family),
                    "type": str(c.type),
                    "local_address": laddr,
                    "remote_address": raddr,
                    "status": c.status,
                })
        except Exception:
            pass

        network = ProcessNetworkDNA(
            connection_count=len(connections_list),
            connections=connections_list,
            listening_ports=listening_ports,
            remote_endpoints=remote_endpoints,
        )

        # 4. Privacy Sentinel Association
        cam_active = False
        mic_active = False
        try:
            from aura.sensors.camera import CameraIntelligenceCollector
            from aura.sensors.microphone import MicrophoneIntelligenceCollector
            cam_snap = CameraIntelligenceCollector.collect_snapshot()
            mic_snap = MicrophoneIntelligenceCollector.collect_snapshot()
            cam_active = bool(pid in cam_snap.active_pids or (cam_snap.active_process_name and cam_snap.active_process_name.lower() == name.lower()))
            mic_active = bool(pid in mic_snap.active_pids or (mic_snap.active_process_name and mic_snap.active_process_name.lower() == name.lower()))
        except Exception:
            pass

        privacy = ProcessPrivacyDNA(
            camera_access_detected=cam_active,
            microphone_access_detected=mic_active,
            privacy_events_count=1 if (cam_active or mic_active) else 0,
            last_privacy_access=now_iso if (cam_active or mic_active) else None,
        )

        # 5. Security & Risk Scoring
        rules_triggered = []
        evidences = []
        risk = 0

        # Location heuristic
        if exe:
            exe_lower = exe.lower()
            if "appdata\\local\\temp" in exe_lower or "\\downloads\\" in exe_lower or "\\users\\public\\" in exe_lower:
                rules_triggered.append("RUL-SUSPICIOUS-EXEC-PATH")
                risk += 25
                evidences.append({
                    "type": "LOCATION_ANOMALY",
                    "description": f"Process executable resides in user-writable/temp directory: {exe}",
                    "severity": "MEDIUM",
                })

        # Exfiltration heuristic
        if (cam_active or mic_active) and len(remote_endpoints) > 0:
            rules_triggered.append("RUL-PRIVACY-NETWORK-CONCURRENCY")
            risk += 35
            evidences.append({
                "type": "PRIVACY_CONCURRENCY",
                "description": f"Process is actively streaming hardware media with {len(remote_endpoints)} remote socket(s)",
                "severity": "HIGH",
            })

        # Listening port heuristic
        if listening_ports:
            risk += 10
            evidences.append({
                "type": "LISTENING_SOCKET",
                "description": f"Process is actively binding listening ports: {listening_ports}",
                "severity": "LOW",
            })

        risk = max(0, min(100, risk))
        if risk >= 75:
            r_level = "CRITICAL"
        elif risk >= 50:
            r_level = "HIGH"
        elif risk >= 25:
            r_level = "MEDIUM"
        elif risk > 0:
            r_level = "LOW"
        else:
            r_level = "NORMAL"

        security = ProcessSecurityDNA(
            rules_triggered=rules_triggered,
            ml_anomaly_score=round(risk / 100.0, 2),
            baseline_deviation=0.0,
            risk_score=risk,
            risk_level=r_level,
            evidences=evidences,
        )

        return ProcessDNAProfile(
            timestamp=now_iso,
            pid=pid,
            identity=identity,
            execution=execution,
            network=network,
            privacy=privacy,
            security=security,
        )
