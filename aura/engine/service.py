"""
AURA Core Engine Service.

Orchestrates continuous telemetry collection, dynamic behavioral baselines,
unsupervised ML anomaly inference, multi-signal correlation, process/network intelligence,
hardened explainable risk evaluation, and SQLite WAL persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from typing import Any
import uuid
import numpy as np

from aura.core.config import Settings, get_settings
from aura.core.paths import AuraPaths, get_paths
from aura.engine.baseline import HostBehaviorBaseline
from aura.engine.correlation import MultiSignalCorrelator
from aura.engine.risk_hardened import HardenedRiskEngine
from aura.models.persistence import load_or_train_model
from aura.models.types import (
    PrivacyHardwareStatus,
    ScanResult,
    SecurityEvent,
    TelemetrySnapshot,
)
from aura.sensors.collector import SensorCollector
from aura.sensors.network_intel import ConnectionInfo, NetworkIntelligenceCollector
from aura.sensors.process_intel import ProcessInfo, ProcessIntelligenceCollector
from aura.storage.sqlite import StorageEngine
from model import AURAModel

logger = logging.getLogger(__name__)


class AuraEngineService:
    """
    Central security engine coordinating telemetry, baselines, correlation, risk, and storage.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        paths: AuraPaths | None = None,
        storage: StorageEngine | None = None,
        collector: SensorCollector | None = None,
        model: AURAModel | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.paths = paths or get_paths()
        self.storage = storage or StorageEngine(self.paths.database_path)
        self.collector = collector or SensorCollector(
            sample_interval=self.settings.sensors.cpu_sample_interval_seconds
        )

        self.baseline = HostBehaviorBaseline(warmup_samples=10)
        self.correlator = MultiSignalCorrelator(time_window_seconds=60)

        model_artifact_path = self.paths.models_dir / "aura_model_v1.joblib"
        if not model_artifact_path.exists():
            shared_art = self.paths.install_root / "models" / "aura_model_v1.joblib"
            if shared_art.exists():
                model_artifact_path = shared_art

        baseline_path = self.paths.legacy_baseline_csv
        if not baseline_path.exists():
            baseline_path = self.paths.install_root / "data" / "baseline.csv"

        if model is not None:
            self.model = model
        else:
            self.model = load_or_train_model(
                baseline_csv_path=baseline_path,
                artifact_path=model_artifact_path,
                contamination=self.settings.detection.contamination,
            )

        self._is_running = False

    def start(self) -> None:
        """Start the engine service."""
        self._is_running = True
        logger.info("AURA Engine Service started successfully.")

    def stop(self) -> None:
        """Stop the engine service."""
        self._is_running = False
        logger.info("AURA Engine Service stopped.")

    def reset_baselines(self) -> None:
        """Reset dynamic baselines (e.g. after sleep/resume or user command)."""
        self.collector.reset_baselines()
        self.baseline.reset_all()
        logger.info("Engine behavioral baselines reset.")

    def scan_once(
        self,
        probe_camera: bool = False,
        probe_microphone: bool = False,
        synthetic: dict[str, Any] | None = None,
        is_demo: bool = False,
    ) -> ScanResult:
        """
        Execute a single security assessment cycle using dynamic baselines,
        multi-signal correlation, and hardened explainable risk evaluation.
        """
        start_time = time.time()
        scan_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()

        # 1. Collect Telemetry Snapshot
        if synthetic is not None:
            telemetry = TelemetrySnapshot(
                timestamp=started_at,
                cpu_percent=float(synthetic.get("CPU", 92.4)),
                net_upload_kbps=float(synthetic.get("Net", 4820.0)),
                camera_status=PrivacyHardwareStatus.AVAILABLE if synthetic.get("Cam") else PrivacyHardwareStatus.NOT_DETECTED,
                process_count=int(synthetic.get("Process_Count", 412)),
                remote_connections=int(synthetic.get("Remote_Connections", 88)),
            )
            is_demo = True
            top_procs: list[ProcessInfo] = []
            active_conns: list[ConnectionInfo] = []
        else:
            telemetry = self.collector.collect_snapshot(
                probe_camera=probe_camera or self.settings.sensors.camera_probe_enabled,
                probe_microphone=probe_microphone,
            )
            top_procs = ProcessIntelligenceCollector.get_top_processes(limit=5)
            active_conns = NetworkIntelligenceCollector.get_active_connections(limit=20)

        # 2. Dynamic Behavioral Baseline Assessment
        assessments = self.baseline.assess_snapshot(telemetry, update=not is_demo)

        # 3. Unsupervised ML Anomaly Inference
        cam_int = 1 if telemetry.camera_status == PrivacyHardwareStatus.AVAILABLE else 0
        feature_vector = np.array([[telemetry.cpu_percent, telemetry.net_upload_kbps, cam_int]], dtype=float)

        try:
            scaled_vector = self.model.scaler.transform(feature_vector)
            if_score = float(self.model.isolation_forest.decision_function(scaled_vector)[0])
            lof_score = float(self.model.lof.decision_function(scaled_vector)[0])

            if_fired = bool(if_score < 0.0)
            lof_fired = bool(lof_score < 0.0)
            is_anomaly = bool(if_fired or lof_fired)
            ml_intensity = max(0.0, -min(if_score, lof_score))

            feature_names = ["CPU", "Net", "Cam"]
            abs_scaled = np.abs(scaled_vector[0])
            strongest_idx = int(np.argmax(abs_scaled))
            strongest_feature = feature_names[strongest_idx]
            deviation = float(abs_scaled[strongest_idx])
        except Exception as exc:
            logger.warning("ML inference fallback triggered: %s", exc)
            if_score, lof_score, ml_intensity, deviation = 0.0, 0.0, 0.0, 0.0
            is_anomaly = False
            strongest_feature = "CPU"

        # 4. Multi-Signal Correlation Engine
        insights = self.correlator.correlate(
            snapshot=telemetry,
            assessments=assessments,
            top_processes=top_procs,
            connections=active_conns,
        )

        # 5. Hardened Explainable Risk Evaluation
        risk_result = HardenedRiskEngine.evaluate(
            snapshot=telemetry,
            assessments=assessments,
            insights=insights,
            ml_anomaly=is_anomaly,
            ml_intensity=ml_intensity,
        )

        risk_score = risk_result.risk_score
        severity = risk_result.severity
        reasons = risk_result.reasons
        privacy_flags = risk_result.privacy_flags

        # Format evidence payloads
        evidence: list[dict[str, Any]] = [
            {
                "signal": c.signal,
                "source": c.source,
                "weight": c.points,
                "severity": c.severity,
                "reason": c.reason,
                "observed_value": str(c.observed_value),
                "baseline_reference": str(c.baseline_reference),
                "reliability": c.reliability,
            }
            for c in risk_result.contributors
        ]

        # 6. Construct Deterministic Incident Identity & Security Event
        if risk_result.compound_exfiltration_flag:
            incident_id = "inc_privacy_compound_exfiltration"
        elif risk_result.contributors:
            top_sig = risk_result.contributors[0].signal.lower().replace(" ", "_").replace("-", "_")
            incident_id = f"inc_{top_sig}"
        elif is_anomaly:
            incident_id = "inc_ml_anomaly_detection"
        else:
            incident_id = "inc_baseline_nominal"

        is_resolved = severity in {"NORMAL", "LOW"} and not (is_anomaly or risk_result.contributors)

        event_id = str(uuid.uuid4())
        sec_event = SecurityEvent(
            event_id=event_id,
            timestamp=started_at,
            event_type="SECURITY_ASSESSMENT",
            severity=severity,
            risk_score=risk_score,
            source="AuraEngineService",
            summary=risk_result.summary,
            evidence=evidence,
            confidence=0.95,
            affected_resource=f"{telemetry.disk_path} (Host)",
            correlation_id=scan_id,
            schema_version=2,
            incident_id=incident_id,
            is_resolved=is_resolved,
        )

        # 7. Persist to Storage
        if not is_demo:
            self.storage.record_telemetry(telemetry)
            self.storage.record_security_event(sec_event)
            self.storage.record_scan_run(
                scan_id=scan_id,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                trigger_source="engine_service",
                is_demo=False,
                is_success=True,
                risk_score=risk_score,
                severity=severity,
            )

        duration_ms = (time.time() - start_time) * 1000.0

        return ScanResult(
            scan_id=scan_id,
            timestamp=started_at,
            telemetry=telemetry,
            event=sec_event,
            is_demo=is_demo,
            is_anomaly=is_anomaly,
            if_score=if_score,
            lof_score=lof_score,
            ml_intensity=ml_intensity,
            strongest_feature=strongest_feature,
            deviation=deviation,
            privacy_flags=privacy_flags,
            reasons=reasons,
            duration_ms=duration_ms,
        )

    def get_status(self) -> dict[str, Any]:
        """Return engine operational status summary."""
        event_counts = self.storage.get_event_counts_by_severity()
        total_events = self.storage.get_event_count()
        return {
            "status": "OPERATIONAL" if self._is_running else "STANDBY",
            "model_version": "2.0.0",
            "training_samples": getattr(self.model, "training_samples", 0),
            "database_path": str(self.storage.db_path),
            "total_stored_events": total_events,
            "event_counts_by_severity": event_counts,
            "baselines": self.baseline.get_summary(),
        }
