"""
Windows-native Named Mutex Single-Instance Guard for AURA Background Agent.

Guarantees:
  - Uses kernel-level Win32 CreateMutexW as the primary Windows protection.
  - Automatically reclaimed by Windows OS kernel if process crashes/terminates.
  - File-lock fallback for cross-platform/testing environments.
  - Strict context manager support.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import os
from pathlib import Path
import sys
from types import TracebackType
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MUTEX_NAME = "Local\\AURA_Privacy_Guardian_SingleInstance"
ERROR_ALREADY_EXISTS = 183


class SingleInstanceGuard:
    """
    Enforces a single running AURA background agent per user session.
    """

    def __init__(self, mutex_name: str = DEFAULT_MUTEX_NAME, fallback_lockfile: Path | None = None) -> None:
        self.mutex_name = mutex_name
        self.fallback_lockfile = fallback_lockfile
        self._mutex_handle: Any = None
        self._file_handle: Any = None
        self._is_acquired = False

    @property
    def is_acquired(self) -> bool:
        return self._is_acquired

    def acquire(self) -> bool:
        """
        Attempt to acquire the single-instance lock.
        Returns True if this process is the sole active instance.
        Returns False if another instance is already running.
        """
        if self._is_acquired:
            return True

        if sys.platform == "win32":
            return self._acquire_windows_mutex()
        return self._acquire_fallback_file_lock()

    def _acquire_windows_mutex(self) -> bool:
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            create_mutex = kernel32.CreateMutexW
            create_mutex.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            create_mutex.restype = wintypes.HANDLE

            handle = create_mutex(None, False, self.mutex_name)
            last_error = ctypes.get_last_error()

            if not handle:
                logger.error("Failed to create Win32 Named Mutex %r (WinError %d)", self.mutex_name, last_error)
                return False

            if last_error == ERROR_ALREADY_EXISTS:
                logger.warning("Active AURA agent detected via Named Mutex %r. Acquisition rejected.", self.mutex_name)
                kernel32.CloseHandle(handle)
                return False

            self._mutex_handle = handle
            self._is_acquired = True
            logger.info("Successfully acquired Win32 Named Mutex: %s", self.mutex_name)
            return True
        except Exception as exc:
            logger.warning("Win32 Named Mutex creation failed (%s), attempting lockfile fallback", exc)
            return self._acquire_fallback_file_lock()

    def _acquire_fallback_file_lock(self) -> bool:
        if self.fallback_lockfile is None:
            self.fallback_lockfile = Path(os.environ.get("LOCALAPPDATA", ".")) / "AURA" / "data" / "agent.lock"

        try:
            self.fallback_lockfile.parent.mkdir(parents=True, exist_ok=True)
            self._file_handle = open(self.fallback_lockfile, "w")
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(self._file_handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            self._file_handle.write(f"pid={os.getpid()}\n")
            self._file_handle.flush()
            self._is_acquired = True
            logger.info("Successfully acquired file lock: %s", self.fallback_lockfile)
            return True
        except (IOError, OSError) as exc:
            logger.warning("Could not acquire file lock %s: %s", self.fallback_lockfile, exc)
            if self._file_handle:
                try:
                    self._file_handle.close()
                except Exception:
                    pass
                self._file_handle = None
            return False

    def release(self) -> None:
        """Release the acquired single-instance lock."""
        if not self._is_acquired:
            return

        if self._mutex_handle and sys.platform == "win32":
            try:
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel32.CloseHandle(self._mutex_handle)
                logger.info("Released Win32 Named Mutex: %s", self.mutex_name)
            except Exception as exc:
                logger.error("Error closing Win32 Mutex handle: %s", exc)
            finally:
                self._mutex_handle = None

        if self._file_handle:
            try:
                if sys.platform == "win32":
                    import msvcrt
                    try:
                        msvcrt.locking(self._file_handle.fileno(), msvcrt.LK_UNLCK, 1)
                    except Exception:
                        pass
                else:
                    import fcntl
                    try:
                        fcntl.flock(self._file_handle.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass
                self._file_handle.close()
                if self.fallback_lockfile and self.fallback_lockfile.exists():
                    try:
                        self.fallback_lockfile.unlink(missing_ok=True)
                    except Exception:
                        pass
                logger.info("Released file lock: %s", self.fallback_lockfile)
            except Exception as exc:
                logger.error("Error releasing file lock: %s", exc)
            finally:
                self._file_handle = None

        self._is_acquired = False

    def __enter__(self) -> SingleInstanceGuard:
        if not self.acquire():
            raise RuntimeError(f"Another instance of AURA agent is already running (Mutex: {self.mutex_name})")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.release()
