"""
Security Overview — the executive SOC command dashboard.

Answers in one unified screen:
1. What is the current security posture and risk score?
2. Are the host sensors and anomaly detection models functioning?
3. What are the live resource measurements?
4. What has been recorded in the historical baseline and audit log?

Honesty guarantees:
- All metrics are physical reads from psutil and the ML ensemble.
- No fabricated confidence percentages or invented security claims.
- Demonstrations are quarantined and clearly labeled as synthetic.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from aura_ui import components as ui
from aura_ui import core, scan
from aura_ui.context import Context
from aura_ui.theme import PALETTE, SEVERITY_STYLES

_ELEVATED_FLOOR = 25  # MEDIUM band (25+) and above


def _protection_badge(ctx: Context) -> str:
    """Report the true operational state rather than a flattering one."""
    if not ctx.has_result:
        return ui.badge("STANDBY", PALETTE["blue"], PALETTE["blue_soft"], "○")
    if ctx.is_demo:
        return ui.badge(
            "DEMONSTRATION",
            PALETTE["violet"],
            "rgba(129, 140, 248, 0.16)",
            "▣",
        )
    return ui.badge("MONITORING", PALETTE["green"], PALETTE["green_soft"], "●")


def _privacy_indicator_count(result: dict | None) -> tuple[int, list[str]]:
    """Count the discrete privacy indicators that actually fired."""
    if not isinstance(result, dict):
        return 0, []
    fired: list[str] = []
    if result.get("privacy_event"):
        fired.append("Privacy-relevant anomaly recorded")
    if result.get("potential_data_exfiltration"):
        fired.append("Outbound traffic above watch threshold")
    if result.get("potential_camera_risk"):
        fired.append("Camera state indicator raised")
    return len(fired), fired


def _band_floor(severity: str) -> str:
    """Return the score at which a severity band begins."""
    lookup = {
        "CRITICAL": "80",
        "HIGH": "55",
        "MEDIUM": "25",
        "LOW": "10",
        "INFO": "0",
    }
    return lookup.get(severity, "0")


# ======================================================================
# Top-Level Security Posture Banner (Command Focal Point)
# ======================================================================

def _hero_posture_card(ctx: Context) -> None:
    """Render the commanding top-level security status hero banner."""
    result = ctx.result
    has_result = ctx.has_result
    rollup = ctx.rollup or {}
    rollup_status = core.safe_text(rollup.get("status"), "UNAVAILABLE")
    assessed = core.safe_int(rollup.get("assessed"), 0)
    healthy = core.safe_int(rollup.get("healthy"), 0)

    if not has_result:
        verdict_title = "SYSTEM ON STANDBY"
        verdict_color = PALETTE["blue"]
        verdict_sub = (
            "AURA is initialized in on-demand monitoring mode. Run a security "
            "scan to sample live host telemetry and evaluate current risk."
        )
        severity_label = "STANDBY"
        score_display = "—"
    elif ctx.is_demo:
        verdict_title = "DEMONSTRATION SCAN"
        verdict_color = PALETTE["violet"]
        verdict_sub = (
            "Evaluating synthetic anomaly vectors for demonstration. Data is "
            "quarantined and not recorded to the host audit log."
        )
        severity_label = "DEMO"
        score_display = core.fmt_float(result.get("Risk_Score"), 0)
    else:
        severity = core.severity_of(result, "UNKNOWN")
        style = SEVERITY_STYLES.get(severity, SEVERITY_STYLES["UNKNOWN"])
        score = core.safe_float(result.get("Risk_Score"), 0.0)
        score_display = core.fmt_float(score, 0)
        verdict_color = style["color"]

        if severity == "CRITICAL":
            verdict_title = "CRITICAL RISK DETECTED"
            verdict_sub = (
                "Multiple high-severity behavioral and network deviations "
                "require immediate analyst investigation."
            )
        elif severity == "HIGH":
            verdict_title = "HIGH RISK OBSERVATION"
            verdict_sub = (
                "Significant abnormal telemetry detected outside learned baseline "
                "parameters."
            )
        elif severity == "MEDIUM":
            verdict_title = "ELEVATED ACTIVITY"
            verdict_sub = (
                "Unusual resource or network activity observed. Review telemetry "
                "details below."
            )
        elif severity == "LOW":
            verdict_title = "LOW / NOMINAL VARIANCE"
            verdict_sub = (
                "Minor variance observed, within normal operational workstation tolerances."
            )
        else:
            verdict_title = "SYSTEM PROTECTED / SAFE"
            verdict_sub = (
                "Current telemetry aligns with learned normal host baseline. "
                "No anomalous deviation detected."
            )
        severity_label = style["label"]

    agreement = core.ensemble_agreement(result)

    # Subsystem details markup
    status_badge_html = ui.status_badge(rollup_status)
    prot_badge_html = _protection_badge(ctx)
    sev_badge_html = (
        ui.severity_badge(severity_label)
        if has_result and not ctx.is_demo
        else ""
    )

    last_scan_text = core.fmt_relative(ctx.scan_time, "No scan yet")
    last_scan_clock = core.fmt_clock(ctx.scan_time, "Awaiting first run")

    detector_label = agreement.get("label", "Awaiting scan")
    detector_color = (
        PALETTE["red"]
        if agreement.get("agreement") == "BOTH"
        else (
            PALETTE["yellow"]
            if agreement.get("agreement") == "ONE"
            else PALETTE["green"]
        )
    )
    if not has_result:
        detector_color = PALETTE["text_faint"]
        detector_label = "Awaiting scan"

    col_posture, col_score, col_engine = st.columns([1.3, 1, 1], gap="medium")

    with col_posture:
        body = "".join([
            '<div style="font-size:1.35rem;font-weight:700;letter-spacing:-0.01em;color:' + verdict_color + ';margin:4px 0 8px 0;">' + ui.esc(verdict_title) + '</div>',
            '<div style="display:flex;gap:6px;align-items:center;margin-bottom:8px;flex-wrap:wrap;">' + prot_badge_html + sev_badge_html + '</div>',
            '<div style="font-size:0.77rem;line-height:1.48;color:var(--aura-text-dim);">' + ui.esc(verdict_sub) + '</div>',
        ])
        ui.card("Overall System Posture", body)

    with col_score:
        body = "".join([
            '<div style="display:flex;align-items:baseline;gap:6px;margin:4px 0 6px 0;">',
            '<span style="font-family:var(--aura-mono);font-size:2.4rem;font-weight:700;color:' + verdict_color + ';line-height:1;">' + score_display + '</span>',
            '<span style="font-family:var(--aura-mono);font-size:1.0rem;color:var(--aura-text-faint);">/ ' + str(core.RISK_SCORE_NOMINAL_MAX) + '</span>',
            '</div>',
            '<div style="font-size:0.75rem;color:var(--aura-text-dim);margin-bottom:4px;">Practical max reachable: <strong>' + str(core.RISK_SCORE_OBSERVED_MAX) + '</strong></div>',
            '<div style="font-size:0.72rem;color:var(--aura-text-faint);">Bands: Normal &lt;10 · Low &ge;10 · Med &ge;25 · High &ge;55 · Crit &ge;80</div>',
        ])
        ui.card("Risk Score Triage", body)

    with col_engine:
        body = "".join([
            '<div style="margin:4px 0 8px 0;">',
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;"><span style="font-size:0.75rem;color:var(--aura-text-dim);">Host Sensors:</span>' + status_badge_html + '</div>',
            '<div style="font-size:0.72rem;color:var(--aura-text-faint);font-family:var(--aura-mono);">' + str(healthy) + ' / ' + str(assessed) + ' sensors verified operational</div>',
            '</div>',
            '<div style="margin-bottom:6px;">',
            '<div style="font-size:0.74rem;color:var(--aura-text-dim);">AI Detectors: <span style="font-weight:600;color:' + detector_color + ';">' + ui.esc(detector_label) + '</span></div>',
            '</div>',
            '<div style="font-size:0.72rem;color:var(--aura-text-faint);">Last scan: <strong>' + ui.esc(last_scan_text) + '</strong> (' + ui.esc(last_scan_clock) + ')</div>',
        ])
        ui.card("Engine & Subsystem Integrity", body)


# ======================================================================
# Quick Scan Action Center
# ======================================================================

def _scan_action_center(ctx: Context) -> None:
    """Interactive scan action center prominently placed on Overview."""
    col1, col2, col3 = st.columns([1.6, 1.2, 1.2], gap="medium")

    with col1:
        st.markdown(
            '<div style="font-size:0.86rem;font-weight:650;color:var(--aura-text);margin-bottom:2px;">'
            'Security Assessment Controls'
            '</div>'
            '<div style="font-size:0.74rem;color:var(--aura-text-dim);">'
            'Initiate live psutil host telemetry collection and AI anomaly inference.'
            '</div>',
            unsafe_allow_html=True,
        )

    with col2:
        cam_avail = core.camera_dependency_present()
        cam_status_text = (
            "Camera check: Active"
            if (ctx.probe_camera and cam_avail)
            else (
                "Camera check: Disabled (toggle in sidebar)"
                if cam_avail
                else "Camera check: Unavailable (requires opencv)"
            )
        )
        st.markdown(
            f'<div style="font-size:0.75rem;color:var(--aura-text-dim);padding-top:8px;">'
            f'<span style="font-family:var(--aura-mono);color:var(--aura-text);">{cam_status_text}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col3:
        btn_col1, btn_col2 = st.columns(2, gap="small")
        with btn_col1:
            run_live = st.button(
                "▶  Run Live Scan",
                key="ov_run_live",
                type="primary",
                use_container_width=True,
                help="Sample live Windows telemetry and evaluate against baseline.",
            )
        with btn_col2:
            run_demo = st.button(
                "▣  Demo Scan",
                key="ov_run_demo",
                use_container_width=True,
                help="Run synthetic abnormal vectors. Quarantined from logs.",
            )

    if run_live:
        with st.spinner("Collecting live telemetry and running detection models…"):
            try:
                res = scan.run_scan(
                    ctx.model,
                    probe_camera=bool(ctx.probe_camera and cam_avail),
                )
            except Exception as exc:  # noqa: BLE001
                st.session_state["aura_scan_error"] = str(exc)
            else:
                st.session_state.pop("aura_scan_error", None)
                scan.store_result(res, is_demo=False)
        core.bump_refresh()
        st.rerun()

    elif run_demo:
        with st.spinner("Running synthetic demonstration scan…"):
            try:
                res = scan.run_scan(
                    ctx.model,
                    probe_camera=False,
                    synthetic=scan.DEMO_PROFILE,
                )
            except Exception as exc:  # noqa: BLE001
                st.session_state["aura_scan_error"] = str(exc)
            else:
                st.session_state.pop("aura_scan_error", None)
                scan.store_result(res, is_demo=True)
        core.bump_refresh()
        st.rerun()


# ======================================================================
# Live Resource Meters
# ======================================================================

def _live_resources_markup(ctx: Context) -> str:
    """Current resource utilisation with physically validated sensor checks."""
    snapshot = ctx.snapshot or {}
    cpu = snapshot.get("cpu") or {}
    memory = snapshot.get("memory") or {}
    disk = snapshot.get("disk") or {}

    cpu_cores = core.safe_int(cpu.get("logical_cores"), 0)
    cpu_dead = cpu_cores <= 0
    memory_total = core.safe_float(memory.get("total_gb"), 0.0)
    disk_total = core.safe_float(disk.get("total_gb"), 0.0)

    cpu_freq = core.safe_float(cpu.get("frequency_mhz"), 0.0)
    freq_str = f" · {cpu_freq:,.0f} MHz" if cpu_freq > 0 else ""

    meters = [
        ui.bar_meter_markup(
            "Processor (CPU)",
            None
            if cpu_dead
            else core.safe_float(cpu.get("usage_percent"), 0.0),
            "CPU probe failed."
            if cpu_dead
            else f"{cpu_cores} logical cores{freq_str} · 0.2s sample interval",
            unavailable=cpu_dead,
        ),
        ui.bar_meter_markup(
            "Physical Memory (RAM)",
            None
            if memory_total <= 0
            else core.safe_float(memory.get("usage_percent"), 0.0),
            "Memory probe failed."
            if memory_total <= 0
            else (
                f"{core.fmt_float(memory.get('used_gb'), 1)} GB used of "
                f"{core.fmt_float(memory_total, 1)} GB total "
                f"({core.fmt_float(memory.get('available_gb'), 1)} GB free)"
            ),
            unavailable=memory_total <= 0,
        ),
        ui.bar_meter_markup(
            f"Storage Drive ({core.safe_text(disk.get('path'), 'C:')})",
            None
            if disk_total <= 0
            else core.safe_float(disk.get("usage_percent"), 0.0),
            "Disk volume query failed."
            if disk_total <= 0
            else (
                f"{core.fmt_float(disk.get('free_gb'), 1)} GB free of "
                f"{core.fmt_float(disk_total, 1)} GB total capacity"
            ),
            unavailable=disk_total <= 0,
        ),
    ]
    return "".join(meters)


# ======================================================================
# AI Detector Breakdown Component
# ======================================================================

def _ai_detectors_markup(ctx: Context) -> str:
    """Render the AI detection ensemble status breakdown."""
    result = ctx.result
    has_res = ctx.has_result
    agreement = core.ensemble_agreement(result)
    model_sum = core.model_summary(ctx.model)

    if not has_res:
        return (
            '<div style="font-size:0.80rem;color:var(--aura-text-dim);padding:8px 0;">'
            'No scan executed yet this session. Run a security scan to evaluate '
            'Isolation Forest and Local Outlier Factor decision margins against '
            f'the learned {model_sum.get("training_samples", 0)} baseline samples.'
            '</div>'
        )

    if_score = core.fmt_float(agreement.get("if_score"), 4, "—")
    lof_score = core.fmt_float(agreement.get("lof_score"), 4, "—")
    if_flag = "FLAGGED" if agreement.get("if_fired") else "NORMAL"
    lof_flag = "FLAGGED" if agreement.get("lof_fired") else "NORMAL"

    if_color = PALETTE["red"] if agreement.get("if_fired") else PALETTE["green"]
    lof_color = PALETTE["red"] if agreement.get("lof_fired") else PALETTE["green"]

    strongest = core.safe_text(result.get("strongest_feature"), "—")
    dev = core.safe_float(result.get("strongest_feature_deviation"), 0.0)

    rows = [
        f'<div class="aura-def"><span class="aura-def-key">Isolation Forest (300 trees)</span>'
        f'<span class="aura-def-val" style="color:{if_color};font-weight:700;">{if_flag} <span style="color:var(--aura-text-faint);font-weight:400;">(score: {if_score})</span></span></div>',
        f'<div class="aura-def"><span class="aura-def-key">Local Outlier Factor (k={model_sum.get("lof_neighbors", 20)})</span>'
        f'<span class="aura-def-val" style="color:{lof_color};font-weight:700;">{lof_flag} <span style="color:var(--aura-text-faint);font-weight:400;">(score: {lof_score})</span></span></div>',
        f'<div class="aura-def"><span class="aura-def-key">Ensemble Agreement</span>'
        f'<span class="aura-def-val">{ui.esc(agreement.get("label", "—"))}</span></div>',
        f'<div class="aura-def"><span class="aura-def-key">Primary Deviation Signal</span>'
        f'<span class="aura-def-val">{ui.esc(strongest)} ({dev:.2f}&sigma;)</span></div>',
        f'<div class="aura-def"><span class="aura-def-key">Learned Baseline Profile</span>'
        f'<span class="aura-def-val">{model_sum.get("training_samples", 0)} samples · Status: {ui.esc(model_sum.get("status", "READY"))}</span></div>',
    ]
    return f'<div class="aura-defs">{"".join(rows)}</div>'


# ======================================================================
# Metrics Grid
# ======================================================================

def _summary_kpi_cards(ctx: Context) -> list[str]:
    """Render standard 4-card metric grid for key security statistics."""
    cards: list[str] = []
    scores = core.numeric_column(ctx.logs, "Risk_Score")

    # Stored events
    cards.append(
        ui.kpi_card(
            "Stored Security Events",
            core.fmt_int(ctx.history_rows),
            "",
            "Total scans committed to host audit log.",
            PALETTE["blue"],
            "Every completed live scan appends one record to data/system_logs.csv.",
        )
    )

    # Elevated events
    if scores.empty:
        cards.append(
            ui.kpi_card(
                "Elevated Risk Events",
                "—",
                "",
                "No scored history available yet.",
                PALETTE["border"],
            )
        )
    else:
        elevated = int((scores >= _ELEVATED_FLOOR).sum())
        share = (elevated / len(scores) * 100.0) if len(scores) else 0.0
        cards.append(
            ui.kpi_card(
                "Elevated Risk Events",
                core.fmt_int(elevated),
                f"/ {len(scores):,}",
                f"{share:.1f}% of history reached MEDIUM or above.",
                PALETTE["orange"] if elevated else PALETTE["green"],
                f"Events with risk score >= {_ELEVATED_FLOOR}.",
            )
        )

    # Privacy indicators
    count, fired = _privacy_indicator_count(ctx.result)
    if not ctx.has_result:
        cards.append(
            ui.kpi_card(
                "Active Privacy Flags",
                "—",
                "",
                "Available following initial scan.",
                PALETTE["border"],
            )
        )
    else:
        cards.append(
            ui.kpi_card(
                "Active Privacy Flags",
                str(count),
                "/ 3",
                fired[0] if fired else "No privacy anomalies raised.",
                PALETTE["orange"] if count else PALETTE["green"],
                "Flags: privacy event, exfiltration watch, camera state.",
            )
        )

    # Host process count
    processes = ctx.processes or {}
    p_count = core.safe_int(processes.get("process_count"), 0)
    cards.append(
        ui.kpi_card(
            "Monitored Processes",
            core.fmt_int(p_count) if p_count > 0 else "—",
            "",
            "Running processes visible to AURA.",
            PALETTE["blue"] if p_count > 0 else PALETTE["red"],
            "Read directly from the Windows process table via psutil.",
        )
    )

    return cards


# ======================================================================
# Charts & Tables
# ======================================================================

def _severity_distribution(ctx: Context) -> None:
    """Bar chart of stored severities in band order."""
    values = core.log_severity_series(ctx.logs)
    if values.empty:
        ui.empty_state(
            "No severity history available",
            "No stored events carry a risk verdict yet. Run live scans to build historical distribution.",
        )
        return

    counts = values.value_counts()
    ordered = {name: int(counts.get(name, 0)) for name in core.SEVERITY_ORDER}
    for name, total in counts.items():
        if name not in ordered:
            ordered[name] = int(total)

    frame = pd.DataFrame(
        {"Events": list(ordered.values())},
        index=list(ordered.keys()),
    )
    st.bar_chart(frame, height=240)
    st.caption(
        "Risk verdicts stored in local audit log (Bands: INFO <10, LOW 10–24, MEDIUM 25–54, HIGH 55–79, CRITICAL 80+)."
    )


def _risk_trend(ctx: Context) -> None:
    """Risk score progression over stored history."""
    trend = core.trend_frame(ctx.logs, ["Risk_Score"], limit=300)
    if trend.empty:
        ui.empty_state(
            "Insufficient history for trend",
            "A trend graph requires at least two recorded scans in the log. Complete additional scans to populate.",
        )
        return
    st.line_chart(trend, height=240)
    st.caption(
        f"Risk score over the {len(trend):,} most recent stored events. Plotted without artificial smoothing."
    )


def _recent_events_table(ctx: Context) -> None:
    """Display the recent log entries in reverse chronological order."""
    if not ctx.has_history:
        ui.empty_state(
            "Audit Log Empty",
            "No scan events recorded yet. Run a live security scan from the controls above.",
        )
        return

    wanted = [
        ("Timestamp", "Timestamp"),
        ("Risk", "Verdict"),
        ("Risk_Score", "Score"),
        ("Anomaly", "Anomaly Flag"),
        ("Process_Count", "Processes"),
        ("Remote_Connections", "Remote Conns"),
        ("Net", "Upload KB/s"),
    ]
    available = [(src, dst) for src, dst in wanted if src in ctx.logs.columns]
    if not available:
        ui.warn_state(
            "Unrecognized Log Format",
            "The monitoring log exists but expected columns were not found.",
        )
        return

    recent = ctx.logs.tail(15).iloc[::-1]
    table = pd.DataFrame()
    for source, target in available:
        if source == "Timestamp":
            table[target] = recent[source].map(core.fmt_timestamp)
        elif source == "Anomaly":
            table[target] = recent[source].map(
                lambda value: "Flagged" if core.safe_int(value, 0) == 1 else "Normal"
            )
        elif source == "Risk_Score":
            table[target] = recent[source].map(lambda v: core.fmt_int(v))
        else:
            table[target] = recent[source]

    ui.full_dataframe(table, height=min(420, 46 + 30 * len(table)))
    st.caption(
        f"Displaying {len(table)} most recent of {ctx.history_rows:,} total stored events from data/system_logs.csv."
    )


# ======================================================================
# Main Page Render
# ======================================================================

def render(ctx: Context) -> None:
    """Render the Security Overview page."""
    ui.page_head(
        f"{core.APP_NAME} Security Overview",
        "AI-Powered Privacy Intelligence & Host Telemetry Assessment for Windows",
        "Executive Security Console",
        _protection_badge(ctx),
    )

    if ctx.is_demo:
        ui.warn_state(
            "Demonstration Mode Active",
            "This scan was executed using synthetic demonstration inputs. It was quarantined and not written to data/system_logs.csv.",
        )
    elif not ctx.has_result:
        ui.info_state(
            "Workstation Telemetry Initialized",
            "AURA operates in on-demand scanning mode. Click 'Run Live Scan' above to collect live host measurements and perform AI anomaly detection.",
        )

    if st.session_state.get("aura_demo_restore_failed"):
        ui.error_state(
            "Demonstration Log Quarantine Warning",
            "Log byte-restoration after demonstration scan encountered an IO exception. Inspect data/system_logs.csv.",
        )

    # 1. COMMAND FOCAL POINT: Top-Level Security Posture Hero Card
    _hero_posture_card(ctx)

    # 2. Quick Assessment Controls
    _scan_action_center(ctx)

    # 3. High-Level Telemetry Signals Grid
    ui.section("Telemetry & Audit Metrics")
    ui.metric_grid(_summary_kpi_cards(ctx), per_row=4)

    # 4. Live Resources & AI Detection Breakdown
    ui.section("Telemetry Subsystems & AI Detection")
    col_left, col_right = st.columns([1.1, 1], gap="medium")
    with col_left:
        ui.card("Live Resource Utilization", _live_resources_markup(ctx))
    with col_right:
        ui.card("AI Anomaly Ensemble State", _ai_detectors_markup(ctx))

    # 5. Stored History Analytics
    ui.section("Historical Behavioral Analytics", f"{ctx.history_rows:,} recorded scans")
    c_left, c_right = st.columns(2, gap="medium")
    with c_left:
        st.markdown(
            '<div style="font-size:0.80rem;font-weight:700;letter-spacing:0.06em;color:var(--aura-text-dim);margin-bottom:8px;">SEVERITY DISTRIBUTION</div>',
            unsafe_allow_html=True,
        )
        _severity_distribution(ctx)
    with c_right:
        st.markdown(
            '<div style="font-size:0.80rem;font-weight:700;letter-spacing:0.06em;color:var(--aura-text-dim);margin-bottom:8px;">RISK SCORE PROGRESSION</div>',
            unsafe_allow_html=True,
        )
        _risk_trend(ctx)

    # 6. Recent Audit Events Table
    ui.section("Recent Security Audit Events")
    _recent_events_table(ctx)
