"""
Pydantic API and Stream Contracts for System Posture, Process Trees, Persistence, and Scans.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


class CpuCoreResponse(BaseModel):
    core_index: int
    utilization_percent: float


class DiskPartitionResponse(BaseModel):
    mountpoint: str
    device: str
    fstype: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


class SystemTelemetryResponse(BaseModel):
    timestamp: str
    os_name: str
    os_version: str
    os_build: str
    os_display_version: str
    architecture: str
    hostname: str
    logged_in_user: str
    boot_time_iso: str
    uptime_seconds: float
    cpu_model: str
    cpu_physical_cores: int
    cpu_logical_cores: int
    cpu_frequency_current_mhz: float
    cpu_frequency_max_mhz: float
    cpu_overall_percent: float
    cpu_cores: list[CpuCoreResponse] = Field(default_factory=list)
    memory_total_gb: float
    memory_used_gb: float
    memory_available_gb: float
    memory_percent: float
    swap_total_gb: float
    swap_used_gb: float
    partitions: list[DiskPartitionResponse] = Field(default_factory=list)


class ProcessTreeNodeResponse(BaseModel):
    pid: int
    name: str
    exe_path: str | None = None
    parent_pid: int | None = None
    created_time: str
    cpu_percent: float
    memory_rss_bytes: int
    status: str
    username: str | None = None
    is_elevated: bool
    cmdline: str | None = None
    num_threads: int = 0
    num_handles: int = 0
    sha256_hash: str | None = None
    children: list[ProcessTreeNodeResponse] = Field(default_factory=list)


class StartupAppResponse(BaseModel):
    name: str
    command: str
    source_location: str
    user_context: str
    is_enabled: bool = True
    executable_path: str | None = None
    exists_on_disk: bool = True


class WindowsServiceResponse(BaseModel):
    name: str
    display_name: str
    status: str
    start_type: str
    bin_path: str | None = None
    username: str | None = None


class ScheduledTaskResponse(BaseModel):
    task_name: str
    next_run_time: str
    status: str
    author: str | None = None


class PersistenceInventoryResponse(BaseModel):
    timestamp: str
    startup_apps: list[StartupAppResponse] = Field(default_factory=list)
    services_count: int
    running_services_count: int
    services: list[WindowsServiceResponse] = Field(default_factory=list)
    scheduled_tasks_count: int
    scheduled_tasks: list[ScheduledTaskResponse] = Field(default_factory=list)


class DefenderStatusResponse(BaseModel):
    is_installed: bool
    antivirus_enabled: bool
    realtime_protection_enabled: bool
    ioav_protection_enabled: bool
    antispyware_enabled: bool
    signature_version: str | None
    quick_scan_age_days: int | None
    full_scan_age_days: int | None


class FirewallStatusResponse(BaseModel):
    domain_profile_enabled: bool
    private_profile_enabled: bool
    public_profile_enabled: bool
    all_profiles_secure: bool


class SecurityPostureResponse(BaseModel):
    timestamp: str
    defender: DefenderStatusResponse
    firewall: FirewallStatusResponse
    is_reboot_pending: bool
    reboot_reasons: list[str] = Field(default_factory=list)
    secure_boot_enabled: bool | None
    tpm_present: bool | None
    uac_enabled: bool
    overall_posture_score: int


class SecurityFindingModel(BaseModel):
    finding_id: str
    timestamp: str
    title: str
    category: str
    severity: str
    confidence: float
    affected_resource: str
    evidence: list[str] = Field(default_factory=list)
    explanation: str
    recommendation: str
    remediation_status: str = "OPEN"  # OPEN, RESOLVED, IGNORED


class FullScanReportResponse(BaseModel):
    scan_id: str
    started_at: str
    completed_at: str
    duration_seconds: float
    total_checks_performed: int
    categories_scanned: list[str] = Field(default_factory=list)
    findings: list[SecurityFindingModel] = Field(default_factory=list)
    overall_security_score: int
    privacy_health_score: int
    composite_risk_score: int
    risk_severity: str
    summary_narrative: str
