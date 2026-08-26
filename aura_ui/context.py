"""
The object every page receives.

Assembled once per script run by ``app.py`` and passed to whichever page is
active. Bundling it has two benefits: a page cannot accidentally trigger a
second expensive telemetry read that a sibling page already performed, and the
sidebar and the page body are guaranteed to be describing the same instant
rather than two readings a few hundred milliseconds apart.

That second point matters more than it sounds. If the sidebar sampled CPU
separately from the System Monitor page, the two would disagree, and a
monitoring tool that contradicts itself on screen is not trusted again.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

__all__ = ["Context"]


@dataclass
class Context:
    """Everything a page needs, gathered once per run."""

    #: The trained detection model.
    model: Any = None

    #: Whether the operator has opted in to the camera probe this session.
    probe_camera: bool = False

    #: The most recent scan result, or None if no scan has run yet.
    result: dict[str, Any] | None = None

    #: True when :attr:`result` came from the demonstration generator.
    is_demo: bool = False

    #: When :attr:`result` was produced.
    scan_time: datetime | None = None

    #: Historical event log. Empty frame when there is no history yet.
    logs: pd.DataFrame = field(default_factory=pd.DataFrame)

    #: Raw sensor snapshot for the current instant.
    snapshot: dict[str, Any] = field(default_factory=dict)

    #: Current process snapshot.
    processes: dict[str, Any] = field(default_factory=dict)

    #: Current socket snapshot.
    connections: dict[str, Any] = field(default_factory=dict)

    #: Per-sensor honest status records, from ``core.derive_sensor_health``.
    health: list[dict[str, str]] = field(default_factory=list)

    #: Aggregate view of :attr:`health`, from ``core.health_rollup``.
    rollup: dict[str, Any] = field(default_factory=dict)

    @property
    def has_result(self) -> bool:
        """True when a scan has been run in this session."""
        return isinstance(self.result, dict) and bool(self.result)

    @property
    def has_history(self) -> bool:
        """True when the monitoring log holds at least one stored event."""
        return isinstance(self.logs, pd.DataFrame) and not self.logs.empty

    @property
    def history_rows(self) -> int:
        """Number of stored events available for analysis."""
        if not isinstance(self.logs, pd.DataFrame):
            return 0
        return int(len(self.logs))
