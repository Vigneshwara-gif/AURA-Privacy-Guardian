"""
AURA presentation primitives.

Every visual element the pages use lives here, so the interface stays coherent
and a page module reads as a description of *what* is shown rather than a wall
of markup.

Two things in this module are load-bearing beyond appearance:

**Escaping.** These helpers render through ``unsafe_allow_html=True``, and some
of the text they render comes from the operating system — process names,
executable paths, remote endpoints. A process could be named
``<img onerror=...>``. Every interpolated value therefore passes through
:func:`esc`. This is not theoretical tidiness; it is the difference between a
monitoring tool and an injection vector.

**Streamlit version tolerance.** Streamlit renamed the full-width argument:
older releases take ``use_container_width=True``, newer ones take
``width="stretch"`` and warn about the old name. Because the target machine's
Streamlit version is not known in advance, the width-sensitive calls are routed
through a wrapper that tries the modern form, falls back to the legacy form,
and remembers which one worked so the cost is paid once per process.
"""

from __future__ import annotations

import html
import math
from typing import Any, Callable

import streamlit as st

from aura_ui.theme import PALETTE, SEVERITY_STYLES, STATUS_STYLES

try:  # Present in every Streamlit that raises it; guarded for safety.
    from streamlit.errors import StreamlitAPIException as _StreamlitError
except Exception:  # noqa: BLE001 - fall back to a broader net
    _StreamlitError = Exception  # type: ignore[assignment, misc]

__all__ = [
    "badge",
    "bar_meter",
    "bar_meter_markup",
    "card",
    "chip_row",
    "def_list",
    "empty_state",
    "error_state",
    "esc",
    "full_dataframe",
    "full_width",
    "info_state",
    "kpi_card",
    "metric_grid",
    "page_head",
    "risk_meter",
    "section",
    "severity_badge",
    "status_badge",
    "unavailable_note",
    "warn_state",
]


# ======================================================================
# Escaping
# ======================================================================


def esc(value: Any, fallback: str = "—") -> str:
    """
    HTML-escape any value for safe interpolation into rendered markup.

    Used on *everything* that reaches the DOM, including values that look
    trustworthy. Process names, command paths and remote hostnames are
    attacker-influenced input on a compromised machine, which is precisely the
    machine this tool is meant to run on.
    """
    if value is None:
        return fallback
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return fallback
    return html.escape(text, quote=True)


# ======================================================================
# Streamlit width compatibility
# ======================================================================

_WIDTH_MODE: str | None = None
_MODE_ORDER: dict[str | None, tuple[str, ...]] = {
    None: ("modern", "legacy", "bare"),
    "modern": ("modern",),
    "legacy": ("legacy",),
    "bare": ("bare",),
}


def full_width(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Call a Streamlit element at full container width, whatever the version.

    Tries ``width="stretch"`` first, then ``use_container_width=True``, then no
    width argument at all. Both rejected forms raise during argument
    validation, before the element is enqueued for rendering, so a failed
    attempt does not leave a half-drawn widget behind.

    The final attempt is deliberately *not* wrapped: if the call fails with no
    width argument, the problem is the data or the caller, and that error must
    surface rather than be swallowed into a blank space on the page.
    """
    global _WIDTH_MODE  # noqa: PLW0603 - one-time capability probe

    order = _MODE_ORDER[_WIDTH_MODE]
    last_index = len(order) - 1

    for index, mode in enumerate(order):
        is_last_attempt = index == last_index
        try:
            if mode == "modern":
                result = func(*args, width="stretch", **kwargs)
            elif mode == "legacy":
                result = func(*args, use_container_width=True, **kwargs)
            else:
                result = func(*args, **kwargs)
        except (TypeError, _StreamlitError):
            if is_last_attempt:
                raise
            continue
        _WIDTH_MODE = mode
        return result

    return None


def full_dataframe(frame: Any, **kwargs: Any) -> Any:
    """Render a dataframe at full width, hiding the pandas index."""
    kwargs.setdefault("hide_index", True)
    try:
        return full_width(st.dataframe, frame, **kwargs)
    except TypeError:
        # `hide_index` predates some supported versions.
        kwargs.pop("hide_index", None)
        return full_width(st.dataframe, frame, **kwargs)


# ======================================================================
# Page and section headers
# ======================================================================


def page_head(
    title: str,
    subtitle: str = "",
    eyebrow: str = "",
    right: str = "",
) -> None:
    """Render the banner that opens every page."""
    parts = ['<div class="aura-page-head"><div>']
    if eyebrow:
        parts.append('<div class="aura-eyebrow">')
        parts.append(esc(eyebrow, ""))
        parts.append("</div>")
    parts.append('<div class="aura-h1">')
    parts.append(esc(title, ""))
    parts.append("</div>")
    if subtitle:
        parts.append('<p class="aura-sub">')
        parts.append(esc(subtitle, ""))
        parts.append("</p>")
    parts.append("</div>")
    if right:
        # `right` is composed from trusted badge markup produced in this
        # module, so it is intentionally not escaped a second time.
        parts.append('<div style="text-align:right">')
        parts.append(right)
        parts.append("</div>")
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def section(title: str, note: str = "") -> None:
    """Render a labelled horizontal section divider."""
    markup = [
        '<div class="aura-section"><span class="aura-section-title">',
        esc(title, ""),
        '</span><span class="aura-section-rule"></span>',
    ]
    if note:
        markup.append('<span class="aura-section-note">')
        markup.append(esc(note, ""))
        markup.append("</span>")
    markup.append("</div>")
    st.markdown("".join(markup), unsafe_allow_html=True)


# ======================================================================
# Badges
# ======================================================================


def badge(
    label: str,
    color: str,
    background: str,
    glyph: str = "",
) -> str:
    """
    Return badge markup. Always pairs colour with a text label and a glyph.

    The glyph is not decoration. Severity conveyed by colour alone is
    invisible to a colour-blind analyst and disappears in a greyscale printout
    of an incident report, so shape carries the same information redundantly.
    """
    safe_label = esc(label, "")
    glyph_markup = ""
    if glyph:
        glyph_markup = (
            '<span class="aura-badge-glyph">' + esc(glyph, "") + "</span>"
        )
    style = (
        "color:" + color + ";background:" + background
        + ";border-color:" + color + "55"
    )
    return (
        '<span class="aura-badge" style="' + style + '">'
        + glyph_markup
        + "<span>" + safe_label + "</span></span>"
    )


def severity_badge(severity: str) -> str:
    """Return badge markup for an AURA severity name."""
    key = str(severity or "UNKNOWN").strip().upper()
    style = SEVERITY_STYLES.get(key, SEVERITY_STYLES["UNKNOWN"])
    return badge(
        style["label"],
        style["color"],
        style["bg"],
        style["glyph"],
    )


def status_badge(status: str) -> str:
    """Return badge markup for a sensor or subsystem status."""
    key = str(status or "UNKNOWN").strip().upper()
    style = STATUS_STYLES.get(key)
    if style is None:
        style = SEVERITY_STYLES["UNKNOWN"]
    return badge(
        style["label"],
        style["color"],
        style["bg"],
        style["glyph"],
    )


def chip_row(items: list[tuple[str, str]]) -> None:
    """Render a horizontal row of compact ``label: value`` chips."""
    if not items:
        return
    chips = "".join(
        '<span class="aura-chip">'
        + esc(label, "")
        + "<strong>"
        + esc(value)
        + "</strong></span>"
        for label, value in items
    )
    st.markdown(
        '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px">'
        + chips
        + "</div>",
        unsafe_allow_html=True,
    )


# ======================================================================
# Metric cards
# ======================================================================


def kpi_card(
    label: str,
    value: str,
    unit: str = "",
    footer: str = "",
    accent: str = "",
    help_text: str = "",
) -> str:
    """
    Return markup for one key-figure card.

    ``value`` should already be formatted, and should be the honest marker
    (``—``, ``Not measured``, ``Unavailable``) when the underlying figure could
    not be established. This function never substitutes a zero for a missing
    measurement.
    """
    accent_color = accent or PALETTE["border"]
    unit_markup = ""
    if unit:
        unit_markup = (
            '<span class="aura-metric-unit">' + esc(unit, "") + "</span>"
        )
    footer_markup = ""
    if footer:
        footer_markup = (
            '<div class="aura-metric-foot">' + esc(footer, "") + "</div>"
        )
    hint = ""
    if help_text:
        hint = ' title="' + esc(help_text, "") + '"'
    return "".join(
        [
            '<div class="aura-metric" style="--aura-accent:',
            accent_color,
            '"',
            hint,
            '><div class="aura-metric-label">',
            esc(label, ""),
            '</div><div class="aura-metric-value">',
            esc(value),
            unit_markup,
            "</div>",
            footer_markup,
            "</div>",
        ]
    )


def metric_grid(cards: list[str], per_row: int = 4) -> None:
    """
    Lay out metric cards in equal-width columns.

    Streamlit columns are used rather than a CSS grid so the cards reflow
    correctly on a narrow window, which a fixed grid inside one markdown block
    would not do.
    """
    if not cards:
        return
    for start in range(0, len(cards), per_row):
        chunk = cards[start : start + per_row]
        columns = st.columns(len(chunk), gap="small")
        for column, card in zip(columns, chunk):
            with column:
                st.markdown(card, unsafe_allow_html=True)


# ======================================================================
# Risk meter
# ======================================================================


def _arc_point(centre_x: float, centre_y: float, radius: float,
               fraction: float) -> tuple[float, float]:
    """Point on a 180°-to-0° arc at ``fraction`` of the way along it."""
    angle = math.radians(180.0 - (180.0 * fraction))
    return (
        centre_x + radius * math.cos(angle),
        centre_y - radius * math.sin(angle),
    )


def risk_meter(
    score: float | None,
    severity: str,
    nominal_max: int = 100,
    observed_max: int = 88,
    caption: str = "",
) -> None:
    """
    Draw the risk score as a semicircular meter.

    Hand-built SVG rather than a charting library, for two reasons: it adds no
    dependency to ``requirements.txt``, and it allows the band boundaries and
    the reachable-maximum marker to be drawn exactly where the risk engine's
    thresholds actually are.

    When ``score`` is None the meter renders empty with an explicit "no scan
    yet" readout, rather than showing a reassuring zero.
    """
    style = SEVERITY_STYLES.get(
        str(severity or "UNKNOWN").strip().upper(),
        SEVERITY_STYLES["UNKNOWN"],
    )

    has_score = score is not None
    value = max(0.0, min(float(nominal_max), float(score or 0.0)))
    fraction = (value / nominal_max) if nominal_max else 0.0

    radius = 96.0
    centre_x, centre_y = 116.0, 112.0
    circumference = math.pi * radius
    filled = circumference * (fraction if has_score else 0.0)

    start_x, start_y = _arc_point(centre_x, centre_y, radius, 0.0)
    end_x, end_y = _arc_point(centre_x, centre_y, radius, 1.0)
    arc = (
        f"M {start_x:.2f} {start_y:.2f} "
        f"A {radius} {radius} 0 0 1 {end_x:.2f} {end_y:.2f}"
    )

    # Band boundary ticks, drawn at the risk engine's real thresholds.
    ticks: list[str] = []
    for boundary, colour in (
        (10, PALETTE["blue"]),
        (25, PALETTE["yellow"]),
        (55, PALETTE["orange"]),
        (80, PALETTE["red"]),
    ):
        tick_fraction = boundary / nominal_max
        inner_x, inner_y = _arc_point(
            centre_x, centre_y, radius - 13, tick_fraction
        )
        outer_x, outer_y = _arc_point(
            centre_x, centre_y, radius + 3, tick_fraction
        )
        ticks.append(
            f'<line x1="{inner_x:.2f}" y1="{inner_y:.2f}" '
            f'x2="{outer_x:.2f}" y2="{outer_y:.2f}" '
            f'stroke="{colour}" stroke-width="2" opacity="0.85" />'
        )

    # The highest score the additive scoring function can actually reach.
    ceiling_fraction = observed_max / nominal_max
    ceil_inner_x, ceil_inner_y = _arc_point(
        centre_x, centre_y, radius - 17, ceiling_fraction
    )
    ceil_outer_x, ceil_outer_y = _arc_point(
        centre_x, centre_y, radius + 7, ceiling_fraction
    )
    ticks.append(
        f'<line x1="{ceil_inner_x:.2f}" y1="{ceil_inner_y:.2f}" '
        f'x2="{ceil_outer_x:.2f}" y2="{ceil_outer_y:.2f}" '
        f'stroke="{PALETTE["text_dim"]}" stroke-width="2" '
        f'stroke-dasharray="3 2" />'
    )

    svg = f"""
<svg width="236" height="132" viewBox="0 0 236 132"
     role="img" aria-label="Risk score {value:.0f} of {nominal_max}">
  <path d="{arc}" fill="none" stroke="{PALETTE['surface_3']}"
        stroke-width="15" stroke-linecap="round" />
  <path d="{arc}" fill="none" stroke="{style['color']}"
        stroke-width="15" stroke-linecap="round"
        stroke-dasharray="{filled:.2f} {circumference:.2f}" />
  {''.join(ticks)}
  <text x="{centre_x}" y="{centre_y - 4}" text-anchor="middle"
        fill="{PALETTE['text_faint']}" font-size="10"
        font-family="Segoe UI, sans-serif" letter-spacing="1.4">
    RISK SCORE
  </text>
  <text x="20" y="128" fill="{PALETTE['text_faint']}" font-size="10"
        font-family="Segoe UI, sans-serif">0</text>
  <text x="212" y="128" fill="{PALETTE['text_faint']}" font-size="10"
        font-family="Segoe UI, sans-serif">{nominal_max}</text>
</svg>
"""

    readout_score = f"{value:.0f}" if has_score else "—"
    if caption:
        note = caption
    elif has_score:
        note = (
            f"Scored on the engine's 0–{nominal_max} scale. The dashed marker "
            f"at {observed_max} is the highest total the current additive "
            f"scoring function can actually produce, so {observed_max} — not "
            f"{nominal_max} — is the practical worst case."
        )
    else:
        note = "No scan has been run in this session yet."

    safe_note = esc(note, "")
    colour = style["color"]
    badge_markup = severity_badge(severity)

    # Assembled by joining fragments rather than by interpolating into one
    # large template. Verbose, but every quote character is unambiguous.
    markup = "".join(
        [
            '<div class="aura-card"><div class="aura-gauge-wrap"><div>',
            svg,
            '</div><div class="aura-gauge-readout">',
            '<div class="aura-gauge-score" style="color:',
            colour,
            '">',
            readout_score,
            '<span class="aura-gauge-scale">/',
            str(nominal_max),
            "</span></div>",
            '<div style="margin-top:8px">',
            badge_markup,
            "</div>",
            '<div class="aura-gauge-caption">',
            safe_note,
            "</div></div></div></div>",
        ]
    )
    st.markdown(markup, unsafe_allow_html=True)


# ======================================================================
# Meters and definition lists
# ======================================================================


def _meter_detail(detail: str) -> str:
    """Return the small caption rendered beneath a meter, or nothing."""
    if not detail:
        return ""
    return "".join(
        [
            '<div style="font-size:0.72rem;color:',
            PALETTE["text_faint"],
            ';margin-top:5px">',
            esc(detail, ""),
            "</div>",
        ]
    )


def bar_meter_markup(
    label: str,
    percent: float | None,
    detail: str = "",
    unavailable: bool = False,
) -> str:
    """
    Return markup for a labelled horizontal utilisation bar.

    When ``unavailable`` is set the bar is drawn as an empty hatched track
    reading UNAVAILABLE, never as a bar sitting at 0%. A 0% bar looks like an
    idle resource, and that is exactly how a failed sensor gets mistaken for a
    quiet one.

    Returns markup rather than rendering, so several meters can be combined
    into one card. Streamlit wraps every ``st.markdown`` call in its own
    container element, which means a card opened in one call and closed in
    another does not actually contain what sits between them.
    """
    safe_label = esc(label, "")
    caption = _meter_detail(detail)
    head_open = (
        '<div style="margin-bottom:11px">'
        '<div style="display:flex;justify-content:space-between;'
        'font-size:0.79rem;margin-bottom:5px">'
        '<span style="color:'
    )

    if unavailable or percent is None:
        return "".join(
            [
                head_open,
                PALETTE["text_dim"],
                '">',
                safe_label,
                "</span>",
                '<span style="color:',
                PALETTE["red"],
                ";font-weight:600;font-size:0.72rem;",
                'letter-spacing:0.06em">UNAVAILABLE</span></div>',
                '<div style="height:7px;border-radius:999px;',
                "background:repeating-linear-gradient(45deg,",
                PALETTE["surface_3"],
                " 0 5px,",
                PALETTE["surface"],
                ' 5px 10px)"></div>',
                caption,
                "</div>",
            ]
        )

    value = max(0.0, min(100.0, float(percent)))
    if value >= 90:
        colour = PALETTE["red"]
    elif value >= 75:
        colour = PALETTE["orange"]
    elif value >= 55:
        colour = PALETTE["yellow"]
    else:
        colour = PALETTE["green"]

    return "".join(
        [
            head_open,
            PALETTE["text_dim"],
            '">',
            safe_label,
            "</span>",
            '<span style="color:',
            PALETTE["text"],
            ";font-family:var(--aura-mono);font-weight:600\">",
            f"{value:.1f}%",
            "</span></div>",
            '<div style="height:7px;border-radius:999px;background:',
            PALETTE["surface_3"],
            ';overflow:hidden">',
            '<div style="height:100%;border-radius:999px;width:',
            f"{value:.2f}%",
            ";background:",
            colour,
            '"></div></div>',
            caption,
            "</div>",
        ]
    )


def bar_meter(
    label: str,
    percent: float | None,
    detail: str = "",
    unavailable: bool = False,
) -> None:
    """Render a single utilisation bar."""
    st.markdown(
        bar_meter_markup(label, percent, detail, unavailable),
        unsafe_allow_html=True,
    )


def card(title: str, body: str) -> None:
    """
    Render pre-built markup inside a titled card, in one call.

    ``body`` must already be escaped markup produced by this module.
    """
    markup = "".join(
        [
            '<div class="aura-card">',
            '<div class="aura-metric-label">',
            esc(title, ""),
            "</div>",
            body,
            "</div>",
        ]
    )
    st.markdown(markup, unsafe_allow_html=True)


def def_list(rows: list[tuple[str, str]], card: bool = True) -> None:
    """Render key/value rows as an aligned definition list."""
    if not rows:
        return
    body = "".join(
        '<div class="aura-def"><span class="aura-def-key">'
        + esc(key, "")
        + '</span><span class="aura-def-val">'
        + esc(value)
        + "</span></div>"
        for key, value in rows
    )
    wrapper_open = '<div class="aura-card">' if card else "<div>"
    st.markdown(
        f'{wrapper_open}<div class="aura-defs">{body}</div></div>',
        unsafe_allow_html=True,
    )


# ======================================================================
# States
# ======================================================================


def _state(
    glyph: str,
    title: str,
    body: str,
    variant: str = "",
) -> None:
    classes = "aura-state" + (" aura-state-" + variant if variant else "")
    markup = "".join(
        [
            '<div class="',
            classes,
            '"><div class="aura-state-glyph">',
            esc(glyph, ""),
            '</div><div><div class="aura-state-title">',
            esc(title, ""),
            '</div><div class="aura-state-body">',
            esc(body, ""),
            "</div></div></div>",
        ]
    )
    st.markdown(markup, unsafe_allow_html=True)


def empty_state(title: str, body: str) -> None:
    """Nothing to show yet, and that is expected."""
    _state("○", title, body)


def info_state(title: str, body: str) -> None:
    """Neutral explanatory notice."""
    _state("ⓘ", title, body)


def warn_state(title: str, body: str) -> None:
    """Something is limited or degraded but the page still works."""
    _state("▲", title, body, "warn")


def error_state(title: str, body: str) -> None:
    """Something failed and the affected content cannot be shown."""
    _state("✕", title, body, "error")


def unavailable_note(what: str, why: str) -> None:
    """
    State plainly that a capability is not available, and why.

    Preferred over hiding a feature or filling it with plausible numbers: an
    operator needs to know the difference between "no findings" and "could not
    look".
    """
    warn_state(f"{what} — unavailable", why)
