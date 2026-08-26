"""
AURA UI data layer.

Every page reads telemetry through this module, so caching, coercion and — most
importantly — *honesty about what a number means* are decided in exactly one
place.

Three responsibilities:

1. **Cached access to the existing backend.** ``logger.load_logs()`` reads and
   re-parses the entire CSV, and Streamlit re-runs the whole script on every
   click. Without caching, changing a dropdown re-reads the full history. The
   cache is keyed on the log file's modification time and size, so a new scan
   invalidates it automatically and no interaction ever shows stale data.

2. **Honest sensor status.** The backend sensor getters return a zero-filled
   dictionary when they fail, and they do it silently. A failed memory probe is
   therefore indistinguishable from 0 GB of RAM *by value alone*. This module
   derives status from value plausibility instead — a machine with zero logical
   CPU cores or zero total bytes of RAM is not idle, it is a failed probe — and
   reports UNAVAILABLE rather than rendering a failure as a healthy zero.

3. **Formatting and coercion.** So no page has to defend itself against a
   ``NaN`` in a CSV column that predates the current schema.

Nothing here invents a measurement. Where a value cannot be established, the
functions return an explicit "unknown" marker and the components layer renders
it as such.
"""

from __future__ import annotations

import math
import os
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

# Existing AURA backend. Imported, never modified.
import aura_core
import logger as aura_logger
import model as ml_model
import privacy_monitor
import sensors

__all__ = [
    "APP_NAME",
    "APP_TAGLINE",
    "APP_VERSION",
    "RISK_BANDS",
    "RISK_SCORE_NOMINAL_MAX",
    "RISK_SCORE_OBSERVED_MAX",
    "SEVERITY_ORDER",
    "UNKNOWN",
    "band_for_score",
    "bump_refresh",
    "camera_dependency_present",
    "clamp",
    "derive_sensor_health",
    "ensemble_agreement",
    "fmt_clock",
    "fmt_float",
    "fmt_int",
    "fmt_relative",
    "fmt_timestamp",
    "get_last_scan_time",
    "get_latest_result",
    "health_rollup",
    "latest_row",
    "live_connections",
    "load_event_log",
    "load_model_or_stop",
    "log_file_present",
    "log_severity_series",
    "model_summary",
    "numeric_column",
    "refresh_token",
    "result_is_demo",
    "safe_float",
    "safe_int",
    "safe_text",
    "severity_of",
    "trend_frame",
]


# ======================================================================
# Identity
# ======================================================================

APP_NAME = "AURA"
APP_TAGLINE = "AI-Powered Privacy Intelligence & Intrusion Detection"
APP_VERSION = "1.0"

UNKNOWN = "—"


# ======================================================================
# Risk scale
# ======================================================================
#
# These thresholds mirror aura_core's bands exactly (80 / 55 / 25 / 10). They
# are duplicated here for *display* only: the UI must never compute a risk
# score, it only labels the score the risk engine produced. If the engine's
# bands ever change, this table must be updated to match.

RISK_BANDS: tuple[tuple[int, str], ...] = (
    (80, "CRITICAL"),
    (55, "HIGH"),
    (25, "MEDIUM"),
    (10, "LOW"),
    (0, "NORMAL"),
)

# The scale the engine nominally reports on.
RISK_SCORE_NOMINAL_MAX = 100

# The highest score the current additive scoring function can actually produce:
# 30 (machine learning) + 30 (network) + 20 (process) + 8 (connections). The
# gauge is drawn against 100 because that is the engine's declared scale, but
# the caption states this ceiling so nobody reads "88" as "12 points from the
# worst case the tool can express".
RISK_SCORE_OBSERVED_MAX = 88


def band_for_score(score: float) -> str:
    """Return the band name for a numeric risk score."""
    value = safe_float(score, 0.0)
    for threshold, name in RISK_BANDS:
        if value >= threshold:
            return name
    return "NORMAL"


def severity_of(row: Any, default: str = "UNKNOWN") -> str:
    """
    Read a severity from a scan result or a log row.

    Prefers the stored ``Severity``, falls back to ``Risk`` / ``Risk_Level``,
    and only then to the score-derived band. The engine's own label always
    wins, because re-deriving it here would silently mask a scoring change.
    """
    if row is None:
        return default

    for key in ("Severity", "Risk", "Risk_Level"):
        try:
            raw = row[key] if key in row else None
        except (KeyError, TypeError, IndexError):
            raw = None
        text = safe_text(raw, "").upper()
        if text and text not in {"NAN", "NONE", "UNKNOWN"}:
            return "INFO" if text == "NORMAL" else text

    try:
        score = row["Risk_Score"] if "Risk_Score" in row else None
    except (KeyError, TypeError, IndexError):
        score = None

    if score is None:
        return default

    band = band_for_score(safe_float(score, 0.0))
    return "INFO" if band == "NORMAL" else band


# The severity ladder, weakest first. Used to order charts consistently.
SEVERITY_ORDER: tuple[str, ...] = ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL")


def log_severity_series(frame: pd.DataFrame) -> pd.Series:
    """
    Resolve a severity label for every stored event.

    Why this does not simply read the ``Severity`` column
    ----------------------------------------------------
    It cannot be trusted. ``aura_core.scan_once`` computes a severity correctly
    but then calls ``logger.append_log()`` *without* passing ``severity=``, so
    the column falls back to its default of ``"INFO"`` on every single row. A
    chart driven by that column would report a flawless history no matter what
    actually happened — a healthy-looking zero standing in for a value that was
    never written.

    The ``risk=`` argument *is* passed on the same call, so the ``Risk`` column
    holds the engine's real verdict. It is preferred here, mapped through the
    engine's own ``NORMAL -> INFO`` rule. ``Risk_Score`` (also written
    faithfully) is the last resort, banded with the documented thresholds.

    Returns an empty Series when the history carries no usable verdict at all,
    so the caller can render an explicit empty state rather than a blank axis.
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.Series(dtype="object")

    def _normalise(column: str) -> pd.Series:
        values = frame[column].astype(str).str.strip().str.upper()
        values = values.where(
            ~values.isin(["", "NAN", "NONE", "NULL", "<NA>", "UNKNOWN"])
        )
        return values.replace({"NORMAL": "INFO"})

    # 1. The engine's real verdict.
    if "Risk" in frame.columns:
        resolved = _normalise("Risk")
        if resolved.notna().any():
            return resolved.dropna()

    # 2. The stored severity, in case a future build starts populating it.
    if "Severity" in frame.columns:
        resolved = _normalise("Severity")
        if resolved.notna().any():
            return resolved.dropna()

    # 3. Band the numeric score.
    if "Risk_Score" in frame.columns:
        scores = pd.to_numeric(frame["Risk_Score"], errors="coerce").dropna()
        if not scores.empty:
            return scores.map(
                lambda value: "INFO"
                if band_for_score(value) == "NORMAL"
                else band_for_score(value)
            )

    return pd.Series(dtype="object")


# ======================================================================
# Coercion
# ======================================================================
#
# The log file has accumulated several schema generations, so any column may
# hold a blank, a string, or a NaN. These helpers keep that reality out of the
# page modules.


def safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce to float, returning ``default`` for blanks, NaN and junk."""
    if value is None:
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    # NaN and infinities are not usable as displayed measurements.
    if math.isnan(result) or math.isinf(result):
        return default
    return result


def safe_int(value: Any, default: int = 0) -> int:
    """Coerce to int via float, so ``"12.0"`` parses as 12."""
    if value is None:
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(result) or math.isinf(result):
        return default
    return int(result)


def safe_text(value: Any, default: str = "") -> str:
    """Coerce to a trimmed string, mapping pandas null markers to default."""
    if value is None:
        return default
    try:
        if isinstance(value, float) and math.isnan(value):
            return default
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return default
    return text


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Constrain a value to an inclusive range."""
    return max(low, min(high, value))


# ======================================================================
# Formatting
# ======================================================================


def fmt_float(value: Any, digits: int = 1, unknown: str = UNKNOWN) -> str:
    """Format a float, or return ``unknown`` when the value is unusable."""
    if value is None:
        return unknown
    try:
        number = float(value)
    except (TypeError, ValueError):
        return unknown
    if math.isnan(number) or math.isinf(number):
        return unknown
    return f"{number:,.{digits}f}"


def fmt_int(value: Any, unknown: str = UNKNOWN) -> str:
    """Format an integer with thousands separators, or ``unknown``."""
    if value is None:
        return unknown
    try:
        number = float(value)
    except (TypeError, ValueError):
        return unknown
    if math.isnan(number) or math.isinf(number):
        return unknown
    return f"{int(number):,}"


def fmt_clock(moment: datetime | None, unknown: str = "Never") -> str:
    """Format a datetime as a readable local wall-clock time."""
    if not isinstance(moment, datetime):
        return unknown
    return moment.strftime("%d %b %Y  %H:%M:%S")


def fmt_relative(moment: datetime | None, unknown: str = "Never") -> str:
    """Describe how long ago something happened, in human terms."""
    if not isinstance(moment, datetime):
        return unknown
    delta = (datetime.now() - moment).total_seconds()
    if delta < 0:
        return "just now"
    if delta < 10:
        return "just now"
    if delta < 60:
        return f"{int(delta)}s ago"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    return f"{int(delta // 86400)}d ago"


def fmt_timestamp(value: Any, unknown: str = UNKNOWN) -> str:
    """Normalise a stored timestamp string for display."""
    text = safe_text(value, "")
    if not text:
        return unknown
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return text
    return parsed.strftime("%d %b %H:%M:%S")


def fmt_seconds(seconds: Any, unknown: str = UNKNOWN) -> str:
    """Format a duration in seconds as ``2d 4h 13m``."""
    total = safe_int(seconds, -1)
    if total < 0:
        return unknown
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


# ======================================================================
# Refresh token
# ======================================================================
#
# Live telemetry is cached with a short time-to-live. A Refresh button needs a
# way to bypass that cache immediately, so every cached live reader takes a
# token argument; changing the token is a cache miss.


def refresh_token() -> int:
    """Return the current live-telemetry cache-busting token."""
    return int(st.session_state.get("aura_refresh_token", 0))


def bump_refresh() -> None:
    """Invalidate cached live telemetry on the next read."""
    st.session_state["aura_refresh_token"] = refresh_token() + 1


# ======================================================================
# Model
# ======================================================================


@st.cache_resource(show_spinner=False)
def _train_model() -> Any:
    """
    Build the detection model once per server process.

    ``cache_resource`` (not ``cache_data``) because the fitted estimators are
    stateful objects that must be shared, not copied.
    """
    baseline = aura_core.get_or_create_baseline()
    return aura_core.train_aura_model(baseline)


def load_model_or_stop() -> Any:
    """
    Return the trained model, or halt the page with an actionable message.

    Halting is correct here: with no model there is no detection, and inventing
    a fallback "everything is fine" state would be exactly the kind of
    fabrication this application must not do.
    """
    try:
        return _train_model()
    except Exception as exc:  # noqa: BLE001 - surfaced to the operator verbatim
        st.error(
            "AURA could not build its detection model, so no analysis can be "
            f"performed.\n\nUnderlying error: `{exc}`"
        )
        st.caption(
            "Most common cause: the behavioural baseline has not been "
            "collected yet, or data\\baseline.csv holds fewer than the "
            "minimum number of samples the model requires."
        )
        st.stop()


def reset_model_cache() -> None:
    """Drop the cached model so the next read retrains from the baseline."""
    _train_model.clear()


def model_summary(model: Any) -> dict[str, Any]:
    """
    Describe the model for display, without asserting anything unmeasured.

    Note the deliberate absence of an accuracy figure. AURA trains
    unsupervised detectors on a single machine's own baseline and has no
    labelled ground truth, so no accuracy, precision or recall has been
    measured. Reporting one would be an invention.
    """
    info: dict[str, Any] = {}
    try:
        # `get_model_info` is a module-level function taking the model, not a
        # method on it. Calling `model.get_model_info()` raises AttributeError,
        # and because the failure is swallowed below, every figure would
        # silently fall back to zero — a fabricated "0 training samples" in
        # place of the real count.
        raw = ml_model.get_model_info(model)
        if isinstance(raw, dict):
            info = raw
    except Exception:  # noqa: BLE001 - a display path must not raise
        info = {}

    # Fall back to the dataclass's own attributes if the helper was
    # unavailable, so a real value is preferred over a zero placeholder.
    if not info:
        info = {
            "status": "READY" if model is not None else "UNKNOWN",
            "algorithms": ["Isolation Forest", "Local Outlier Factor"],
            "features": list(getattr(model, "feature_names", ()) or ()),
            "training_samples": getattr(model, "training_samples", None),
            "contamination": getattr(model, "contamination", None),
            "lof_neighbors": getattr(model, "lof_neighbors", None),
            "isolation_trees": getattr(ml_model, "ISOLATION_TREES", None),
        }

    algorithms = info.get("algorithms")
    if not isinstance(algorithms, list) or not algorithms:
        algorithms = ["Isolation Forest", "Local Outlier Factor"]

    features = info.get("features")
    if not isinstance(features, list) or not features:
        features = []

    def _int_or_none(value: Any) -> int | None:
        """Preserve the difference between a real 0 and 'not established'."""
        return None if value is None else safe_int(value, 0)

    def _float_or_none(value: Any) -> float | None:
        return None if value is None else safe_float(value, 0.0)

    return {
        "status": safe_text(info.get("status"), "UNKNOWN"),
        "algorithms": [safe_text(item) for item in algorithms],
        "features": [safe_text(item) for item in features],
        "training_samples": _int_or_none(info.get("training_samples")),
        "contamination": _float_or_none(info.get("contamination")),
        "lof_neighbors": _int_or_none(info.get("lof_neighbors")),
        "isolation_trees": _int_or_none(info.get("isolation_trees")),
        # Stated explicitly so no page is tempted to fill the gap.
        "accuracy": "Not measured",
        "accuracy_reason": (
            "AURA's detectors are unsupervised and are fitted to this "
            "machine's own baseline. No labelled attack data exists for this "
            "deployment, so no accuracy, precision or recall has been "
            "computed. A percentage here would be fabricated."
        ),
    }


def _first_present(source: dict, *keys: str) -> Any:
    """
    Return the first key that is actually present, trying each in order.

    The live scan result and the stored log row disagree on casing. A result
    from ``aura_core.scan_once`` spreads ``**ml_result`` verbatim, so it carries
    the model's own *lowercase* keys (``if_anomaly``, ``if_score``). The CSV
    written by ``logger.append_log`` uses *title-case* column names
    (``IF_Anomaly``, ``IF_Score``). Reading only one casing silently loses the
    signal for the other source, which is exactly the failure mode this helper
    exists to prevent, so both are accepted.
    """
    for key in keys:
        if key in source and source[key] is not None:
            return source[key]
    return None


def ensemble_agreement(result: Any) -> dict[str, Any]:
    """
    Describe how the two detectors voted, in plain language.

    This deliberately replaces the stored ``Anomaly_Confidence`` /
    ``*_Anomaly_Intensity`` fields on screen. Those are derived from
    ``min(abs(score) * 100, 100)``, which runs *backwards* for Isolation
    Forest — a more normal observation yields a higher "intensity" — and the
    confidence value itself is only ever 0, 60 or 100, i.e. a restatement of
    how many detectors fired. Presenting that as a probability would be
    misleading, so the vote is reported as a vote and the raw decision
    function scores are shown beside it.

    Both key casings are read (see ``_first_present``): the live result carries
    the model's lowercase keys, a replayed log row carries the CSV's title-case
    columns.
    """
    if not isinstance(result, dict):
        return {
            "if_fired": False,
            "lof_fired": False,
            "agreement": "UNKNOWN",
            "label": "No detection run yet",
            "detail": "Run a scan to evaluate the current system state.",
            "if_score": None,
            "lof_score": None,
        }

    if_fired = bool(safe_int(_first_present(result, "if_anomaly", "IF_Anomaly"), 0))
    lof_fired = bool(
        safe_int(_first_present(result, "lof_anomaly", "LOF_Anomaly"), 0)
    )

    if if_fired and lof_fired:
        agreement, label = "BOTH", "Both detectors flagged this observation"
        detail = (
            "Isolation Forest and Local Outlier Factor independently placed "
            "this sample outside the learned baseline. Agreement between two "
            "different algorithms is the strongest signal AURA produces."
        )
    elif if_fired or lof_fired:
        which = "Isolation Forest" if if_fired else "Local Outlier Factor"
        agreement, label = "ONE", f"One detector flagged this ({which})"
        detail = (
            f"{which} placed this sample outside the baseline; the other "
            "detector did not. Single-detector disagreement is common near "
            "the edge of normal behaviour and is not by itself evidence of "
            "an intrusion."
        )
    else:
        agreement, label = "NONE", "Neither detector flagged this observation"
        detail = (
            "Both detectors placed this sample inside the learned baseline "
            "for this machine."
        )

    return {
        "if_fired": if_fired,
        "lof_fired": lof_fired,
        "agreement": agreement,
        "label": label,
        "detail": detail,
        "if_score": _first_present(result, "if_score", "IF_Score"),
        "lof_score": _first_present(result, "lof_score", "LOF_Score"),
    }


# ======================================================================
# Event log
# ======================================================================


def log_file_present() -> bool:
    """True when the historical event log exists and is non-empty."""
    try:
        return os.path.isfile(aura_logger.LOG_FILE) and (
            os.path.getsize(aura_logger.LOG_FILE) > 0
        )
    except OSError:
        return False


def _log_signature() -> tuple[int, int]:
    """
    Cheap fingerprint of the log file: (modification time, size).

    Used as the cache key. A new appended scan changes both, so the cache
    invalidates itself without any manual bookkeeping, and repeated widget
    interactions inside one scan cycle re-read nothing.
    """
    try:
        stat = os.stat(aura_logger.LOG_FILE)
    except OSError:
        return (0, 0)
    return (int(stat.st_mtime_ns), int(stat.st_size))


@st.cache_data(show_spinner=False)
def _read_logs(signature: tuple[int, int]) -> pd.DataFrame:
    """Read the log exactly once per distinct file state."""
    # `signature` is unused inside the body on purpose: its only job is to be
    # part of the cache key.
    del signature
    try:
        frame = aura_logger.load_logs()
    except Exception:  # noqa: BLE001 - an unreadable log must not crash the UI
        return pd.DataFrame()
    if not isinstance(frame, pd.DataFrame):
        return pd.DataFrame()
    return frame


def load_event_log() -> pd.DataFrame:
    """
    Return the historical event log as a DataFrame.

    Always a copy, so a page that adds a derived column cannot corrupt the
    cached object shared with every other page.
    """
    frame = _read_logs(_log_signature())
    if frame.empty:
        return frame
    return frame.copy()


def latest_row(frame: pd.DataFrame) -> pd.Series | None:
    """Return the most recent log row, or None when there is no history."""
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    return frame.iloc[-1]


def numeric_column(frame: pd.DataFrame, column: str) -> pd.Series:
    """
    Return one column coerced to numeric, with unparseable values dropped.

    Dropping rather than zero-filling matters: a blank cell in an old schema
    generation is *missing*, and averaging it as zero would drag every
    historical statistic downwards.
    """
    if not isinstance(frame, pd.DataFrame) or column not in frame.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").dropna()


def trend_frame(
    frame: pd.DataFrame,
    columns: list[str],
    limit: int = 200,
) -> pd.DataFrame:
    """
    Build a time-indexed frame for charting.

    Returns an empty frame when none of the requested columns hold usable
    numbers, which lets the caller render an explicit "insufficient history"
    state instead of an empty axis that looks like a broken chart.
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame()

    available = [name for name in columns if name in frame.columns]
    if not available:
        return pd.DataFrame()

    recent = frame.tail(max(limit, 2)).copy()

    numeric = pd.DataFrame(index=recent.index)
    for name in available:
        series = pd.to_numeric(recent[name], errors="coerce")
        if series.notna().any():
            numeric[name] = series

    if numeric.empty or numeric.columns.empty:
        return pd.DataFrame()

    if "Timestamp" in recent.columns:
        stamps = pd.to_datetime(recent["Timestamp"], errors="coerce")
        if stamps.notna().sum() >= 2:
            numeric.index = stamps
            numeric.index.name = "Time"
            numeric = numeric[stamps.notna().to_numpy()]

    return numeric.dropna(how="all")


# ======================================================================
# Live telemetry
# ======================================================================
#
# Short-lived caches serve a second purpose beyond speed. The disk and network
# sensors report *rates*, computed from the delta between consecutive counter
# readings. Streamlit re-runs the script on every interaction, so uncached
# readings could be milliseconds apart, dividing a tiny byte delta by a tiny
# elapsed time and producing meaningless spikes. Spacing the reads out by a
# few seconds makes the reported rates meaningful as well as cheap.

_LIVE_TTL = 5.0


@st.cache_data(show_spinner=False, ttl=_LIVE_TTL)
def _snapshot(token: int, probe_camera: bool) -> dict[str, Any]:
    del token
    try:
        return sensors.get_full_sensor_snapshot(probe_camera=probe_camera)
    except Exception:  # noqa: BLE001 - reported through derive_sensor_health
        return {}


def live_snapshot(probe_camera: bool = False) -> dict[str, Any]:
    """Return a full sensor snapshot, cached for a few seconds."""
    snapshot = _snapshot(refresh_token(), bool(probe_camera))
    return snapshot if isinstance(snapshot, dict) else {}


@st.cache_data(show_spinner=False, ttl=_LIVE_TTL)
def _processes(token: int) -> dict[str, Any]:
    del token
    try:
        return privacy_monitor.get_process_snapshot()
    except Exception:  # noqa: BLE001 - absence is reported, not guessed
        return {}


def live_processes() -> dict[str, Any]:
    """
    Return the current process snapshot.

    ``process_names`` arrives as a set, which is not JSON- or table-friendly,
    so it is normalised to a sorted list here.
    """
    raw = _processes(refresh_token())
    if not isinstance(raw, dict):
        return {}
    data = dict(raw)
    names = data.get("process_names")
    if isinstance(names, set):
        data["process_names"] = sorted(names)
    return data


@st.cache_data(show_spinner=False, ttl=_LIVE_TTL)
def _connections(token: int) -> dict[str, Any]:
    del token
    try:
        return privacy_monitor.get_connection_snapshot()
    except Exception:  # noqa: BLE001 - absence is reported, not guessed
        return {}


def live_connections() -> dict[str, Any]:
    """Return the current network connection snapshot."""
    raw = _connections(refresh_token())
    return dict(raw) if isinstance(raw, dict) else {}


def camera_dependency_present() -> bool:
    """
    True when the OpenCV dependency the camera probe needs is importable.

    Checked through the sensors module rather than by importing cv2 here, so
    the UI observes exactly what the sensor observes.
    """
    return getattr(sensors, "cv2", None) is not None


# ======================================================================
# Honest sensor health
# ======================================================================
#
# The backend's own get_sensor_health() only tests whether each key exists in
# the snapshot. Because every getter returns a dictionary even on failure --
# a zero-filled one -- that check always passes and health is always reported
# as 100%. It is structurally incapable of reporting a problem.
#
# Rather than change the backend before a submission deadline, the UI derives
# status from whether each value is *physically plausible*. The reasoning for
# each rule is written next to it, because a health check nobody can justify
# is just another number to distrust.


def _status(name: str, status: str, detail: str, value: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail, "value": value}


def derive_sensor_health(
    snapshot: dict[str, Any],
    probe_camera: bool = False,
    connections: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """
    Assess each sensor from the plausibility of what it returned.

    Returns one record per sensor with ``name``, ``status``, ``detail`` and a
    display ``value``. Statuses are HEALTHY, DEGRADED, PERMISSION_LIMITED,
    UNAVAILABLE, NOT_PRESENT, NOT_PROBED and PRIMING.
    """
    if not isinstance(snapshot, dict) or not snapshot:
        return [
            _status(
                "Sensor subsystem",
                "UNAVAILABLE",
                "The telemetry collector returned no data at all. On Windows "
                "this usually means psutil could not be imported or the "
                "process lacks permission to query the system.",
                UNKNOWN,
            )
        ]

    records: list[dict[str, str]] = []

    # --- CPU ---------------------------------------------------------
    # A real machine always reports at least one logical core. Zero means
    # psutil.cpu_count() raised and the zero-filled fallback was returned.
    cpu = snapshot.get("cpu") or {}
    logical = safe_int(cpu.get("logical_cores"), 0)
    if logical <= 0:
        records.append(
            _status(
                "CPU",
                "UNAVAILABLE",
                "Reported zero logical cores, which no running system does. "
                "The CPU probe failed and returned its zero-filled fallback.",
                UNKNOWN,
            )
        )
    else:
        usage = safe_float(cpu.get("usage_percent"), 0.0)
        records.append(
            _status(
                "CPU",
                "HEALTHY",
                f"{logical} logical cores visible; utilisation sampled over "
                "a 0.2 second interval.",
                f"{usage:.1f}%",
            )
        )

    # --- Memory ------------------------------------------------------
    # Total physical memory is a constant of the machine and cannot be zero.
    memory = snapshot.get("memory") or {}
    total_gb = safe_float(memory.get("total_gb"), 0.0)
    if total_gb <= 0.0:
        records.append(
            _status(
                "Memory",
                "UNAVAILABLE",
                "Reported zero total physical memory. This is a failed probe, "
                "not an idle system.",
                UNKNOWN,
            )
        )
    else:
        records.append(
            _status(
                "Memory",
                "HEALTHY",
                f"{total_gb:.1f} GB total physical memory visible.",
                f"{safe_float(memory.get('usage_percent'), 0.0):.1f}%",
            )
        )

    # --- Disk --------------------------------------------------------
    # The monitored volume is fixed at C:\ by the backend. Zero capacity means
    # the path could not be queried.
    disk = snapshot.get("disk") or {}
    disk_total = safe_float(disk.get("total_gb"), 0.0)
    disk_path = safe_text(disk.get("path"), "C:\\")
    if disk_total <= 0.0:
        records.append(
            _status(
                "Disk capacity",
                "UNAVAILABLE",
                f"Could not read capacity for {disk_path}. The volume may be "
                "missing, or access may be denied.",
                UNKNOWN,
            )
        )
    else:
        records.append(
            _status(
                "Disk capacity",
                "HEALTHY",
                f"{disk_path} reports {disk_total:.1f} GB total capacity.",
                f"{safe_float(disk.get('usage_percent'), 0.0):.1f}%",
            )
        )

    # --- Disk I/O ----------------------------------------------------
    # Rates are deltas between counter reads. The first read of the process
    # has no previous value to subtract, so it legitimately returns 0.00 --
    # which is why an idle result is labelled as indistinguishable rather than
    # asserted to be zero activity.
    disk_io = snapshot.get("disk_io") or {}
    read_mbps = safe_float(disk_io.get("read_mbps"), 0.0)
    write_mbps = safe_float(disk_io.get("write_mbps"), 0.0)
    if disk_total <= 0.0:
        records.append(
            _status(
                "Disk I/O",
                "UNAVAILABLE",
                "The disk subsystem is not reporting, so throughput cannot "
                "be measured.",
                UNKNOWN,
            )
        )
    elif read_mbps == 0.0 and write_mbps == 0.0:
        records.append(
            _status(
                "Disk I/O",
                "PRIMING",
                "Throughput is measured between two counter readings. A "
                "0.00 MB/s result is what both a genuinely idle disk and the "
                "very first reading look like; these cannot be distinguished "
                "from a single sample.",
                "0.00 MB/s",
            )
        )
    else:
        records.append(
            _status(
                "Disk I/O",
                "HEALTHY",
                "Throughput derived from consecutive counter readings.",
                f"{read_mbps + write_mbps:.2f} MB/s",
            )
        )

    # --- Network -----------------------------------------------------
    # bytes_sent/bytes_received are cumulative since boot. Both being exactly
    # zero on a booted machine indicates the counters were never read, which
    # is a much stronger signal than the instantaneous rate.
    network = snapshot.get("network") or {}
    sent = safe_int(network.get("bytes_sent"), 0)
    received = safe_int(network.get("bytes_received"), 0)
    interfaces = network.get("active_interfaces")
    interface_count = len(interfaces) if isinstance(interfaces, list) else 0
    down_kbps = safe_float(network.get("download_kbps"), 0.0)
    up_kbps = safe_float(network.get("upload_kbps"), 0.0)

    if sent == 0 and received == 0:
        records.append(
            _status(
                "Network counters",
                "UNAVAILABLE",
                "Cumulative byte counters read zero in both directions. On a "
                "booted machine that indicates the counters could not be "
                "read, not that no traffic has occurred.",
                UNKNOWN,
            )
        )
    elif interface_count == 0:
        records.append(
            _status(
                "Network counters",
                "DEGRADED",
                "Traffic counters are readable but no interface reports as "
                "up. Interface enumeration may be restricted.",
                f"{down_kbps + up_kbps:.1f} KB/s",
            )
        )
    else:
        records.append(
            _status(
                "Network counters",
                "HEALTHY",
                f"{interface_count} active interface(s); rates derived from "
                "consecutive counter readings.",
                f"{down_kbps + up_kbps:.1f} KB/s",
            )
        )

    # --- Processes ---------------------------------------------------
    process_count = safe_int(snapshot.get("process_count"), 0)
    if process_count <= 0:
        records.append(
            _status(
                "Process table",
                "UNAVAILABLE",
                "Zero processes enumerated. AURA itself is a process, so a "
                "zero count means enumeration failed.",
                UNKNOWN,
            )
        )
    else:
        records.append(
            _status(
                "Process table",
                "HEALTHY",
                f"{process_count} processes enumerated.",
                f"{process_count:,}",
            )
        )

    # --- Connections -------------------------------------------------
    # psutil.net_connections() raises AccessDenied for sockets owned by other
    # users unless the process is elevated. The backend swallows that and
    # returns an empty list, so an empty result is reported as a permission
    # limit rather than as "no connections".
    if connections is not None:
        connection_count = safe_int(connections.get("connection_count"), 0)
        if connection_count <= 0:
            records.append(
                _status(
                    "Socket table",
                    "PERMISSION_LIMITED",
                    "No sockets were returned. Windows withholds connection "
                    "details for processes owned by other users unless AURA "
                    "runs elevated, so this is a visibility limit rather "
                    "than proof of an idle network.",
                    UNKNOWN,
                )
            )
        else:
            records.append(
                _status(
                    "Socket table",
                    "HEALTHY",
                    f"{connection_count} sockets visible to this process. "
                    "Sockets owned by other users may still be hidden "
                    "without elevation.",
                    f"{connection_count:,}",
                )
            )

    # --- Battery -----------------------------------------------------
    # An absent battery is a fact about the hardware, not a fault, so it is
    # NOT_PRESENT and must not count against overall health.
    battery = snapshot.get("battery") or {}
    battery_status = safe_text(battery.get("status"), "NOT_AVAILABLE")
    if not battery.get("available") or battery_status == "NOT_AVAILABLE":
        records.append(
            _status(
                "Battery",
                "NOT_PRESENT",
                "No battery is exposed by this system, which is expected on "
                "a desktop or virtual machine.",
                UNKNOWN,
            )
        )
    else:
        records.append(
            _status(
                "Battery",
                "HEALTHY",
                f"Power state: {battery_status.replace('_', ' ').lower()}.",
                f"{safe_float(battery.get('percent'), 0.0):.0f}%",
            )
        )

    # --- Uptime ------------------------------------------------------
    uptime = snapshot.get("uptime") or {}
    uptime_seconds = safe_int(uptime.get("uptime_seconds"), 0)
    uptime_text = safe_text(uptime.get("uptime_text"), "UNKNOWN")
    if uptime_seconds <= 0 or uptime_text == "UNKNOWN":
        records.append(
            _status(
                "System uptime",
                "UNAVAILABLE",
                "Boot time could not be read.",
                UNKNOWN,
            )
        )
    else:
        records.append(
            _status(
                "System uptime",
                "HEALTHY",
                "Derived from the system boot timestamp.",
                uptime_text,
            )
        )

    # --- Camera ------------------------------------------------------
    # Opt-in, off by default, and honest about what the probe can and cannot
    # establish. Opening a device proves it is openable; it proves nothing
    # about whether anything else is using it.
    camera_value = snapshot.get("camera_available")
    if not probe_camera:
        records.append(
            _status(
                "Camera probe",
                "NOT_PROBED",
                "Disabled by default. AURA does not open the camera unless "
                "you explicitly enable the probe, and it never captures, "
                "stores or transmits an image.",
                "Off",
            )
        )
    elif not camera_dependency_present():
        records.append(
            _status(
                "Camera probe",
                "UNAVAILABLE",
                "The probe is enabled but OpenCV (opencv-python) is not "
                "importable, so the device cannot be tested.",
                UNKNOWN,
            )
        )
    elif safe_int(camera_value, 0) == 1:
        records.append(
            _status(
                "Camera probe",
                "HEALTHY",
                "A default camera device was openable at probe time. This "
                "shows the device exists and is not exclusively held; it is "
                "not evidence of unauthorised access.",
                "Openable",
            )
        )
    else:
        records.append(
            _status(
                "Camera probe",
                "NOT_PRESENT",
                "No default camera could be opened. Either no camera is "
                "fitted, or another application currently holds it. These "
                "two cases are indistinguishable to this probe.",
                "Not openable",
            )
        )

    return records


# Statuses that represent a genuine fault, as opposed to hardware that simply
# is not fitted or a probe that was deliberately left switched off.
_FAULT_STATUSES = {"UNAVAILABLE", "DEGRADED"}
_EXCLUDED_FROM_ROLLUP = {"NOT_PRESENT", "NOT_PROBED"}


def health_rollup(records: list[dict[str, str]]) -> dict[str, Any]:
    """
    Summarise sensor records into one overall status.

    Sensors that are absent by design (no battery) or off by design (the
    camera probe) are excluded from the denominator, because counting them as
    failures would understate health just as counting them as successes would
    overstate it.
    """
    assessed = [
        record
        for record in records
        if record.get("status") not in _EXCLUDED_FROM_ROLLUP
    ]
    total = len(assessed)
    faults = [
        record
        for record in assessed
        if record.get("status") in _FAULT_STATUSES
    ]
    limited = [
        record
        for record in assessed
        if record.get("status") == "PERMISSION_LIMITED"
    ]
    healthy = total - len(faults) - len(limited)

    if total == 0:
        status = "UNAVAILABLE"
    elif faults:
        status = "UNAVAILABLE" if len(faults) >= total / 2 else "DEGRADED"
    elif limited:
        status = "PERMISSION_LIMITED"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "assessed": total,
        "healthy": healthy,
        "faults": len(faults),
        "limited": len(limited),
        "percent": (healthy / total * 100.0) if total else 0.0,
        "fault_names": [safe_text(r.get("name")) for r in faults],
        "limited_names": [safe_text(r.get("name")) for r in limited],
    }


# ======================================================================
# Session state
# ======================================================================
#
# These key names match the ones the previous interface used, so a scan
# performed before this build was applied is still readable and nothing about
# the scan lifecycle changes.


def get_latest_result() -> dict[str, Any] | None:
    """Return the most recent scan result held in this session."""
    result = st.session_state.get("latest_result")
    return result if isinstance(result, dict) else None


def get_last_scan_time() -> datetime | None:
    """Return when the most recent scan in this session completed."""
    moment = st.session_state.get("last_scan_time")
    return moment if isinstance(moment, datetime) else None


def result_is_demo(result: dict[str, Any] | None = None) -> bool:
    """
    True when the current result came from the demonstration generator.

    Checked from two independent places -- the scan source recorded in session
    state and the ``Is_Demo`` flag the backend sets on the result itself -- so
    a demonstration result cannot be presented as live telemetry by accident.
    """
    if safe_text(st.session_state.get("latest_scan_source")) == (
        "SAFE_DEMONSTRATION"
    ):
        return True
    target = result if result is not None else get_latest_result()
    if isinstance(target, dict):
        return bool(target.get("Is_Demo", False))
    return False
