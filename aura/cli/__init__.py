"""
Command-line entry points for AURA.

These live inside the package rather than in a top-level ``scripts/`` folder
for a concrete packaging reason: ``[tool.setuptools.packages.find]`` installs
only ``aura*``, so a console script pointing at ``scripts.something`` resolves
during development and then fails with ``ModuleNotFoundError`` once installed.
Keeping CLIs in ``aura.cli`` means the entry point works in an editable
install, a wheel install and a PyInstaller bundle alike.

Every CLI here must be import-safe: no filesystem writes, no network access
and no telemetry collection at import time.
"""

from __future__ import annotations

__all__: list[str] = []
