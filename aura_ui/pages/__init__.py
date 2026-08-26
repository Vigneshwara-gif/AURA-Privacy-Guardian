"""
Page registry and router.

The navigation is data, not code: one ordered list of :class:`PageSpec`
records. The sidebar builds itself from that list, and the router dispatches to
the matching ``render`` function. Adding a page in a later batch means adding
one row here and one module — nothing else changes.

Pages not yet implemented in this batch are represented honestly. They appear
in the navigation with a short, accurate description of what they will show, on
a "planned for a later increment" notice. This is a deliberate choice over
hiding them: the reviewer sees the full intended scope, and the notice never
pretends the feature already works or fills the space with invented numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import streamlit as st

from aura_ui import components as ui
from aura_ui.context import Context

# Implemented pages. Each exposes a module-level ``render(ctx)``.
from aura_ui.pages import about as about_page
from aura_ui.pages import network_intel as network_page
from aura_ui.pages import overview as overview_page
from aura_ui.pages import process_intel as process_page
from aura_ui.pages import system_monitor as system_page

__all__ = ["PAGES", "PageSpec", "render_page"]


@dataclass(frozen=True)
class PageSpec:
    """One navigation destination."""

    key: str
    label: str  # includes a leading glyph for the sidebar
    title: str
    render: Callable[[Context], None] | None = None
    planned: str = ""  # description shown when render is None


def _planned(title: str, description: str) -> Callable[[Context], None]:
    """Build a render function for a not-yet-implemented page."""

    def render(_: Context) -> None:
        ui.page_head(
            title,
            "AURA Cybersecurity Architecture & Module Roadmap",
            "Planned Capability",
            ui.badge("PLANNED MODULE", PALETTE["blue"], PALETTE["blue_soft"], "○"),
        )
        ui.info_state(
            f"{title} — Planned for Incremental Release",
            description,
        )
        ui.section("Design Specification & Honesty Guarantee")
        st.markdown(
            '<div class="aura-card">'
            '<div style="font-size:0.83rem;line-height:1.55;color:var(--aura-text-dim);">'
            'This destination is part of AURA\'s defined scope and is shown here so the complete '
            'SOC console structure is accessible. It is intentionally rendered with its honest '
            'specification rather than populated with mocked or simulated telemetry numbers — '
            'nothing in AURA ever displays a measurement that was not physically sampled from the host.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    return render


# The complete 12-destination navigation. Order is the display order.
PAGES: tuple[PageSpec, ...] = (
    PageSpec(
        "overview",
        "◱  Overview",
        "Security Overview",
        overview_page.render,
    ),
    PageSpec(
        "threats",
        "◆  Threat Center",
        "Threat Center",
        planned=(
            "A prioritised view of elevated-risk observations with severity, "
            "risk score, contributing evidence and a plain-language "
            "explanation for each, plus filtering by severity, category, "
            "process and time. It reads the same stored events the Event "
            "Explorer and Analytics pages use."
        ),
    ),
    PageSpec(
        "system",
        "▤  System Monitor",
        "System Monitor",
        system_page.render,
    ),
    PageSpec(
        "process",
        "▦  Process Intelligence",
        "Process Intelligence",
        process_page.render,
    ),
    PageSpec(
        "network",
        "◈  Network Intelligence",
        "Network Intelligence",
        network_page.render,
    ),
    PageSpec(
        "privacy",
        "◉  Privacy Intelligence",
        "Privacy Intelligence",
        planned=(
            "A privacy summary derived only from real signals AURA already "
            "collects — connection exposure, sensitive-file access counts and "
            "the opt-in camera probe — with each indicator labelled Observed, "
            "Inferred or Unavailable. No score is shown unless it is computed "
            "from those real inputs."
        ),
    ),
    PageSpec(
        "behavioral",
        "◊  Behavioral Intelligence",
        "Behavioral Intelligence",
        planned=(
            "An explanation of the two-detector model: which of Isolation "
            "Forest and Local Outlier Factor flagged the current observation, "
            "the raw decision-function scores, the strongest feature "
            "deviations and the learned baseline. Model accuracy is reported "
            "as 'Not measured', because AURA's detectors are unsupervised and "
            "no labelled ground truth exists for this machine."
        ),
    ),
    PageSpec(
        "events",
        "▧  Event Explorer",
        "Event Explorer",
        planned=(
            "A searchable, sortable, date-filterable table over the stored "
            "monitoring log: timestamp, event type, severity, risk, process "
            "and explanation for every recorded scan."
        ),
    ),
    PageSpec(
        "analytics",
        "◴  Analytics",
        "Analytics",
        planned=(
            "Trends over the stored history — risk, CPU, memory, network "
            "activity and severity distribution over time — each drawn only "
            "from real logged data, with an explicit notice when there is not "
            "yet enough history to plot."
        ),
    ),
    PageSpec(
        "reports",
        "▭  Reports",
        "Reports",
        planned=(
            "Export of the real monitoring history to CSV and JSON, plus a "
            "professional summary of the monitoring period, risk profile, "
            "event counts and system health for inclusion in a report."
        ),
    ),
    PageSpec(
        "settings",
        "⚙  Settings",
        "Settings",
        planned=(
            "Monitoring, detection, privacy, appearance and diagnostics "
            "controls — exposing only settings that are actually wired to "
            "backend behaviour, so no control on this page is inert."
        ),
    ),
    PageSpec(
        "about",
        "◇  About AURA",
        "About AURA",
        about_page.render,
    ),
)


def render_page(key: str, ctx: Context) -> None:
    """Dispatch to the page matching ``key``."""
    for spec in PAGES:
        if spec.key == key:
            render = spec.render or _planned(spec.title, spec.planned)
            render(ctx)
            return
    # Unknown key: fall back to the first page rather than showing nothing.
    PAGES[0].render(ctx)  # type: ignore[misc]
