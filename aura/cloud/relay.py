"""
Real-time Multi-Tenant Telemetry Relay Hub.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class CloudTelemetryRelay:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._agents: Dict[str, WebSocket] = {}
        self._client_subscribers: Dict[str, Set[WebSocket]] = {}
        self._latest_ticks: Dict[str, str] = {}

    async def register_agent(self, device_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._agents[device_id] = ws
            logger.info("Agent connected for device [%s]", device_id)

    async def unregister_agent(self, device_id: str) -> None:
        async with self._lock:
            if self._agents.get(device_id) is not None:
                del self._agents[device_id]
            logger.info("Agent disconnected for device [%s]", device_id)

        offline_msg = json.dumps({
            "version": 2,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "agent_status_change",
            "payload": {
                "state": "STOPPED",
                "version": "2.0.0",
                "uptime_seconds": 0.0,
                "degraded_components": ["Agent Offline / Disconnected"],
            },
        })
        await self.broadcast_to_device_subscribers(device_id, offline_msg)

    async def register_client(self, device_id: str, ws: WebSocket) -> None:
        cached_tick = None
        async with self._lock:
            if device_id not in self._client_subscribers:
                self._client_subscribers[device_id] = set()
            self._client_subscribers[device_id].add(ws)
            cached_tick = self._latest_ticks.get(device_id)

        if cached_tick:
            try:
                await ws.send_text(cached_tick)
            except Exception:
                pass

    async def unregister_client(self, device_id: str, ws: WebSocket) -> None:
        async with self._lock:
            if device_id in self._client_subscribers:
                self._client_subscribers[device_id].discard(ws)
                if not self._client_subscribers[device_id]:
                    del self._client_subscribers[device_id]

    async def broadcast_to_device_subscribers(self, device_id: str, raw_json: str) -> None:
        try:
            parsed = json.loads(raw_json)
            if parsed.get("type") == "telemetry_tick":
                async with self._lock:
                    self._latest_ticks[device_id] = raw_json
        except Exception:
            pass

        async with self._lock:
            subscribers = list(self._client_subscribers.get(device_id, []))

        if not subscribers:
            return

        dead_sockets = []
        for client_ws in subscribers:
            try:
                await client_ws.send_text(raw_json)
            except Exception:
                dead_sockets.append(client_ws)

        if dead_sockets:
            async with self._lock:
                if device_id in self._client_subscribers:
                    for dead in dead_sockets:
                        self._client_subscribers[device_id].discard(dead)

    def is_agent_connected(self, device_id: str) -> bool:
        return device_id in self._agents
