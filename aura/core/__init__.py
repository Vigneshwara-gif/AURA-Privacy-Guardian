"""
Core infrastructure for AURA: paths, configuration and logging.

Import order matters here. ``paths`` has no dependencies beyond the standard
library, ``config`` depends on ``paths``, and ``logging_config`` depends on
both. Nothing in this package imports from ``aura.sensors``,
``aura.detection`` or any other future subpackage, so it is always safe to
import.
"""

from __future__ import annotations

__all__ = [
    "paths",
    "config",
    "redaction",
    "logging_config",
]
