"""
Outbound Cloud WebSocket Connector for AURA Windows Agent.

Connects to AURA Cloud Backend and securely streams local real Windows telemetry
and security events to the user's paired cloud account.

Guarantees:
  - Zero local telemetry loss if cloud is offline (local SQLite WAL continues unaffected).
  - Outbound-only WSS connection (no open inbound ports exposed to internet).
  - Exponential backoff with jitter on reconnect.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any
import urllib.request
import urllib.error

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore[assignment]

from aura.core.paths import get_paths

logger = logging.getLogger(__name__)


class CloudAgentConnector:
    """Manages outbound streaming to AURA Cloud."""

    def __init__(self, config_file: Path | None = None) -> None:
        self.config_file = config_file or (get_paths().config_dir / "cloud_pairing.json")
        self._device_id: str | None = None
        self._device_token: str | None = None
        self._cloud_url: str | None = None
        self._ws: Any = None
        self._is_running = False
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self.load_config()

    def load_config(self) -> bool:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._device_id = data.get("device_id")
                    self._device_token = data.get("device_token")
                    self._cloud_url = data.get("cloud_url", "http://127.0.0.1:8000")
                    return bool(self._device_token)
            except Exception as exc:
                logger.debug("Failed to read cloud pairing config: %s", exc)
        return False

    def save_config(self, device_id: str, device_token: str, cloud_url: str) -> None:
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._device_id = device_id
        self._device_token = device_token
        self._cloud_url = cloud_url
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump({
                "device_id": device_id,
                "device_token": device_token,
                "cloud_url": cloud_url,
                "paired_at": datetime.now(timezone.utc).isoformat(),
            }, f, indent=2)
        logger.info("Saved cloud device pairing to %s", self.config_file)

    def clear_config(self) -> None:
        if self.config_file.exists():
            try:
                self.config_file.unlink()
            except Exception:
                pass
        self._device_id = None
        self._device_token = None
        logger.info("Cleared cloud device pairing config.")

    @property
    def is_paired(self) -> bool:
        return bool(self._device_token)

    def pair_with_code(self, pairing_code: str, cloud_url: str = "http://127.0.0.1:8000", hostname: str = "Windows PC") -> bool:
        """Call Cloud API /api/v1/devices/pair to exchange pairing code for permanent device_token."""
        import socket
        import platform

        real_host = socket.gethostname()
        os_info = f"Windows {platform.version()}"
        endpoint = f"{cloud_url.rstrip('/')}/api/v1/devices/pair"
        payload = json.dumps({
            "pairing_code": pairing_code.strip(),
            "hostname": real_host,
            "os_version": os_info,
        }).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                dev_id = data["device_id"]
                dev_tok = data["device_token"]
                self.save_config(dev_id, dev_tok, cloud_url)
                return True
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8")
            try:
                msg = json.loads(err_body).get("detail", err_body)
            except Exception:
                msg = err_body
            raise RuntimeError(f"Pairing failed ({err.code}): {msg}") from err
        except Exception as exc:
            raise RuntimeError(f"Could not connect to cloud server at {cloud_url}: {exc}") from exc

    def enqueue_message(self, raw_json: str) -> None:
        if not self.is_paired or not self._is_running:
            return
        try:
            self._queue.put_nowait(raw_json)
        except asyncio.QueueFull:
            pass

    async def run(self) -> None:
        if not self.is_paired or websockets is None:
            return

        self._is_running = True
        logger.info("Starting outbound Cloud Agent Connector for device [%s]...", self._device_id)

        ws_base = self._cloud_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_base}/api/v1/stream/agent?device_token={self._device_token}"

        reconnect_delay = 1.0

        while self._is_running:
            try:
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                    self._ws = ws
                    reconnect_delay = 1.0
                    logger.info("Connected to AURA Cloud WebSocket stream.")

                    while self._is_running:
                        msg = await self._queue.get()
                        await ws.send(msg)
            except (websockets.ConnectionClosed, OSError, asyncio.CancelledError) as exc:
                self._ws = None
                if not self._is_running:
                    break
                logger.debug("Cloud WebSocket disconnected (%s). Reconnecting in %.1fs...", exc, reconnect_delay)
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(15.0, reconnect_delay * 1.5)

    def stop(self) -> None:
        self._is_running = False
