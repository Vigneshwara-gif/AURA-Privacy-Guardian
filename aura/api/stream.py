"""
WebSocket Live Stream Manager with bounded per-client queues and backpressure protection.

Guarantees:
  - Bounded queues (maxsize=100) per connected client.
  - Engine continuous monitoring NEVER blocks on slow or disconnected clients.
  - Broadcast returns immediately if zero clients are connected.
  - Heartbeats transmitted every 20 seconds.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any
from fastapi import WebSocket

from aura.contracts.auth import AuthTokenClaims
from aura.contracts.stream import HeartbeatMessage, LiveStreamMessage, StreamMessageType

logger = logging.getLogger(__name__)

MAX_WEBSOCKET_CLIENTS = 10
CLIENT_QUEUE_MAXSIZE = 100


class StreamManager:
    """Manages active WebSocket client connections, backpressure, and broadcast fan-out."""

    def __init__(self, max_clients: int = MAX_WEBSOCKET_CLIENTS, queue_maxsize: int = CLIENT_QUEUE_MAXSIZE) -> None:
        self.max_clients = max_clients
        self.queue_maxsize = queue_maxsize
        self._clients: dict[str, tuple[WebSocket, asyncio.Queue, AuthTokenClaims]] = {}
        self._lock = asyncio.Lock()
        self._sequence = 0

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def register_client(
        self,
        client_id: str,
        websocket: WebSocket,
        claims: AuthTokenClaims,
    ) -> asyncio.Queue:
        """Register a new authenticated WebSocket client connection."""
        async with self._lock:
            if len(self._clients) >= self.max_clients:
                raise ValueError(f"Maximum concurrent client limit ({self.max_clients}) reached")
            queue: asyncio.Queue = asyncio.Queue(maxsize=self.queue_maxsize)
            self._clients[client_id] = (websocket, queue, claims)
            logger.info("Registered WebSocket client [%s] (Total active: %d)", client_id, len(self._clients))
            return queue

    async def remove_client(self, client_id: str) -> None:
        """Remove a disconnected client."""
        async with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                logger.info("Removed WebSocket client [%s] (Total active: %d)", client_id, len(self._clients))

    def broadcast_sync(self, message: Any) -> int:
        """
        Synchronously dispatch a broadcast message to all active client queues without blocking.
        If zero clients are connected, returns 0 immediately.
        """
        if not self._clients:
            return 0

        dispatched = 0
        raw_msg = message.model_dump_json() if hasattr(message, "model_dump_json") else str(message)

        for client_id, (_, queue, _) in list(self._clients.items()):
            try:
                queue.put_nowait(raw_msg)
                dispatched += 1
            except asyncio.QueueFull:
                # Backpressure: Drop non-critical telemetry tick if full
                msg_type = getattr(message, "type", "")
                if msg_type == StreamMessageType.TELEMETRY_TICK:
                    try:
                        queue.get_nowait()  # Drop oldest tick
                        queue.put_nowait(raw_msg)
                        dispatched += 1
                    except Exception:
                        pass
                else:
                    logger.warning("WebSocket queue saturated for client [%s]; dropped frame", client_id)

        return dispatched

    async def send_heartbeat(self) -> None:
        """Send periodic heartbeat to all connected clients."""
        self._sequence += 1
        hb = HeartbeatMessage(sequence=self._sequence)
        self.broadcast_sync(hb)
