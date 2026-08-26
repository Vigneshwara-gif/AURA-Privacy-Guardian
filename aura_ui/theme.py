"""
AURA visual language.

One place defines every colour, radius and spacing value used by the interface,
so the whole application stays consistent and a change here changes everywhere.

Colour rules (deliberate, and enforced by the helpers in ``components.py``):

  * green  = healthy / safe / normal
  * blue   = informational / nominal
  * amber  = warning / elevated (MEDIUM)
  * orange = high risk (HIGH)
  * red    = critical / failure
  * gray   = unknown / not measured

Colour is never the only carrier of meaning. Every severity or status surface
also renders a text label and a shape glyph, ensuring accessibility and contrast.

The palette is a premium SOC dark console aesthetic: deep navy/near-black,
restrained cyan/blue accents, and crisp semantic indicators.
"""

from __future__ import annotations

import streamlit as st

__all__ = [
    "PALETTE",
    "SEVERITY_STYLES",
    "STATUS_STYLES",
    "inject_theme",
    "severity_color",
]


# ======================================================================
# Palette
# ======================================================================

PALETTE: dict[str, str] = {
    # Surfaces, darkest to lightest (Deep Navy / Near-Black SOC Console)
    "bg": "#06090f",
    "bg_alt": "#090e17",
    "surface": "#0d1522",
    "surface_2": "#121d2d",
    "surface_3": "#18263a",
    "border": "#20324d",
    "border_soft": "#142234",
    "border_cyan": "rgba(56, 189, 248, 0.35)",

    # Typography
    "text": "#f1f5f9",
    "text_dim": "#94a3b8",
    "text_faint": "#64748b",

    # Semantic security colors
    "green": "#22c55e",
    "green_soft": "rgba(34, 197, 94, 0.12)",
    "yellow": "#f59e0b",  # Amber/warning
    "yellow_soft": "rgba(245, 158, 11, 0.12)",
    "orange": "#f97316",  # High risk
    "orange_soft": "rgba(249, 115, 22, 0.12)",
    "red": "#ef4444",     # Critical / failure
    "red_soft": "rgba(239, 68, 68, 0.14)",
    "blue": "#38bdf8",    # Restrained cyan/blue
    "blue_soft": "rgba(56, 189, 248, 0.12)",
    "violet": "#818cf8",
    "cyan": "#06b6d4",
}


# ======================================================================
# Severity and status vocabularies
# ======================================================================

SEVERITY_STYLES: dict[str, dict[str, str]] = {
    "CRITICAL": {
        "label": "CRITICAL",
        "glyph": "◆",  # filled diamond
        "color": PALETTE["red"],
        "bg": PALETTE["red_soft"],
    },
    "HIGH": {
        "label": "HIGH",
        "glyph": "▲",  # filled triangle
        "color": PALETTE["orange"],
        "bg": PALETTE["orange_soft"],
    },
    "MEDIUM": {
        "label": "MEDIUM",
        "glyph": "■",  # filled square
        "color": PALETTE["yellow"],
        "bg": PALETTE["yellow_soft"],
    },
    "LOW": {
        "label": "LOW",
        "glyph": "●",  # filled circle
        "color": PALETTE["blue"],
        "bg": PALETTE["blue_soft"],
    },
    "NORMAL": {
        "label": "NORMAL",
        "glyph": "●",
        "color": PALETTE["green"],
        "bg": PALETTE["green_soft"],
    },
    "INFO": {
        "label": "INFO",
        "glyph": "○",  # hollow circle
        "color": PALETTE["blue"],
        "bg": PALETTE["blue_soft"],
    },
    "UNKNOWN": {
        "label": "UNKNOWN",
        "glyph": "—",  # em dash
        "color": PALETTE["text_faint"],
        "bg": "rgba(100, 116, 139, 0.12)",
    },
}

STATUS_STYLES: dict[str, dict[str, str]] = {
    "HEALTHY": {
        "label": "HEALTHY",
        "glyph": "●",
        "color": PALETTE["green"],
        "bg": PALETTE["green_soft"],
    },
    "DEGRADED": {
        "label": "DEGRADED",
        "glyph": "▲",
        "color": PALETTE["yellow"],
        "bg": PALETTE["yellow_soft"],
    },
    "PERMISSION_LIMITED": {
        "label": "PERMISSION LIMITED",
        "glyph": "■",
        "color": PALETTE["orange"],
        "bg": PALETTE["orange_soft"],
    },
    "UNAVAILABLE": {
        "label": "UNAVAILABLE",
        "glyph": "✕",  # multiplication x
        "color": PALETTE["red"],
        "bg": PALETTE["red_soft"],
    },
    "NOT_PRESENT": {
        "label": "NOT PRESENT",
        "glyph": "—",
        "color": PALETTE["text_faint"],
        "bg": "rgba(100, 116, 139, 0.12)",
    },
    "NOT_PROBED": {
        "label": "NOT PROBED",
        "glyph": "○",
        "color": PALETTE["text_dim"],
        "bg": "rgba(148, 163, 184, 0.10)",
    },
    "PRIMING": {
        "label": "PRIMING",
        "glyph": "○",
        "color": PALETTE["blue"],
        "bg": PALETTE["blue_soft"],
    },
}


def severity_color(severity: str) -> str:
    """Return the palette colour for a severity name, defaulting to UNKNOWN."""
    key = str(severity or "UNKNOWN").strip().upper()
    return SEVERITY_STYLES.get(key, SEVERITY_STYLES["UNKNOWN"])["color"]


# ======================================================================
# Stylesheet
# ======================================================================

_CSS_VARS: dict[str, str] = {
    "--aura-bg": PALETTE["bg"],
    "--aura-bg-alt": PALETTE["bg_alt"],
    "--aura-surface": PALETTE["surface"],
    "--aura-surface-2": PALETTE["surface_2"],
    "--aura-surface-3": PALETTE["surface_3"],
    "--aura-border": PALETTE["border"],
    "--aura-border-soft": PALETTE["border_soft"],
    "--aura-border-cyan": PALETTE["border_cyan"],
    "--aura-text": PALETTE["text"],
    "--aura-text-dim": PALETTE["text_dim"],
    "--aura-text-faint": PALETTE["text_faint"],
    "--aura-green": PALETTE["green"],
    "--aura-yellow": PALETTE["yellow"],
    "--aura-orange": PALETTE["orange"],
    "--aura-red": PALETTE["red"],
    "--aura-blue": PALETTE["blue"],
    "--aura-cyan": PALETTE["cyan"],
    "--aura-radius": "8px",
    "--aura-radius-sm": "5px",
    "--aura-gap": "14px",
    "--aura-font": (
        '"Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, '
        '"Helvetica Neue", Arial, sans-serif'
    ),
    "--aura-mono": (
        '"Cascadia Mono", "Consolas", "SF Mono", "Menlo", '
        '"Roboto Mono", monospace'
    ),
}


def _root_css() -> str:
    """Render the ``:root`` custom-property block from :data:`_CSS_VARS`."""
    declarations = "\n".join(
        "    " + name + ": " + value + ";"
        for name, value in _CSS_VARS.items()
    )
    return ":root {\n" + declarations + "\n}\n"


_STYLESHEET_BODY = """

/* ================================================================
   TYPOGRAPHY AND BASE
   ================================================================ */

html, body, .stApp, [class*="css"] {
    font-family: var(--aura-font);
}

.stApp {
    background:
        radial-gradient(circle at 90% -5%,
            rgba(56, 189, 248, 0.07), transparent 32%),
        radial-gradient(circle at 5% 95%,
            rgba(129, 140, 248, 0.05), transparent 30%),
        var(--aura-bg);
    color: var(--aura-text);
}

.block-container {
    max-width: 1560px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}

#MainMenu, footer, header [data-testid="stStatusWidget"] {
    visibility: hidden;
}

[data-testid="stHeader"] {
    background: transparent;
    height: 0;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--aura-text);
    letter-spacing: -0.015em;
    font-weight: 600;
}

a, a:visited { color: var(--aura-blue); text-decoration: none; }
a:hover { text-decoration: underline; }

code, kbd, pre, .aura-mono {
    font-family: var(--aura-mono) !important;
}

/* ================================================================
   PAGE HEADER
   ================================================================ */

.aura-page-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 20px;
    padding: 16px 20px;
    margin-bottom: 18px;
    background: linear-gradient(135deg,
        rgba(56, 189, 248, 0.06) 0%,
        var(--aura-surface-2) 40%,
        var(--aura-surface) 100%);
    border: 1px solid var(--aura-border);
    border-left: 3px solid var(--aura-blue);
    border-radius: var(--aura-radius);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25);
}

.aura-page-head .aura-eyebrow {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--aura-blue);
    margin-bottom: 4px;
}

.aura-page-head .aura-h1 {
    font-size: 1.55rem;
    font-weight: 650;
    line-height: 1.2;
    letter-spacing: -0.02em;
    margin: 0 0 4px 0;
    color: var(--aura-text);
}

.aura-page-head .aura-sub {
    font-size: 0.85rem;
    line-height: 1.45;
    color: var(--aura-text-dim);
    max-width: 78ch;
    margin: 0;
}

/* ================================================================
   SECTION HEADER
   ================================================================ */

.aura-section {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 22px 0 10px 0;
}

.aura-section .aura-section-title {
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--aura-text-dim);
    white-space: nowrap;
}

.aura-section .aura-section-rule {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg,
        var(--aura-border) 0%, transparent 100%);
}

.aura-section .aura-section-note {
    font-size: 0.72rem;
    color: var(--aura-text-faint);
    white-space: nowrap;
}

/* ================================================================
   HERO SECURITY POSTURE CARD
   ================================================================ */

.aura-hero-posture {
    background: linear-gradient(135deg,
        var(--aura-surface-2) 0%,
        var(--aura-surface) 100%);
    border: 1px solid var(--aura-border);
    border-radius: var(--aura-radius);
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35),
                inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.aura-hero-grid {
    display: grid;
    grid-template-columns: 1.4fr 1.1fr 1fr;
    gap: 24px;
    align-items: center;
}

@media (max-width: 1024px) {
    .aura-hero-grid {
        grid-template-columns: 1fr;
        gap: 18px;
    }
}

.aura-posture-title {
    font-size: 0.70rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--aura-text-faint);
    margin-bottom: 6px;
}

.aura-posture-verdict {
    font-size: 1.85rem;
    font-weight: 750;
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin-bottom: 8px;
}

.aura-posture-summary {
    font-size: 0.84rem;
    line-height: 1.45;
    color: var(--aura-text-dim);
    margin-top: 6px;
}

/* ================================================================
   CARDS AND METRICS
   ================================================================ */

.aura-card {
    background: linear-gradient(180deg,
        var(--aura-surface-2) 0%, var(--aura-surface) 100%);
    border: 1px solid var(--aura-border);
    border-radius: var(--aura-radius);
    padding: 16px 18px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25),
                inset 0 1px 0 rgba(255, 255, 255, 0.02);
}

.aura-metric {
    position: relative;
    background: linear-gradient(180deg,
        var(--aura-surface-2) 0%, var(--aura-surface) 100%);
    border: 1px solid var(--aura-border);
    border-radius: var(--aura-radius);
    padding: 14px 16px 14px 16px;
    height: 100%;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25),
                inset 0 1px 0 rgba(255, 255, 255, 0.02);
    transition: border-color 120ms ease;
}

.aura-metric:hover {
    border-color: rgba(56, 189, 248, 0.30);
}

.aura-metric::before {
    content: "";
    position: absolute;
    left: 0; top: 10px; bottom: 10px;
    width: 2px;
    border-radius: 2px;
    background: var(--aura-accent, var(--aura-border));
}

.aura-metric .aura-metric-label {
    font-size: 0.67rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: var(--aura-text-faint);
    margin-bottom: 7px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.aura-metric .aura-metric-value {
    font-family: var(--aura-mono);
    font-size: 1.55rem;
    font-weight: 650;
    line-height: 1.05;
    letter-spacing: -0.025em;
    color: var(--aura-text);
    display: flex;
    align-items: baseline;
    gap: 5px;
}

.aura-metric .aura-metric-unit {
    font-size: 0.80rem;
    font-weight: 500;
    color: var(--aura-text-faint);
    letter-spacing: 0;
}

.aura-metric .aura-metric-foot {
    margin-top: 7px;
    font-size: 0.72rem;
    line-height: 1.4;
    color: var(--aura-text-dim);
}

/* ================================================================
   BADGES AND PILLS
   ================================================================ */

.aura-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px 3px 8px;
    border-radius: 999px;
    font-size: 0.69rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    border: 1px solid;
    white-space: nowrap;
    line-height: 1.5;
}

.aura-badge .aura-badge-glyph {
    font-size: 0.70rem;
    line-height: 1;
}

.aura-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: var(--aura-radius-sm);
    background: var(--aura-surface-3);
    border: 1px solid var(--aura-border);
    color: var(--aura-text-dim);
    font-size: 0.74rem;
    font-weight: 500;
    white-space: nowrap;
}

.aura-chip strong {
    color: var(--aura-text);
    font-family: var(--aura-mono);
    font-weight: 600;
}

/* ================================================================
   RISK METER
   ================================================================ */

.aura-gauge-wrap {
    display: flex;
    align-items: center;
    gap: 22px;
    flex-wrap: wrap;
}

.aura-gauge-readout .aura-gauge-score {
    font-family: var(--aura-mono);
    font-size: 2.7rem;
    font-weight: 650;
    line-height: 1;
    letter-spacing: -0.035em;
}

.aura-gauge-readout .aura-gauge-scale {
    font-family: var(--aura-mono);
    font-size: 0.95rem;
    color: var(--aura-text-faint);
    font-weight: 500;
}

.aura-gauge-readout .aura-gauge-caption {
    margin-top: 8px;
    font-size: 0.735rem;
    line-height: 1.45;
    color: var(--aura-text-dim);
    max-width: 44ch;
}

/* ================================================================
   STATES: empty, loading, error, warning
   ================================================================ */

.aura-state {
    display: flex;
    gap: 14px;
    align-items: flex-start;
    padding: 16px 20px;
    border-radius: var(--aura-radius);
    border: 1px dashed var(--aura-border);
    background: rgba(13, 21, 34, 0.55);
}

.aura-state.aura-state-error {
    border-style: solid;
    border-color: rgba(239, 68, 68, 0.45);
    background: rgba(239, 68, 68, 0.08);
}

.aura-state.aura-state-warn {
    border-style: solid;
    border-color: rgba(245, 158, 11, 0.40);
    background: rgba(245, 158, 11, 0.07);
}

.aura-state .aura-state-glyph {
    font-size: 1.05rem;
    line-height: 1.4;
    color: var(--aura-text-faint);
}

.aura-state .aura-state-title {
    font-size: 0.88rem;
    font-weight: 620;
    color: var(--aura-text);
    margin-bottom: 4px;
}

.aura-state .aura-state-body {
    font-size: 0.80rem;
    line-height: 1.5;
    color: var(--aura-text-dim);
    max-width: 84ch;
}

/* ================================================================
   DEFINITION ROWS
   ================================================================ */

.aura-defs { display: flex; flex-direction: column; gap: 1px; }

.aura-def {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 14px;
    padding: 8px 2px;
    border-bottom: 1px solid var(--aura-border-soft);
    font-size: 0.80rem;
}

.aura-def:last-child { border-bottom: none; }

.aura-def .aura-def-key {
    color: var(--aura-text-dim);
    flex-shrink: 0;
}

.aura-def .aura-def-val {
    color: var(--aura-text);
    font-family: var(--aura-mono);
    font-weight: 550;
    text-align: right;
    word-break: break-word;
}

/* ================================================================
   SIDEBAR
   ================================================================ */

[data-testid="stSidebar"] {
    background: linear-gradient(180deg,
        #080c14 0%, #06090e 100%);
    border-right: 1px solid var(--aura-border);
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.0rem;
}

.aura-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 2px 4px 12px 4px;
    border-bottom: 1px solid var(--aura-border);
    margin-bottom: 12px;
}

.aura-brand .aura-brand-mark {
    width: 34px; height: 34px;
    flex-shrink: 0;
    border-radius: 8px;
    display: grid;
    place-items: center;
    background: linear-gradient(145deg,
        rgba(56, 189, 248, 0.20), rgba(129, 140, 248, 0.15));
    border: 1px solid rgba(56, 189, 248, 0.40);
    font-size: 0.98rem;
    color: var(--aura-blue);
}

.aura-brand .aura-brand-name {
    font-size: 1.12rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    line-height: 1.1;
    color: var(--aura-text);
}

.aura-brand .aura-brand-tag {
    font-size: 0.60rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--aura-blue);
    margin-top: 2px;
}

.aura-side-label {
    font-size: 0.63rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--aura-text-faint);
    margin: 14px 4px 6px 4px;
}

/* Sidebar Navigation Buttons */
[data-testid="stSidebar"] .stButton > button {
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 6px 10px !important;
    font-size: 0.81rem !important;
    font-weight: 520 !important;
    border-radius: 5px !important;
    margin-bottom: 2px !important;
    border: 1px solid transparent !important;
    background: transparent !important;
    color: var(--aura-text-dim) !important;
    transition: all 100ms ease-in-out !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(56, 189, 248, 0.08) !important;
    border-color: rgba(56, 189, 248, 0.20) !important;
    color: var(--aura-text) !important;
}

[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(56, 189, 248, 0.12) !important;
    border-color: rgba(56, 189, 248, 0.35) !important;
    border-left: 3px solid var(--aura-blue) !important;
    color: #ffffff !important;
    font-weight: 650 !important;
}

.aura-side-stat {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    padding: 5px 4px;
    font-size: 0.76rem;
    border-bottom: 1px solid var(--aura-border-soft);
}

.aura-side-stat:last-child { border-bottom: none; }
.aura-side-stat .aura-side-stat-key { color: var(--aura-text-faint); }
.aura-side-stat .aura-side-stat-val {
    color: var(--aura-text);
    font-family: var(--aura-mono);
    font-weight: 600;
}

.aura-side-note {
    margin-top: 14px;
    padding: 10px 11px;
    border-radius: var(--aura-radius-sm);
    background: rgba(56, 189, 248, 0.04);
    border: 1px solid var(--aura-border);
    font-size: 0.70rem;
    line-height: 1.45;
    color: var(--aura-text-faint);
}

/* ================================================================
   STREAMLIT WIDGET OVERRIDES
   ================================================================ */

.stButton > button, .stDownloadButton > button {
    background: var(--aura-surface-3);
    color: var(--aura-text);
    border: 1px solid var(--aura-border);
    border-radius: var(--aura-radius-sm);
    font-size: 0.82rem;
    font-weight: 560;
    padding: 0.40rem 0.90rem;
    transition: background 120ms ease, border-color 120ms ease;
}

.stButton > button:hover, .stDownloadButton > button:hover {
    background: #1e2c40;
    border-color: #2b3f5c;
    color: #ffffff;
}

.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {
    background: linear-gradient(180deg, #0284c7 0%, #0369a1 100%);
    border-color: #38bdf8;
    color: #ffffff;
    font-weight: 620;
    box-shadow: 0 2px 4px rgba(2, 132, 199, 0.25);
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(180deg, #0369a1 0%, #075985 100%);
    border-color: #7dd3fc;
}

/* Inputs */
.stTextInput input, .stNumberInput input, .stDateInput input,
.stTextArea textarea {
    background: var(--aura-bg-alt) !important;
    color: var(--aura-text) !important;
    border: 1px solid var(--aura-border) !important;
    border-radius: var(--aura-radius-sm) !important;
    font-size: 0.84rem !important;
}

.stTextInput input:focus, .stNumberInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--aura-blue) !important;
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.18) !important;
}

[data-baseweb="select"] > div, [data-baseweb="input"] > div {
    background: var(--aura-bg-alt) !important;
    border-color: var(--aura-border) !important;
    border-radius: var(--aura-radius-sm) !important;
}

/* Labels */
.stTextInput label, .stSelectbox label, .stMultiSelect label,
.stSlider label, .stNumberInput label, .stDateInput label,
.stRadio label, .stCheckbox label, .stTextArea label {
    font-size: 0.76rem !important;
    color: var(--aura-text-dim) !important;
    font-weight: 550 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 3px;
    border-bottom: 1px solid var(--aura-border);
    background: transparent;
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    padding: 8px 14px;
    font-size: 0.80rem;
    font-weight: 560;
    color: var(--aura-text-faint);
}

.stTabs [aria-selected="true"] {
    color: var(--aura-text) !important;
    border-bottom-color: var(--aura-blue) !important;
    background: rgba(56, 189, 248, 0.05);
}

/* Expanders */
[data-testid="stExpander"] {
    background: var(--aura-surface);
    border: 1px solid var(--aura-border);
    border-radius: var(--aura-radius);
    overflow: hidden;
}

[data-testid="stExpander"] summary {
    font-size: 0.83rem;
    font-weight: 570;
    color: var(--aura-text);
    padding: 10px 14px;
}

[data-testid="stExpander"] summary:hover {
    background: rgba(56, 189, 248, 0.05);
}

/* Dataframes */
[data-testid="stDataFrame"], [data-testid="stTable"] {
    border: 1px solid var(--aura-border);
    border-radius: var(--aura-radius);
    overflow: hidden;
}

[data-testid="stDataFrame"] [role="columnheader"] {
    background: var(--aura-surface-3) !important;
    color: var(--aura-text-dim) !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.055em;
    text-transform: uppercase;
}

/* Native metric */
[data-testid="stMetric"] {
    background: var(--aura-surface);
    border: 1px solid var(--aura-border);
    border-radius: var(--aura-radius);
    padding: 12px 14px;
}

[data-testid="stMetricValue"] {
    font-family: var(--aura-mono);
    font-size: 1.38rem;
    font-weight: 600;
    color: var(--aura-text);
}

[data-testid="stMetricLabel"] {
    font-size: 0.68rem;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--aura-text-faint);
}

/* Alerts */
[data-testid="stAlert"] {
    border-radius: var(--aura-radius);
    border-width: 1px;
    font-size: 0.83rem;
}

/* Dividers and captions */
hr, [data-testid="stDivider"] {
    border-color: var(--aura-border-soft);
    margin: 1.0rem 0;
}

[data-testid="stCaptionContainer"], .stCaption {
    color: var(--aura-text-faint) !important;
    font-size: 0.745rem !important;
    line-height: 1.45 !important;
}

/* Progress bar */
.stProgress > div > div > div {
    background: var(--aura-surface-3);
    border-radius: 999px;
    height: 7px;
}

.stProgress > div > div > div > div {
    border-radius: 999px;
}

/* Tooltip */
[data-baseweb="tooltip"] {
    background: #18263a !important;
    border: 1px solid var(--aura-border) !important;
    border-radius: var(--aura-radius-sm) !important;
    font-size: 0.76rem !important;
    color: var(--aura-text) !important;
    max-width: 340px;
}

/* Scrollbars */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--aura-bg); }
::-webkit-scrollbar-thumb {
    background: #1c2b40;
    border-radius: 4px;
    border: 2px solid var(--aura-bg);
}
::-webkit-scrollbar-thumb:hover { background: #263a56; }

/* Tighten Streamlit default vertical rhythm */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
    gap: 0.55rem;
}

[data-testid="stElementContainer"] { margin-bottom: 0.15rem; }

"""


def inject_theme() -> None:
    """Inject the AURA stylesheet."""
    st.markdown(
        "<style>\n" + _root_css() + _STYLESHEET_BODY + "\n</style>",
        unsafe_allow_html=True,
    )
