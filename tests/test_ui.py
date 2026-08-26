"""Tests for AURA UI components, theme, and page registry."""

from __future__ import annotations

import pandas as pd
import pytest

from aura_ui import components as ui
from aura_ui import core
from aura_ui.context import Context
from aura_ui.pages import PAGES, PageSpec, render_page
from aura_ui.theme import PALETTE, SEVERITY_STYLES, STATUS_STYLES, inject_theme, severity_color


def test_palette_keys() -> None:
    """Ensure all required theme colors and surfaces exist in PALETTE."""
    required_keys = [
        "bg", "bg_alt", "surface", "surface_2", "surface_3",
        "border", "border_soft", "text", "text_dim", "text_faint",
        "green", "yellow", "orange", "red", "blue",
    ]
    for key in required_keys:
        assert key in PALETTE, f"Missing required palette key: {key}"


def test_severity_vocabularies() -> None:
    """Ensure all severity levels have complete visual definitions."""
    required_severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NORMAL", "INFO", "UNKNOWN"]
    for sev in required_severities:
        assert sev in SEVERITY_STYLES
        style = SEVERITY_STYLES[sev]
        assert "label" in style
        assert "glyph" in style
        assert "color" in style
        assert "bg" in style


def test_status_vocabularies() -> None:
    """Ensure all subsystem status definitions are present."""
    required_statuses = ["HEALTHY", "DEGRADED", "PERMISSION_LIMITED", "UNAVAILABLE", "NOT_PRESENT", "NOT_PROBED", "PRIMING"]
    for status in required_statuses:
        assert status in STATUS_STYLES
        style = STATUS_STYLES[status]
        assert "label" in style
        assert "glyph" in style
        assert "color" in style


def test_severity_color_fallback() -> None:
    """Ensure severity_color helper defaults to UNKNOWN safely."""
    assert severity_color("CRITICAL") == PALETTE["red"]
    assert severity_color("NORMAL") == PALETTE["green"]
    assert severity_color("NON_EXISTENT_VERDICT") == SEVERITY_STYLES["UNKNOWN"]["color"]


def test_esc_sanitization() -> None:
    """Ensure HTML escaping protects against injection attacks."""
    assert ui.esc("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert ui.esc("Normal Text") == "Normal Text"
    assert ui.esc(None) == "—"
    assert ui.esc("null") == "—"
    assert ui.esc("") == "—"


def test_page_specs_registry() -> None:
    """Ensure all 12 page destinations are declared with valid specifications."""
    assert len(PAGES) == 12
    keys = [p.key for p in PAGES]
    expected_keys = [
        "overview", "threats", "system", "process", "network", "privacy",
        "behavioral", "events", "analytics", "reports", "settings", "about",
    ]
    for key in expected_keys:
        assert key in keys, f"Missing expected page key: {key}"


def test_bar_meter_markup() -> None:
    """Ensure bar meter generates markup for both active and unavailable states."""
    active_markup = ui.bar_meter_markup("CPU", 45.2, "8 cores")
    assert "45.2%" in active_markup
    assert "CPU" in active_markup

    unavail_markup = ui.bar_meter_markup("Disk", None, unavailable=True)
    assert "UNAVAILABLE" in unavail_markup


def test_context_camera_probe_lifecycle() -> None:
    """Ensure Context accurately preserves the probe_camera boolean setting."""
    ctx_disabled = Context(probe_camera=False)
    assert ctx_disabled.probe_camera is False

    ctx_enabled = Context(probe_camera=True)
    assert ctx_enabled.probe_camera is True


def test_overview_camera_status_markup() -> None:
    """Ensure overview page reflects camera probe status correctly without state mutation."""
    ctx_off = Context(probe_camera=False)
    assert ctx_off.probe_camera is False

    ctx_on = Context(probe_camera=True)
    assert ctx_on.probe_camera is True


def test_overview_markup_has_no_indented_code_blocks() -> None:
    """Ensure HTML strings built for overview do not have lines starting with 4+ spaces."""
    from aura_ui.pages.overview import _ai_detectors_markup, _live_resources_markup

    ctx = Context()
    resources_html = _live_resources_markup(ctx)
    assert isinstance(resources_html, str)
    for line in resources_html.splitlines():
        # A line with 4+ spaces inside an HTML block can trigger markdown indented-code-block conversion
        assert not line.startswith("    "), f"Indented line found in resources markup: {line!r}"

    ai_html = _ai_detectors_markup(ctx)
    assert isinstance(ai_html, str)
    for line in ai_html.splitlines():
        assert not line.startswith("    "), f"Indented line found in AI markup: {line!r}"


