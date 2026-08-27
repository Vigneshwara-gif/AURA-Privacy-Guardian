"""
Pydantic API contracts for AURA MASTER 2 Intelligence Subsystem.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class ProcessIdentityDNAResponse(BaseModel):
    pid: int
    name: str
    exe_path: str | None = None
    exe_exists: bool
    sha256_hash: str | None = None
    parent_pid: int | None = None
    parent_name: str | None = None
    child_pids: list[int] = Field(default_factory=list)
    created_time: str
    lifetime_seconds: float
    is_elevated: bool
    username: str | None = None
    cmdline: str | None = None


class ProcessExecutionDNAResponse(BaseModel):
    cpu_percent: float
    memory_rss_bytes: int
    memory_mb: float
    num_threads: int
    num_handles: int
    status: str


class ProcessNetworkDNAResponse(BaseModel):
    connection_count: int
    connections: list[dict[str, Any]] = Field(default_factory=list)
    listening_ports: list[int] = Field(default_factory=list)
    remote_endpoints: list[str] = Field(default_factory=list)


class ProcessPrivacyDNAResponse(BaseModel):
    camera_access_detected: bool
    microphone_access_detected: bool
    privacy_events_count: int
    last_privacy_access: str | None = None


class ProcessSecurityDNAResponse(BaseModel):
    rules_triggered: list[str] = Field(default_factory=list)
    ml_anomaly_score: float
    baseline_deviation: float
    risk_score: int
    risk_level: str
    evidences: list[dict[str, Any]] = Field(default_factory=list)


class ProcessDNAResponse(BaseModel):
    timestamp: str
    pid: int
    identity: ProcessIdentityDNAResponse
    execution: ProcessExecutionDNAResponse
    network: ProcessNetworkDNAResponse
    privacy: ProcessPrivacyDNAResponse
    security: ProcessSecurityDNAResponse


class NetworkEndpointResponse(BaseModel):
    ip: str
    port: int
    classification: str
    protocol: str
    state: str
    pid: int | None = None
    process_name: str | None = None
    first_observed: str
    last_observed: str
    reputation_status: str


class NetworkExposureFindingResponse(BaseModel):
    port: int
    protocol: str
    bind_address: str
    pid: int | None = None
    process_name: str | None = None
    service_name: str | None = None
    is_public_exposure: bool
    firewall_profile_active: bool
    severity: str
    title: str
    recommendation: str


class NetworkInvestigationResponse(BaseModel):
    timestamp: str
    total_connections: int
    established_count: int
    listening_count: int
    remote_public_count: int
    active_endpoints: list[NetworkEndpointResponse] = Field(default_factory=list)
    exposure_findings: list[NetworkExposureFindingResponse] = Field(default_factory=list)
    summary: str


class PersistenceAnalysisItemResponse(BaseModel):
    item_type: str
    name: str
    executable_path: str | None = None
    location_or_trigger: str
    is_suspicious_location: bool
    exists_on_disk: bool
    risk_severity: str
    evidence_notes: list[str] = Field(default_factory=list)


class PersistenceAnalysisResponse(BaseModel):
    timestamp: str
    total_startup_apps: int
    total_services: int
    total_scheduled_tasks: int
    analyzed_items: list[PersistenceAnalysisItemResponse] = Field(default_factory=list)
    suspicious_count: int
    summary: str


class ThreatHuntMatchResponse(BaseModel):
    match_id: str
    hunt_id: str
    timestamp: str
    entity: str
    severity: str
    title: str
    evidence_details: list[str] = Field(default_factory=list)
    suggested_remediation: str


class ThreatHuntResultResponse(BaseModel):
    timestamp: str
    hunts_executed: int
    matches_found: int
    matches: list[ThreatHuntMatchResponse] = Field(default_factory=list)
    summary: str


class FeatureExplanationResponse(BaseModel):
    feature_name: str
    observed_raw: float
    observed_normalized: float
    nominal_range_min: float
    nominal_range_max: float
    is_outlier: bool
    contribution_weight: float
    explanation_text: str


class AnomalyExplanationResponse(BaseModel):
    timestamp: str
    is_anomaly: bool
    combined_score: float
    isolation_forest_score: float
    lof_score: float
    confidence: float
    primary_signal: str | None = None
    feature_explanations: list[FeatureExplanationResponse] = Field(default_factory=list)
    narrative: str


class TimelineItemResponse(BaseModel):
    item_id: str
    timestamp: str
    event_type: str
    severity: str
    title: str
    entity_name: str
    entity_id: str
    details: dict[str, Any] = Field(default_factory=dict)


class SecurityIncidentResponse(BaseModel):
    incident_id: str
    title: str
    severity: str
    state: str
    created_at: str
    updated_at: str
    summary: str
    affected_entities: list[str] = Field(default_factory=list)
    findings_count: int
    findings: list[dict[str, Any]] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    action_history: list[dict[str, Any]] = Field(default_factory=list)


class UpdateIncidentStateRequest(BaseModel):
    state: Literal["NEW", "INVESTIGATING", "ACKNOWLEDGED", "CONTAINED", "RESOLVED", "FALSE_POSITIVE"]
    note: str = ""


class TerminateProcessRequest(BaseModel):
    pid: int


class OpenShortcutRequest(BaseModel):
    shortcut_type: Literal["CAMERA", "MICROPHONE", "DEFENDER", "FIREWALL", "UPDATE", "NETWORK"]


class ResponseActionResultResponse(BaseModel):
    action_id: str
    action_type: str
    target: str
    success: bool
    message: str
    timestamp: str
    actor: str
    details: dict[str, Any] = Field(default_factory=dict)


class SecurityAlertResponse(BaseModel):
    alert_id: str
    title: str
    severity: str
    timestamp: str
    source: str
    summary: str
    entity_id: str
    finding_id: str | None = None
    incident_id: str | None = None
    is_acknowledged: bool
    acknowledged_by: str | None = None
    acknowledged_at: str | None = None


class AnalyticsMetricsResponse(BaseModel):
    timestamp: str
    time_window: str
    current_security_score: int
    current_privacy_score: int
    current_composite_risk: int
    total_findings_count: int
    open_findings_count: int
    resolved_findings_count: int
    critical_findings_count: int
    high_findings_count: int
    medium_findings_count: int
    low_findings_count: int
    total_incidents_count: int
    open_incidents_count: int
    score_history_points: list[dict[str, Any]] = Field(default_factory=list)
    findings_by_category: dict[str, int] = Field(default_factory=dict)


class FullSecurityAuditReportResponse(BaseModel):
    report_id: str
    generated_at: str
    hostname: str
    os_name: str
    os_build: str
    executive_summary: str
    overall_security_score: int
    privacy_health_score: int
    composite_risk_score: int
    risk_level: str
    sections: dict[str, Any] = Field(default_factory=dict)
