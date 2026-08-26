"""
Process Intelligence — what is actually running, from the live process table.

This page shows real ``psutil`` process telemetry and nothing else. It does not
assign a "process risk" score, a reputation, or a malicious/benign verdict to
any process, because AURA has no data that would justify one: it does not hash
executables, consult threat intelligence, or inspect signing certificates. A
process consuming CPU is a process consuming CPU, not a threat.

What the page does do is rank processes by the resources they are using and
surface the counts AURA's risk engine actually consumes (the total process
count, which is compared against a learned baseline elsewhere). Every figure
here is a direct read of the operating system's own accounting.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from aura_ui import components as ui
from aura_ui import core
from aura_ui.context import Context
from aura_ui.theme import PALETTE


def _kpi_cards(ctx: Context) -> list[str]:
    processes = ctx.processes or {}
    count = core.safe_int(processes.get("process_count"), 0)
    names = processes.get("process_names")
    unique = len(names) if isinstance(names, list) else 0
    agg_cpu = core.safe_float(processes.get("aggregate_cpu_percent"), 0.0)
    agg_mem = core.safe_float(processes.get("aggregate_memory_percent"), 0.0)

    cards: list[str] = []

    if count <= 0:
        cards.append(
            ui.kpi_card(
                "Processes running",
                "Unavailable",
                "",
                "Process enumeration returned nothing. AURA is itself a "
                "process, so a zero count means the probe failed.",
                PALETTE["red"],
            )
        )
    else:
        cards.append(
            ui.kpi_card(
                "Processes running",
                core.fmt_int(count),
                "",
                f"{unique} distinct executable names.",
                PALETTE["blue"],
                "Counted directly from the operating system's process table.",
            )
        )

    cards.append(
        ui.kpi_card(
            "Distinct names",
            core.fmt_int(unique) if unique else "—",
            "",
            "Unique process names seen in this snapshot.",
            PALETTE["blue"] if unique else PALETTE["border"],
        )
    )

    cards.append(
        ui.kpi_card(
            "Aggregate CPU",
            core.fmt_float(agg_cpu, 1),
            "%",
            "Sum across all visible processes; can exceed 100% on a "
            "multi-core machine because each core contributes separately.",
            PALETTE["blue"],
            "This is a sum of per-process CPU percentages, not overall "
            "utilisation. On an 8-core system the ceiling is roughly 800%.",
        )
    )

    cards.append(
        ui.kpi_card(
            "Aggregate memory",
            core.fmt_float(agg_mem, 1),
            "%",
            "Sum of each process's share of physical memory.",
            PALETTE["blue"],
        )
    )

    return cards


def _process_frame(processes: dict) -> pd.DataFrame:
    """Build a display frame from the raw process list."""
    rows = processes.get("processes")
    if not isinstance(rows, list) or not rows:
        return pd.DataFrame()

    records: list[dict] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        records.append(
            {
                "PID": core.safe_int(item.get("pid"), 0),
                "Process": core.safe_text(item.get("name"), "unknown"),
                "User": core.safe_text(item.get("username"), "—"),
                "Status": core.safe_text(item.get("status"), "—"),
                "CPU %": core.safe_float(item.get("cpu_percent"), 0.0),
                "Memory %": core.safe_float(item.get("memory_percent"), 0.0),
            }
        )

    return pd.DataFrame.from_records(records)


def _top_table(title: str, rows: list, metric_key: str, metric_label: str,
               note: str) -> None:
    """Render one 'top consumers' table for CPU or memory."""
    if not isinstance(rows, list) or not rows:
        ui.empty_state(
            f"No {title.lower()} available",
            "The process probe returned no ranked entries for this metric.",
        )
        return

    records: list[dict] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        records.append(
            {
                "PID": core.safe_int(item.get("pid"), 0),
                "Process": core.safe_text(item.get("name"), "unknown"),
                "User": core.safe_text(item.get("username"), "—"),
                metric_label: core.safe_float(item.get(metric_key), 0.0),
            }
        )

    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        ui.empty_state(
            f"No {title.lower()} available",
            "The ranked entries could not be read.",
        )
        return

    ui.full_dataframe(frame, height=min(400, 46 + 34 * len(frame)))
    st.caption(note)


def render(ctx: Context) -> None:
    """Render the Process Intelligence page."""
    ui.page_head(
        "Process Intelligence",
        "The live process table exactly as the operating system reports it. "
        "AURA ranks processes by real resource use and does not assign any "
        "invented risk, reputation or verdict to a process.",
        "Processes",
    )

    control_left, control_right = st.columns([1, 4], gap="small")
    with control_left:
        if st.button("↻  Refresh processes", key="proc_refresh"):
            core.bump_refresh()
            st.rerun()
    with control_right:
        st.caption(
            "Process telemetry is cached for a few seconds so repeated "
            "interactions do not re-enumerate the whole table each time."
        )

    processes = ctx.processes or {}
    if core.safe_int(processes.get("process_count"), 0) <= 0:
        ui.error_state(
            "Process telemetry unavailable",
            "The process enumeration probe returned no processes. Because "
            "AURA itself runs as a process, an empty table means the probe "
            "failed rather than that nothing is running. No further detail on "
            "this page can be trusted until it recovers.",
        )
        return

    ui.section("Process summary")
    ui.metric_grid(_kpi_cards(ctx), per_row=4)

    ui.section("Top consumers")
    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown("**By CPU**")
        _top_table(
            "CPU consumers",
            processes.get("top_cpu_processes"),
            "cpu_percent",
            "CPU %",
            "The ten processes using the most CPU in this snapshot. A high "
            "value is not by itself suspicious — compilers, browsers and "
            "AURA's own scan all use CPU.",
        )
    with right:
        st.markdown("**By memory**")
        _top_table(
            "memory consumers",
            processes.get("top_memory_processes"),
            "memory_percent",
            "Memory %",
            "The ten processes holding the most physical memory in this "
            "snapshot, as a share of total RAM.",
        )

    ui.section("Full process table")
    frame = _process_frame(processes)
    if frame.empty:
        ui.warn_state(
            "No per-process detail",
            "A process count was reported but the detailed per-process list "
            "was empty, which usually means the fields were withheld by the "
            "operating system for processes owned by other users.",
        )
        return

    query = st.text_input(
        "Filter by process name, user or PID",
        key="proc_filter",
        placeholder="e.g. chrome, SYSTEM, 1024",
    )
    if query:
        needle = query.strip().lower()
        mask = (
            frame["Process"].astype(str).str.lower().str.contains(needle)
            | frame["User"].astype(str).str.lower().str.contains(needle)
            | frame["PID"].astype(str).str.contains(needle)
        )
        filtered = frame[mask]
    else:
        filtered = frame

    filtered = filtered.sort_values("CPU %", ascending=False)

    ui.full_dataframe(filtered, height=min(560, 46 + 30 * len(filtered)))
    st.caption(
        f"Showing {len(filtered):,} of {len(frame):,} processes visible to "
        "AURA, sorted by CPU. Processes owned by other users may be hidden or "
        "have fields withheld unless AURA runs elevated — an incomplete table "
        "is a permission limit, not proof of a clean system."
    )
