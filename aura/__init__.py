"""
AURA — AI-Powered Real-Time Privacy Intelligence & Intrusion Detection System.

This package is the importable core of AURA. It deliberately contains no
Streamlit, FastAPI or React specific code so that it can be consumed by:

  * the existing Streamlit application (``app.py`` at the repository root)
  * the FastAPI backend introduced in a later phase
  * the test suite
  * offline scripts (training, evaluation, migration)

Phase 2 scope: configuration, application paths, logging, shared utilities.
Nothing in this package changes AURA's runtime behaviour until existing
modules are explicitly migrated to consume it.
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "__app_name__",
]

# ----------------------------------------------------------------------
# Version
# ----------------------------------------------------------------------
# The legacy Streamlit UI hard-codes APP_VERSION = "1.0" in app.py.
# This is the single authoritative version going forward; app.py will be
# migrated to read it in a later phase rather than duplicating it.
#
# Uses PEP 440 development versioning: 2.0.0.dev0 sorts *before* 2.0.0,
# which correctly signals that the migration is incomplete.
from aura.core.version import __app_name__, __version__
