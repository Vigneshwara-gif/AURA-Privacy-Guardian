"""
Fault tolerance and failure isolation tests for AURA background daemon.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from aura.agent.daemon import AuraAgentDaemon
from aura.agent.mutex import SingleInstanceGuard
from aura.contracts.agent import AgentState
from aura.core.config import Settings
from aura.core.paths import AuraPaths
from aura.engine.service import AuraEngineService
from aura.sensors.collector import SensorCollector
from aura.storage.sqlite import StorageEngine


@pytest.mark.anyio
async def test_agent_continues_on_failing_sensor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify an isolated sensor failure degrades health status without killing the loop."""
    db_path = tmp_path / "failing_sensor_test.db"
    storage = StorageEngine(db_path)
    paths = AuraPaths(
        install_root=Path(__file__).resolve().parents[1],
        user_root=tmp_path,
        user_root_origin="test",
    )
    settings = Settings()
    settings.sensors.collection_interval_seconds = 0.1

    collector = SensorCollector(sample_interval=0.02)
    # Inject a failing sensor probe via monkeypatch on psutil
    monkeypatch.setattr("psutil.net_io_counters", MagicMock(side_effect=RuntimeError("Simulated network driver fault")))

    engine = AuraEngineService(settings=settings, paths=paths, storage=storage, collector=collector)
    mutex_name = f"Local\\AURA_Failing_Test_{tmp_path.name}"
    guard = SingleInstanceGuard(mutex_name=mutex_name, fallback_lockfile=tmp_path / "fail.lock")

    daemon = AuraAgentDaemon(
        settings=settings,
        paths=paths,
        storage=storage,
        collector=collector,
        engine=engine,
        mutex_guard=guard,
    )

    await daemon.start(run_api=False)
    for _ in range(30):
        if daemon.cycle_count >= 2:
            break
        await asyncio.sleep(0.05)

    # Daemon is still running and collecting other sensors
    assert daemon.is_running is True
    assert daemon.cycle_count >= 2

    # Status reflects degraded component
    status = daemon.get_status()
    assert any("Network" in comp for comp in status.degraded_components)

    await daemon.stop()
    storage.close()
