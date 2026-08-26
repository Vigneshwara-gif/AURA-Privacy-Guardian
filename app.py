"""
AURA — application entry point.

Run with::

    streamlit run app.py

This module is deliberately thin. It does five things and nothing else:
configure the page, inject the stylesheet, render the sidebar, gather one
telemetry context for this script run, and hand that context to whichever page
is selected. All measurement lives in the engine modules (``aura_core``,
``sensors``, ``privacy_monitor``, ``model``, ``logger``) and all rendering lives
in ``aura_ui``. Nothing in this file measures, scores or decides anything.

Three ordering decisions here are load-bearing and should not be rearranged
casually.

``st.set_page_config`` must run before any other Streamlit command, so it comes
immediately after the imports. None of the imported modules emit a Streamlit
command at import time — they only define functions and register caches — so
importing them first is safe.

The model is loaded *before* the sidebar is drawn. If the baseline is missing,
``load_model_or_stop`` reports that and halts; doing so outside the sidebar puts
the explanation in the main area where it is readable, rather than squeezed into
a 300-pixel column.

The telemetry context is assembled *once*, between the sidebar's controls and
the sidebar's status readout. That ordering means the status figures in the
sidebar and the figures on the page body come from the same instant. A
monitoring tool that contradicts itself between its own sidebar and its own
charts is not trusted again, and the only way to guarantee it cannot is to read
once and share the result.
"""

from __future__ import annotations

import streamlit as st

from aura_ui import components as ui
from aura_ui import core, scan
from aura_ui.context import Context
from aura_ui.pages import PAGES, render_page
from aura_ui.theme import PALETTE, SEVERITY_STYLES, inject_theme

# ----------------------------------------------------------------------
# Page configuration — must precede every other Streamlit call.
# ----------------------------------------------------------------------

st.set_page_config(
    page_title="AURA — Privacy Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()


# ======================================================================
# Sidebar building blocks
# ======================================================================


def _brand() -> None:
    """The product mark at the top of the sidebar."""
    st.sidebar.markdown(
        "".join(
            [
                '<div class="aura-brand">',
                '<div class="aura-brand-mark">◈</div>',
                "<div>",
                '<div class="aura-brand-name">',
                ui.esc(core.APP_NAME, "AURA"),
                "</div>",
                '<div class="aura-brand-tag">Privacy Guardian</div>',
                "</div></div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def _side_label(text: str) -> None:
    """A small uppercase group heading in the sidebar."""
    st.sidebar.markdown(
        '<div class="aura-side-label">' + ui.esc(text, "") + "</div>",
        unsafe_allow_html=True,
    )


def _side_stats(rows: list[tuple[str, str]]) -> None:
    """A compact key/value block in the sidebar."""
    if not rows:
        return
    markup = ['<div class="aura-card" style="padding:6px 10px">']
    for key, value in rows:
        markup.append(
            "".join(
                [
                    '<div class="aura-side-stat">',
                    '<span class="aura-side-stat-key">',
                    ui.esc(key, ""),
                    "</span>",
                    '<span class="aura-side-stat-val">',
                    ui.esc(value, core.UNKNOWN),
                    "</span></div>",
                ]
            )
        )
    markup.append("</div>")
    st.sidebar.markdown("".join(markup), unsafe_allow_html=True)


def _side_badge(markup: str) -> None:
    """Centre a badge on its own row in the sidebar."""
    st.sidebar.markdown(
        '<div style="padding:2px 4px 6px 4px">' + markup + "</div>",
        unsafe_allow_html=True,
    )


NAV_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "MONITOR",
        [
            ("overview", "◱  Overview"),
            ("threats", "◆  Threat Center"),
            ("system", "▤  System Monitor"),
        ],
    ),
    (
        "INTELLIGENCE",
        [
            ("process", "▦  Process Intelligence"),
            ("network", "◈  Network Intelligence"),
            ("privacy", "◉  Privacy Intelligence"),
            ("behavioral", "◊  Behavioral Intelligence"),
        ],
    ),
    (
        "ANALYSIS",
        [
            ("events", "▧  Event Explorer"),
            ("analytics", "◴  Analytics"),
            ("reports", "▭  Reports"),
        ],
    ),
    (
        "SYSTEM",
        [
            ("settings", "⚙  Settings"),
            ("about", "◇  About AURA"),
        ],
    ),
]


def _navigation() -> str:
    """Render the 12-destination navigation organized by security domain."""
    valid_keys = [spec.key for spec in PAGES]
    current = st.session_state.get("aura_nav", "overview")
    if current not in valid_keys:
        current = valid_keys[0]
        st.session_state["aura_nav"] = current

    for group_title, items in NAV_GROUPS:
        _side_label(group_title)
        for key, label in items:
            is_active = (current == key)
            if st.sidebar.button(
                label,
                key=f"nav_{key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if current != key:
                    st.session_state["aura_nav"] = key
                    st.rerun()

    return st.session_state.get("aura_nav", "overview")


def _scan_controls(model: object) -> bool:
    """
    Render the scan controls. Returns True when the camera probe is enabled.

    A scan runs during this script run, before the page body is assembled, so
    the result it produces is the one the page renders.
    """
    _side_label("SECURITY SCAN")

    camera_available = core.camera_dependency_present()
    probe_camera = st.sidebar.checkbox(
        "Include camera availability check",
        key="aura_probe_camera",
        disabled=not camera_available,
        help=(
            "Asks the operating system whether a capture device can be opened, "
            "then releases it immediately. No image is captured, decoded, "
            "displayed or stored."
            if camera_available
            else "Requires opencv-python, which is not installed. The check is "
            "unavailable rather than silently reported as clear."
        ),
    )
    probe_camera = bool(probe_camera) and camera_available

    if not camera_available:
        st.sidebar.caption(
            "Camera check unavailable — opencv-python is not installed."
        )

    run_live = ui.full_width(
        st.sidebar.button,
        "▶  Run Security Scan",
        key="aura_run_live",
        type="primary",
        help="Collects live host telemetry (CPU, Memory, Disk, Network, Process table) and runs AI detection.",
    )
    run_demo = ui.full_width(
        st.sidebar.button,
        "▣  Demonstration Scan (Synthetic)",
        key="aura_run_demo",
        help="Evaluates synthetic abnormal values to demonstrate anomaly detection. Never written to logs.",
    )

    if run_live:
        with st.spinner("Collecting live telemetry from this computer…"):
            try:
                result = scan.run_scan(model, probe_camera=probe_camera)
            except Exception as exc:  # noqa: BLE001 - surfaced, never hidden
                st.session_state["aura_scan_error"] = str(exc)
            else:
                st.session_state.pop("aura_scan_error", None)
                scan.store_result(result, is_demo=False)
        core.bump_refresh()

    elif run_demo:
        with st.spinner("Running the synthetic demonstration scan…"):
            try:
                result = scan.run_scan(
                    model,
                    probe_camera=False,
                    synthetic=scan.DEMO_PROFILE,
                )
            except Exception as exc:  # noqa: BLE001 - surfaced, never hidden
                st.session_state["aura_scan_error"] = str(exc)
            else:
                st.session_state.pop("aura_scan_error", None)
                scan.store_result(result, is_demo=True)
        core.bump_refresh()

    st.sidebar.caption(
        "Demonstration scan feeds synthetic values to test detector response. "
        "It is clearly marked and quarantined from production logs."
    )

    return probe_camera


def _session_controls() -> None:
    """Maintenance actions, kept out of the way but genuinely wired up."""
    with st.sidebar.expander("Session", expanded=False):
        if st.button("Clear result from this session", key="aura_clear"):
            for key in (
                "latest_result",
                "latest_scan_source",
                "last_scan_time",
                "aura_scan_error",
                "aura_demo_restore_failed",
            ):
                st.session_state.pop(key, None)
            core.bump_refresh()
            st.rerun()
        st.caption(
            "Discards the on-screen result only. The monitoring log on disk is "
            "not touched."
        )

        if st.button("Retrain detection model", key="aura_retrain"):
            core.reset_model_cache()
            st.rerun()
        st.caption(
            "Refits the Isolation Forest and Local Outlier Factor from the "
            "stored baseline. Useful after the baseline has been extended."
        )

        if st.button("Refresh live telemetry", key="aura_refresh_all"):
            core.bump_refresh()
            st.rerun()
        st.caption(
            "Invalidates the few-second telemetry cache and re-reads every "
            "sensor."
        )


def _status_readout(ctx: Context) -> None:
    """The sidebar's live status block, drawn from the shared context."""
    _side_label("Status")

    if not ctx.has_result:
        _side_badge(
            ui.badge("STANDBY", PALETTE["blue"], PALETTE["blue_soft"], "○")
        )
    elif ctx.is_demo:
        _side_badge(
            ui.badge(
                "DEMONSTRATION",
                PALETTE["violet"],
                "rgba(122, 108, 208, 0.16)",
                "▣",
            )
        )
    else:
        _side_badge(
            ui.badge("MONITORING", PALETTE["green"], PALETTE["green_soft"], "●")
        )

    rollup_status = core.safe_text(
        (ctx.rollup or {}).get("status"), "UNAVAILABLE"
    )
    _side_badge(ui.status_badge(rollup_status))

    if ctx.has_result:
        severity = core.severity_of(ctx.result, "UNKNOWN")
        style = SEVERITY_STYLES.get(severity, SEVERITY_STYLES["UNKNOWN"])
        risk = (
            core.fmt_float(ctx.result.get("Risk_Score"), 0)
            + " / "
            + str(core.RISK_SCORE_NOMINAL_MAX)
        )
        verdict = core.safe_text(style.get("label"), severity)
    else:
        risk = "Not measured"
        verdict = "No scan yet"

    _side_stats(
        [
            ("Risk score", risk),
            ("Verdict", verdict),
            ("Last scan", core.fmt_relative(ctx.scan_time, "Never")),
            (
                "Sensors",
                str(core.safe_int((ctx.rollup or {}).get("healthy"), 0))
                + " / "
                + str(core.safe_int((ctx.rollup or {}).get("assessed"), 0)),
            ),
            ("Stored events", core.fmt_int(ctx.history_rows)),
        ]
    )


def _footer() -> None:
    """The standing disclaimer, present on every screen."""
    st.sidebar.markdown(
        "".join(
            [
                '<div class="aura-side-note">',
                "<strong>Defensive monitoring only.</strong> AURA observes this "
                "computer, reports what it measured and explains what it "
                "cannot conclude. It takes no action against the host, sends "
                "nothing off the machine, and never displays a value it has "
                "not actually measured.",
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div style="padding:10px 4px 4px 4px;font-size:0.66rem;'
        "letter-spacing:0.08em;text-transform:uppercase;color:"
        + PALETTE["text_faint"]
        + '">'
        + ui.esc(core.APP_NAME, "AURA")
        + " v"
        + ui.esc(core.APP_VERSION, "")
        + "  ·  Local build</div>",
        unsafe_allow_html=True,
    )


# ======================================================================
# Context assembly
# ======================================================================


def _build_context(model: object, probe_camera: bool) -> Context:
    """
    Read every source once and bundle it.

    Each read is individually cached for a few seconds inside ``core``, so a
    page that touches all of them costs one set of reads per interaction rather
    than one per call site.
    """
    snapshot = core.live_snapshot(probe_camera=probe_camera)
    connections = core.live_connections()
    health = core.derive_sensor_health(
        snapshot,
        probe_camera=probe_camera,
        connections=connections,
    )

    return Context(
        model=model,
        probe_camera=probe_camera,
        result=core.get_latest_result(),
        is_demo=core.result_is_demo(),
        scan_time=core.get_last_scan_time(),
        logs=core.load_event_log(),
        snapshot=snapshot,
        processes=core.live_processes(),
        connections=connections,
        health=health,
        rollup=core.health_rollup(health),
    )


# ======================================================================
# Main
# ======================================================================


def main() -> None:
    """Assemble the shell and render the selected page."""
    # Initialize session state keys early before widget instantiations
    st.session_state.setdefault("aura_probe_camera", False)

    with st.spinner("Preparing the detection model…"):
        # Halts with an actionable message if the baseline is unusable. No
        # fallback "everything is fine" state is invented in its place.
        model = core.load_model_or_stop()

    _brand()
    page_key = _navigation()
    probe_camera = _scan_controls(model)
    _session_controls()

    ctx = _build_context(model, probe_camera)

    _status_readout(ctx)
    _footer()

    scan_error = st.session_state.get("aura_scan_error")
    if scan_error:
        ui.error_state(
            "The last scan did not complete",
            "AURA could not finish the requested scan, so no new result was "
            "recorded. Anything shown below is from an earlier scan or from "
            "stored history. Underlying error: " + str(scan_error),
        )

    render_page(page_key, ctx)


main()
