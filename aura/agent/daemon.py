"""
Autonomous AURA Windows Background Agent Daemon.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import signal
import sys
import time
from typing import Any
import uuid
import uvicorn

from aura.agent.cloud_client import CloudAgentConnector
from aura.agent.mutex import SingleInstanceGuard
from aura.agent.notifications import IncidentNotificationTracker, WindowsToastNotifier
from aura.agent.power import PowerTransitionDetector
from aura.api.auth import SessionManager
from aura.api.ratelimit import RateLimiter
from aura.api.server import create_app
from aura.api.stream import StreamManager
from aura.contracts.agent import AgentState, AgentStatus
from aura.contracts.api import SecurityEventResponse, TelemetryResponse
from aura.contracts.auth import AuthScope
from aura.contracts.stream import SecurityEventMessage, TelemetryTickMessage
from aura.core.config import Settings, get_settings
from aura.core.paths import AuraPaths, get_paths
from aura.engine.service import AuraEngineService
from aura.models.types import SecurityEvent
from aura.sensors.collector import SensorCollector
from aura.storage.sqlite import StorageEngine

logger = logging.getLogger(__name__)


class AuraAgentDaemon:
    def __init__(
        self,
        settings: Settings | None = None,
        paths: AuraPaths | None = None,
        storage: StorageEngine | None = None,
        collector: SensorCollector | None = None,
        engine: AuraEngineService | None = None,
        mutex_guard: SingleInstanceGuard | None = None,
        session_manager: SessionManager | None = None,
        stream_manager: StreamManager | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.paths = paths or get_paths()
        self.storage = storage or StorageEngine(self.paths.database_path)
        self.collector = collector or SensorCollector(
            sample_interval=self.settings.sensors.cpu_sample_interval_seconds
        )
        self.engine = engine or AuraEngineService(
            settings=self.settings,
            paths=self.paths,
            storage=self.storage,
            collector=self.collector,
        )
        self.mutex_guard = mutex_guard or SingleInstanceGuard()
        self.session_manager = session_manager or SessionManager()
        self.stream_manager = stream_manager or StreamManager()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.power_detector = PowerTransitionDetector()
        self.notification_tracker = IncidentNotificationTracker(min_severity="MEDIUM", enabled=True)
        self.toast_notifier = WindowsToastNotifier()
        self.cloud_connector = CloudAgentConnector()

        self._state = AgentState.STOPPED
        self._started_at: datetime | None = None
        self._last_collection: datetime | None = None
        self._last_persistence: datetime | None = None
        self._consecutive_failures = 0
        self._degraded_components: set[str] = set()

        self._stop_event = asyncio.Event()
        self._monitoring_task: asyncio.Task | None = None
        self._cloud_task: asyncio.Task | None = None
        self._uvicorn_server: uvicorn.Server | None = None
        self._uvicorn_task: asyncio.Task | None = None
        self._cycle_lock = asyncio.Lock()
        self._cycle_count = 0

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state in {AgentState.RUNNING, AgentState.DEGRADED}

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    def get_status(self) -> AgentStatus:
        now = datetime.now(timezone.utc)
        uptime = (now - self._started_at).total_seconds() if self._started_at else 0.0

        return AgentStatus(
            state=self._state,
            version="2.0.0",
            pid=os.getpid(),
            started_at=self._started_at.isoformat() if self._started_at else None,
            uptime_seconds=uptime,
            last_successful_collection=self._last_collection.isoformat() if self._last_collection else None,
            last_persistence=self._last_persistence.isoformat() if self._last_persistence else None,
            consecutive_failures=self._consecutive_failures,
            degraded_components=sorted(list(self._degraded_components)),
        )

    async def start(self, run_api: bool = True) -> None:
        if self.is_running or self._state == AgentState.STARTING:
            logger.warning("Agent already running or starting.")
            return

        self._state = AgentState.STARTING
        logger.info("Starting AURA Background Agent Daemon (PID: %d)...", os.getpid())

        if not self.mutex_guard.acquire():
            self._state = AgentState.FAILED
            logger.error("Single-Instance acquisition failed. Another AURA agent is active.")
            raise RuntimeError("Another instance of AURA agent is already running.")

        try:
            self.storage.migrate()
            self.engine.start()
            self._started_at = datetime.now(timezone.utc)
            self._stop_event.clear()
            self.power_detector = PowerTransitionDetector()

            self._monitoring_task = asyncio.create_task(self._run_monitoring_loop())

            if self.cloud_connector.is_paired:
                self._cloud_task = asyncio.create_task(self.cloud_connector.run())

            if run_api:
                await self._start_api_server()

            self._state = AgentState.RUNNING
            logger.info("AURA Background Agent Daemon is RUNNING.")

        except Exception as exc:
            self._state = AgentState.FAILED
            logger.exception("Fatal error during agent startup: %s", exc)
            self.mutex_guard.release()
            raise

    async def _start_api_server(self) -> None:
        self.session_manager.create_bootstrap_code(
            scope=AuthScope.OPERATOR,
            ttl_seconds=86400,
            custom_code="local-dev",
        )

        app = create_app(
            engine=self.engine,
            storage=self.storage,
            settings=self.settings,
            session_manager=self.session_manager,
            stream_manager=self.stream_manager,
            rate_limiter=self.rate_limiter,
        )

        host = self.settings.api.host or "127.0.0.1"
        port = self.settings.api.port or 8787

        if host not in {"127.0.0.1", "localhost", "::1"}:
            logger.warning("Unsafe bind host %r rejected. Defaulting to 127.0.0.1.", host)
            host = "127.0.0.1"

        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((host, port))
            sock.close()
        except OSError as exc:
            logger.error("Port %d is occupied (%s). API disabled; engine continuing in DEGRADED mode.", port, exc)
            self._degraded_components.add(f"API Server (Port {port} occupied)")
            return

        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="warning",
            access_log=False,
        )
        self._uvicorn_server = uvicorn.Server(config)
        self._uvicorn_task = asyncio.create_task(self._uvicorn_server.serve())
        logger.info("AURA Local API Server bound to http://%s:%d", host, port)

    async def stop(self) -> None:
        if self._state == AgentState.STOPPED or self._state == AgentState.STOPPING:
            return

        self._state = AgentState.STOPPING
        logger.info("Stopping AURA Background Agent Daemon...")

        self._stop_event.set()
        self.cloud_connector.stop()

        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._monitoring_task), timeout=3.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        if self._cloud_task and not self._cloud_task.done():
            self._cloud_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._cloud_task), timeout=1.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        if self._uvicorn_server:
            self._uvicorn_server.should_exit = True
        if self._uvicorn_task and not self._uvicorn_task.done():
            try:
                await asyncio.wait_for(asyncio.shield(self._uvicorn_task), timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        self.engine.stop()
        try:
            self.storage.close()
        except Exception as exc:
            logger.error("Error closing storage: %s", exc)

        self.mutex_guard.release()
        self._state = AgentState.STOPPED
        logger.info("AURA Background Agent Daemon STOPPED cleanly.")

    async def _run_monitoring_loop(self) -> None:
        interval = float(self.settings.sensors.collection_interval_seconds or 5.0)

        while not self._stop_event.is_set():
            power_event = self.power_detector.check_transition(interval)
            if power_event is not None:
                logger.warning("System power resume detected (gap: %.1fs). Resetting baselines.", power_event.gap_seconds)
                self.collector.reset_baselines()
                self.engine.reset_baselines()

            cycle_start = time.monotonic()

            async with self._cycle_lock:
                try:
                    await self._execute_cycle()
                    self._consecutive_failures = 0
                    if not self._degraded_components:
                        self._state = AgentState.RUNNING
                except Exception as exc:
                    self._consecutive_failures += 1
                    self._state = AgentState.DEGRADED
                    logger.error("Exception in monitoring cycle #%d: %s", self._cycle_count, exc)

            elapsed = time.monotonic() - cycle_start
            sleep_duration = max(0.01, interval - elapsed)

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_duration)
                break
            except (asyncio.TimeoutError, TimeoutError):
                pass

    async def _execute_cycle(self) -> None:
        now = datetime.now(timezone.utc)

        scan_res = await asyncio.to_thread(self.engine.scan_once, probe_camera=True, probe_microphone=True, is_demo=False)
        self._last_collection = now
        self._last_persistence = now

        degraded = []
        for health in scan_res.telemetry.sensor_health:
            if health.status.value in {"ERROR", "DEGRADED", "UNAVAILABLE"}:
                degraded.append(f"{health.name} ({health.status.value})")

        if degraded:
            self._degraded_components.update(degraded)
        else:
            self._degraded_components.clear()

        telem_resp = TelemetryResponse(
            timestamp=scan_res.telemetry.timestamp,
            cpu_percent=scan_res.telemetry.cpu_percent,
            cpu_cores=scan_res.telemetry.cpu_cores,
            cpu_frequency_mhz=scan_res.telemetry.cpu_frequency_mhz,
            memory_percent=scan_res.telemetry.memory_percent,
            memory_used_gb=scan_res.telemetry.memory_used_gb,
            memory_total_gb=scan_res.telemetry.memory_total_gb,
            disk_percent=scan_res.telemetry.disk_percent,
            disk_free_gb=scan_res.telemetry.disk_free_gb,
            disk_total_gb=scan_res.telemetry.disk_total_gb,
            disk_path=scan_res.telemetry.disk_path,
            net_upload_kbps=scan_res.telemetry.net_upload_kbps,
            net_download_kbps=scan_res.telemetry.net_download_kbps,
            process_count=scan_res.telemetry.process_count,
            established_connections=scan_res.telemetry.established_connections,
            listening_connections=scan_res.telemetry.listening_connections,
            remote_connections=scan_res.telemetry.remote_connections,
            camera_status=scan_res.telemetry.camera_status,
            microphone_status=scan_res.telemetry.microphone_status,
        )
        tick_msg = TelemetryTickMessage(payload=telem_resp)
        self.stream_manager.broadcast_sync(tick_msg)

        # Also push to Cloud Relay
        raw_tick_json = json.dumps(tick_msg.to_dict()) if hasattr(tick_msg, "to_dict") else json.dumps({
            "version": 2,
            "timestamp": tick_msg.timestamp,
            "type": "telemetry_tick",
            "payload": telem_resp.model_dump(),
        })
        self.cloud_connector.enqueue_message(raw_tick_json)

        if scan_res.event:
            should_notify, reason = self.notification_tracker.evaluate_event(scan_res.event)
            if should_notify:
                logger.info("Dispatching notification for %s (%s, reason=%s)", scan_res.event.event_type, scan_res.event.severity, reason)
                asyncio.create_task(
                    self.toast_notifier.notify_async(
                        title=f"{scan_res.event.event_type}",
                        message=scan_res.event.summary,
                        severity=scan_res.event.severity,
                    )
                )

            if scan_res.event.severity in {"MEDIUM", "HIGH", "CRITICAL"}:
                evt_resp = SecurityEventResponse(
                    event_id=scan_res.event.event_id,
                    timestamp=scan_res.event.timestamp,
                    event_type=scan_res.event.event_type,
                    severity=scan_res.event.severity,
                    risk_score=scan_res.event.risk_score,
                    source=scan_res.event.source,
                    summary=scan_res.event.summary,
                    evidence=scan_res.event.evidence,
                    affected_resource=scan_res.event.affected_resource,
                    correlation_id=scan_res.event.correlation_id,
                    schema_version=scan_res.event.schema_version,
                    incident_id=scan_res.event.incident_id,
                    is_resolved=scan_res.event.is_resolved,
                )
                evt_msg = SecurityEventMessage(payload=evt_resp)
                self.stream_manager.broadcast_sync(evt_msg)
                raw_evt_json = json.dumps(evt_msg.to_dict()) if hasattr(evt_msg, "to_dict") else json.dumps({
                    "version": 2,
                    "timestamp": evt_msg.timestamp,
                    "type": "security_event",
                    "payload": evt_resp.model_dump(),
                })
                self.cloud_connector.enqueue_message(raw_evt_json)

        self._cycle_count += 1
