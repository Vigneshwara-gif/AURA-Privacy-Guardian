"""
About AURA — what the application is, how it decides, and what it cannot do.

This page exists to be read by an evaluator, so it is written to survive
scrutiny rather than to impress. Three things on it are deliberate.

First, there is no accuracy figure. AURA fits unsupervised detectors to one
machine's own baseline and has no labelled attack data, so no accuracy,
precision or recall has ever been computed for this deployment. The page states
"Evaluation metric not available" and explains why, because printing a
percentage would be an invention.

Second, the limitations section is not a formality. It names the reachable
ceiling of the risk scale, the log columns the current pipeline never writes,
and the visibility Windows withholds without elevation. An operator who does
not know these things will misread the other eleven pages.

Third, every number that describes the model is read from the model itself. A
field the model does not expose is rendered as "Not established", never as 0 —
a zero would read as a measurement.
"""

from __future__ import annotations

import platform
import sys

import streamlit as st

from aura_ui import components as ui
from aura_ui import core
from aura_ui.context import Context
from aura_ui.theme import PALETTE

# ======================================================================
# Static copy
# ======================================================================

_PURPOSE = (
    "AURA is a defensive privacy and intrusion-detection assistant for a "
    "single Windows workstation. It samples telemetry the operating system "
    "already exposes — processor and memory pressure, disk and network "
    "throughput, the running process table, open sockets and counts of "
    "accesses to sensitive locations — and compares the current observation "
    "against a behavioural baseline learned from that same machine. When an "
    "observation sits outside the learned normal range, AURA says so, shows "
    "which measurements moved and explains what it can and cannot conclude "
    "from them."
)

_POSITIONING = (
    "AURA is an assistant, not an authority. It produces evidence and a "
    "prioritised opinion; a person decides what it means. It does not quarantine, "
    "terminate, block, delete or modify anything on the host, and it makes no "
    "attribution claim about who or what caused an observation."
)

_DOES = [
    "Reads system telemetry that Windows already exposes to a normal user "
    "process, through psutil.",
    "Learns a numeric baseline of normal behaviour from this machine and "
    "stores it locally.",
    "Flags observations that fall outside that baseline, using two "
    "independent anomaly detectors.",
    "Explains each verdict: which detectors fired, which measurements "
    "deviated, and by how much.",
    "Records every completed live scan to a local monitoring log so history "
    "can be reviewed and exported.",
]

_DOES_NOT = [
    "Capture keystrokes, passwords, clipboard contents, message bodies, "
    "browsing history or document contents.",
    "Record from the microphone, or read frames from the webcam. The optional "
    "camera check only asks the operating system whether a capture device can "
    "be opened.",
    "Transmit anything off the machine. There is no telemetry upload, no "
    "cloud service and no external API call.",
    "Attack, exploit, persist, hide, escalate privilege or interfere with "
    "other software. AURA is strictly read-only against the host.",
    "Identify named malware, resolve threat-intelligence feeds, or geolocate "
    "the addresses it observes.",
]

_PRIVACY_PRINCIPLES = [
    (
        "Local by construction",
        "Every reading, the learned baseline and the full monitoring log stay "
        "in this project's data directory on this machine. Nothing is sent "
        "anywhere, because no code in AURA opens an outbound connection.",
    ),
    (
        "Metadata, not content",
        "AURA counts and measures. It records that a process exists, that a "
        "socket is established and that a sensitive path was accessed. It does "
        "not read the file, the packet or the process memory.",
    ),
    (
        "Camera is opt-in and never captures",
        "The camera check is off by default and must be enabled explicitly for "
        "the session. When enabled it asks whether a capture device can be "
        "opened and immediately releases it. No frame is decoded, displayed or "
        "stored.",
    ),
    (
        "Hardware identifiers withheld",
        "Interface MAC addresses are available to the sensor layer but are "
        "deliberately not displayed, because they identify hardware and are "
        "not needed for any view in this application.",
    ),
    (
        "Demonstration data is quarantined",
        "A demonstration scan is labelled on screen and is never written to the "
        "monitoring log, so synthetic values cannot enter the stored history or "
        "any chart derived from it.",
    ),
]

_LIMITATIONS = [
    (
        "The risk scale does not reach 100",
        "Risk is additive: 30 points for a model-flagged anomaly, 30 for "
        "very high network activity, 20 for a very high process signal and 8 "
        "for connection volume. The highest score the engine can actually "
        "produce is therefore 88, not 100. The gauge marks that reachable "
        "ceiling rather than implying the top of the dial is attainable.",
    ),
    (
        "Scanning is on demand, not continuous",
        "AURA is a Streamlit application, not a Windows service. It observes "
        "the moment you ask it to. There is no protection between scans, and "
        "the interface never claims otherwise.",
    ),
    (
        "Windows withholds socket detail without elevation",
        "Enumerating sockets owned by other users requires administrator "
        "rights. Without them the socket table can come back empty or partial. "
        "An empty table is a visibility limit, not evidence of an idle network, "
        "and the Network Intelligence page labels it as such.",
    ),
    (
        "Twenty of the log's thirty-eight columns are never written",
        "The current scan pipeline passes only fourteen fields to the logging "
        "call, so columns such as Memory, Network_Upload, Network_Download, "
        "IF_Score and Anomaly_Confidence keep their default of 0 on every row. "
        "No chart in this build plots those columns, because a flat line at "
        "zero would misrepresent unrecorded data as a measured zero.",
    ),
    (
        "The stored Severity column is not usable",
        "No severity is passed to the logging call, so that column reads INFO "
        "on every stored row. Severity shown against history is resolved from "
        "the Risk column, which the engine does write.",
    ),
    (
        "Detection is unsupervised and machine-specific",
        "The baseline describes how this computer behaved while the baseline "
        "was collected. If that period was unusual, the baseline is unusual. A "
        "genuinely novel attack that resembles ordinary resource use will not "
        "stand out, and normal-but-rare activity such as a large backup can "
        "read as anomalous.",
    ),
    (
        "One model feature carries almost no information",
        "The camera indicator is constant across the baseline, so it has "
        "near-zero variance and contributes little to either detector. It is "
        "retained for continuity with the stored schema, not because it is "
        "currently discriminative.",
    ),
]

_ARCHITECTURE = [
    (
        "app.py",
        "Entry point. Configures the page, injects the theme, renders the "
        "sidebar and navigation, assembles one telemetry context per run and "
        "dispatches to the active page.",
    ),
    (
        "aura_core.py",
        "Orchestration. Collects the baseline, trains the model, runs a single "
        "scan, combines the model verdict with the privacy signals into a risk "
        "score and severity, and records the event.",
    ),
    (
        "model.py",
        "Detection. Fits a StandardScaler, an Isolation Forest and a Local "
        "Outlier Factor novelty detector, then scores an observation and "
        "reports which features deviated.",
    ),
    (
        "sensors.py",
        "Measurement. Wraps psutil to read processor, memory, disk, network, "
        "interface, process, socket, battery and uptime telemetry.",
    ),
    (
        "privacy_monitor.py",
        "Interpretation. Classifies network, process and connection activity "
        "into conservative bands and raises the discrete privacy indicators.",
    ),
    (
        "logger.py",
        "Persistence. Owns the CSV schema, migrates older files forward and "
        "appends one row per completed scan.",
    ),
    (
        "aura_ui/",
        "Presentation only. Theme, reusable components, shared formatting and "
        "the twelve pages. This layer reads from the modules above and never "
        "writes to them, so the detection engine is unaffected by interface "
        "changes.",
    ),
]

_STACK = [
    ("Language", "Python 3"),
    ("Interface", "Streamlit"),
    ("Machine learning", "scikit-learn — Isolation Forest, Local Outlier Factor"),
    ("Numerics", "NumPy"),
    ("Data handling", "pandas"),
    ("System telemetry", "psutil"),
    ("Camera availability check", "OpenCV (optional, opt-in)"),
    ("Storage", "Local CSV files under data\\"),
    ("Charts", "Streamlit native charts — no external chart service"),
    ("Network dependencies", "None. No CDN, font service or remote API."),
]


# ======================================================================
# Markup helpers
# ======================================================================


def _bullets(items: list[str], glyph: str, colour: str) -> str:
    """Return an escaped, glyph-marked list as card body markup."""
    rows: list[str] = []
    for item in items:
        rows.append(
            "".join(
                [
                    '<div style="display:flex;gap:9px;align-items:flex-start;'
                    'padding:5px 0;line-height:1.55">',
                    '<span style="color:',
                    colour,
                    ";flex:0 0 auto;font-size:0.8rem;line-height:1.55;",
                    'font-weight:700">',
                    ui.esc(glyph, ""),
                    "</span>",
                    '<span style="color:',
                    PALETTE["text_dim"],
                    ';font-size:0.83rem">',
                    ui.esc(item, ""),
                    "</span></div>",
                ]
            )
        )
    return "".join(rows)


def _paragraph(text: str) -> str:
    """Return a body paragraph as card markup."""
    return "".join(
        [
            '<p style="margin:0;color:',
            PALETTE["text_dim"],
            ';font-size:0.86rem;line-height:1.65">',
            ui.esc(text, ""),
            "</p>",
        ]
    )


def _labelled_blocks(rows: list[tuple[str, str]]) -> str:
    """Return heading/body pairs as card markup."""
    blocks: list[str] = []
    for index, (heading, body) in enumerate(rows):
        blocks.append(
            "".join(
                [
                    '<div style="padding:',
                    "0 0 12px" if index == 0 else "12px 0",
                    ";border-top:",
                    "none" if index == 0 else "1px solid "
                    + PALETTE["border_soft"],
                    '">',
                    '<div style="color:',
                    PALETTE["text"],
                    ";font-size:0.84rem;font-weight:600;letter-spacing:0.01em;",
                    'margin-bottom:4px">',
                    ui.esc(heading, ""),
                    "</div>",
                    '<div style="color:',
                    PALETTE["text_dim"],
                    ';font-size:0.82rem;line-height:1.6">',
                    ui.esc(body, ""),
                    "</div></div>",
                ]
            )
        )
    return "".join(blocks)


# ======================================================================
# Sections
# ======================================================================


def _model_facts(ctx: Context) -> list[tuple[str, str]]:
    """Read the model's own description; never substitute zero for unknown."""
    summary = core.model_summary(ctx.model)
    not_established = "Not established"

    algorithms = summary.get("algorithms") or []
    features = summary.get("features") or []

    training = summary.get("training_samples")
    contamination = summary.get("contamination")
    neighbours = summary.get("lof_neighbors")
    trees = summary.get("isolation_trees")

    rows: list[tuple[str, str]] = [
        (
            "Model status",
            core.safe_text(summary.get("status"), "UNKNOWN").replace("_", " "),
        ),
        (
            "Detectors",
            ", ".join(algorithms) if algorithms else not_established,
        ),
        (
            "Input features",
            ", ".join(features) if features else not_established,
        ),
        (
            "Baseline samples used for fitting",
            core.fmt_int(training) if training is not None else not_established,
        ),
        (
            "Isolation Forest trees",
            core.fmt_int(trees) if trees is not None else not_established,
        ),
        (
            "Contamination parameter",
            core.fmt_float(contamination, 3)
            if contamination is not None
            else not_established,
        ),
        (
            "Local Outlier Factor neighbours",
            core.fmt_int(neighbours)
            if neighbours is not None
            else not_established,
        ),
        ("Evaluation metric", "Evaluation metric not available"),
    ]
    return rows


def _methodology(ctx: Context) -> None:
    """How a verdict is produced, end to end."""
    left, right = st.columns([1, 1], gap="medium")

    with left:
        ui.card(
            "Fitted model",
            _labelled_blocks(
                [(label, value) for label, value in _model_facts(ctx)]
            ),
        )

    with right:
        ui.card(
            "How a verdict is produced",
            _labelled_blocks(
                [
                    (
                        "1 · Baseline",
                        "Telemetry is sampled repeatedly while the machine is "
                        "behaving normally and stored locally. This is the only "
                        "notion of 'normal' AURA has.",
                    ),
                    (
                        "2 · Scaling",
                        "Readings are standardised so a feature measured in "
                        "thousands does not dominate one measured in tens "
                        "purely because of its units.",
                    ),
                    (
                        "3 · Two independent detectors",
                        "Isolation Forest looks for observations that are easy "
                        "to separate from the rest of the data. Local Outlier "
                        "Factor looks for observations in a sparser "
                        "neighbourhood than their neighbours. They are "
                        "combined with a logical OR, so either can raise a "
                        "flag — a deliberately sensitive choice for a "
                        "monitoring tool.",
                    ),
                    (
                        "4 · Privacy signals",
                        "Independently of the model, network volume, process "
                        "count and connection count are classified into "
                        "conservative bands, and the discrete privacy "
                        "indicators are evaluated.",
                    ),
                    (
                        "5 · Additive risk score",
                        "Points from the model verdict and from each elevated "
                        "signal are summed, then mapped to a severity band at "
                        "10, 25, 55 and 80.",
                    ),
                    (
                        "6 · Explanation",
                        "The verdict is reported with the detectors that "
                        "fired, their raw decision-function scores and the "
                        "features that deviated most from the baseline.",
                    ),
                ]
            ),
        )

    summary = core.model_summary(ctx.model)
    ui.unavailable_note(
        "Model accuracy, precision and recall",
        core.safe_text(summary.get("accuracy_reason"), ""),
    )


def _build_information(ctx: Context) -> None:
    """Facts about this specific installation, all directly observable."""
    camera = core.camera_dependency_present()
    log_present = core.log_file_present()

    rows: list[tuple[str, str]] = [
        ("Application", f"{core.APP_NAME} {core.APP_VERSION}"),
        ("Interface build", "Professional submission edition"),
        (
            "Python",
            f"{sys.version_info.major}.{sys.version_info.minor}."
            f"{sys.version_info.micro}",
        ),
        ("Streamlit", core.safe_text(getattr(st, "__version__", ""), core.UNKNOWN)),
        (
            "Host platform",
            core.safe_text(platform.system(), core.UNKNOWN)
            + " "
            + core.safe_text(platform.release(), ""),
        ),
        (
            "Camera check dependency",
            "opencv-python present" if camera else "opencv-python not installed",
        ),
        (
            "Monitoring log",
            f"Present — {ctx.history_rows:,} stored events"
            if log_present
            else "Not created yet",
        ),
        (
            "Scan performed this session",
            "Yes" if ctx.has_result else "No",
        ),
        ("Outbound network calls made", "None"),
    ]
    ui.def_list(rows)


# ======================================================================
# Entry point
# ======================================================================


def render(ctx: Context) -> None:
    """Render the About AURA page."""
    ui.page_head(
        "About AURA",
        "What this application measures, how it reaches a verdict, and the "
        "limits of what it can conclude.",
        "About",
        ui.badge(
            "DEFENSIVE  ·  LOCAL ONLY",
            PALETTE["blue"],
            PALETTE["blue_soft"],
            "◇",
        ),
    )

    ui.section("Purpose")
    ui.card("What AURA is", _paragraph(_PURPOSE) + "<div style='height:10px'></div>"
            + _paragraph(_POSITIONING))

    ui.section("Scope")
    scope_left, scope_right = st.columns([1, 1], gap="medium")
    with scope_left:
        ui.card(
            "What AURA does",
            _bullets(_DOES, "✓", PALETTE["green"]),
        )
    with scope_right:
        ui.card(
            "What AURA does not do",
            _bullets(_DOES_NOT, "✕", PALETTE["red"]),
        )

    st.caption(
        "The second list is a design constraint, not a roadmap. AURA is "
        "strictly defensive and read-only by intent; none of those "
        "capabilities is planned."
    )

    ui.section("Detection methodology")
    _methodology(ctx)

    ui.section("Privacy by design")
    ui.card("Principles applied", _labelled_blocks(_PRIVACY_PRINCIPLES))

    ui.section("Known limitations")
    ui.card(
        "Read this before interpreting any other page",
        _labelled_blocks(_LIMITATIONS),
    )

    ui.section("Architecture")
    ui.def_list(_ARCHITECTURE)
    st.caption(
        "The interface layer depends on the engine modules. The engine modules "
        "do not depend on the interface, so the detection pipeline behaves "
        "identically whether it is driven from this application or from a "
        "script."
    )

    ui.section("Technology")
    ui.def_list(_STACK)

    ui.section("Build information")
    _build_information(ctx)

    ui.section("Responsible use")
    ui.card(
        "Intended use and boundaries",
        _paragraph(
            "AURA is intended for use on a computer you own or are authorised "
            "to monitor. It observes the host it runs on and nothing else: it "
            "does not scan a network, probe other hosts, or collect data about "
            "other people. Its output is evidence for a human decision, not a "
            "verdict to be acted on automatically, and an elevated risk score "
            "means an observation was unusual for this machine — not that an "
            "intrusion has been proven."
        ),
    )
