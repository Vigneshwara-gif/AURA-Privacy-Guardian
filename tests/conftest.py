"""
Shared pytest fixtures for AURA.

Two invariants are enforced here, both autouse, because forgetting either one
produces tests that pass or fail depending on the machine they run on.

**Isolation.** Every test runs against a throwaway ``AURA_HOME`` inside pytest's
``tmp_path``, with all other ``AURA_*`` environment variables removed and the
working directory moved out of the repository. Without this, a developer's own
``.env`` file or exported ``AURA_LOG__LEVEL`` would silently change test
outcomes, and — far worse — a test could write telemetry into the real
``%LOCALAPPDATA%\\AURA`` or truncate ``data/system_logs.csv``.

**Cache clearing.** ``get_paths`` and ``get_settings`` are both
``lru_cache``-wrapped, deliberately, so the whole process observes one
configuration. That makes them process-global state, which must be reset around
every test — before as well as after, since an earlier import may already have
populated them.

Test modules here intentionally have no ``__init__.py``. pytest inserts the
rootdir on ``sys.path`` via the ``pythonpath`` setting in ``pyproject.toml``, so
test modules are imported by their own filename; adding package markers would
only add a way for names to collide.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

# ----------------------------------------------------------------------
# Marker handling
# ----------------------------------------------------------------------


def pytest_runtest_setup(item: pytest.Item) -> None:
    """
    Skip Windows-only tests elsewhere instead of failing them.

    AURA's sensor layer reads Windows telemetry. A test that asserts on
    ``psutil.net_connections`` permission behaviour or on ``%SystemDrive%``
    cannot pass on Linux, and pretending otherwise would mean either a
    permanently red suite or a test weakened until it proves nothing.
    """
    if list(item.iter_markers(name="windows")) and sys.platform != "win32":
        pytest.skip(f"requires a real Windows host; running on {sys.platform}")


# ----------------------------------------------------------------------
# Isolation
# ----------------------------------------------------------------------


def _clear_caches() -> None:
    """Reset every process-global cache AURA installs."""
    from aura.core.config import get_settings
    from aura.core.paths import get_paths

    get_paths.cache_clear()
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def isolated_aura_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[Path]:
    """
    Point AURA at a throwaway home directory for the duration of one test.

    The working directory is changed as well, because ``Settings`` declares
    ``env_file=".env"``, which pydantic-settings resolves relative to the
    current directory. Moving out of the repository is the only reliable way to
    guarantee a developer's local ``.env`` cannot reach the test.
    ``pythonpath`` has already been applied by the time fixtures run, so imports
    are unaffected.
    """
    for name in [key for key in os.environ if key.startswith("AURA_")]:
        monkeypatch.delenv(name, raising=False)

    home = tmp_path / "aura-home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AURA_HOME", str(home))

    workdir = tmp_path / "cwd"
    workdir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workdir)

    _clear_caches()
    try:
        yield home
    finally:
        _clear_caches()


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    """
    Undo any logging configuration a test performed.

    ``configure_logging`` attaches handlers to the root logger and records
    module-level state so that Streamlit reruns do not stack duplicates. In a
    test session that same guard would leak a file handler pointing at a
    deleted ``tmp_path`` into every later test, so both the handlers and the
    recorded state are reverted here.
    """
    root = logging.getLogger()
    original_level = root.level
    original_handlers = list(root.handlers)

    yield

    from aura.core import logging_config

    for handler in list(root.handlers):
        if handler not in original_handlers:
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:  # noqa: BLE001 - closing a broken handler is not fatal
                pass

    for handler in original_handlers:
        if handler not in root.handlers:
            root.addHandler(handler)

    root.setLevel(original_level)
    logging_config.logging_state = logging_config.LoggingState()


# ----------------------------------------------------------------------
# Convenience fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def paths() -> Any:
    """The resolved :class:`~aura.core.paths.AuraPaths` for this test."""
    from aura.core.paths import get_paths

    return get_paths()


@pytest.fixture
def ensured_paths(paths: Any) -> Any:
    """Paths with every managed directory created."""
    from aura.core.paths import ensure_directories

    return ensure_directories(paths)


@pytest.fixture
def make_settings() -> Callable[..., Any]:
    """
    Build a ``Settings`` instance with ``.env`` loading disabled.

    Constructed directly rather than through ``get_settings()`` so a test can
    override a single nested value without mutating the environment, and so no
    ``.env`` file can influence the result even if the working directory
    changes.
    """
    from aura.core.config import Settings

    def factory(**overrides: Any) -> Any:
        return Settings(_env_file=None, **overrides)

    return factory


@pytest.fixture
def settings(make_settings: Callable[..., Any]) -> Any:
    """Default settings, isolated from the environment and from ``.env``."""
    return make_settings()
