/**
 * Standard error schemas and error codes for AURA API.
 */

export type ErrorCode =
  | 'INVALID_REQUEST'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'RATE_LIMITED'
  | 'SERVICE_UNAVAILABLE'
  | 'SENSOR_UNAVAILABLE'
  | 'STORAGE_ERROR'
  | 'INTERNAL_ERROR';

export interface ApiErrorResponse {
  code: ErrorCode;
  message: string;
  timestamp: string;
  correlation_id?: string | null;
  details?: Record<string, unknown> | null;
}
