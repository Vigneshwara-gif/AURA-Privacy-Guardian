"""
Database schema definitions and migrations for AURA storage layer.

Supports SQLite in WAL mode with strict parameterized queries,
versioned schema migrations, and optimized indexes.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1


class Migration(NamedTuple):
    version: int
    description: str
    up_sql: str


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        description="Initial AURA production schema: telemetry, security_events, baseline_profiles, scan_runs",
        up_sql="""
        -- Schema migration history tracking
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT NOT NULL
        );

        -- Telemetry time-series measurements
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            disk_io_kbps REAL,
            net_up_kbps REAL,
            net_down_kbps REAL,
            process_count INTEGER,
            established_conns INTEGER,
            listening_conns INTEGER,
            remote_conns INTEGER,
            camera_status TEXT,
            microphone_status TEXT,
            sensor_health_json TEXT,
            raw_payload_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp);

        -- Structured security and privacy events
        CREATE TABLE IF NOT EXISTS security_events (
            event_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            risk_score REAL NOT NULL,
            source TEXT NOT NULL,
            summary TEXT NOT NULL,
            evidence_json TEXT,
            confidence REAL,
            affected_resource TEXT,
            correlation_id TEXT,
            schema_version INTEGER NOT NULL DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON security_events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_severity ON security_events(severity);
        CREATE INDEX IF NOT EXISTS idx_events_type ON security_events(event_type);

        -- Baseline machine learning profiles
        CREATE TABLE IF NOT EXISTS baseline_profiles (
            profile_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            feature_names_json TEXT NOT NULL,
            sample_count INTEGER NOT NULL,
            mean_vector_json TEXT NOT NULL,
            std_vector_json TEXT NOT NULL,
            model_version TEXT NOT NULL,
            metadata_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_baseline_created_at ON baseline_profiles(created_at);

        -- Scan execution log
        CREATE TABLE IF NOT EXISTS scan_runs (
            scan_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            trigger_source TEXT NOT NULL,
            is_demo INTEGER NOT NULL DEFAULT 0,
            is_success INTEGER NOT NULL DEFAULT 1,
            risk_score REAL,
            severity TEXT,
            error_message TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_scans_started_at ON scan_runs(started_at);
        """,
    ),
)
