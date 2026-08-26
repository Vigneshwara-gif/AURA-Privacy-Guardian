"""
Unit and integration tests for WindowsStartupManager (Registry Run Key & Task Scheduler).
"""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
import pytest

from aura.agent.startup import WindowsStartupManager


def test_resolve_executable_target() -> None:
    """Verify target executable resolution in dev environment."""
    mgr = WindowsStartupManager()
    exe, args = mgr.resolve_executable_target()
    assert exe.exists()
    assert exe.name.lower().endswith(".exe")


def test_startup_lifecycle_windows() -> None:
    """Live integration test for Windows startup registration & unregistration."""
    if sys.platform != "win32":
        pytest.skip("Windows-only integration test")

    test_reg_name = "AURA_Test_AutoStart_Key"
    mgr = WindowsStartupManager(reg_name=test_reg_name)

    try:
        # 1. Clean pre-state
        mgr.uninstall_startup()
        assert mgr.is_installed() is False

        # 2. Install startup entry
        res = mgr.install_startup()
        assert res.get("success") is True
        assert mgr.is_installed() is True

        # 3. Verify status
        status = mgr.get_status()
        assert status.get("installed") is True

        # 4. Verify integrity
        integrity = mgr.verify_integrity()
        assert integrity.get("valid") is True
        assert integrity.get("tampered") is False

        # 5. Idempotent re-install
        res2 = mgr.install_startup()
        assert res2.get("success") is True
        assert mgr.is_installed() is True

    finally:
        # 6. Clean post-state
        uninst = mgr.uninstall_startup()
        assert uninst.get("success") is True
        assert mgr.is_installed() is False


def test_startup_manager_non_windows() -> None:
    """Verify safe degradation on non-Windows platforms."""
    with patch("sys.platform", "linux"):
        mgr = WindowsStartupManager()
        assert mgr.is_installed() is False
        assert mgr.install_startup().get("success") is False
        assert mgr.uninstall_startup().get("success") is False
