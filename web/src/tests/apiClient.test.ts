import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiClient, AuraApiError } from '../services/apiClient';
import { AuthService } from '../services/authService';

describe('ApiClient Authentication & Request Flow', () => {
  beforeEach(() => {
    AuthService.clearSession();
    vi.restoreAllMocks();
  });

  it('attaches Bearer token to protected API requests when authenticated', async () => {
    AuthService.setSession({
      status: 'AUTHENTICATED',
      session_id: 'mock-valid-token-xyz',
      scope: 'OPERATOR',
      server_time: new Date().toISOString(),
    });

    let capturedAuthHeader = '';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
        const headers = init?.headers as Record<string, string>;
        capturedAuthHeader = headers?.['Authorization'] || '';
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ state: 'RUNNING', version: '1.0.0' }),
        } as Response);
      })
    );

    const status = await ApiClient.getStatus();
    expect(status.state).toBe('RUNNING');
    expect(capturedAuthHeader).toBe('Bearer mock-valid-token-xyz');
  });

  it('automatically triggers session exchange if token is absent on protected request', async () => {
    let exchangeCalled = false;
    AuthService.setExchangeHandler(async (code: string) => {
      exchangeCalled = true;
      expect(code).toBe('local-dev');
      return {
        status: 'AUTHENTICATED',
        session_id: 'auto-exchanged-token',
        scope: 'OPERATOR',
        server_time: new Date().toISOString(),
      };
    });

    let capturedAuthHeader = '';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
        const headers = init?.headers as Record<string, string>;
        capturedAuthHeader = headers?.['Authorization'] || '';
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ risk_score: 12.5, severity: 'LOW' }),
        } as Response);
      })
    );

    const risk = await ApiClient.getCurrentRisk();
    expect(exchangeCalled).toBe(true);
    expect(capturedAuthHeader).toBe('Bearer auto-exchanged-token');
    expect(risk.risk_score).toBe(12.5);
  });

  it('transparently retries request on 401 when token expires', async () => {
    AuthService.setSession({
      status: 'AUTHENTICATED',
      session_id: 'expired-token-123',
      scope: 'OPERATOR',
      server_time: new Date().toISOString(),
    });

    let attemptCount = 0;
    AuthService.setExchangeHandler(async () => {
      return {
        status: 'AUTHENTICATED',
        session_id: 'refreshed-token-456',
        scope: 'OPERATOR',
        server_time: new Date().toISOString(),
      };
    });

    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
        attemptCount++;
        const headers = init?.headers as Record<string, string>;
        const auth = headers?.['Authorization'] || '';

        if (attemptCount === 1) {
          expect(auth).toBe('Bearer expired-token-123');
          return Promise.resolve({
            ok: false,
            status: 401,
            statusText: 'Unauthorized',
            json: () => Promise.resolve({ code: 'UNAUTHORIZED', message: 'Token expired', timestamp: new Date().toISOString() }),
          } as Response);
        }

        expect(auth).toBe('Bearer refreshed-token-456');
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            scan_id: 'scan-abc-999',
            state: 'COMPLETED',
            stage: 'FINALIZING',
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
            elapsed_seconds: 0.15,
            result_summary: 'Baseline clean',
            risk_score: 0.0,
            severity: 'NORMAL',
            is_demo: false,
          }),
        } as Response);
      })
    );

    const scanResult = await ApiClient.triggerScan({ is_demo: false });
    expect(attemptCount).toBe(2);
    expect(scanResult.scan_id).toBe('scan-abc-999');
    expect(scanResult.state).toBe('COMPLETED');
    expect(AuthService.getSessionToken()).toBe('refreshed-token-456');
  });

  it('throws AuraApiError when request fails permanently with 403 Forbidden', async () => {
    AuthService.setSession({
      status: 'AUTHENTICATED',
      session_id: 'read-only-token',
      scope: 'READ_ONLY',
      server_time: new Date().toISOString(),
    });

    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() => {
        return Promise.resolve({
          ok: false,
          status: 403,
          statusText: 'Forbidden',
          json: () => Promise.resolve({ code: 'FORBIDDEN', message: 'Insufficient scope', timestamp: new Date().toISOString() }),
        } as Response);
      })
    );

    await expect(ApiClient.triggerScan()).rejects.toThrowError(AuraApiError);
  });
});
