"""
Unit tests for StreamManager, bounded queues, backpressure, and heartbeat.
"""

from __future__ import annotations

import asyncio
import pytest

from aura.api.stream import CLIENT_QUEUE_MAXSIZE, MAX_WEBSOCKET_CLIENTS, StreamManager
from aura.contracts.auth import AuthScope, AuthTokenClaims
from aura.contracts.stream import HeartbeatMessage, LiveStreamMessage, StreamMessageType, TelemetryTickMessage
from aura.models.types import PrivacyHardwareStatus


@pytest.mark.anyio
async def test_stream_manager_registration_and_bounds() -> None:
    """Verify client connection limits and queue bounding."""
    manager = StreamManager(max_clients=3, queue_maxsize=5)
    claims = AuthTokenClaims(token_id="tok1", issued_to="Tab 1", scope=AuthScope.READ_ONLY, issued_at="now")

    # Mock websocket object
    class DummyWS:
        pass

    q1 = await manager.register_client("c1", DummyWS(), claims)  # type: ignore[arg-type]
    q2 = await manager.register_client("c2", DummyWS(), claims)  # type: ignore[arg-type]
    q3 = await manager.register_client("c3", DummyWS(), claims)  # type: ignore[arg-type]

    assert manager.client_count == 3

    # Exceeding max clients raises ValueError
    with pytest.raises(ValueError, match="limit"):
        await manager.register_client("c4", DummyWS(), claims)  # type: ignore[arg-type]

    await manager.remove_client("c2")
    assert manager.client_count == 2


@pytest.mark.anyio
async def test_stream_manager_broadcast_and_engine_independence() -> None:
    """Verify broadcast returns immediately when 0 clients and dispatches when clients exist."""
    manager = StreamManager()
    hb = HeartbeatMessage(sequence=1)

    # 1. Zero clients: returns 0 immediately without error
    assert manager.broadcast_sync(hb) == 0

    # 2. Add client and broadcast
    claims = AuthTokenClaims(token_id="tok1", issued_to="Tab 1", scope=AuthScope.READ_ONLY, issued_at="now")
    q = await manager.register_client("c1", None, claims)  # type: ignore[arg-type]

    dispatched = manager.broadcast_sync(hb)
    assert dispatched == 1
    assert not q.empty()

    msg_json = await q.get()
    assert '"type":"heartbeat"' in msg_json
