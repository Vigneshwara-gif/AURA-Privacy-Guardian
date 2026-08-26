"""
AURA presentation layer.

This package contains ONLY user-interface code. It reads from the existing
AURA backend (``sensors``, ``model``, ``logger``, ``privacy_monitor``,
``aura_core``) and never modifies it, so the detection engine, risk engine and
data pipeline behave exactly as they did before.

Layout:

    theme.py       colour language and the injected stylesheet
    components.py  reusable presentation primitives
    core.py        cached data access, honest sensor health, formatting
    pages/         one module per navigation destination

Nothing in here fabricates a measurement. Where a value cannot be derived from
real telemetry the UI says so explicitly rather than showing a plausible zero.
"""

from __future__ import annotations

UI_BUILD = "Submission Edition"

__all__ = ["UI_BUILD"]
