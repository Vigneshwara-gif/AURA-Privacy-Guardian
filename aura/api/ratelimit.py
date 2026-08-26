"""
In-memory sliding-window rate limiter for AURA Local API.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import threading
import time


class RateLimiter:
    """Thread-safe bounded in-memory sliding-window rate limiter."""

    def __init__(self, max_tracked_keys: int = 1000) -> None:
        self._lock = threading.RLock()
        self._max_keys = max_tracked_keys
        self._requests: dict[str, deque[float]] = {}

    def check(self, key: str, max_requests: int, window_seconds: float = 60.0) -> bool:
        """
        Record a request for the key and check if it is within limits.
        Returns True if request is permitted, False if rate limited.
        """
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            if key not in self._requests:
                if len(self._requests) >= self._max_keys:
                    # Clean up old keys
                    self._cleanup(now, window_seconds)
                self._requests[key] = deque()

            timestamps = self._requests[key]
            # Drop entries outside window
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            if len(timestamps) >= max_requests:
                return False

            timestamps.append(now)
            return True

    def _cleanup(self, now: float, window_seconds: float) -> None:
        cutoff = now - window_seconds
        stale_keys = [k for k, v in self._requests.items() if not v or v[-1] < cutoff]
        for k in stale_keys:
            del self._requests[k]
