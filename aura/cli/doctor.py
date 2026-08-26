"""
AURA self-diagnostics.

Run this before anything else, and again after any configuration change:

    aura-doctor
    aura-doctor --verbose
    aura-doctor --json

It answers one question, honestly: does this installation actually work on this
machine? Nothing in AURA's foundation layer had ever been executed before this
command existed, so every claim about it was theoretical. This turns the
foundation into something that either passes or fails visibly.

What it checks, and what it deliberately does not:

  * Checks are *executed*, not asserted. The directory check really writes and
    deletes a file. The redaction check really pushes synthetic secrets through
    the filter and confirms they do not survive. The coercion check really
    evaluates the edge cases the legacy helpers get wrong.

  * Third-party packages are detected from installed distribution metadata and
    module specs, without importing them. Importing ``cv2`` is expensive and
    importing ``streamlit`` is slow, and neither tells us anything a spec
    lookup does not. Where a check reports on metadata rather than behaviour it
    says so.

  * Configuration values are *reported*, not validated against reality.
    ``camera_probe_enabled: false`` means the setting is off, not that a camera
    was tested. AURA must never imply it verified something it did not.

Exit status is 0 when no check failed, 1 when any check failed. Warnings do not
fail the run: a missing optional dependency is information, not a fault.

Output contains no secrets. Exception text produced by configuration errors is
passed through AURA's own redactor before display, because a malformed database
URL can otherwise echo a password straight back to the terminal.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import platform
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

__all__ = ["main", "run_checks", "Check"]

# Status labels. Text, never colour alone — a red dot is invisible to a
# colour-blind analyst and to a log file.
OK = "OK"
WARN = "WARN"
FAIL = "FAIL"
INFO = "INFO"

_MINIMUM_PYTHON = (3, 11)

# Distributions AURA cannot run without.
_REQUIRED: tuple[tuple[str, str], ...] = (
    ("pydantic", "pydantic"),
    ("pydantic-settings", "pydantic_settings"),
    ("psutil", "psutil"),
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("scikit-learn", "sklearn"),
    ("streamlit", "streamlit"),
)

# Distributions that unlock features. Absence is reported, never treated as an
# error, because AURA is required to degrade honestly rather than fail.
_OPTIONAL: tuple[tuple[str, str, str], ...] = (
    ("opencv-python", "cv2", "camera availability probe — install aura[camera]"),
    ("fastapi", "fastapi", "HTTP API — install aura[api]"),
    ("uvicorn", "uvicorn", "ASGI server — install aura[api]"),
    ("sqlalchemy", "sqlalchemy", "database persistence — install aura[api]"),
    ("pytest", "pytest", "test suite — install aura[dev]"),
)

# Synthetic secrets used to prove the redaction filter works. Every value is
# obviously fake and none is a credential for anything. The check asserts the
# marker string does NOT appear in the redacted output.
_REDACTION_PROBES: tuple[tuple[str, str, str], ...] = (
    (
        "key=value",
        "password=PLACEHOLDER-NOT-A-REAL-SECRET",
        "PLACEHOLDER-NOT-A-REAL-SECRET",
    ),
    (
        "authorization header",
        "Authorization: Bearer PLACEHOLDERTOKENVALUE",
        "PLACEHOLDERTOKENVALUE",
    ),
    (
        "database URL credentials",
        "postgresql://aura:PLACEHOLDERPASSWORD@localhost:5432/aura",
        "PLACEHOLDERPASSWORD",
    ),
    (
        "long hex blob",
        "session=0123456789abcdef0123456789abcdef",
        "0123456789abcdef0123456789abcdef",
    ),
)


@dataclass(slots=True)
class Check:
    """One executed diagnostic and its outcome."""

    name: str
    status: str
    detail: str
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "data": self.data,
        }


def _redact_for_display(text: str) -> str:
    """
    Scrub text before printing it.

    Used on exception messages. A pydantic validation error for a malformed
    ``database_url`` includes the offending value, which for a PostgreSQL DSN
    means a password. Routing it through AURA's own redactor also means the
    doctor exercises that code path on every run.
    """
    try:
        from aura.core.redaction import redact

        scrubbed = redact(text)
        return scrubbed if isinstance(scrubbed, str) else str(scrubbed)
    except Exception:  # noqa: BLE001 - diagnostics must not fail while reporting a failure
        return "<error text withheld: redaction unavailable>"


def _distribution_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None
    except Exception:  # noqa: BLE001 - broken metadata must not abort diagnostics
        return None


def _module_importable(module: str) -> bool:
    """
    Report whether a top-level module can be located.

    Uses ``find_spec``, which does not execute the module. That matters here:
    executing ``cv2`` is heavy and executing ``streamlit`` is slow, and neither
    is necessary to answer "is it installed".
    """
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False
    except Exception:  # noqa: BLE001
        return False


# ----------------------------------------------------------------------
# Checks
# ----------------------------------------------------------------------


def check_runtime() -> Check:
    """Python version and host platform."""
    version = sys.version_info
    data = {
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "is_windows": sys.platform == "win32",
        "in_virtualenv": sys.prefix != sys.base_prefix,
        "frozen": bool(getattr(sys, "frozen", False)),
    }

    if (version.major, version.minor) < _MINIMUM_PYTHON:
        return Check(
            "runtime",
            FAIL,
            f"Python {platform.python_version()} is below the required "
            f"{_MINIMUM_PYTHON[0]}.{_MINIMUM_PYTHON[1]}.",
            data,
        )

    if sys.platform != "win32":
        return Check(
            "runtime",
            WARN,
            f"Python {platform.python_version()} on {sys.platform}. AURA "
            f"collects Windows telemetry; on any other platform the sensor "
            f"layer reports this host, not a Windows host.",
            data,
        )

    if not data["in_virtualenv"]:
        return Check(
            "runtime",
            WARN,
            f"Python {platform.python_version()} on Windows, but not inside a "
            f"virtual environment. Installing into the system interpreter is "
            f"workable but makes dependency conflicts likely.",
            data,
        )

    return Check(
        "runtime",
        OK,
        f"Python {platform.python_version()} on Windows, virtual environment active.",
        data,
    )


def check_paths() -> Check:
    """Resolve the application paths and explain where they came from."""
    try:
        from aura.core.paths import get_paths

        paths = get_paths()
    except Exception as exc:  # noqa: BLE001
        return Check(
            "paths",
            FAIL,
            f"Path resolution failed: {type(exc).__name__}: "
            f"{_redact_for_display(str(exc))}",
        )

    return Check(
        "paths",
        OK,
        f"User data root: {paths.user_root} (source: {paths.user_root_origin}).",
        paths.describe(),
    )


def check_directories() -> Check:
    """
    Create the managed directories and prove each one is writable.

    A real write-then-delete, not a permission bit inspection. On Windows the
    permission model is complex enough that only an actual write is
    trustworthy, and an unwritable data directory is the single most common way
    a local tool fails silently.
    """
    try:
        from aura.core.paths import ensure_directories, get_paths

        paths = get_paths()
        ensure_directories(paths)
    except Exception as exc:  # noqa: BLE001
        return Check(
            "directories",
            FAIL,
            f"Could not create AURA directories: {type(exc).__name__}: "
            f"{_redact_for_display(str(exc))}",
        )

    probe_name = f".aura-write-probe-{os.getpid()}"
    unwritable: list[str] = []

    for directory in paths.managed_directories():
        probe = directory / probe_name
        try:
            probe.write_text("aura write probe", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            unwritable.append(f"{directory} ({exc.strerror or exc})")
        finally:
            if probe.exists():
                try:
                    probe.unlink()
                except OSError:
                    pass

    data = {
        "directories": [str(directory) for directory in paths.managed_directories()],
        "unwritable": unwritable,
    }

    if unwritable:
        return Check(
            "directories",
            FAIL,
            "Not writable: "
            + "; ".join(unwritable)
            + ". Set AURA_HOME to a writable location, or AURA_DEV_MODE=1 to "
            "keep data inside the project folder.",
            data,
        )

    count = len(data["directories"])
    return Check(
        "directories",
        OK,
        f"All {count} managed directories exist and are writable.",
        data,
    )


def check_settings() -> Check:
    """Load and validate configuration, then report a non-sensitive summary."""
    try:
        from aura.core.config import get_settings

        settings = get_settings()
    except Exception as exc:  # noqa: BLE001
        return Check(
            "settings",
            FAIL,
            f"Configuration is invalid: {type(exc).__name__}: "
            f"{_redact_for_display(str(exc))}",
        )

    try:
        summary = settings.summary()
    except Exception as exc:  # noqa: BLE001
        return Check(
            "settings",
            FAIL,
            f"Configuration loaded but could not be summarised: "
            f"{type(exc).__name__}: {_redact_for_display(str(exc))}",
        )

    return Check(
        "settings",
        OK,
        f"Configuration valid. environment={settings.environment}, "
        f"scoring_version={settings.risk.scoring_version}, "
        f"feature_schema_version={settings.detection.feature_schema_version}.",
        dict(summary),
    )


def check_logging() -> Check:
    """Configure logging and report what was actually achieved."""
    try:
        from aura.core.logging_config import configure_logging

        state = configure_logging()
    except Exception as exc:  # noqa: BLE001
        return Check(
            "logging",
            FAIL,
            f"Logging configuration failed: {type(exc).__name__}: "
            f"{_redact_for_display(str(exc))}",
        )

    data = state.describe()

    if state.file_error:
        return Check(
            "logging",
            WARN,
            f"Console logging active, but the log file at {state.log_file} "
            f"could not be opened ({state.file_error}). Nothing is being "
            f"written to disk.",
            data,
        )

    if not state.file_enabled:
        return Check(
            "logging",
            WARN,
            "File logging is disabled by configuration. After an incident "
            "there will be no log to consult.",
            data,
        )

    if not state.redaction_enabled:
        return Check(
            "logging",
            WARN,
            f"Log file {state.log_file} is active but redaction is DISABLED. "
            f"Credentials appearing in log output will be written to disk.",
            data,
        )

    return Check(
        "logging",
        OK,
        f"Level {state.level}, redaction on, writing to {state.log_file}.",
        data,
    )


def check_redaction() -> Check:
    """
    Push synthetic secrets through the redactor and confirm they do not survive.

    This is the check that matters most: redaction is the control standing
    between a debug log and a leaked credential, and a silently broken pattern
    would never be noticed otherwise.
    """
    try:
        from aura.core.redaction import Redactor
    except Exception as exc:  # noqa: BLE001
        return Check(
            "redaction",
            FAIL,
            f"Redaction module unavailable: {type(exc).__name__}: {exc}",
        )

    redactor = Redactor(enabled=True, redact_user_paths=True)
    leaked: list[str] = []
    results: dict[str, str] = {}

    for label, probe, marker in _REDACTION_PROBES:
        try:
            scrubbed = redactor.scrub_text(probe)
        except Exception as exc:  # noqa: BLE001
            leaked.append(f"{label} (raised {type(exc).__name__})")
            continue
        results[label] = scrubbed
        if marker in scrubbed:
            leaked.append(label)

    # Username inside a Windows path must be replaced, not removed.
    user_probe = r"C:\Users\PLACEHOLDERUSER\Documents\report.docx"
    user_scrubbed = redactor.scrub_text(user_probe)
    results["windows user path"] = user_scrubbed
    if "PLACEHOLDERUSER" in user_scrubbed:
        leaked.append("windows user path")
    elif "Documents" not in user_scrubbed:
        # Over-redaction is also a defect: the path must stay useful.
        leaked.append("windows user path (over-redacted, lost the path tail)")

    data = {"probes": results, "leaked": leaked}

    if leaked:
        return Check(
            "redaction",
            FAIL,
            "Redaction did not neutralise: " + "; ".join(leaked),
            data,
        )

    return Check(
        "redaction",
        OK,
        f"All {len(results)} redaction probes neutralised, paths preserved.",
        data,
    )


def check_coercion() -> Check:
    """
    Evaluate the coercion edge cases the legacy helpers get wrong.

    Each case corresponds to a real defect: ``int("12.0")`` raises, so
    ``logger._safe_int`` loses the value; ``bool("False")`` is ``True``, so a
    boolean round-tripped through CSV inverts; an infinite decision score would
    reach JSON as ``Infinity``, which is not valid JSON.
    """
    try:
        from aura.utils.coercion import safe_bool, safe_float, safe_int, safe_text
    except Exception as exc:  # noqa: BLE001
        return Check(
            "coercion",
            FAIL,
            f"Coercion module unavailable: {type(exc).__name__}: {exc}",
        )

    cases: tuple[tuple[str, Any, Any], ...] = (
        ('safe_int("12.0")', safe_int("12.0"), 12),
        ('safe_int("not a number", default=-1)', safe_int("not a number", default=-1), -1),
        ("safe_int(float('inf'))", safe_int(float("inf")), 0),
        ('safe_float("inf")', safe_float("inf"), 0.0),
        ("safe_float(float('nan'))", safe_float(float("nan")), 0.0),
        ('safe_bool("False")', safe_bool("False"), False),
        ('safe_bool("yes")', safe_bool("yes"), True),
        (
            "safe_text strips CRLF (log injection)",
            safe_text("chrome.exe\r\nFAKE LOG LINE"),
            "chrome.exeFAKE LOG LINE",
        ),
        (
            "safe_text strips bidi override",
            safe_text("invoice\u202egpj.exe"),
            "invoicegpj.exe",
        ),
    )

    failures = [
        f"{label}: got {actual!r}, expected {expected!r}"
        for label, actual, expected in cases
        if actual != expected
    ]

    data = {
        "cases": {label: repr(actual) for label, actual, _ in cases},
        "failures": failures,
    }

    if failures:
        return Check("coercion", FAIL, "; ".join(failures), data)

    return Check(
        "coercion",
        OK,
        f"All {len(cases)} coercion edge cases behave correctly.",
        data,
    )


def check_dependencies() -> Check:
    """Report installed distributions. Metadata and module specs only."""
    required: dict[str, str] = {}
    missing_required: list[str] = []

    for distribution, module in _REQUIRED:
        version = _distribution_version(distribution)
        importable = _module_importable(module)
        if version is None and not importable:
            missing_required.append(distribution)
        else:
            required[distribution] = version or "installed (version unknown)"

    optional: dict[str, str] = {}
    for distribution, module, purpose in _OPTIONAL:
        version = _distribution_version(distribution)
        importable = _module_importable(module)
        if version is None and not importable:
            optional[distribution] = f"not installed — {purpose}"
        else:
            optional[distribution] = version or "installed (version unknown)"

    data = {
        "required": required,
        "missing_required": missing_required,
        "optional": optional,
        "note": "Detected from distribution metadata and module specs; "
        "modules were not imported.",
    }

    if missing_required:
        return Check(
            "dependencies",
            FAIL,
            "Missing required packages: "
            + ", ".join(missing_required)
            + ". Run: python -m pip install -e .",
            data,
        )

    absent = [name for name, value in optional.items() if value.startswith("not installed")]
    if absent:
        return Check(
            "dependencies",
            OK,
            f"All {len(required)} required packages present. "
            f"Optional not installed: {', '.join(absent)}.",
            data,
        )

    return Check(
        "dependencies",
        OK,
        f"All {len(required)} required and {len(optional)} optional packages present.",
        data,
    )


def _count_lines(path: Path, limit_bytes: int = 64 * 1024 * 1024) -> int | None:
    """
    Count newlines in a file without parsing it.

    Deliberately not ``pandas.read_csv``: the point of this check is to report
    on the legacy file cheaply and without invoking the very code path that is
    suspected of being slow. The result is a line count, which for a CSV
    containing quoted newlines is an upper bound on the row count, not the row
    count itself — reported as such.
    """
    try:
        if path.stat().st_size > limit_bytes:
            return None
        count = 0
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                count += chunk.count(b"\n")
        return count
    except OSError:
        return None


def check_legacy_data() -> Check:
    """Report on the pre-migration CSV files. Read-only, no parsing."""
    try:
        from aura.core.paths import get_paths

        paths = get_paths()
    except Exception as exc:  # noqa: BLE001
        return Check(
            "legacy_data",
            FAIL,
            f"Path resolution failed: {type(exc).__name__}: {exc}",
        )

    data: dict[str, Any] = {}
    present: list[str] = []

    for label, path in (
        ("system_logs.csv", paths.legacy_log_csv),
        ("baseline.csv", paths.legacy_baseline_csv),
    ):
        if not path.exists():
            data[label] = {"exists": False, "path": str(path)}
            continue
        try:
            size = path.stat().st_size
        except OSError:
            size = -1
        lines = _count_lines(path)
        data[label] = {
            "exists": True,
            "path": str(path),
            "size_bytes": size,
            "line_count": lines,
            "line_count_note": "upper bound on row count; newlines inside "
            "quoted fields are counted",
        }
        present.append(f"{label} ({size} bytes, {lines} lines)")

    if not present:
        return Check(
            "legacy_data",
            INFO,
            "No legacy CSV data found. Nothing to import.",
            data,
        )

    return Check(
        "legacy_data",
        INFO,
        "Legacy data present: "
        + "; ".join(present)
        + ". These files are read-only to AURA and are imported, never "
        "written, once migration lands.",
        data,
    )


def check_privacy_posture() -> Check:
    """
    Report the settings that determine how much AURA collects about the user.

    This reports configuration, not observed behaviour. It is here so that a
    privacy-relevant default cannot be quietly changed without showing up in
    the first diagnostic anyone runs.
    """
    try:
        from aura.core.config import LOOPBACK_HOSTS, get_settings

        settings = get_settings()
    except Exception as exc:  # noqa: BLE001
        return Check(
            "privacy_posture",
            FAIL,
            f"Configuration unavailable: {type(exc).__name__}: "
            f"{_redact_for_display(str(exc))}",
        )

    data = {
        "environment": settings.environment,
        "demo_mode": settings.demo_mode,
        "camera_probe_enabled": settings.sensors.camera_probe_enabled,
        "retain_sensitive_file_paths": settings.sensors.retain_sensitive_file_paths,
        "api_host": settings.api.host,
        "api_allow_network_exposure": settings.api.allow_network_exposure,
        "log_redact_enabled": settings.log.redact_enabled,
        "log_redact_user_paths": settings.log.redact_user_paths,
        "note": "Configuration state only. No camera, network or filesystem "
        "probe was performed by this check.",
    }

    concerns: list[str] = []
    if settings.demo_mode:
        concerns.append(
            "demo_mode is ON — synthetic telemetry may be produced and must be "
            "labelled as simulated everywhere it appears"
        )
    if settings.sensors.camera_probe_enabled:
        concerns.append(
            "camera probe is ON — opening the camera powers the device on and "
            "lights its indicator; availability is not evidence of misuse"
        )
    if settings.sensors.retain_sensitive_file_paths:
        concerns.append(
            "sensitive file paths are RETAINED — the risk engine only needs "
            "the count, so this stores more than is required"
        )
    if settings.api.host not in LOOPBACK_HOSTS:
        concerns.append(
            f"api host {settings.api.host} is not loopback — telemetry would be "
            f"reachable from the network"
        )

    if concerns:
        return Check("privacy_posture", WARN, "; ".join(concerns), data)

    return Check(
        "privacy_posture",
        OK,
        "Data minimisation defaults in force: camera probe off, sensitive "
        "paths not retained, demo mode off, API loopback only, redaction on.",
        data,
    )


_CHECKS: tuple[Callable[[], Check], ...] = (
    check_runtime,
    check_paths,
    check_directories,
    check_settings,
    check_logging,
    check_redaction,
    check_coercion,
    check_dependencies,
    check_legacy_data,
    check_privacy_posture,
)


def run_checks() -> list[Check]:
    """
    Execute every diagnostic in order.

    A check that raises is converted into a FAIL rather than aborting the run,
    so one broken subsystem does not hide the state of the others.
    """
    results: list[Check] = []
    for check in _CHECKS:
        try:
            results.append(check())
        except Exception as exc:  # noqa: BLE001 - a diagnostic must always report
            results.append(
                Check(
                    getattr(check, "__name__", "unknown").removeprefix("check_"),
                    FAIL,
                    f"Diagnostic raised {type(exc).__name__}: "
                    f"{_redact_for_display(str(exc))}",
                )
            )
    return results


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------


def _render_text(checks: list[Check], *, verbose: bool) -> str:
    from aura import __version__

    lines: list[str] = [
        "AURA DIAGNOSTICS",
        f"version {__version__}  ·  {datetime.now(UTC).isoformat(timespec='seconds')}",
        "=" * 72,
        "",
    ]

    width = max(len(check.name) for check in checks)

    for check in checks:
        lines.append(f"[{check.status:<4}] {check.name:<{width}}  {check.detail}")
        if verbose and check.data:
            for key, value in check.data.items():
                if isinstance(value, dict):
                    lines.append(f"         {key}:")
                    for inner_key, inner_value in value.items():
                        lines.append(f"           {inner_key} = {inner_value}")
                elif isinstance(value, list):
                    rendered = ", ".join(str(item) for item in value) or "(none)"
                    lines.append(f"         {key} = {rendered}")
                else:
                    lines.append(f"         {key} = {value}")
        if verbose:
            lines.append("")

    failed = [check.name for check in checks if check.status == FAIL]
    warned = [check.name for check in checks if check.status == WARN]

    lines.extend(["", "=" * 72])

    if failed:
        lines.append(f"RESULT: FAIL — {len(failed)} check(s) failed: {', '.join(failed)}")
    elif warned:
        lines.append(
            f"RESULT: PASS WITH WARNINGS — review: {', '.join(warned)}"
        )
    else:
        lines.append("RESULT: PASS — every check succeeded.")

    lines.append(
        "This command verifies AURA's foundation layer only. It does not "
        "validate telemetry collection, detection accuracy or the risk engine."
    )
    return "\n".join(lines)


def _render_json(checks: list[Check]) -> str:
    from aura import __version__

    failed = [check.name for check in checks if check.status == FAIL]
    warned = [check.name for check in checks if check.status == WARN]
    payload = {
        "aura_version": __version__,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "result": FAIL if failed else (WARN if warned else OK),
        "failed": failed,
        "warned": warned,
        "scope": "foundation layer only: paths, configuration, logging, "
        "redaction, coercion, dependencies",
        "checks": [check.as_dict() for check in checks],
    }
    return json.dumps(payload, indent=2, default=str)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``aura-doctor`` console script."""
    parser = argparse.ArgumentParser(
        prog="aura-doctor",
        description=(
            "Verify that this AURA installation works: resolve paths, validate "
            "configuration, configure logging, and self-test redaction and "
            "coercion. Exits 1 if any check fails."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of text",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="include the full data payload for every check",
    )
    args = parser.parse_args(argv)

    checks = run_checks()

    if args.json:
        print(_render_json(checks))
    else:
        print(_render_text(checks, verbose=args.verbose))

    return 1 if any(check.status == FAIL for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
