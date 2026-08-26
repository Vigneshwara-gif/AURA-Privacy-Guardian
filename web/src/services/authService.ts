/**
 * Authentication service for ephemeral bootstrap tokens and short-lived sessions.
 */

import type { SessionHandshakeResponse } from '../contracts/auth';

const SESSION_KEY = 'aura_session_token';
const SCOPE_KEY = 'aura_session_scope';

export type AuthExchangeHandler = (code: string) => Promise<SessionHandshakeResponse>;

export class AuthService {
  private static cachedToken: string | null = null;
  private static cachedScope: string | null = null;
  private static bootstrapToken: string | null = null;
  private static authPromise: Promise<string | null> | null = null;
  private static exchangeHandler: AuthExchangeHandler | null = null;

  public static setExchangeHandler(handler: AuthExchangeHandler): void {
    this.exchangeHandler = handler;
  }

  public static getSessionToken(): string | null {
    if (this.cachedToken) return this.cachedToken;
    try {
      this.cachedToken = sessionStorage.getItem(SESSION_KEY);
      this.cachedScope = sessionStorage.getItem(SCOPE_KEY);
    } catch {
      this.cachedToken = null;
    }
    return this.cachedToken;
  }

  public static getScope(): string | null {
    if (this.cachedScope) return this.cachedScope;
    try {
      this.cachedScope = sessionStorage.getItem(SCOPE_KEY);
    } catch {
      this.cachedScope = null;
    }
    return this.cachedScope;
  }

  public static setSession(response: SessionHandshakeResponse): void {
    this.cachedToken = response.session_id;
    this.cachedScope = response.scope;
    try {
      sessionStorage.setItem(SESSION_KEY, response.session_id);
      sessionStorage.setItem(SCOPE_KEY, response.scope);
    } catch {
      // Session storage restricted
    }
  }

  public static clearSession(): void {
    this.cachedToken = null;
    this.cachedScope = null;
    try {
      sessionStorage.removeItem(SESSION_KEY);
      sessionStorage.removeItem(SCOPE_KEY);
    } catch {
      // Storage clearance
    }
  }

  /**
   * Consume bootstrap token if present in URL query parameters and sanitize URL history.
   */
  public static consumeBootstrapParam(): string | null {
    if (this.bootstrapToken) {
      return this.bootstrapToken;
    }
    try {
      const params = new URLSearchParams(window.location.search);
      const token = params.get('bootstrap');
      if (token) {
        this.bootstrapToken = token;
        // Immediately sanitize URL history to prevent token leakage
        window.history.replaceState({}, document.title, window.location.pathname);
        return token;
      }
    } catch {
      // Non-browser or iframe context
    }
    return null;
  }

  /**
   * Guarantees a valid session token is available for protected API requests.
   * Deduplicates concurrent handshake requests across multiple caller components.
   */
  public static async ensureAuthenticated(): Promise<string | null> {
    const existing = this.getSessionToken();
    if (existing) return existing;

    if (this.authPromise) {
      return this.authPromise;
    }

    this.authPromise = (async () => {
      try {
        const bootstrapCode = this.consumeBootstrapParam() || 'local-dev';
        if (!this.exchangeHandler) {
          throw new Error('No exchangeHandler registered in AuthService');
        }
        const res = await this.exchangeHandler(bootstrapCode);
        this.setSession(res);
        return res.session_id;
      } catch (err) {
        console.warn('Authentication handshake failed:', err);
        return null;
      } finally {
        this.authPromise = null;
      }
    })();

    return this.authPromise;
  }
}
