/**
 * Strongly typed REST API client for AURA Local API.
 */

import type {
  AgentHealthResponse,
  AgentStatus,
  SensorHealthItem,
} from '../contracts/agent';
import type {
  EventAcknowledgeRequest,
  MonitoringStartRequest,
  MonitoringStopRequest,
  PaginatedResponse,
  RiskResponse,
  ScanRequest,
  ScanStatusResponse,
  SecurityEventResponse,
  TelemetryResponse,
  TelemetrySeriesPoint,
} from '../contracts/api';
import type { SessionHandshakeRequest, SessionHandshakeResponse } from '../contracts/auth';
import type { ApiErrorResponse } from '../contracts/errors';
import { AuthService } from './authService';

export class AuraApiError extends Error {
  public readonly code: string;
  public readonly timestamp: string;
  public readonly details?: Record<string, unknown> | null;
  public readonly status: number;

  constructor(errorResponse: ApiErrorResponse, status: number) {
    super(errorResponse.message);
    this.name = 'AuraApiError';
    this.code = errorResponse.code;
    this.timestamp = errorResponse.timestamp;
    this.details = errorResponse.details;
    this.status = status;
  }
}

interface RequestOptions extends RequestInit {
  _isRetry?: boolean;
}

export class ApiClient {
  private static baseUrl = '/api/v1';

  static {
    AuthService.setExchangeHandler((code: string) => ApiClient.exchangeSession(code));
  }

  private static async request<T>(
    path: string,
    options: RequestOptions = {},
    timeoutMs = 8000
  ): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    // Ensure session is authenticated for protected endpoints
    if (path !== '/auth/session' && !headers['Authorization'] && !headers['X-AURA-Bootstrap']) {
      const token = await AuthService.ensureAuthenticated();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...options,
        headers,
        signal: controller.signal,
      });

      if (!response.ok) {
        if (response.status === 401 && path !== '/auth/session' && !options._isRetry) {
          // Token expired or invalid; clear and attempt single retry
          AuthService.clearSession();
          const refreshedToken = await AuthService.ensureAuthenticated();
          if (refreshedToken) {
            clearTimeout(timer);
            return this.request<T>(path, { ...options, _isRetry: true }, timeoutMs);
          }
        }

        let errData: ApiErrorResponse;
        try {
          errData = await response.json();
        } catch {
          errData = {
            code: 'INTERNAL_ERROR',
            message: `HTTP Error ${response.status}: ${response.statusText}`,
            timestamp: new Date().toISOString(),
          };
        }
        if (response.status === 401) {
          AuthService.clearSession();
        }
        throw new AuraApiError(errData, response.status);
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      if (err instanceof AuraApiError) throw err;
      if (err instanceof DOMException && err.name === 'AbortError') {
        throw new AuraApiError(
          {
            code: 'SERVICE_UNAVAILABLE',
            message: `Request timed out after ${timeoutMs}ms`,
            timestamp: new Date().toISOString(),
          },
          504
        );
      }
      throw new AuraApiError(
        {
          code: 'SERVICE_UNAVAILABLE',
          message: err instanceof Error ? err.message : 'Network error or backend unreachable',
          timestamp: new Date().toISOString(),
        },
        503
      );
    } finally {
      clearTimeout(timer);
    }
  }

  // Authentication
  public static async exchangeSession(
    bootstrapCode: string,
    req: SessionHandshakeRequest = { client_name: 'AURA Web Application' }
  ): Promise<SessionHandshakeResponse> {
    return this.request<SessionHandshakeResponse>('/auth/session', {
      method: 'POST',
      headers: {
        'X-AURA-Bootstrap': bootstrapCode,
      },
      body: JSON.stringify(req),
    });
  }

  // Status & Health
  public static async getStatus(): Promise<AgentStatus> {
    return this.request<AgentStatus>('/status');
  }

  public static async getHealth(): Promise<AgentHealthResponse> {
    return this.request<AgentHealthResponse>('/health');
  }

  public static async getLiveTelemetry(): Promise<TelemetryResponse> {
    return this.request<TelemetryResponse>('/telemetry/live');
  }

  public static async getTelemetryHistory(
    metric: string,
    limit = 100
  ): Promise<TelemetrySeriesPoint[]> {
    return this.request<TelemetrySeriesPoint[]>(
      `/telemetry/history?metric=${encodeURIComponent(metric)}&limit=${limit}`
    );
  }

  public static async getCurrentRisk(): Promise<RiskResponse> {
    return this.request<RiskResponse>('/risk/current');
  }

  public static async getSensors(): Promise<SensorHealthItem[]> {
    return this.request<SensorHealthItem[]>('/sensors');
  }

  public static async getEvents(
    limit = 50,
    offset = 0,
    minSeverity?: string
  ): Promise<PaginatedResponse<SecurityEventResponse>> {
    let url = `/events?limit=${limit}&offset=${offset}`;
    if (minSeverity) {
      url += `&min_severity=${encodeURIComponent(minSeverity)}`;
    }
    return this.request<PaginatedResponse<SecurityEventResponse>>(url);
  }

  public static async getSingleEvent(eventId: string): Promise<SecurityEventResponse> {
    return this.request<SecurityEventResponse>(`/events/${encodeURIComponent(eventId)}`);
  }

  public static async getEvent(eventId: string): Promise<SecurityEventResponse> {
    return this.getSingleEvent(eventId);
  }

  public static async getConfig(): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>('/config');
  }

  // Commands & Operations
  public static async triggerScan(req: ScanRequest = {}): Promise<ScanStatusResponse> {
    return this.request<ScanStatusResponse>('/scan/trigger', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  public static async startEngine(req: MonitoringStartRequest = {}): Promise<AgentStatus> {
    return this.request<AgentStatus>('/engine/start', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  public static async stopEngine(req: MonitoringStopRequest = {}): Promise<AgentStatus> {
    return this.request<AgentStatus>('/engine/stop', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  public static async acknowledgeEvent(
    eventId: string,
    notes = ''
  ): Promise<SecurityEventResponse> {
    const body: EventAcknowledgeRequest = {
      event_id: eventId,
      acknowledged_by: 'User (Web UI)',
      notes,
    };
    return this.request<SecurityEventResponse>(`/events/${encodeURIComponent(eventId)}/ack`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }
}
