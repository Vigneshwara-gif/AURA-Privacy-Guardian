"""
Persistent multi-tenant storage for AURA Cloud Backend.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import sqlite3
import threading
from typing import Any, Generator
import uuid

from aura.cloud.security import generate_pairing_code, generate_secure_token, generate_device_token

logger = logging.getLogger(__name__)


class CloudStorage:
    def __init__(self, db_path: Path | str, busy_timeout: float = 5.0) -> None:
        self.db_path = Path(db_path)
        self.busy_timeout = busy_timeout
        self._lock = threading.RLock()
        self._local = threading.local()
        self._all_connections: set[sqlite3.Connection] = set()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "connection", None)
        if conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=self.busy_timeout,
                check_same_thread=False,
                isolation_level=None,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute(f"PRAGMA busy_timeout={int(self.busy_timeout * 1000)};")
            conn.execute("PRAGMA foreign_keys=ON;")
            self._local.connection = conn
            with self._lock:
                self._all_connections.add(conn)
        return conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self._get_connection()
        with self._lock:
            conn.execute("BEGIN IMMEDIATE;")
            cursor = conn.cursor()
            try:
                yield cursor
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                cursor.close()

    def _init_schema(self) -> None:
        with self._lock:
            conn = self._get_connection()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    is_revoked INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    device_name TEXT NOT NULL,
                    platform TEXT NOT NULL DEFAULT 'Windows',
                    os_version TEXT,
                    hostname TEXT,
                    device_token TEXT UNIQUE NOT NULL,
                    is_online INTEGER NOT NULL DEFAULT 0,
                    is_revoked INTEGER NOT NULL DEFAULT 0,
                    last_heartbeat TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pairing_sessions (
                    pairing_code TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    device_name TEXT NOT NULL DEFAULT 'Windows PC',
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    is_consumed INTEGER NOT NULL DEFAULT 0,
                    consumed_by_device_id TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(user_id);
                CREATE INDEX IF NOT EXISTS idx_devices_token ON devices(device_token);
                CREATE INDEX IF NOT EXISTS idx_pairing_code ON pairing_sessions(pairing_code);
            """)

    def create_user(self, user_id: str, email: str, password_hash: str, display_name: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.transaction() as cur:
            cur.execute(
                """
                INSERT INTO users (user_id, email, password_hash, display_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (user_id, email.lower().strip(), password_hash, display_name.strip(), now, now),
            )
        return self.get_user_by_id(user_id)  # type: ignore

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM users WHERE email = ?;", (email.lower().strip(),))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close()

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT user_id, email, display_name, created_at, updated_at FROM users WHERE user_id = ?;", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close()

    def create_session(self, user_id: str, ttl_hours: float = 72.0) -> str:
        token = generate_secure_token()
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(hours=ttl_hours)).isoformat()
        with self.transaction() as cur:
            cur.execute(
                """
                INSERT INTO user_sessions (session_token, user_id, created_at, expires_at, is_revoked)
                VALUES (?, ?, ?, ?, 0);
                """,
                (token, user_id, now.isoformat(), expires_at),
            )
        return token

    def validate_session(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT s.session_token, s.user_id, s.expires_at, s.is_revoked, u.email, u.display_name
                FROM user_sessions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.session_token = ? AND s.is_revoked = 0;
                """,
                (token,),
            )
            row = cur.fetchone()
            if not row:
                return None

            now = datetime.now(timezone.utc).isoformat()
            if now > row["expires_at"]:
                return None

            return dict(row)
        finally:
            cur.close()

    def revoke_session(self, token: str) -> bool:
        with self.transaction() as cur:
            cur.execute("UPDATE user_sessions SET is_revoked = 1 WHERE session_token = ?;", (token,))
            return cur.rowcount > 0

    def create_pairing_session(self, user_id: str, device_name: str = "Windows PC", ttl_seconds: int = 600) -> str:
        code = generate_pairing_code()
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
        with self.transaction() as cur:
            cur.execute(
                """
                INSERT INTO pairing_sessions (pairing_code, user_id, device_name, created_at, expires_at, is_consumed)
                VALUES (?, ?, ?, ?, ?, 0);
                """,
                (code, user_id, device_name, now.isoformat(), expires_at),
            )
        return code

    def consume_pairing_code(self, pairing_code: str, hostname: str, os_version: str = "Windows") -> tuple[str, str, str]:
        clean_code = pairing_code.strip().upper()
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()

        with self.transaction() as cur:
            cur.execute(
                """
                SELECT pairing_code, user_id, device_name, expires_at, is_consumed
                FROM pairing_sessions
                WHERE (pairing_code = ? OR replace(pairing_code, '-', '') = replace(?, '-', ''))
                  AND is_consumed = 0;
                """,
                (clean_code, clean_code),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Invalid or already consumed pairing code.")

            if now_iso > row["expires_at"]:
                raise ValueError("Pairing code has expired. Please generate a new one.")

            user_id = row["user_id"]
            device_name = row["device_name"] or hostname or "Windows PC"
            matched_code = row["pairing_code"]

            device_id = f"dev_{uuid.uuid4().hex[:12]}"
            device_token = generate_device_token()

            cur.execute(
                """
                INSERT INTO devices (
                    device_id, user_id, device_name, platform, os_version, hostname,
                    device_token, is_online, is_revoked, last_heartbeat, created_at, updated_at
                ) VALUES (?, ?, ?, 'Windows', ?, ?, ?, 1, 0, ?, ?, ?);
                """,
                (device_id, user_id, device_name, os_version, hostname, device_token, now_iso, now_iso, now_iso),
            )

            cur.execute(
                """
                UPDATE pairing_sessions
                SET is_consumed = 1, consumed_by_device_id = ?
                WHERE pairing_code = ?;
                """,
                (device_id, matched_code),
            )

            return device_id, device_token, user_id

    def get_user_devices(self, user_id: str) -> list[dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT device_id, user_id, device_name, platform, os_version, hostname,
                       is_online, is_revoked, last_heartbeat, created_at, updated_at
                FROM devices
                WHERE user_id = ? AND is_revoked = 0
                ORDER BY created_at DESC;
                """,
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            cur.close()

    def get_device_by_id(self, device_id: str) -> dict[str, Any] | None:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM devices WHERE device_id = ?;", (device_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close()

    def get_device_by_token(self, device_token: str) -> dict[str, Any] | None:
        if not device_token:
            return None
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT * FROM devices WHERE device_token = ? AND is_revoked = 0;",
                (device_token,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close()

    def update_device_online_status(self, device_id: str, is_online: bool) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.transaction() as cur:
            cur.execute(
                """
                UPDATE devices
                SET is_online = ?, last_heartbeat = ?, updated_at = ?
                WHERE device_id = ?;
                """,
                (1 if is_online else 0, now, now, device_id),
            )

    def revoke_device(self, user_id: str, device_id: str) -> bool:
        with self.transaction() as cur:
            cur.execute(
                "UPDATE devices SET is_revoked = 1, is_online = 0 WHERE device_id = ? AND user_id = ?;",
                (device_id, user_id),
            )
            return cur.rowcount > 0

    def delete_device(self, user_id: str, device_id: str) -> bool:
        with self.transaction() as cur:
            cur.execute(
                "DELETE FROM devices WHERE device_id = ? AND user_id = ?;",
                (device_id, user_id),
            )
            return cur.rowcount > 0
