"""
Centralised, validated configuration for AURA.

This replaces constants currently scattered across four modules (audit finding
F13). Every default below is transcribed from the existing code, with its
source recorded inline so the values can be audited rather than trusted.

    privacy_monitor.py  lines 147-167   collection limits, network and
                                        connection thresholds
    privacy_monitor.py  lines 627-634   process ratio thresholds
    privacy_monitor.py  lines 1192-1210 risk bands
    privacy_monitor.py  line  1217      privacy-event minimum score
    privacy_monitor.py  privacy_risk()  signal weights
    model.py            lines 38-57     ML hyperparameters
    aura_core.py        DEFAULT_*       baseline collection parameters

Phase 2 introduces this module but does NOT rewire the existing code to use
it. That happens per-module in later phases so each change can be verified
independently. Until then, these values are a *specification* of current
behaviour, and the Phase 3 test suite asserts that the live code agrees with
them. If a test fails, this file is wrong and must be corrected â€” the
existing behaviour is the reference.

Configuration precedence, lowest to highest:

    built-in defaults  <  .env file  <  environment variables

Environment variables use the ``AURA_`` prefix and ``__`` to descend into
nested sections:

    AURA_LOG__LEVEL=DEBUG
    AURA_SENSORS__COLLECTION_INTERVAL_SECONDS=10
    AURA_RISK__BANDS__HIGH=60
    AURA_API__PORT=9001
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from aura import __version__
from aura.core.paths import AuraPaths, get_paths

__all__ = [
    "Settings",
    "RiskBands",
    "RiskWeights",
    "NetworkThresholds",
    "ConnectionThresholds",
    "ProcessRatioThresholds",
    "RiskConfig",
    "DetectionConfig",
    "SensorConfig",
    "AlertConfig",
    "StorageConfig",
    "LogConfig",
    "ApiConfig",
    "get_settings",
    "SeverityName",
]

SeverityName = Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def default_system_drive() -> str:
    """
    Return the drive to report disk statistics for.

    ``sensors.get_disk_info`` hard-codes ``"C:\\"`` (audit finding F13). Windows
    exposes the real system drive via ``%SystemDrive%``, which is not always C:
    â€” it differs on some corporate images and on Windows-To-Go installs.
    """
    if sys.platform == "win32":
        drive = os.environ.get("SystemDrive", "C:").strip()
        if not drive.endswith("\\"):
            drive = drive + "\\"
        return drive
    return "/"


# ======================================================================
# Risk configuration
# ======================================================================


class RiskBands(BaseModel):
    """
    Score-to-severity cut points.

    Source: privacy_monitor.py lines 1192-1210. These same four numbers are
    currently duplicated in ``privacy_monitor.get_privacy_health_summary``,
    ``aura_core.scan_once`` and ``app.risk_from_score``. This is the single
    definition they will all be migrated to read.
    """

    model_config = {"extra": "forbid"}

    critical: int = Field(default=80, ge=0, le=100)
    high: int = Field(default=55, ge=0, le=100)
    medium: int = Field(default=25, ge=0, le=100)
    low: int = Field(default=10, ge=0, le=100)

    @model_validator(mode="after")
    def _must_be_strictly_descending(self) -> RiskBands:
        ordered = [
            ("critical", self.critical),
            ("high", self.high),
            ("medium", self.medium),
            ("low", self.low),
        ]
        for (upper_name, upper), (lower_name, lower) in zip(ordered, ordered[1:]):
            if upper <= lower:
                raise ValueError(
                    f"risk band {upper_name}={upper} must be strictly greater "
                    f"than {lower_name}={lower}; overlapping bands would make "
                    f"severity assignment ambiguous"
                )
        return self

    def severity_for(self, score: float) -> SeverityName:
        """
        Map a 0-100 score to a severity name.

        The score is authoritative. ``app.normalize_risk`` already relies on
        this property deliberately, to prevent contradictory displays such as
        a score of 29 labelled PROTECTED â€” the stored log contains exactly
        such a row (2026-08-19 20:39:46, Risk_Score=10 with Risk=NORMAL).
        """
        if score >= self.critical:
            return "CRITICAL"
        if score >= self.high:
            return "HIGH"
        if score >= self.medium:
            return "MEDIUM"
        if score >= self.low:
            return "LOW"
        return "INFO"


class RiskWeights(BaseModel):
    """
    Additive contribution of each signal to the 0-100 risk score.

    Source: the weights applied in ``privacy_monitor.privacy_risk``.

    The calibration is deliberate and should not be "tidied" into uniform
    values. A machine-learning anomaly is worth 30 because it reflects a
    deviation from that machine's own learned behaviour. A high remote
    connection count is worth only 8 because a normal Windows desktop
    maintains dozens of remote connections at rest, making it a weak
    indicator on its own.
    """

    model_config = {"extra": "forbid"}

    ml_anomaly: int = Field(default=30, ge=0, le=100)

    network_very_high: int = Field(default=30, ge=0, le=100)
    network_high: int = Field(default=22, ge=0, le=100)
    network_elevated: int = Field(default=10, ge=0, le=100)

    process_very_high: int = Field(default=20, ge=0, le=100)
    process_elevated: int = Field(default=15, ge=0, le=100)
    process_watch: int = Field(default=7, ge=0, le=100)

    connections_very_high: int = Field(default=8, ge=0, le=100)
    connections_high: int = Field(default=5, ge=0, le=100)
    connections_watch: int = Field(default=2, ge=0, le=100)

    @model_validator(mode="after")
    def _tiers_must_be_ordered(self) -> RiskWeights:
        tiers = {
            "network": (self.network_elevated, self.network_high, self.network_very_high),
            "process": (self.process_watch, self.process_elevated, self.process_very_high),
            "connections": (
                self.connections_watch,
                self.connections_high,
                self.connections_very_high,
            ),
        }
        for name, (low, mid, high) in tiers.items():
            if not low <= mid <= high:
                raise ValueError(
                    f"{name} weights must be non-decreasing by tier, got "
                    f"{low} / {mid} / {high}; a more severe tier scoring less "
                    f"than a milder one would invert the risk ordering"
                )
        return self


class NetworkThresholds(BaseModel):
    """
    Outbound transfer-rate thresholds in KB/s.

    Source: privacy_monitor.py lines 161-163.
    """

    model_config = {"extra": "forbid"}

    elevated_kbps: float = Field(default=100.0, gt=0)
    high_kbps: float = Field(default=1000.0, gt=0)
    very_high_kbps: float = Field(default=5000.0, gt=0)

    @model_validator(mode="after")
    def _ascending(self) -> NetworkThresholds:
        if not self.elevated_kbps < self.high_kbps < self.very_high_kbps:
            raise ValueError(
                "network thresholds must ascend: "
                f"elevated={self.elevated_kbps} < high={self.high_kbps} "
                f"< very_high={self.very_high_kbps}"
            )
        return self


class ConnectionThresholds(BaseModel):
    """
    Remote-connection count thresholds.

    Source: privacy_monitor.py lines 165-167.
    """

    model_config = {"extra": "forbid"}

    watch: int = Field(default=30, ge=0)
    high: int = Field(default=75, ge=0)
    very_high: int = Field(default=150, ge=0)

    @model_validator(mode="after")
    def _ascending(self) -> ConnectionThresholds:
        if not self.watch < self.high < self.very_high:
            raise ValueError(
                "connection thresholds must ascend: "
                f"watch={self.watch} < high={self.high} "
                f"< very_high={self.very_high}"
            )
        return self


class ProcessRatioThresholds(BaseModel):
    """
    Process-count thresholds, expressed as a ratio of the learned baseline.

    Source: privacy_monitor.py lines 627-634.

    Ratios rather than absolute counts, because a normal process count is
    entirely machine-dependent â€” this repository's own history ranges from 368
    to 391. ``classify_process_activity`` correctly returns NORMAL when no
    baseline exists rather than inventing an anomaly, and that behaviour is
    preserved.
    """

    model_config = {"extra": "forbid"}

    watch: float = Field(default=1.35, gt=1.0)
    elevated: float = Field(default=1.75, gt=1.0)
    very_high: float = Field(default=2.0, gt=1.0)

    @model_validator(mode="after")
    def _ascending(self) -> ProcessRatioThresholds:
        if not self.watch < self.elevated < self.very_high:
            raise ValueError(
                "process ratio thresholds must ascend: "
                f"watch={self.watch} < elevated={self.elevated} "
                f"< very_high={self.very_high}"
            )
        return self


class RiskConfig(BaseModel):
    """Everything the single risk engine needs."""

    model_config = {"extra": "forbid"}

    # Incremented whenever the weights, thresholds or bands change in a way
    # that makes scores incomparable with previously stored events.
    #
    # Version 2 is the current weight set. It is verifiable against stored
    # data: rows from 2026-08-19 21:57:17 onward reconcile exactly (an ML
    # anomaly plus a connection watch gives 30+2=32; adding a very-high
    # network rate gives 30+30+2=62). Rows before that timestamp do not
    # reconcile â€” the same 96% CPU / 5000 KB/s input scored 70 â€” so they were
    # produced by an earlier, unrecoverable weight set and are stamped
    # version 1 by the Phase 7 import.
    scoring_version: int = Field(default=2, ge=1)

    bands: RiskBands = Field(default_factory=RiskBands)
    weights: RiskWeights = Field(default_factory=RiskWeights)
    network: NetworkThresholds = Field(default_factory=NetworkThresholds)
    connections: ConnectionThresholds = Field(default_factory=ConnectionThresholds)
    process: ProcessRatioThresholds = Field(default_factory=ProcessRatioThresholds)

    # Source: privacy_monitor.py line 1217.
    privacy_event_min_score: int = Field(default=25, ge=0, le=100)

    # Source: privacy_monitor.py â€” exfiltration requires a suspicious network
    # signal AND an independent behavioural signal, never traffic volume
    # alone. Exposed as configuration so it can be tested, not so it can be
    # casually disabled.
    exfiltration_requires_two_signals: bool = True


# ======================================================================
# Detection / ML configuration
# ======================================================================


class DetectionConfig(BaseModel):
    """
    Feature pipeline and anomaly detector settings.

    Source: model.py lines 38-57, aura_core.py DEFAULT_SAMPLES /
    DEFAULT_BASELINE_INTERVAL.
    """

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    # Incremented whenever the feature vector's composition, order or
    # semantics change. Persisted alongside every model artifact and every
    # event so a model trained on one schema can never silently receive
    # another.
    #
    # Version 1 is the current three-feature vector. Note that ``Cam`` is
    # effectively constant zero in the existing baseline, which makes it a
    # near-zero-variance feature â€” a known detection-quality defect recorded
    # in the audit, to be addressed when the feature set is widened.
    feature_schema_version: int = Field(default=1, ge=1)

    features: tuple[str, ...] = ("CPU", "Net", "Cam")

    contamination: float = Field(default=0.10, gt=0.0, lt=0.5)
    min_baseline_samples: int = Field(default=10, ge=2)
    isolation_trees: int = Field(default=300, ge=10)
    min_lof_neighbors: int = Field(default=2, ge=1)
    max_lof_neighbors: int = Field(default=20, ge=1)

    # Fixed seed so a given baseline always produces an identical model.
    # Reproducibility is a correctness property for a security tool: the same
    # inputs must yield the same verdict.
    random_state: int = 42

    baseline_samples: int = Field(default=30, ge=2)
    baseline_interval_seconds: float = Field(default=0.5, gt=0.0)

    # Model-health tiers, from aura_core.scan_once.
    health_healthy_samples: int = Field(default=30, ge=1)
    health_limited_samples: int = Field(default=10, ge=1)

    @field_validator("features")
    @classmethod
    def _features_non_empty_and_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("at least one feature is required")
        if len(set(value)) != len(value):
            raise ValueError(f"duplicate feature names in {value!r}")
        return value

    @model_validator(mode="after")
    def _consistency(self) -> DetectionConfig:
        if self.min_lof_neighbors > self.max_lof_neighbors:
            raise ValueError(
                f"min_lof_neighbors={self.min_lof_neighbors} exceeds "
                f"max_lof_neighbors={self.max_lof_neighbors}"
            )
        if self.health_limited_samples > self.health_healthy_samples:
            raise ValueError(
                f"health_limited_samples={self.health_limited_samples} exceeds "
                f"health_healthy_samples={self.health_healthy_samples}"
            )
        if self.baseline_samples < self.min_baseline_samples:
            raise ValueError(
                f"baseline_samples={self.baseline_samples} is below "
                f"min_baseline_samples={self.min_baseline_samples}; training "
                f"would always fail"
            )
        return self


# ======================================================================
# Sensor configuration
# ======================================================================


class SensorConfig(BaseModel):
    """
    Telemetry collection settings.

    Source: privacy_monitor.py lines 147-150 for the caps, sensors.py for the
    sampling intervals.
    """

    model_config = {"extra": "forbid"}

    # Interval for the background collector introduced in Phase 8. The
    # current application has no continuous collection at all, so this value
    # has no precedent in the existing code; 5 seconds balances
    # responsiveness against overhead and will be revised against the
    # measurements taken in Phase 13.
    collection_interval_seconds: float = Field(default=5.0, ge=0.01, le=3600.0)

    # Blocking psutil sampling windows. These are the dominant fixed cost of
    # a scan, so they are configuration rather than magic numbers.
    cpu_sample_interval_seconds: float = Field(default=0.2, gt=0.0, le=5.0)

    # Empty string means auto-detect via %SystemDrive%.
    disk_path: str = ""

    # ------------------------------------------------------------------
    # Webcam probe â€” privacy sensitive
    # ------------------------------------------------------------------
    # Disabled by default and must stay that way. cv2.VideoCapture physically
    # powers on the camera and illuminates its activity LED, so probing for
    # availability has a real privacy cost and also blocks other applications
    # from using the device while held. Camera availability is never treated
    # as evidence of camera misuse.
    camera_probe_enabled: bool = False
    camera_probe_index: int = Field(default=0, ge=0)

    # ------------------------------------------------------------------
    # Sensitive-file inventory
    # ------------------------------------------------------------------
    max_files_scanned: int = Field(default=2500, ge=1)
    max_file_results: int = Field(default=250, ge=1)

    # The risk engine only ever consumes the *count*. Retaining absolute
    # paths to the user's documents in order to display a number violates
    # data minimisation, so retention defaults to off.
    retain_sensitive_file_paths: bool = False

    # The inventory walks the filesystem, so it does not belong on the fast
    # telemetry loop.
    file_scan_interval_seconds: float = Field(default=300.0, ge=1.0)

    # ------------------------------------------------------------------
    # Network / process caps
    # ------------------------------------------------------------------
    max_endpoints: int = Field(default=100, ge=1)
    max_connection_records: int = Field(default=150, ge=1)
    max_process_records: int = Field(default=100, ge=1)

    # Source: privacy_monitor._get_process_baseline â€” median of the last 50
    # observations, requiring at least 5 valid samples before a baseline is
    # considered to exist.
    process_baseline_window: int = Field(default=50, ge=2)
    process_baseline_min_samples: int = Field(default=5, ge=2)

    def resolved_disk_path(self) -> str:
        """Return the configured disk path, auto-detecting if unset."""
        return self.disk_path.strip() or default_system_drive()


# ======================================================================
# Alerting
# ======================================================================


class AlertConfig(BaseModel):
    """
    Alert engine behaviour. Consumed from Phase 6 onward.

    No precedent exists in the current code, which has no alert lifecycle â€”
    these are initial values to be tuned once real event volumes are
    observable.
    """

    model_config = {"extra": "forbid"}

    enabled: bool = True

    # Events below this severity are recorded but do not raise an alert.
    min_severity: SeverityName = "MEDIUM"

    # Identical alerts inside this window collapse into one with an
    # incremented occurrence count.
    dedup_window_seconds: float = Field(default=300.0, ge=0.0)

    # Minimum spacing between notifications for the same alert signature.
    cooldown_seconds: float = Field(default=600.0, ge=0.0)

    # Repeated occurrences beyond this count escalate one severity level.
    escalation_repeat_count: int = Field(default=3, ge=2)

    # Bounded to prevent unbounded memory growth.
    max_active_alerts: int = Field(default=500, ge=1)


# ======================================================================
# Storage
# ======================================================================


class StorageConfig(BaseModel):
    """
    Database and retention settings.

    Replaces the current design in which ``logger.append_log`` rewrites the
    entire CSV on every event (audit finding F6).
    """

    model_config = {"extra": "forbid"}

    # Empty means SQLite at the resolved user-data path. Any SQLAlchemy URL
    # is accepted, which is what keeps PostgreSQL available later without
    # committing to it now.
    database_url: str = ""

    retention_days: int = Field(default=90, ge=1)
    metrics_retention_days: int = Field(default=14, ge=1)
    cleanup_interval_hours: int = Field(default=24, ge=1)

    # SQLite serialises writers. A busy timeout lets a concurrent writer wait
    # rather than fail immediately, which matters once a background collector
    # and an API request can write at the same time.
    sqlite_busy_timeout_seconds: float = Field(default=5.0, ge=0.0)

    # WAL allows readers to proceed during a write â€” appropriate for a
    # write-often, read-often local application.
    sqlite_journal_mode: Literal["WAL", "DELETE", "TRUNCATE", "PERSIST", "MEMORY"] = "WAL"

    # Bounded queue between the collector and the writer. Bounded, because an
    # unbounded queue converts a slow disk into an out-of-memory crash.
    write_queue_max_size: int = Field(default=1000, ge=1)

    # Events are flushed in batches to reduce transaction overhead.
    write_batch_size: int = Field(default=25, ge=1)

    def resolved_database_url(self, paths: AuraPaths) -> str:
        """Return the configured URL, defaulting to SQLite in user data."""
        explicit = self.database_url.strip()
        if explicit:
            return explicit
        return f"sqlite:///{paths.database_path.as_posix()}"


# ======================================================================
# Logging
# ======================================================================


class LogConfig(BaseModel):
    """Structured logging with rotation and redaction."""

    model_config = {"extra": "forbid"}

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # JSON is preferable for machine parsing; plain text is far easier to read
    # during development, so it is the default.
    json_format: bool = False

    console_enabled: bool = True
    file_enabled: bool = True

    max_bytes: int = Field(default=5 * 1024 * 1024, ge=1024)
    backup_count: int = Field(default=5, ge=0)

    # Redaction of credentials and usernames. Configurable for testing, but
    # disabling it in production would risk writing sensitive values to disk.
    redact_enabled: bool = True

    # Replaces the username inside Windows user paths so that log files do
    # not carry the account name of the person running AURA.
    redact_user_paths: bool = True


# ======================================================================
# API
# ======================================================================


class ApiConfig(BaseModel):
    """
    HTTP surface settings. Consumed from Phase 9 onward.

    The current application has no HTTP API, so this is the one genuinely new
    attack surface in the project and its defaults are deliberately
    restrictive.
    """

    model_config = {"extra": "forbid"}

    # Loopback only. Binding to 0.0.0.0 would expose Windows telemetry to
    # the local network with no authentication.
    host: str = "127.0.0.1"
    port: int = Field(default=8787, ge=1024, le=65535)

    # Explicit, deliberate opt-in required before a non-loopback bind is
    # permitted. See the validator below.
    allow_network_exposure: bool = False

    # Vite's dev server default. Production serves the built frontend from
    # the same origin, so no CORS entry is needed there.
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://localhost:4173",
    )

    rate_limit_per_minute: int = Field(default=240, ge=1)

    # OpenAPI docs are useful in development and are an information-disclosure
    # surface in production, so they follow the environment.
    docs_enabled: bool | None = None

    websocket_max_queue: int = Field(default=250, ge=1)
    websocket_heartbeat_seconds: float = Field(default=20.0, gt=0.0)

    @model_validator(mode="after")
    def _guard_network_exposure(self) -> ApiConfig:
        if self.host not in LOOPBACK_HOSTS and not self.allow_network_exposure:
            raise ValueError(
                f"api.host is set to {self.host!r}, which is not loopback. "
                f"Binding AURA to a non-loopback address exposes Windows "
                f"telemetry to the network. If that is genuinely intended, "
                f"set AURA_API__ALLOW_NETWORK_EXPOSURE=true and configure "
                f"authentication first."
            )
        if self.host == "0.0.0.0":  # noqa: S104 - explicitly rejected, not bound
            raise ValueError(
                "api.host must not be 0.0.0.0. Bind to a specific interface "
                "address so the exposure is explicit and auditable."
            )
        return self


# ======================================================================
# Root settings
# ======================================================================


class Settings(BaseSettings):
    """
    The single configuration object for AURA.

    Obtain it via :func:`get_settings` rather than constructing it, so the
    whole process shares one validated instance.
    """

    model_config = SettingsConfigDict(
        env_prefix="AURA_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )

    app_name: str = "AURA"
    version: str = __version__

    environment: Literal["development", "production"] = "development"

    # DEMO / SIMULATION MODE.
    #
    # When true, synthetic telemetry may be generated for UI development. Any
    # value produced in this mode must be labelled as simulated in every
    # surface that displays it, and must never be written to the production
    # event store. Defaults off; production must never enable it.
    demo_mode: bool = False

    sensors: SensorConfig = Field(default_factory=SensorConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    alerts: AlertConfig = Field(default_factory=AlertConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)

    @field_validator("demo_mode")
    @classmethod
    def _demo_mode_never_in_production(
        cls, value: bool, info: ValidationInfo
    ) -> bool:
        if value and info.data.get("environment") == "production":
            raise ValueError(
                "demo_mode cannot be enabled when environment=production. "
                "Simulated telemetry must never reach a production event "
                "store or dashboard."
            )
        return value

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def paths(self) -> AuraPaths:
        return get_paths()

    def docs_are_enabled(self) -> bool:
        """OpenAPI docs: explicit setting if given, else development only."""
        if self.api.docs_enabled is not None:
            return self.api.docs_enabled
        return not self.is_production

    def database_url(self) -> str:
        return self.storage.resolved_database_url(self.paths)

    def summary(self) -> dict[str, object]:
        """
        Non-sensitive summary for diagnostics and the /api/health endpoint.

        Deliberately excludes anything credential-like. The database URL is
        reduced to its scheme so a future PostgreSQL DSN containing a password
        can never be echoed back to a client.
        """
        return {
            "app_name": self.app_name,
            "version": self.version,
            "environment": self.environment,
            "demo_mode": self.demo_mode,
            "scoring_version": self.risk.scoring_version,
            "feature_schema_version": self.detection.feature_schema_version,
            "features": list(self.detection.features),
            "collection_interval_seconds": self.sensors.collection_interval_seconds,
            "camera_probe_enabled": self.sensors.camera_probe_enabled,
            "retain_sensitive_file_paths": self.sensors.retain_sensitive_file_paths,
            "disk_path": self.sensors.resolved_disk_path(),
            "database_backend": self.database_url().split(":", 1)[0],
            "retention_days": self.storage.retention_days,
            "log_level": self.log.level,
            "api_host": self.api.host,
            "api_port": self.api.port,
            "docs_enabled": self.docs_are_enabled(),
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the process-wide settings instance.

    Cached so validation runs once and every component observes the same
    configuration. Tests that patch the environment should call
    ``get_settings.cache_clear()`` afterwards.
    """
    return Settings()
