/**
 * Authentication and session handshake contracts.
 */

export type AuthScope = 'READ_ONLY' | 'OPERATOR' | 'ADMIN';

export type AuthSessionStatus =
  | 'UNAUTHENTICATED'
  | 'AUTHENTICATED'
  | 'EXPIRED'
  | 'REVOKED';

export interface SessionHandshakeRequest {
  client_name?: string;
  client_version?: string;
  requested_scope?: AuthScope;
}

export interface SessionHandshakeResponse {
  status: AuthSessionStatus;
  session_id: string;
  scope: AuthScope;
  expires_at?: string | null;
  server_time: string;
}

export interface AuthTokenClaims {
  token_id: string;
  issued_to: string;
  scope: AuthScope;
  issued_at: string;
  expires_at?: string | null;
}
