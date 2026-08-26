import { describe, expect, it } from 'vitest';
import { AuthService } from '../services/authService';

describe('AuthService', () => {
  it('stores and clears session tokens', () => {
    AuthService.clearSession();
    expect(AuthService.getSessionToken()).toBeNull();

    AuthService.setSession({
      status: 'AUTHENTICATED',
      session_id: 'test-session-123',
      scope: 'OPERATOR',
      server_time: new Date().toISOString(),
    });

    expect(AuthService.getSessionToken()).toBe('test-session-123');
    expect(AuthService.getScope()).toBe('OPERATOR');

    AuthService.clearSession();
    expect(AuthService.getSessionToken()).toBeNull();
  });
});
