"""
Logging configuration for AURA.

Replaces the current situation in which diagnostics are emitted via ``print``
and Streamlit warnings, leaving nothing on disk to investigate after an
incident (audit finding F16). A security tool that cannot explain what it did
an hour ago is not usable as a security tool.

What this provides:

  * one configuration point, :func:`configure_logging`, idempotent so it can be
    called from the Streamlit app, the FastAPI backend and the test suite
    without stacking duplicate handlers
  * a rotating file handler under the user-data directory, so logs survive
    process exit and cannot fill the disk
  * a console handler on **stderr** — deliberately not stdout, because
    Streamlit captures stdout and would render log lines into the page
  * structured JSON output when enabled, plain text otherwise
  * redaction attached at handler level, so third-party log output is covered
    too
  * a correlation id on every record, so the lines belonging to one scan can
    be reconstructed from a busy log

Failure policy: if the log file cannot be opened, AURA logs a warning to the
console and continues with console-only logging. Refusing to start because a
log file is unavailable would be a worse outcome than degraded logging, but
degrading silently would be worse still — so the degradation is announced.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from aura.core.config import Settings, get_settings
from aura.core.paths import AuraPaths, get_paths
from aura.core.redaction import install_redaction

__all__ = [
    "configure_logging",
    "get_logger",
    "correlation_id",
    "new_correlation_id",
    "correlation_scope",
    "LoggingState",
    "logging_state",
]

# ----------------------------------------------------------------------
# Correlation id
# ----------------------------------------------------------------------
# A ContextVar rather than a thread local, so the value survives across
# ``await`` boundaries in the future async collector as well as across threads.

_correlation_id: ContextVar[str] = ContextVar("aura_correlation_id", default="-")

_HANDLER_MARKER = "_aura_managed"
_configure_lock = threading.Lock()


def correlation_id() -> str:
    """Return the correlation id for the current context."""
    return _correlation_id.get()


def new_correlation_id(prefix: str = "") -> str:
    """Generate and install a fresh correlation id for the current context."""
    token = uuid.uuid4().hex[:12]
    value = f"{prefix}-{token}" if prefix else token
    _correlation_id.set(value)
    return value


@contextmanager
def correlation_scope(prefix: str = "") -> Iterator[str]:
    """
    Bind a correlation id for the duration of a block, then restore.

    Wrap each telemetry scan in one of these and every log line produced by
    that scan becomes greppable by a single value.
    """
    token_value = uuid.uuid4().hex[:12]
    value = f"{prefix}-{token_value}" if prefix else token_value
    reset_token = _correlation_id.set(value)
    try:
        yield value
    finally:
        _correlation_id.reset(reset_token)


class CorrelationFilter(logging.Filter):
    """Injects ``correlation_id`` onto every record so formatters can use it."""

    # `filter` is the stdlib logging.Filter API name; it is not ours to rename.
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = _correlation_id.get()
        return True


# ----------------------------------------------------------------------
# Formatters
# ----------------------------------------------------------------------

# Attributes present on every LogRecord. Anything outside this set was added
# by the caller via ``extra=`` and is therefore worth emitting.
_STANDARD_RECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class JsonFormatter(logging.Formatter):
    """
    One JSON object per line.

    Chosen over a multi-line pretty format because log shipping, ``jq`` and
    every log aggregator expect line-delimited JSON. Serialisation failures
    fall back to a minimal object rather than raising, since a formatter that
    throws loses the record entirely.
    """

    def __init__(self, *, app_name: str = "AURA", version: str = "") -> None:
        super().__init__()
        self.app_name = app_name
        self.version = version

    # `format` is the stdlib logging.Formatter API name.
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.threadName,
            "app": self.app_name,
        }
        if self.version:
            payload["version"] = self.version

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        elif record.exc_text:
            payload["exception"] = record.exc_text

        if record.stack_info:
            payload["stack"] = record.stack_info

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_ATTRS or key in payload:
                continue
            if key.startswith("_"):
                continue
            payload[key] = value

        try:
            return json.dumps(payload, default=str, ensure_ascii=False)
        except Exception:  # noqa: BLE001 - a formatter must not raise
            return json.dumps(
                {
                    "timestamp": payload["timestamp"],
                    "level": record.levelname,
                    "logger": record.name,
                    "message": "log record could not be serialised to JSON",
                }
            )


class ConsoleFormatter(logging.Formatter):
    """Compact, aligned, human-readable format for interactive use."""

    DEFAULT_FORMAT = (
        "%(asctime)s %(levelname)-8s [%(correlation_id)s] %(name)s: %(message)s"
    )

    def __init__(self) -> None:
        super().__init__(fmt=self.DEFAULT_FORMAT, datefmt="%H:%M:%S")


class FileFormatter(logging.Formatter):
    """Verbose plain-text format including the source location."""

    DEFAULT_FORMAT = (
        "%(asctime)s %(levelname)-8s [%(correlation_id)s] "
        "%(name)s %(module)s:%(lineno)d - %(message)s"
    )

    def __init__(self) -> None:
        super().__init__(fmt=self.DEFAULT_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

# Third-party loggers that are informative at DEBUG and pure noise at INFO.
_NOISY_LOGGERS = {
    "asyncio": logging.WARNING,
    "matplotlib": logging.WARNING,
    "PIL": logging.WARNING,
    "urllib3": logging.WARNING,
    "watchdog": logging.WARNING,
    "streamlit": logging.WARNING,
    "streamlit.runtime": logging.WARNING,
    "streamlit.runtime.scriptrunner": logging.WARNING,
    "streamlit.runtime.caching": logging.WARNING,
    "tornado": logging.WARNING,
    "sqlalchemy.engine": logging.WARNING,
    "uvicorn.access": logging.WARNING,
}


class LoggingState:
    """
    What logging configuration actually achieved.

    Returned by :func:`configure_logging` so callers — and
    ``scripts/aura_doctor.py`` in particular — can report the truth rather than
    assume success. ``file_error`` being populated is the honest signal that
    file logging is unavailable.
    """

    __slots__ = ("configured", "level", "log_file", "file_enabled", "console_enabled",
                 "json_format", "redaction_enabled", "file_error")

    def __init__(self) -> None:
        self.configured: bool = False
        self.level: str = "NOTSET"
        self.log_file: Path | None = None
        self.file_enabled: bool = False
        self.console_enabled: bool = False
        self.json_format: bool = False
        self.redaction_enabled: bool = False
        self.file_error: str | None = None

    def describe(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "level": self.level,
            "log_file": str(self.log_file) if self.log_file else None,
            "file_enabled": self.file_enabled,
            "console_enabled": self.console_enabled,
            "json_format": self.json_format,
            "redaction_enabled": self.redaction_enabled,
            "file_error": self.file_error,
        }


logging_state = LoggingState()


def _remove_managed_handlers(root: logging.Logger) -> None:
    """
    Remove only the handlers AURA installed.

    Handlers added by pytest's ``caplog``, by Streamlit or by an embedding
    application are left alone — tearing those down would break the host
    process's own logging.
    """
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:  # noqa: BLE001 - closing a broken handler is not fatal
                pass


def configure_logging(
    settings: Settings | None = None,
    paths: AuraPaths | None = None,
    *,
    force: bool = False,
) -> LoggingState:
    """
    Configure process-wide logging. Safe to call more than once.

    Subsequent calls return the existing state without rebuilding handlers,
    unless ``force=True``. This matters because Streamlit re-executes the whole
    script on every interaction — without the guard, handlers would accumulate
    and each log line would be written once per rerun.
    """
    global logging_state

    with _configure_lock:
        if logging_state.configured and not force:
            return logging_state

        resolved_settings = settings or get_settings()
        resolved_paths = paths or get_paths()
        log_config = resolved_settings.log

        state = LoggingState()
        state.level = log_config.level
        state.json_format = log_config.json_format
        state.redaction_enabled = log_config.redact_enabled

        level = getattr(logging, log_config.level, logging.INFO)

        root = logging.getLogger()
        _remove_managed_handlers(root)
        root.setLevel(level)

        correlation_filter = CorrelationFilter()

        # --------------------------------------------------------------
        # Console handler — stderr, never stdout.
        # --------------------------------------------------------------
        if log_config.console_enabled:
            console = logging.StreamHandler(stream=sys.stderr)
            console.setLevel(level)
            console.setFormatter(
                JsonFormatter(
                    app_name=resolved_settings.app_name,
                    version=resolved_settings.version,
                )
                if log_config.json_format
                else ConsoleFormatter()
            )
            console.addFilter(correlation_filter)
            install_redaction(
                console,
                enabled=log_config.redact_enabled,
                redact_user_paths=log_config.redact_user_paths,
            )
            setattr(console, _HANDLER_MARKER, True)
            root.addHandler(console)
            state.console_enabled = True

        # --------------------------------------------------------------
        # Rotating file handler.
        # --------------------------------------------------------------
        if log_config.file_enabled:
            log_file = resolved_paths.log_file
            state.log_file = log_file
            try:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.handlers.RotatingFileHandler(
                    filename=os.fspath(log_file),
                    maxBytes=log_config.max_bytes,
                    backupCount=log_config.backup_count,
                    encoding="utf-8",
                    delay=True,
                )
                file_handler.setLevel(level)
                file_handler.setFormatter(
                    JsonFormatter(
                        app_name=resolved_settings.app_name,
                        version=resolved_settings.version,
                    )
                    if log_config.json_format
                    else FileFormatter()
                )
                file_handler.addFilter(correlation_filter)
                install_redaction(
                    file_handler,
                    enabled=log_config.redact_enabled,
                    redact_user_paths=log_config.redact_user_paths,
                )
                setattr(file_handler, _HANDLER_MARKER, True)
                root.addHandler(file_handler)
                state.file_enabled = True
            except OSError as exc:
                # Announce the degradation. Silent console-only logging would
                # leave the user believing they have a log file to consult.
                state.file_error = f"{type(exc).__name__}: {exc}"

        for logger_name, logger_level in _NOISY_LOGGERS.items():
            logging.getLogger(logger_name).setLevel(max(logger_level, level))

        state.configured = True
        logging_state = state

    logger = logging.getLogger("aura.core.logging")
    if state.file_error:
        logger.warning(
            "File logging unavailable at %s (%s). Continuing with console "
            "logging only; nothing will be written to disk.",
            state.log_file,
            state.file_error,
        )
    logger.debug(
        "Logging configured: level=%s json=%s file=%s redaction=%s",
        state.level,
        state.json_format,
        state.log_file if state.file_enabled else "disabled",
        state.redaction_enabled,
    )
    return state


def get_logger(name: str) -> logging.Logger:
    """
    Return a namespaced logger.

    Does **not** configure logging as a side effect. Implicit configuration on
    first use would mean the settings in force depend on which module happened
    to import first; the entry point configures logging explicitly instead.
    """
    if not name.startswith("aura"):
        name = f"aura.{name}"
    return logging.getLogger(name)
