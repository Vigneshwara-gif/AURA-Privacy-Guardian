"""
Unit tests for SingleInstanceGuard Named Mutex and file lock mechanisms.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from aura.agent.mutex import SingleInstanceGuard


def test_mutex_acquire_and_duplicate_rejection(tmp_path: Path) -> None:
    """Verify primary instance acquires mutex and second instance is rejected."""
    mutex_name = f"Local\\AURA_Test_Mutex_{tmp_path.name}"
    lock_file = tmp_path / "test_agent.lock"

    guard1 = SingleInstanceGuard(mutex_name=mutex_name, fallback_lockfile=lock_file)
    guard2 = SingleInstanceGuard(mutex_name=mutex_name, fallback_lockfile=lock_file)

    # 1. First acquisition must succeed
    assert guard1.acquire() is True
    assert guard1.is_acquired is True

    # 2. Second acquisition must be rejected (duplicate instance blocked)
    assert guard2.acquire() is False
    assert guard2.is_acquired is False

    # 3. Releasing first allows second to acquire
    guard1.release()
    assert guard1.is_acquired is False

    assert guard2.acquire() is True
    assert guard2.is_acquired is True
    guard2.release()


def test_mutex_context_manager(tmp_path: Path) -> None:
    """Verify context manager semantics."""
    mutex_name = f"Local\\AURA_Test_Ctx_{tmp_path.name}"
    lock_file = tmp_path / "test_ctx.lock"

    guard = SingleInstanceGuard(mutex_name=mutex_name, fallback_lockfile=lock_file)

    with guard:
        assert guard.is_acquired is True
        # Inside context, another guard cannot acquire
        dup = SingleInstanceGuard(mutex_name=mutex_name, fallback_lockfile=lock_file)
        assert dup.acquire() is False

    assert guard.is_acquired is False
