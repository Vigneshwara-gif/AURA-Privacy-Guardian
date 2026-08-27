"""
Tests for System Intelligence and Process Tree Builder.
"""

import pytest
from aura.sensors.system_intel import SystemIntelligenceCollector
from aura.sensors.process_tree import ProcessTreeBuilder, ProcessTreeNode


def test_system_intelligence_snapshot():
    snap = SystemIntelligenceCollector.collect_snapshot()
    assert snap.os_name != ""
    assert snap.architecture != ""
    assert snap.cpu_logical_cores >= 1
    assert snap.memory_total_gb > 0.0
    assert snap.uptime_seconds >= 0.0
    assert isinstance(snap.cpu_cores, list)
    assert isinstance(snap.partitions, list)


def test_process_tree_builder():
    roots = ProcessTreeBuilder.get_process_tree()
    assert len(roots) > 0
    first_root = roots[0]
    assert isinstance(first_root, ProcessTreeNode)
    assert first_root.pid >= 0
    assert first_root.name != ""
    d = first_root.to_dict()
    assert "pid" in d
    assert "children" in d
    assert isinstance(d["children"], list)


def test_process_subtree_search():
    roots = ProcessTreeBuilder.get_process_tree()
    target_pid = roots[0].pid
    sub = ProcessTreeBuilder.get_process_subtree(target_pid)
    assert sub is not None
    assert sub.pid == target_pid
