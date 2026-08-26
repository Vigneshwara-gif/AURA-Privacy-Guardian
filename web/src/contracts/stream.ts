/**
 * WebSocket live-stream message models.
 */

import type { AgentStatus, SensorHealthItem } from './agent';
import type { ScanStatusResponse, SecurityEventResponse, TelemetryResponse } from './api';
import type { ApiErrorResponse } from './errors';

export type StreamMessageType =
  | 'telemetry_tick'
  | 'security_event'
  | 'sensor_health_change'
  | 'agent_status_change'
  | 'scan_progress'
  | 'heartbeat'
  | 'error';

export interface BaseStreamMessage {
  version: number;
  timestamp: string;
}

export interface TelemetryTickMessage extends BaseStreamMessage {
  type: 'telemetry_tick';
  payload: TelemetryResponse;
}

export interface SecurityEventMessage extends BaseStreamMessage {
  type: 'security_event';
  payload: SecurityEventResponse;
}

export interface SensorHealthChangeMessage extends BaseStreamMessage {
  type: 'sensor_health_change';
  payload: SensorHealthItem[];
}

export interface AgentStatusChangeMessage extends BaseStreamMessage {
  type: 'agent_status_change';
  payload: AgentStatus;
}

export interface ScanProgressMessage extends BaseStreamMessage {
  type: 'scan_progress';
  payload: ScanStatusResponse;
}

export interface HeartbeatMessage extends BaseStreamMessage {
  type: 'heartbeat';
  sequence: number;
}

export interface ErrorStreamMessage extends BaseStreamMessage {
  type: 'error';
  payload: ApiErrorResponse;
}

export type LiveStreamMessage =
  | TelemetryTickMessage
  | SecurityEventMessage
  | SensorHealthChangeMessage
  | AgentStatusChangeMessage
  | ScanProgressMessage
  | HeartbeatMessage
  | ErrorStreamMessage;
