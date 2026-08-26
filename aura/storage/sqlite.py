"""
Production SQLite storage engine for AURA.
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

from aura.models.types import SecurityEvent, TelemetrySnapshot
from aura.storage.schema import CURRENT_SCHEMA_VERSION, MIGRATIONS

logger = logging.getLogger(__name__)


class StorageEngine:
    def __init__(
        self,
        db_path: Path | str,
        busy_timeout: float = 5.0,
        wal_mode: bool = True,
    ) -> None:
        self.db_path = Path(db_path)
        self.busy_timeout = busy_timeout
        self.wal_mode = wal_mode
        self._lock = threading.RLock()
        self._local = threading.local()
        self._all_connections: set[sqlite3.Connection] = set()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

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
            if self.wal_mode:
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

    def migrate(self) -> None:
        with self._lock:
            conn = self._get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL,
                    description TEXT NOT NULL
                );
            """)

            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version ASC;")
            applied_versions = {row["version"] for row in cursor.fetchall()}
            cursor.close()

            for migration in MIGRATIONS:
                if migration.version not in applied_versions:
                    logger.info("Applying schema migration v%d: %s", migration.version, migration.description)
                    conn.executescript(migration.up_sql)
                    conn.execute(
                        "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?, ?, ?);",
                        (
                            migration.version,
                            datetime.now(timezone.utc).isoformat(),
                            migration.description,
                        ),
                    )

    def record_telemetry(self, snapshot: TelemetrySnapshot) -> int:
        sql = """
        INSERT INTO telemetry (
            timestamp, cpu_percent, memory_percent, disk_percent, disk_io_kbps,
            net_up_kbps, net_down_kbps, process_count, established_conns,
            listening_conns, remote_conns, camera_status, microphone_status,
            sensor_health_json, raw_payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        sensor_health_json = json.dumps([h.to_dict() for h in snapshot.sensor_health])
        raw_payload_json = json.dumps(snapshot.raw_payload) if snapshot.raw_payload else None

        with self.transaction() as cur:
            cur.execute(
                sql,
                (
                    snapshot.timestamp,
                    snapshot.cpu_percent,
                    snapshot.memory_percent,
                    snapshot.disk_percent,
                    snapshot.disk_io_write_kbps,
                    snapshot.net_upload_kbps,
                    snapshot.net_download_kbps,
                    snapshot.process_count,
                    snapshot.established_connections,
                    snapshot.listening_connections,
                    snapshot.remote_connections,
                    snapshot.camera_status.value,
                    snapshot.microphone_status.value,
                    sensor_health_json,
                    raw_payload_json,
                ),
            )
            return int(cur.lastrowid)

    def record_security_event(self, event: SecurityEvent) -> str:
        sql = """
        INSERT INTO security_events (
            event_id, timestamp, event_type, severity, risk_score, source,
            summary, evidence_json, confidence, affected_resource,
            correlation_id, schema_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        evidence_json = json.dumps(event.evidence) if event.evidence else None

        with self.transaction() as cur:
            cur.execute(
                sql,
                (
                    event.event_id,
                    event.timestamp,
                    event.event_type,
                    event.severity,
                    event.risk_score,
                    event.source,
                    event.summary,
                    evidence_json,
                    event.confidence,
                    event.affected_resource,
                    event.correlation_id,
                    event.schema_version,
                ),
            )
            return event.event_id

    def record_scan_run(
        self,
        scan_id: str,
        started_at: str,
        completed_at: str,
        trigger_source: str,
        is_demo: bool = False,
        is_success: bool = True,
        risk_score: float | None = None,
        severity: str | None = None,
        error_message: str | None = None,
    ) -> str:
        sql = """
        INSERT INTO scan_runs (
            scan_id, started_at, completed_at, trigger_source,
            is_demo, is_success, risk_score, severity, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.transaction() as cur:
            cur.execute(
                sql,
                (
                    scan_id,
                    started_at,
                    completed_at,
                    trigger_source,
                    1 if is_demo else 0,
                    1 if is_success else 0,
                    risk_score,
                    severity,
                    error_message,
                ),
            )
            return scan_id

    def record_audit_log(
        self,
        action: str,
        actor: str = "User",
        target: str | None = None,
        details: dict[str, Any] | None = None,
        result: str = "SUCCESS",
    ) -> str:
        log_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details) if details else None
        sql = """
        INSERT INTO audit_logs (log_id, timestamp, action, actor, target, details_json, result)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        with self.transaction() as cur:
            cur.execute(sql, (log_id, now, action, actor, target, details_json, result))
            return log_id

    def get_audit_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?;", (max(1, limit),))
            rows = cur.fetchall()
            logs = []
            for r in rows:
                d = dict(r)
                if d.get("details_json"):
                    try:
                        d["details"] = json.loads(d["details_json"])
                    except Exception:
                        d["details"] = {}
                else:
                    d["details"] = {}
                logs.append(d)
            return logs
        finally:
            cur.close()

    def get_recent_events(
        self,
        limit: int = 100,
        min_severity: str | None = None,
    ) -> list[dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if min_severity:
                cursor.execute(
                    "SELECT * FROM security_events WHERE severity = ? ORDER BY timestamp DESC LIMIT ?;",
                    (min_severity.upper(), max(1, limit)),
                )
            else:
                cursor.execute(
                    "SELECT * FROM security_events ORDER BY timestamp DESC LIMIT ?;",
                    (max(1, limit),),
                )

            rows = cursor.fetchall()
            results: list[dict[str, Any]] = []
            for row in rows:
                d = dict(row)
                if d.get("evidence_json"):
                    try:
                        d["evidence"] = json.loads(d["evidence_json"])
                    except Exception:
                        d["evidence"] = []
                else:
                    d["evidence"] = []
                results.append(d)
            return results
        finally:
            cursor.close()

    def get_recent_telemetry(self, limit: int = 100) -> list[dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT ?;", (max(1, limit),))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            cursor.close()

    def get_event_counts_by_severity(self) -> dict[str, int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT severity, COUNT(*) as count FROM security_events GROUP BY severity;")
            rows = cursor.fetchall()
            counts = {"INFO": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
            for row in rows:
                sev = row["severity"]
                if sev in counts:
                    counts[sev] = row["count"]
            return counts
        finally:
            cursor.close()

    def get_risk_history(self, limit: int = 100) -> list[dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT timestamp, risk_score, severity, event_type, summary
                FROM security_events
                ORDER BY timestamp DESC LIMIT ?;
                """,
                (max(1, limit),),
            )
            rows = cur.fetchall()
            return [dict(r) for r in reversed(rows)]
        finally:
            cur.close()

    def get_telemetry_series(
        self,
        metric_column: str,
        limit: int = 100,
    ) -> list[tuple[str, float]]:
        allowed = {
            "cpu_percent", "memory_percent", "disk_percent", "disk_io_kbps",
            "net_up_kbps", "net_down_kbps", "process_count", "remote_conns",
        }
        if metric_column not in allowed:
            raise ValueError(f"Invalid metric column: {metric_column}")

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT timestamp, {metric_column} FROM telemetry ORDER BY timestamp DESC LIMIT ?;",
                (max(1, limit),),
            )
            rows = cursor.fetchall()
            return [(row["timestamp"], float(row[metric_column] or 0.0)) for row in reversed(rows)]
        finally:
            cursor.close()

    def get_event_count(self) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) as count FROM security_events;")
            row = cursor.fetchone()
            return int(row["count"]) if row else 0
        finally:
            cursor.close()

    def get_telemetry_count(self) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) as count FROM telemetry;")
            row = cursor.fetchone()
            return int(row["count"]) if row else 0
        finally:
            cursor.close()

    def prune_retention(self, retention_days: int = 90, metrics_retention_days: int = 14) -> dict[str, int]:
        cutoff_events = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        cutoff_metrics = (datetime.now(timezone.utc) - timedelta(days=metrics_retention_days)).isoformat()

        pruned = {"events": 0, "telemetry": 0}
        with self.transaction() as cur:
            cur.execute("DELETE FROM security_events WHERE timestamp < ?;", (cutoff_events,))
            pruned["events"] = cur.rowcount
            cur.execute("DELETE FROM telemetry WHERE timestamp < ?;", (cutoff_metrics,))
            pruned["telemetry"] = cur.rowcount

        return pruned

    def close(self) -> None:
        with self._lock:
            for conn in list(self._all_connections):
                try:
                    conn.close()
                except Exception:
                    pass
            self._all_connections.clear()
