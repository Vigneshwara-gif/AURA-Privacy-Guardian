/**
 * Typed contracts for AURA background agent state, lifecycle, and subsystem health.
 */

export type AgentState =
  | 'STOPPED'
  | 'STARTING'
  | 'RUNNING'
  | 'DEGRADED'
  | 'STOPPING'
  | 'CRASHING'
  | 'FAILED';

export type SensorStatus = 'OK' | 'WARN' | 'FAIL' | 'UNKNOWN' | 'UNAVAILABLE';

export interface AgentStatus {
  state: AgentState;
  version: string;
  pid?: number | null;
  started_at?: string | null;
  uptime_seconds: number;
  last_successful_collection?: string | null;
  last_persistence?: string | null;
  consecutive_failures: number;
  degraded_components: string[];
}

export interface CollectionHealth {
  last_collection_time?: string | null;
  interval_seconds: number;
  consecutive_failures: number;
  loop_duration_ms: number;
}

export interface StorageHealth {
  status: string;
  backend: string;
  journal_mode: string;
  total_events: number;
  db_size_bytes: number;
  wal_size_bytes: number;
  last_write_time?: string | null;
}

export interface DetectionHealth {
  model_status: string;
  model_version: string;
  feature_schema_version: number;
  features: string[];
  training_samples: number;
  last_inference_time?: string | null;
}

export interface SensorHealthItem {
  name: string;
  status: SensorStatus;
  value: string;
  detail: string;
  last_seen: string;
}

export interface DiagnosticsHealth {
  error_count: number;
  degraded_components: string[];
}

export interface AgentHealthResponse {
  agent: AgentStatus;
  collection: CollectionHealth;
  storage: StorageHealth;
  detection: DetectionHealth;
  sensors: SensorHealthItem[];
  diagnostics: DiagnosticsHealth;
}
