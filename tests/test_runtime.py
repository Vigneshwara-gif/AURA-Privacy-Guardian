"""
Unit and integration tests for AuraRuntime lifecycle.
"""

import asyncio
from pathlib import Path
import uuid
import pytest

from aura.agent.mutex import SingleInstanceGuard
from aura.contracts.agent import AgentState
from aura.core.config import Settings
from aura.core.paths import AuraPaths
from aura.runtime import AuraRuntime


@pytest.mark.anyio
async def test_runtime_lifecycle_start_and_stop(tmp_path: Path) -> None:
    """Verify complete runtime initialization, start, and graceful stop."""
    paths = AuraPaths(
        install_root=Path(__file__).resolve().parents[1],
        user_root=tmp_path / "user",
        user_root_origin="test",
    )
    settings = Settings()
    settings.api.port = 18787  # Use isolated port for test
    mutex_guard = SingleInstanceGuard(mutex_name=f"Local\\AURA_Test_Mutex_{uuid.uuid4().hex}")

    runtime = AuraRuntime(settings=settings, paths=paths, mutex_guard=mutex_guard)

    # Start daemon in background task
    task = asyncio.create_task(runtime.start())
    await asyncio.sleep(1.2)

    assert runtime.daemon.is_running
    assert runtime.daemon.state in {AgentState.RUNNING, AgentState.DEGRADED}

    # Stop runtime
    await runtime.stop()
    await task

    assert runtime.daemon.state == AgentState.STOPPED
