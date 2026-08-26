"""
AURA Production Local Runtime Launcher.

Initializes and coordinates the full runtime lifecycle:
  Settings -> AuraPaths -> StorageEngine (migrations) -> SensorCollector ->
  AuraEngineService -> StreamManager -> SessionManager -> RateLimiter ->
  AuraAgentDaemon (FastAPI on 127.0.0.1:8787 + background loop + Named Mutex guard).
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
from typing import Any

from aura.agent.daemon import AuraAgentDaemon
from aura.agent.mutex import SingleInstanceGuard
from aura.api.auth import SessionManager
from aura.api.ratelimit import RateLimiter
from aura.api.stream import StreamManager
from aura.contracts.agent import AgentState
from aura.contracts.auth import AuthScope
from aura.core.config import Settings, get_settings
from aura.core.logging_config import configure_logging
from aura.core.paths import AuraPaths, get_paths
from aura.core.version import __app_name__, __version__
from aura.engine.service import AuraEngineService
from aura.sensors.collector import SensorCollector
from aura.storage.sqlite import StorageEngine

logger = logging.getLogger("aura.runtime")


class AuraRuntime:
    """
    Complete lifecycle manager and supervisor for local AURA execution.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        paths: AuraPaths | None = None,
        port: int | None = None,
        host: str | None = None,
        mutex_guard: SingleInstanceGuard | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.paths = paths or get_paths()
        if port:
            self.settings.api.port = port
        if host:
            self.settings.api.host = host

        self.mutex_guard = mutex_guard or SingleInstanceGuard()
        self.storage = StorageEngine(self.paths.database_path)
        self.collector = SensorCollector(
            sample_interval=self.settings.sensors.cpu_sample_interval_seconds
        )
        self.engine = AuraEngineService(
            settings=self.settings,
            paths=self.paths,
            storage=self.storage,
            collector=self.collector,
        )
        self.session_manager = SessionManager()
        self.stream_manager = StreamManager()
        self.rate_limiter = RateLimiter()

        self.daemon = AuraAgentDaemon(
            settings=self.settings,
            paths=self.paths,
            storage=self.storage,
            collector=self.collector,
            engine=self.engine,
            mutex_guard=self.mutex_guard,
            session_manager=self.session_manager,
            stream_manager=self.stream_manager,
            rate_limiter=self.rate_limiter,
        )
        self._stop_event = asyncio.Event()

    def print_banner(self, bootstrap_code: str) -> None:
        host = self.settings.api.host or "127.0.0.1"
        port = self.settings.api.port or 8787
        api_url = f"http://{host}:{port}"
        ws_url = f"ws://{host}:{port}/api/v1/stream"
        web_url = f"http://{host}:{port}/?bootstrap={bootstrap_code}"

        print("=" * 66)
        print(f"  {__app_name__} v{__version__} — Autonomous Local Security Platform")
        print("=" * 66)
        print(f"  PID:              {os.getpid()}")
        print(f"  Local API:        {api_url}")
        print(f"  WebSocket Stream: {ws_url}")
        print(f"  Web Dashboard:    {web_url}")
        print(f"  Single-Instance:  HELD ({self.mutex_guard.mutex_name})")
        print(f"  Database Storage: {self.paths.database_path}")
        print("=" * 66)
        print("  [+] Background Sensor Sampling: ACTIVE (interval: 5.0s)")
        print("  [+] Machine Learning Engine:    ONLINE (Isolation Forest + LOF)")
        print("  [+] Real-time Event Stream:     READY")
        print("  Press Ctrl+C to terminate cleanly.")
        print("=" * 66)
        sys.stdout.flush()

    async def start(self) -> None:
        """Start daemon and local API server, maintaining event loop."""
        # Ensure local development bootstrap codes are registered
        dev_code = self.session_manager.create_bootstrap_code(
            scope=AuthScope.OPERATOR,
            ttl_seconds=86400,
            custom_code="local-dev",
        )
        cli_code = self.session_manager.create_bootstrap_code(
            scope=AuthScope.OPERATOR,
            ttl_seconds=3600,
        )

        await self.daemon.start(run_api=True)
        self.print_banner(bootstrap_code=cli_code)

        try:
            while self.daemon.is_running and not self._stop_event.is_set():
                await asyncio.sleep(0.5)
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Gracefully stop daemon, API, and release resources."""
        self._stop_event.set()
        await self.daemon.stop()


def main(args: list[str] | None = None) -> int:
    """Synchronous entry point for AURA runtime."""
    configure_logging()
    runtime = AuraRuntime()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _signal_handler() -> None:
        print("\nTermination signal received. Shutting down AURA...")
        asyncio.create_task(runtime.stop())

    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)

    try:
        loop.run_until_complete(runtime.start())
        return 0
    except KeyboardInterrupt:
        print("\nAURA Runtime interrupted by user.")
        loop.run_until_complete(runtime.stop())
        return 0
    except Exception as exc:
        print(f"FATAL: AURA Runtime encountered an unhandled error: {exc}", file=sys.stderr)
        return 1
    finally:
        loop.close()


if __name__ == "__main__":
    sys.exit(main())
