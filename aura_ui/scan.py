"""
Scan orchestration for the AURA interface.

The scan itself belongs to ``aura_core.scan_once``; this module only decides
*when* to call it and *how* the result is recorded in the session, so the
detection engine is untouched.

The one non-obvious behaviour here is demonstration isolation, and it is worth
reading before changing anything.

``aura_core.scan_once`` appends every scan it performs to the monitoring log,
including a synthetic one. That is the correct default for live monitoring and
the wrong outcome for a demonstration: synthetic values would enter the
historical record, then feed the process baseline, the analytics charts and
every anomaly counter, permanently and invisibly. So a demonstration scan runs
with the log file captured beforehand and restored byte-for-byte afterwards in
a ``finally`` block. The result is still returned and displayed, clearly marked
as synthetic, but the production history is exactly as it was.

This preserves the behaviour the previous interface already had. The cleaner
long-term fix is a ``persist=False`` parameter on ``scan_once`` itself, which
would remove the need to touch the file at all — but that changes backend
behaviour, so it is deliberately not done here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st

import aura_core
from logger import LOG_FILE

__all__ = [
    "DEMO_PROFILE",
    "SOURCE_DEMO",
    "SOURCE_LIVE",
    "run_scan",
    "store_result",
]

SOURCE_LIVE = "LIVE_WINDOWS"
SOURCE_DEMO = "SAFE_DEMONSTRATION"

#: Values used for the demonstration scan. Deliberately extreme, obviously
#: synthetic, and harmless: they are inputs to the detector, never actions
#: taken against the machine.
DEMO_PROFILE: dict[str, float] = {
    "CPU": 96.0,
    "Net": 5000.0,
}


def run_scan(
    model: Any,
    probe_camera: bool = False,
    synthetic: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Run one scan and return the raw result dictionary.

    A live scan is persisted to the monitoring log by the engine, as intended.
    A synthetic scan is not: the log is restored afterwards so demonstration
    telemetry cannot contaminate production history.
    """
    if synthetic is None:
        return aura_core.scan_once(
            model,
            probe_camera=probe_camera,
            synthetic=None,
        )

    original_bytes: bytes | None = None
    try:
        if LOG_FILE.exists():
            original_bytes = LOG_FILE.read_bytes()

        # The camera is never probed during a demonstration. A synthetic run
        # must not touch real hardware.
        return aura_core.scan_once(
            model,
            probe_camera=False,
            synthetic=synthetic,
        )
    finally:
        try:
            if original_bytes is None:
                # There was no log before this scan, so the only rows in it
                # are the synthetic ones the scan just wrote.
                if LOG_FILE.exists():
                    LOG_FILE.unlink()
            else:
                LOG_FILE.write_bytes(original_bytes)
        except OSError:
            # A failure to restore must not mask the scan result or crash the
            # page, but it must be visible, because it means synthetic rows
            # may have survived into the log.
            st.session_state["aura_demo_restore_failed"] = True


def store_result(result: dict[str, Any], is_demo: bool) -> None:
    """
    Record a scan result in the session.

    Uses the same session keys the previous interface used, so nothing about
    the scan lifecycle changes and a result taken before this build was applied
    remains readable.
    """
    st.session_state["latest_result"] = result
    st.session_state["latest_scan_source"] = (
        SOURCE_DEMO if is_demo else SOURCE_LIVE
    )
    st.session_state["last_scan_time"] = datetime.now()
