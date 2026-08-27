"""
Hierarchical Windows Process Tree Intelligence for AURA.

Constructs true parent-child trees from the live Windows process table,
identifying orphan processes, root services, interactive sessions, and
anomalous execution lineage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import logging
import os
from typing import Any
import psutil

from aura.sensors.process_intel import ConfidenceLevel, ProcessInfo

logger = logging.getLogger(__name__)


@dataclass
class ProcessTreeNode:
    """Node in the hierarchical process tree."""
    pid: int
    name: str
    exe_path: str | None
    parent_pid: int | None
    created_time: str
    cpu_percent: float
    memory_rss_bytes: int
    status: str
    username: str | None
    is_elevated: bool
    cmdline: str | None = None
    num_threads: int = 0
    num_handles: int = 0
    sha256_hash: str | None = None
    children: list[ProcessTreeNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert tree node to nested JSON dictionary."""
        return {
            "pid": self.pid,
            "name": self.name,
            "exe_path": self.exe_path,
            "parent_pid": self.parent_pid,
            "created_time": self.created_time,
            "cpu_percent": self.cpu_percent,
            "memory_rss_bytes": self.memory_rss_bytes,
            "status": self.status,
            "username": self.username,
            "is_elevated": self.is_elevated,
            "cmdline": self.cmdline,
            "num_threads": self.num_threads,
            "num_handles": self.num_handles,
            "sha256_hash": self.sha256_hash,
            "children": [child.to_dict() for child in self.children],
        }


class ProcessTreeBuilder:
    """Constructs, queries, and analyzes the Windows process tree."""

    @staticmethod
    def _compute_sha256(file_path: str | None) -> str | None:
        """Safely compute SHA-256 for an executable path (capped at 50MB)."""
        if not file_path or not os.path.isfile(file_path):
            return None
        try:
            if os.path.getsize(file_path) > 50 * 1024 * 1024:
                return None
            h = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    @classmethod
    def get_process_tree(cls, compute_hashes_for_roots: bool = False) -> list[ProcessTreeNode]:
        """
        Build the full parent-child hierarchy of all running processes.
        Returns a list of root process tree nodes.
        """
        nodes_by_pid: dict[int, ProcessTreeNode] = {}
        parent_map: dict[int, int | None] = {}

        now_iso = datetime.now(timezone.utc).isoformat()

        # Phase 1: Collect snapshots for all processes
        for p in psutil.process_iter():
            try:
                pid = p.pid
                name = p.name()
                ppid = p.ppid()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

            ctime_iso = now_iso
            try:
                ctime_iso = datetime.fromtimestamp(p.create_time(), timezone.utc).isoformat()
            except Exception:
                pass

            exe_path = None
            try:
                exe_path = p.exe()
            except Exception:
                pass

            mem_rss = 0
            try:
                mem_rss = p.memory_info().rss
            except Exception:
                pass

            cpu_pct = 0.0
            try:
                cpu_pct = p.cpu_percent(interval=None)
            except Exception:
                pass

            username = None
            try:
                username = p.username()
            except Exception:
                pass

            cmdline_str = None
            try:
                cmd_parts = p.cmdline()
                if cmd_parts:
                    cmdline_str = " ".join(cmd_parts)
            except Exception:
                pass

            threads = 0
            try:
                threads = p.num_threads()
            except Exception:
                pass

            handles = 0
            try:
                if hasattr(p, "num_handles"):
                    handles = p.num_handles()
            except Exception:
                pass

            node = ProcessTreeNode(
                pid=pid,
                name=name,
                exe_path=exe_path,
                parent_pid=ppid,
                created_time=ctime_iso,
                cpu_percent=cpu_pct,
                memory_rss_bytes=mem_rss,
                status="running",
                username=username,
                is_elevated=(exe_path is None and pid > 0),
                cmdline=cmdline_str,
                num_threads=threads,
                num_handles=handles,
                sha256_hash=None,
                children=[],
            )
            nodes_by_pid[pid] = node
            parent_map[pid] = ppid

        # Phase 2: Link children to parents
        roots: list[ProcessTreeNode] = []
        for pid, node in nodes_by_pid.items():
            ppid = parent_map.get(pid)
            if ppid is not None and ppid in nodes_by_pid and ppid != pid:
                nodes_by_pid[ppid].children.append(node)
            else:
                # Root process or parent terminated (orphan)
                roots.append(node)

        # Sort roots and children deterministically by memory usage
        roots.sort(key=lambda x: x.memory_rss_bytes, reverse=True)
        for node in nodes_by_pid.values():
            node.children.sort(key=lambda x: x.memory_rss_bytes, reverse=True)

        return roots

    @classmethod
    def get_process_subtree(cls, target_pid: int) -> ProcessTreeNode | None:
        """Retrieve the process tree subtree rooted at target_pid."""
        tree = cls.get_process_tree()

        def find_node(current: ProcessTreeNode, pid: int) -> ProcessTreeNode | None:
            if current.pid == pid:
                return current
            for child in current.children:
                found = find_node(child, pid)
                if found:
                    return found
            return None

        for root_node in tree:
            res = find_node(root_node, target_pid)
            if res:
                return res
        return None
