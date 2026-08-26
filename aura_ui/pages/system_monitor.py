"""
System Monitor — live host telemetry and sensor integrity.

The important content on this page is the sensor health table, which reports
what each probe is *actually* doing rather than whether it returned a value.

The backend sensor functions return a zero-filled dictionary when they fail,
and they fail silently. A machine reporting 0 GB of RAM and 0 logical cores has
not become extraordinarily idle; its probes have broken. Because a failure and
a genuine zero are indistinguishable by value, this page classifies each sensor
by whether its reading is physically possible, and shows a status of HEALTHY,
DEGRADED, PERMISSION LIMITED, UNAVAILABLE, NOT PRESENT, NOT PROBED or PRIMING
with the reasoning attached.

Two statuses exist specifically to avoid overstating a problem. Hardware that
is not fitted (no battery) is NOT PRESENT, not a fault. And a rate sensor whose
first reading is necessarily 0.00 — because a rate needs two counter readings to
exist — is PRIMING, not broken and not proof of an idle disk.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from aura_ui import components as ui
from aura_ui import core
from aura_ui.context import Context
from aura_ui.theme import PALETTE


def _kpi_cards(ctx: Context) -> list[str]:
    snapshot = ctx.snapshot or {}
    cpu = snapshot.get("cpu") or {}
    memory = snapshot.get("memory") or {}
    disk = snapshot.get("disk") or {}
    network = snapshot.get("network") or {}

    cards: list[str] = []

    cores = core.safe_int(cpu.get("logical_cores"), 0)
    if cores <= 0:
        cards.append(
            ui.kpi_card(
                "Processor",
                "Unavailable",
                "",
                "The CPU probe reported zero logical cores.",
                PALETTE["red"],
            )
        )
    else:
        frequency = core.safe_float(cpu.get("frequency_mhz"), 0.0)
        footer = f"{cores} logical cores"
        if frequency > 0:
            footer += f" · {frequency:,.0f} MHz"
        cards.append(
            ui.kpi_card(
                "Processor",
                core.fmt_float(cpu.get("usage_percent"), 1),
                "%",
                footer,
                PALETTE["blue"],
                "Sampled over a 0.2 second interval by psutil.",
            )
        )

    total_gb = core.safe_float(memory.get("total_gb"), 0.0)
    if total_gb <= 0:
        cards.append(
            ui.kpi_card(
                "Memory",
                "Unavailable",
                "",
                "The memory probe reported zero total capacity.",
                PALETTE["red"],
            )
        )
    else:
        cards.append(
            ui.kpi_card(
                "Memory",
                core.fmt_float(memory.get("usage_percent"), 1),
                "%",
                f"{core.fmt_float(memory.get('available_gb'), 1)} GB "
                f"available of {core.fmt_float(total_gb, 1)} GB",
                PALETTE["blue"],
            )
        )

    disk_total = core.safe_float(disk.get("total_gb"), 0.0)
    if disk_total <= 0:
        cards.append(
            ui.kpi_card(
                "Disk",
                "Unavailable",
                "",
                "Volume capacity could not be read.",
                PALETTE["red"],
            )
        )
    else:
        cards.append(
            ui.kpi_card(
                "Disk  " + core.safe_text(disk.get("path"), "C:"),
                core.fmt_float(disk.get("usage_percent"), 1),
                "%",
                f"{core.fmt_float(disk.get('free_gb'), 1)} GB free of "
                f"{core.fmt_float(disk_total, 1)} GB",
                PALETTE["blue"],
            )
        )

    sent = core.safe_int(network.get("bytes_sent"), 0)
    received = core.safe_int(network.get("bytes_received"), 0)
    if sent == 0 and received == 0:
        cards.append(
            ui.kpi_card(
                "Network throughput",
                "Unavailable",
                "",
                "Cumulative byte counters read zero in both directions.",
                PALETTE["red"],
            )
        )
    else:
        down = core.safe_float(network.get("download_kbps"), 0.0)
        up = core.safe_float(network.get("upload_kbps"), 0.0)
        cards.append(
            ui.kpi_card(
                "Network throughput",
                core.fmt_float(down + up, 1),
                "KB/s",
                f"↓ {down:,.1f}  ·  ↑ {up:,.1f} KB/s",
                PALETTE["blue"],
                "Derived from the difference between two counter readings a "
                "few seconds apart.",
            )
        )

    return cards


def _health_table(ctx: Context) -> None:
    """Per-sensor status, with the reasoning for each verdict."""
    records = ctx.health or []
    if not records:
        ui.error_state(
            "Sensor status unavailable",
            "No sensor records could be produced, which means the telemetry "
            "collector itself did not return usable data.",
        )
        return

    rows: list[str] = [
        '<div class="aura-card" style="padding:0;overflow:hidden">',
        '<table style="width:100%;border-collapse:collapse;'
        'font-size:0.82rem">',
        "<thead><tr>",
    ]
    for heading, width in (
        ("Sensor", "20%"),
        ("Status", "17%"),
        ("Reading", "13%"),
        ("Assessment", "50%"),
    ):
        rows.append(
            '<th style="text-align:left;padding:10px 14px;width:'
            + width
            + ";background:"
            + PALETTE["surface_3"]
            + ";color:"
            + PALETTE["text_dim"]
            + ";font-size:0.72rem;letter-spacing:0.055em;"
            + 'text-transform:uppercase;font-weight:700">'
            + ui.esc(heading, "")
            + "</th>"
        )
    rows.append("</tr></thead><tbody>")

    for record in records:
        status = core.safe_text(record.get("status"), "UNKNOWN")
        rows.append(
            '<tr style="border-top:1px solid '
            + PALETTE["border_soft"]
            + '">'
            + '<td style="padding:10px 14px;color:'
            + PALETTE["text"]
            + ';font-weight:550">'
            + ui.esc(record.get("name"), "")
            + "</td>"
            + '<td style="padding:10px 14px">'
            + ui.status_badge(status)
            + "</td>"
            + '<td style="padding:10px 14px;font-family:var(--aura-mono);'
            + "color:"
            + PALETTE["text"]
            + '">'
            + ui.esc(record.get("value"), "—")
            + "</td>"
            + '<td style="padding:10px 14px;color:'
            + PALETTE["text_dim"]
            + ';line-height:1.5">'
            + ui.esc(record.get("detail"), "")
            + "</td></tr>"
        )

    rows.append("</tbody></table></div>")
    st.markdown("".join(rows), unsafe_allow_html=True)

    rollup = ctx.rollup or {}
    faults = rollup.get("fault_names") or []
    limited = rollup.get("limited_names") or []
    if faults:
        ui.error_state(
            "Sensors not reporting",
            "The following probes returned physically impossible readings and "
            "are treated as failed rather than as zero: "
            + ", ".join(str(name) for name in faults)
            + ". Any figure derived from them on other pages is incomplete.",
        )
    if limited:
        ui.warn_state(
            "Reduced visibility",
            "Windows is withholding information from: "
            + ", ".join(str(name) for name in limited)
            + ". Running AURA as an administrator would widen visibility, but "
            "the absence of data is not evidence that nothing is happening.",
        )


def _per_core(ctx: Context) -> None:
    """Per-core utilisation, when the platform exposes it."""
    cpu = (ctx.snapshot or {}).get("cpu") or {}
    per_core = cpu.get("per_core_usage")
    if not isinstance(per_core, list) or not per_core:
        ui.info_state(
            "Per-core detail not available",
            "This platform did not return per-core utilisation figures.",
        )
        return

    columns = st.columns(min(4, len(per_core)), gap="small")
    for index, usage in enumerate(per_core):
        with columns[index % len(columns)]:
            ui.bar_meter(
                f"Core {index}",
                core.safe_float(usage, 0.0),
            )


def _interfaces(ctx: Context) -> None:
    """Active network interfaces and their addresses."""
    interfaces = (ctx.snapshot or {}).get("network_interfaces")
    if not isinstance(interfaces, list) or not interfaces:
        ui.warn_state(
            "No interface detail",
            "Interface enumeration returned nothing. This is usually a "
            "permission restriction rather than an absence of interfaces.",
        )
        return

    table = pd.DataFrame(
        [
            {
                "Interface": core.safe_text(item.get("interface"), "—"),
                "IPv4": core.safe_text(item.get("ipv4"), "—"),
                "IPv6": core.safe_text(item.get("ipv6"), "—"),
                "Link": "Up" if item.get("up") else "Down",
            }
            for item in interfaces
            if isinstance(item, dict)
        ]
    )
    if table.empty:
        ui.warn_state(
            "No interface detail",
            "Interface records were returned but none could be read.",
        )
        return

    ui.full_dataframe(table, height=min(320, 46 + 30 * len(table)))
    st.caption(
        "Interface metadata only. AURA reads addresses and link state; it "
        "does not capture, inspect or store packet contents. MAC addresses "
        "are collected by the sensor but deliberately not displayed here, "
        "since they identify hardware and are not needed for this view."
    )


def _resource_history(ctx: Context) -> None:
    """CPU over the stored history.

    Only CPU is charted from history. The monitoring log's ``Memory`` column
    exists in the schema but the current logging call never populates it, so it
    is a constant 0.0 on every row. Plotting it would draw a flat line at zero
    that reads as "memory was measured at 0%", which is false — it was simply
    never recorded. Live memory is shown above; only the truthfully logged CPU
    series is trended here.
    """
    trend = core.trend_frame(ctx.logs, ["CPU"], limit=300)
    if trend.empty:
        ui.empty_state(
            "No CPU history yet",
            "The CPU trend is drawn from the monitoring log. Once at least "
            "two scans have been recorded, this chart populates from those "
            "real stored readings.",
        )
        return
    st.line_chart(trend, height=260)
    st.caption(
        f"CPU utilisation across the most recent {len(trend):,} stored "
        "events, taken directly from the monitoring log. Memory is not "
        "charted here because it is not written to the log by the current "
        "scan pipeline; the live memory reading is shown above instead."
    )


def _network_history(ctx: Context) -> None:
    """Outbound network rate over the stored history.

    Charts the ``Net`` column, which is the outbound rate the scan pipeline
    actually logs. The schema also defines ``Network_Upload`` and
    ``Network_Download``, but the current logging call does not populate them,
    so they are a constant 0.0 and are deliberately not plotted — a flat zero
    would misrepresent unrecorded data as a measured idle network.
    """
    trend = core.trend_frame(ctx.logs, ["Net"], limit=300)
    if trend.empty:
        ui.empty_state(
            "No network history yet",
            "Outbound network history will appear here once scans have been "
            "recorded in the monitoring log.",
        )
        return
    trend = trend.rename(columns={"Net": "Upload KB/s"})
    st.area_chart(trend, height=260)
    st.caption(
        "Outbound network rate in KB/s across stored events, from the log's "
        "Net column. Download is not charted from history because it is not "
        "written to the log by the current scan pipeline; the live download "
        "figure is shown in the throughput card above."
    )


def _host_facts(ctx: Context) -> None:
    """Platform, uptime and power state."""
    snapshot = ctx.snapshot or {}
    platform_info = snapshot.get("platform")
    uptime = snapshot.get("uptime") or {}
    battery = snapshot.get("battery") or {}
    disk_io = snapshot.get("disk_io") or {}

    rows: list[tuple[str, str]] = []

    if isinstance(platform_info, dict):
        for key in ("system", "release", "version", "machine", "processor"):
            value = core.safe_text(platform_info.get(key), "")
            if value:
                rows.append((key.title(), value))
    elif platform_info:
        rows.append(("Platform", core.safe_text(platform_info, "—")))

    rows.append(
        (
            "Uptime",
            core.safe_text(uptime.get("uptime_text"), core.UNKNOWN),
        )
    )
    rows.append(
        (
            "Processes",
            core.fmt_int(snapshot.get("process_count")),
        )
    )
    rows.append(
        (
            "Disk read",
            core.fmt_float(disk_io.get("read_mbps"), 2) + " MB/s",
        )
    )
    rows.append(
        (
            "Disk write",
            core.fmt_float(disk_io.get("write_mbps"), 2) + " MB/s",
        )
    )

    if battery.get("available"):
        rows.append(
            (
                "Battery",
                core.fmt_float(battery.get("percent"), 0)
                + "%  ("
                + core.safe_text(battery.get("status"), "—")
                .replace("_", " ")
                .lower()
                + ")",
            )
        )
    else:
        rows.append(("Battery", "Not present"))

    ui.def_list(rows)


def render(ctx: Context) -> None:
    """Render the System Monitor page."""
    rollup = ctx.rollup or {}
    status = core.safe_text(rollup.get("status"), "UNAVAILABLE")

    ui.page_head(
        "System Monitor",
        "Live host telemetry from Windows, with the integrity of each sensor "
        "reported alongside its reading.",
        "System",
        ui.status_badge(status),
    )

    control_left, control_right = st.columns([1, 4], gap="small")
    with control_left:
        if st.button("↻  Refresh telemetry", key="sysmon_refresh"):
            core.bump_refresh()
            st.rerun()
    with control_right:
        st.caption(
            "Readings are cached for a few seconds. This is deliberate: "
            "throughput is calculated between two counter readings, so "
            "sampling faster than the cache interval would divide a tiny byte "
            "delta by a tiny time delta and report meaningless spikes."
        )

    ui.section("Current utilisation")
    ui.metric_grid(_kpi_cards(ctx), per_row=4)

    left, right = st.columns([1, 1], gap="medium")
    with left:
        ui.card("Resource pressure", _live_bars(ctx))
    with right:
        _host_facts(ctx)

    ui.section(
        "Sensor integrity",
        f"{core.safe_int(rollup.get('assessed'), 0)} sensors assessed",
    )
    _health_table(ctx)

    ui.section("Processor detail")
    _per_core(ctx)

    ui.section("Network interfaces")
    _interfaces(ctx)

    ui.section("Historical trends", f"{ctx.history_rows:,} stored events")
    history_left, history_right = st.columns(2, gap="medium")
    with history_left:
        st.markdown("**CPU utilisation**")
        _resource_history(ctx)
    with history_right:
        st.markdown("**Outbound network**")
        _network_history(ctx)


def _live_bars(ctx: Context) -> str:
    """Resource bars as a single markup string for one card."""
    snapshot = ctx.snapshot or {}
    cpu = snapshot.get("cpu") or {}
    memory = snapshot.get("memory") or {}
    disk = snapshot.get("disk") or {}

    cores = core.safe_int(cpu.get("logical_cores"), 0)
    memory_total = core.safe_float(memory.get("total_gb"), 0.0)
    disk_total = core.safe_float(disk.get("total_gb"), 0.0)
    swap_percent = core.safe_float(memory.get("swap_percent"), 0.0)

    parts = [
        ui.bar_meter_markup(
            "Processor",
            None if cores <= 0 else core.safe_float(cpu.get("usage_percent")),
            "Probe failed" if cores <= 0 else f"{cores} logical cores",
            unavailable=cores <= 0,
        ),
        ui.bar_meter_markup(
            "Physical memory",
            None
            if memory_total <= 0
            else core.safe_float(memory.get("usage_percent")),
            "Probe failed"
            if memory_total <= 0
            else f"{core.fmt_float(memory.get('used_gb'), 1)} GB in use",
            unavailable=memory_total <= 0,
        ),
        ui.bar_meter_markup(
            "Swap / page file",
            None if memory_total <= 0 else swap_percent,
            "Probe failed"
            if memory_total <= 0
            else f"{core.fmt_float(memory.get('swap_used_gb'), 2)} GB used",
            unavailable=memory_total <= 0,
        ),
        ui.bar_meter_markup(
            "Disk  " + core.safe_text(disk.get("path"), "C:"),
            None
            if disk_total <= 0
            else core.safe_float(disk.get("usage_percent")),
            "Capacity unreadable"
            if disk_total <= 0
            else f"{core.fmt_float(disk.get('free_gb'), 1)} GB free",
            unavailable=disk_total <= 0,
        ),
    ]
    return "".join(parts)
