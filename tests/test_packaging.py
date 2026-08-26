"""
Unit and regression tests for AURA production packaging, paths, and manifests.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest

from aura.core.paths import get_paths
from aura.core.version import __app_name__, __version__


def test_version_consistency() -> None:
    """Verify version source of truth."""
    assert __version__ == "2.0.0"
    assert __app_name__ == "AURA Privacy Guardian"


def test_paths_packaged_structure() -> None:
    """Verify paths abstraction resolves required directories."""
    paths = get_paths()
    assert paths.web_dir.name in ("web", "dist")
    assert paths.database_path.name == "aura.db"
    assert paths.log_file.name == "aura.log"
    assert paths.data_dir.name == "data"
    assert paths.models_dir.name == "models"
    assert paths.logs_dir.name == "logs"


def test_web_dashboard_placeholder_exists() -> None:
    """Verify web dashboard is present and contains bootstrap handling."""
    paths = get_paths()
    index_html = paths.web_dir / "index.html"
    assert index_html.exists()
    content = index_html.read_text(encoding="utf-8")
    assert "AURA Privacy Guardian" in content
    # Check if replaceState is in index.html (static placeholder) or in bundled JS
    has_sanitization = "replaceState" in content
    if not has_sanitization:
        for js_file in (paths.web_dir / "assets").glob("*.js"):
            if "replaceState" in js_file.read_text(encoding="utf-8"):
                has_sanitization = True
                break
    assert has_sanitization  # Verifies immediate URL sanitization


def test_cli_version_flag() -> None:
    """Verify aura --version returns valid version string."""
    from aura.cli.main import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--version"])
    assert exc.value.code == 0
