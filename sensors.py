from __future__ import annotations

import time
from typing import Optional

import psutil

try:
    import cv2
except ImportError:
    cv2 = None


_last_net_sent: Optional[int] = None
_last_net_time: Optional[float] = None


def get_network_rate() -> float:
    """Return outgoing network activity in KB/s over the last sampling interval."""
    global _last_net_sent, _last_net_time

    now = time.time()
    current = psutil.net_io_counters().bytes_sent

    if _last_net_sent is None or _last_net_time is None:
        _last_net_sent = current
        _last_net_time = now
        return 0.0

    elapsed = max(now - _last_net_time, 0.001)
    rate_kbps = max(current - _last_net_sent, 0) / 1024 / elapsed

    _last_net_sent = current
    _last_net_time = now
    return round(rate_kbps, 3)


def get_camera_status(enabled: bool = False) -> int:
    """
    Probe whether a camera can be opened.

    1 = available/openable
    0 = unavailable/not probed

    This is NOT proof that another application is currently using the camera.
    """
    if not enabled or cv2 is None:
        return 0

    cap = None
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        return int(cap.isOpened())
    except Exception:
        return 0
    finally:
        if cap is not None:
            cap.release()


def get_data(probe_camera: bool = False) -> tuple[float, float, int]:
    """Collect one AURA sensor reading."""
    cpu = round(psutil.cpu_percent(interval=0.5), 2)
    net = get_network_rate()
    cam = get_camera_status(probe_camera)
    return cpu, net, cam
