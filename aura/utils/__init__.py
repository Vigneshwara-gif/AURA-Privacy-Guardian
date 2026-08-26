"""
Shared, dependency-light utilities for AURA.

These exist to replace the three independent implementations of
``safe_float`` / ``safe_int`` / ``safe_text`` currently duplicated across
``app.py``, ``aura_core.py`` and ``logger.py`` (audit finding F18).

The duplicates are NOT removed in Phase 2 — that happens when each module is
migrated, so that the change can be verified one file at a time.
"""

from __future__ import annotations

from aura.utils.coercion import (
    clamp,
    safe_bool,
    safe_float,
    safe_int,
    safe_text,
    strip_control_characters,
)

__all__ = [
    "clamp",
    "safe_bool",
    "safe_float",
    "safe_int",
    "safe_text",
    "strip_control_characters",
]
