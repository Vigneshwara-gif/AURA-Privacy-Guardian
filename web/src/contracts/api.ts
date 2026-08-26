/**
 * REST API query parameters, command payloads, and response contracts.
 */

export type PrivacyHardwareStatus =
  | 'ACTIVE'
  | 'INACTIVE'
  | 'UNAVAILABLE'
  | 'PERMISSION_LIMITED'
  | 'UNKNOWN';

export type ScanState = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type ScanStage =
  | 'INITIALIZING'
  | 'COLLECTING_SENSORS'
  | 'RUNNING_DETECTION'
  | 'EVALUATING_RISK'
  | 'PERSISTING'
  | 'FINALIZING';

export interface TelemetryResponse {
  timestamp: string;
  cpu_percent: number;
  cpu_cores: number;
  cpu_frequency_mhz: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_free_gb: number;
  disk_total_gb: number;
  disk_path: string;
  net_upload_kbps: number;
  net_download_kbps: number;
  process_count: number;
  established_connections: number;
  listening_connections: number;
  remote_connections: number;
  camera_status: PrivacyHardwareStatus;
  microphone_status: PrivacyHardwareStatus;
}

export interface EvidenceItem {
  signal: string;
  severity: string;
  value?: unknown;
  unit?: string | null;
  weight: number;
}

export interface RiskResponse {
  risk_score: number;
  severity: string;
  reasons: string[];
  evidence: EvidenceItem[];
  privacy_flags: string[];
  compound_exfiltration_flag: boolean;
}

export interface SecurityEventResponse {
  event_id: string;
  timestamp: string;
  event_type: string;
  severity: string;
  risk_score: number;
  source: string;
  summary: string;
  evidence: Array<Record<string, unknown>>;
  confidence?: number | null;
  affected_resource: string;
  correlation_id: string;
  schema_version: number;
  incident_id?: string;
  is_resolved?: boolean;
}

export interface ScanStatusResponse {
  scan_id: string;
  state: ScanState;
  stage: ScanStage;
  started_at: string;
  completed_at?: string | null;
  elapsed_seconds: number;
  result_summary?: string | null;
  risk_score?: number | null;
  severity?: string | null;
  is_demo: boolean;
  error_code?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface TelemetrySeriesPoint {
  timestamp: string;
  value: number;
}

export interface ScanRequest {
  probe_camera?: boolean;
  probe_microphone?: boolean;
  is_demo?: boolean;
}

export interface MonitoringStartRequest {
  interval_seconds?: number;
}

export interface MonitoringStopRequest {
  reason?: string;
}

export interface EventAcknowledgeRequest {
  event_id: string;
  acknowledged_by?: string;
  notes?: string;
}
