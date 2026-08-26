"""
Unit and integration tests for AuraAgentDaemon lifecycle, loop scheduling, and persistence.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import pytest

from aura.agent.daemon import AuraAgentDaemon
from aura.agent.mutex import SingleInstanceGuard
from aura.contracts.agent import AgentState
from aura.core.config import Settings
from aura.core.paths import AuraPaths
from aura.engine.service import AuraEngineService
from aura.sensors.collector import SensorCollector
from aura.storage.sqlite import StorageEngine


@pytest.fixture
def agent_daemon(tmp_path: Path) -> AuraAgentDaemon:
    db_path = tmp_path / "daemon_test.db"
    storage = StorageEngine(db_path)
    paths = AuraPaths(
        install_root=Path(__file__).resolve().parents[1],
        user_root=tmp_path,
        user_root_origin="test",
    )
    settings = Settings()
    # Fast 0.1s interval for tests
    settings.sensors.collection_interval_seconds = 0.1
    collector = SensorCollector(sample_interval=0.02)
    engine = AuraEngineService(settings=settings, paths=paths, storage=storage, collector=collector)

    mutex_name = f"Local\\AURA_Daemon_Test_{tmp_path.name}"
    lock_file = tmp_path / "agent_daemon.lock"
    guard = SingleInstanceGuard(mutex_name=mutex_name, fallback_lockfile=lock_file)

    daemon = AuraAgentDaemon(
        settings=settings,
        paths=paths,
        storage=storage,
        collector=collector,
        engine=engine,
        mutex_guard=guard,
    )
    yield daemon
    guard.release()
    storage.close()


@pytest.mark.anyio
async def test_agent_daemon_lifecycle(agent_daemon: AuraAgentDaemon) -> None:
    """Verify STARTING -> RUNNING -> multiple cycles -> STOPPING -> STOPPED."""
    assert agent_daemon.state == AgentState.STOPPED
    assert agent_daemon.is_running is False

    # 1. Start daemon without opening live port (fast test)
    await agent_daemon.start(run_api=False)
    assert agent_daemon.state == AgentState.RUNNING
    assert agent_daemon.is_running is True

    # 2. Let background loop execute at least 2 cycles
    for _ in range(60):
        if agent_daemon.cycle_count >= 2:
            break
        await asyncio.sleep(0.05)
    assert agent_daemon.cycle_count >= 2

    # 3. Check status reporting
    status = agent_daemon.get_status()
    assert status.state == AgentState.RUNNING
    assert status.pid > 0
    assert status.uptime_seconds >= 0.2
    assert status.last_successful_collection is not None

    # 4. Check that data reached SQLite
    count = agent_daemon.storage.get_telemetry_count()
    assert count >= 2

    # 5. Stop daemon
    await agent_daemon.stop()
    assert agent_daemon.state == AgentState.STOPPED
    assert agent_daemon.is_running is False
