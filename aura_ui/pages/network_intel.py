"""
Network Intelligence — sockets and remote endpoints, with visibility limits
stated plainly.

The single most important honesty point on this page: on Windows,
``psutil.net_connections()`` raises ``AccessDenied`` for sockets owned by other
users unless the process is elevated, and the backend swallows that into an
empty list. An empty socket table therefore means "AURA could not see" far more
often than it means "nothing is connected". This page never renders an empty or
sparse result as an all-clear; it labels it as a permission limit and says so.

The page also refuses to editorialise about endpoints. A remote address AURA is
connected to is just an address. AURA does not resolve it against threat
intelligence, does not geolocate it, and does not call it malicious. The counts
and the classification band shown here come straight from the privacy engine's
own conservative thresholds, which treat connection volume as weak evidence by
design.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from aura_ui import components as ui
from aura_ui import core
from aura_ui.context import Context
from aura_ui.theme import PALETTE

# Mirrors privacy_monitor.classify_connection_activity thresholds, for display
# only. The engine remains the single source of truth for the actual score.
_CONNECTION_BANDS = {
    "VERY_HIGH": (PALETTE["orange"], "Unusually high — review with other "
                  "indicators"),
    "HIGH": (PALETTE["yellow"], "Elevated remote connection volume"),
    "WATCH": (PALETTE["blue"], "Above the usual level; informational"),
    "NORMAL": (PALETTE["green"], "Within the normal range for a desktop"),
}


def _band_for_remote(count: int) -> str:
    """Label a remote-connection count using the engine's own thresholds."""
    if count >= 150:
        return "VERY_HIGH"
    if count >= 75:
        return "HIGH"
    if count >= 30:
        return "WATCH"
    return "NORMAL"


def _kpi_cards(ctx: Context, permission_limited: bool) -> list[str]:
    conn = ctx.connections or {}
    total = core.safe_int(conn.get("connection_count"), 0)
    remote = core.safe_int(conn.get("remote_connection_count"), 0)
    established = core.safe_int(conn.get("established_connections"), 0)
    listening = core.safe_int(conn.get("listening_connections"), 0)

    cards: list[str] = []

    if permission_limited:
        cards.append(
            ui.kpi_card(
                "Sockets visible",
                "Limited",
                "",
                "No sockets were returned. Windows withholds connection "
                "details for other users' processes without elevation.",
                PALETTE["orange"],
                "This is a visibility limit, not evidence of an idle network.",
            )
        )
    else:
        cards.append(
            ui.kpi_card(
                "Sockets visible",
                core.fmt_int(total),
                "",
                f"{established} established · {listening} listening.",
                PALETTE["blue"],
                "Total sockets this process can see. Others may be hidden "
                "without elevation.",
            )
        )

    band = _band_for_remote(remote)
    band_colour, band_note = _CONNECTION_BANDS[band]
    cards.append(
        ui.kpi_card(
            "Remote connections",
            core.fmt_int(remote),
            "",
            band_note,
            band_colour if remote else PALETTE["green"],
            "Classified by the privacy engine's conservative thresholds. "
            "Connection volume is deliberately weak evidence on its own.",
        )
    )

    cards.append(
        ui.kpi_card(
            "Established",
            core.fmt_int(established),
            "",
            "Sockets in the ESTABLISHED state.",
            PALETTE["blue"] if established else PALETTE["border"],
        )
    )

    cards.append(
        ui.kpi_card(
            "Listening",
            core.fmt_int(listening),
            "",
            "Local services accepting inbound connections.",
            PALETTE["blue"] if listening else PALETTE["border"],
        )
    )

    return cards


def _state_breakdown(ctx: Context) -> None:
    """Bar chart of socket states."""
    conn = ctx.connections or {}
    states = {
        "Established": core.safe_int(conn.get("established_connections"), 0),
        "Listening": core.safe_int(conn.get("listening_connections"), 0),
        "Time-wait": core.safe_int(conn.get("time_wait_connections"), 0),
        "Other": core.safe_int(conn.get("other_connections"), 0),
    }
    if sum(states.values()) <= 0:
        ui.empty_state(
            "No socket states to chart",
            "No sockets were visible to AURA, so there is nothing to break "
            "down by state.",
        )
        return
    frame = pd.DataFrame(
        {"Sockets": list(states.values())},
        index=list(states.keys()),
    )
    st.bar_chart(frame, height=240)
    st.caption(
        "Sockets grouped by TCP state, counted directly from the socket "
        "table. Listening sockets are local services; time-wait sockets are "
        "connections that have already closed."
    )


def _endpoints_table(ctx: Context) -> None:
    """Most-frequent remote endpoints."""
    conn = ctx.connections or {}
    endpoints = conn.get("top_remote_endpoints")
    if not isinstance(endpoints, list) or not endpoints:
        ui.info_state(
            "No remote endpoints recorded",
            "Either no outbound connections are currently visible, or their "
            "remote addresses were withheld by the operating system.",
        )
        return

    records: list[dict] = []
    for item in endpoints:
        if not isinstance(item, dict):
            continue
        records.append(
            {
                "Endpoint": core.safe_text(item.get("endpoint"), "—"),
                "Connections": core.safe_int(item.get("connections"), 0),
            }
        )

    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        ui.info_state(
            "No remote endpoints recorded",
            "The endpoint list was returned but could not be read.",
        )
        return

    ui.full_dataframe(frame, height=min(360, 46 + 32 * len(frame)))
    st.caption(
        "Remote endpoints ordered by how many current sockets connect to "
        "them. AURA does not resolve, geolocate or reputation-check these "
        "addresses; a frequently contacted endpoint is often a legitimate "
        "service such as an update server or content delivery network."
    )


def _connection_records(ctx: Context) -> None:
    """The per-socket detail table."""
    conn = ctx.connections or {}
    records = conn.get("connections")
    if not isinstance(records, list) or not records:
        ui.info_state(
            "No per-socket detail",
            "Individual socket records were not available in this snapshot.",
        )
        return

    rows: list[dict] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "PID": core.safe_int(item.get("pid"), 0),
                "Process": core.safe_text(item.get("process"), "—"),
                "Status": core.safe_text(item.get("status"), "—"),
                "Local": core.safe_text(item.get("local"), "—"),
                "Remote": core.safe_text(item.get("remote"), "—"),
            }
        )

    frame = pd.DataFrame.from_records(rows)
    if frame.empty:
        ui.info_state(
            "No per-socket detail",
            "Socket records were returned but none could be read.",
        )
        return

    query = st.text_input(
        "Filter sockets by process, address or state",
        key="net_filter",
        placeholder="e.g. ESTABLISHED, chrome, 443",
    )
    if query:
        needle = query.strip().lower()
        mask = pd.Series(False, index=frame.index)
        for column in ("Process", "Status", "Local", "Remote", "PID"):
            mask = mask | frame[column].astype(str).str.lower().str.contains(
                needle
            )
        filtered = frame[mask]
    else:
        filtered = frame

    ui.full_dataframe(filtered, height=min(520, 46 + 30 * len(filtered)))
    st.caption(
        f"Showing {len(filtered):,} of {len(frame):,} socket records visible "
        "to AURA. A process shown as '—' means the owning process could not "
        "be identified without elevation, not that the connection is hidden "
        "or malicious."
    )


def render(ctx: Context) -> None:
    """Render the Network Intelligence page."""
    ui.page_head(
        "Network Intelligence",
        "Live socket and remote-endpoint telemetry. Where Windows withholds "
        "information without administrator rights, that limit is labelled "
        "rather than shown as a quiet network.",
        "Network",
    )

    conn = ctx.connections or {}
    total = core.safe_int(conn.get("connection_count"), 0)
    permission_limited = total <= 0

    control_left, control_right = st.columns([1, 4], gap="small")
    with control_left:
        if st.button("↻  Refresh connections", key="net_refresh"):
            core.bump_refresh()
            st.rerun()
    with control_right:
        st.caption(
            "Socket telemetry is cached for a few seconds. Enumerating every "
            "connection on each interaction would be needlessly expensive."
        )

    if permission_limited:
        ui.warn_state(
            "Connection visibility is limited",
            "AURA received an empty socket table. On Windows this almost "
            "always means it is running without administrator rights, so the "
            "operating system is withholding sockets owned by other users. "
            "Run AURA elevated for a complete view. Critically, an empty "
            "table is not evidence that the network is idle.",
        )

    ui.section("Connection posture")
    ui.metric_grid(_kpi_cards(ctx, permission_limited), per_row=4)

    ui.section("Socket states")
    left, right = st.columns([1, 1], gap="medium")
    with left:
        _state_breakdown(ctx)
    with right:
        st.markdown("**Top remote endpoints**")
        _endpoints_table(ctx)

    ui.section("Socket detail")
    _connection_records(ctx)
