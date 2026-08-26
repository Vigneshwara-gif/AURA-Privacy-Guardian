"""
Application path strategy for AURA.

Separates four concerns that the current code conflates by storing everything
inside the source tree (audit finding F13):

  * installation root  — where the code lives; read-only in production
  * user data          — database, exports
  * logs               — rotating application logs
  * models             — persisted ML artifacts
  * config             — user-editable configuration

Why this matters: the existing ``logger.py`` computes
``BASE_DIR / "data" / "system_logs.csv"`` relative to its own file. That breaks
the moment AURA is installed to ``C:\\Program Files\\AURA``, because Program
Files is not user-writable. It also means every developer checkout mixes real
telemetry into the repository.

Resolution order for the user-data root:

  1. ``AURA_HOME`` environment variable, if set (highest priority; used by
     tests, portable installs and the eventual installer)
  2. Repository-local ``.aura-dev/`` when ``AURA_DEV_MODE`` is truthy
  3. ``%LOCALAPPDATA%\\AURA`` on Windows
  4. ``$XDG_DATA_HOME/aura`` or ``~/.local/share/aura`` on Linux
  5. ``~/Library/Application Support/AURA`` on macOS

LOCALAPPDATA is deliberately chosen over APPDATA: AURA's data is
machine-specific telemetry and must not follow a roaming Windows profile
across machines.

This module has no third-party dependencies and performs no filesystem writes
at import time. Directory creation is explicit via ``ensure_directories()``.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

__all__ = [
    "AuraPaths",
    "get_paths",
    "ensure_directories",
]


# ----------------------------------------------------------------------
# Environment variable names
# ----------------------------------------------------------------------

ENV_HOME = "AURA_HOME"
ENV_DEV_MODE = "AURA_DEV_MODE"

_TRUTHY = {"1", "true", "yes", "on", "y"}


def _is_truthy(raw: str | None) -> bool:
    """Interpret an environment variable as a boolean."""
    if raw is None:
        return False
    return raw.strip().lower() in _TRUTHY


def _installation_root() -> Path:
    """
    Locate the repository / installation root.

    ``paths.py`` lives at ``<root>/aura/core/paths.py``, so the root is three
    levels up. When frozen by PyInstaller, ``sys.frozen`` is set and the
    executable's directory is the installation root instead.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _platform_data_root() -> Path:
    """Return the OS-conventional per-user application data directory."""
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / "AURA"
        # Fallback if LOCALAPPDATA is somehow unset.
        return Path.home() / "AppData" / "Local" / "AURA"

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AURA"

    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "aura"
    return Path.home() / ".local" / "share" / "aura"


def _resolve_user_root(install_root: Path) -> tuple[Path, str]:
    """
    Resolve the user-data root and report which rule produced it.

    Returning the origin lets ``aura_doctor`` explain to the user *why* their
    data is where it is, which is otherwise a common source of confusion.
    """
    explicit = os.environ.get(ENV_HOME)
    if explicit and explicit.strip():
        return Path(explicit).expanduser().resolve(), f"{ENV_HOME} environment variable"

    if _is_truthy(os.environ.get(ENV_DEV_MODE)):
        return install_root / ".aura-dev", f"{ENV_DEV_MODE} (repository-local)"

    return _platform_data_root(), "platform default"


@dataclass(frozen=True, slots=True)
class AuraPaths:
    """
    Immutable, fully-resolved set of application paths.

    Construct via :func:`get_paths` rather than directly, so that the result is
    cached and consistent for the lifetime of the process.
    """

    install_root: Path
    user_root: Path
    user_root_origin: str

    # ------------------------------------------------------------------
    # Derived directories
    # ------------------------------------------------------------------

    @property
    def data_dir(self) -> Path:
        """Database and structured exports."""
        return self.user_root / "data"

    @property
    def logs_dir(self) -> Path:
        """Rotating application logs."""
        return self.user_root / "logs"

    @property
    def models_dir(self) -> Path:
        """Persisted ML model artifacts and their metadata."""
        return self.user_root / "models"

    @property
    def config_dir(self) -> Path:
        """User-editable configuration."""
        return self.user_root / "config"

    @property
    def reports_dir(self) -> Path:
        """Generated CSV / JSON / human-readable reports."""
        return self.user_root / "reports"

    @property
    def web_dir(self) -> Path:
        """Static web dashboard assets (HTML, CSS, JS)."""
        dist_dir = self.install_root / "web" / "dist"
        if dist_dir.exists() and (dist_dir / "index.html").exists():
            return dist_dir
        return self.install_root / "web"

    @property
    def bin_dir(self) -> Path:
        """Installed executable binary directory."""
        installed_bin = self.install_root / "bin"
        return installed_bin if installed_bin.exists() else self.install_root

    @property
    def staging_dir(self) -> Path:
        """Temporary staging directory for atomic upgrades."""
        return self.user_root / "staging"

    @property
    def backup_dir(self) -> Path:
        """Backup directory for rollback preservation."""
        return self.user_root / "backup"

    @property
    def is_packaged(self) -> bool:
        """Check if running inside a frozen PyInstaller bundle."""
        return getattr(sys, "frozen", False)

    # ------------------------------------------------------------------
    # Well-known files
    # ------------------------------------------------------------------

    @property
    def database_path(self) -> Path:
        """SQLite database file."""
        return self.data_dir / "aura.db"

    @property
    def log_file(self) -> Path:
        """Primary rotating log file."""
        return self.logs_dir / "aura.log"

    @property
    def config_file(self) -> Path:
        """Optional TOML configuration overriding built-in defaults."""
        return self.config_dir / "aura.toml"

    @property
    def env_file(self) -> Path:
        """Optional .env file, read from the installation root."""
        return self.install_root / ".env"

    # ------------------------------------------------------------------
    # Legacy locations (read-only; required by the Phase 7 CSV import)
    # ------------------------------------------------------------------
    #
    # The existing application writes these paths relative to the source
    # tree. They are exposed here so the future migration can locate real
    # historical data without hard-coding paths a second time. AURA must never
    # *write* to these once migration is complete.

    @property
    def legacy_data_dir(self) -> Path:
        return self.install_root / "data"

    @property
    def legacy_log_csv(self) -> Path:
        return self.legacy_data_dir / "system_logs.csv"

    @property
    def legacy_baseline_csv(self) -> Path:
        return self.legacy_data_dir / "baseline.csv"

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def managed_directories(self) -> tuple[Path, ...]:
        """Directories AURA creates and owns."""
        return (
            self.user_root,
            self.data_dir,
            self.logs_dir,
            self.models_dir,
            self.config_dir,
            self.reports_dir,
        )

    def describe(self) -> dict[str, str]:
        """Flat, printable mapping for diagnostics output."""
        return {
            "install_root": str(self.install_root),
            "user_root": str(self.user_root),
            "user_root_origin": self.user_root_origin,
            "data_dir": str(self.data_dir),
            "logs_dir": str(self.logs_dir),
            "models_dir": str(self.models_dir),
            "config_dir": str(self.config_dir),
            "reports_dir": str(self.reports_dir),
            "database_path": str(self.database_path),
            "log_file": str(self.log_file),
            "config_file": str(self.config_file),
            "legacy_log_csv": str(self.legacy_log_csv),
            "legacy_baseline_csv": str(self.legacy_baseline_csv),
        }


@lru_cache(maxsize=1)
def get_paths() -> AuraPaths:
    """
    Return the process-wide path configuration.

    Cached so that every caller observes identical paths even if the
    environment is mutated later. Tests that need to change paths should call
    ``get_paths.cache_clear()`` after patching the environment.
    """
    install_root = _installation_root()
    user_root, origin = _resolve_user_root(install_root)
    return AuraPaths(
        install_root=install_root,
        user_root=user_root,
        user_root_origin=origin,
    )


def ensure_directories(paths: AuraPaths | None = None) -> AuraPaths:
    """
    Create AURA's managed directories if they do not already exist.

    Idempotent and safe to call repeatedly. Raises ``OSError`` with a clear
    message if the location is not writable, which is a genuine fatal
    condition worth surfacing rather than swallowing — silently falling back
    to a different directory would hide data in a place the user cannot find.
    """
    resolved = paths or get_paths()

    for directory in resolved.managed_directories():
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OSError(
                f"AURA cannot create required directory {directory!s}: {exc}. "
                f"Set the {ENV_HOME} environment variable to a writable "
                f"location, or enable {ENV_DEV_MODE}=1 to keep data inside "
                f"the project folder."
            ) from exc

    return resolved
