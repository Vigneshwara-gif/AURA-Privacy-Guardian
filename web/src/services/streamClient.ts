/**
 * Resilient WebSocket Client for AURA live stream.
 * Implements heartbeat monitoring, exponential backoff with jitter, and malformed-message isolation.
 */

import type { LiveStreamMessage } from '../contracts/stream';
import { AuthService } from './authService';

export type StreamConnectionState = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'ERROR';

export type StreamMessageListener = (message: LiveStreamMessage) => void;
export type StateChangeListener = (state: StreamConnectionState) => void;

export class StreamClient {
  private socket: WebSocket | null = null;
  private state: StreamConnectionState = 'DISCONNECTED';
  private reconnectAttempts = 0;
  private reconnectTimer: number | null = null;
  private heartbeatTimer: number | null = null;
  private messageListeners = new Set<StreamMessageListener>();
  private stateListeners = new Set<StateChangeListener>();
  private isExplicitlyClosed = false;

  private static instance: StreamClient | null = null;

  public static getInstance(): StreamClient {
    if (!this.instance) {
      this.instance = new StreamClient();
    }
    return this.instance;
  }

  public getState(): StreamConnectionState {
    return this.state;
  }

  public onMessage(listener: StreamMessageListener): () => void {
    this.messageListeners.add(listener);
    return () => this.messageListeners.delete(listener);
  }

  public onStateChange(listener: StateChangeListener): () => void {
    this.stateListeners.add(listener);
    listener(this.state);
    return () => this.stateListeners.delete(listener);
  }

  public async connect(): Promise<void> {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitlyClosed = false;
    this.setState('CONNECTING');

    const token = await AuthService.ensureAuthenticated();
    if (!token) {
      this.setState('ERROR');
      if (!this.isExplicitlyClosed) {
        this.scheduleReconnect();
      }
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || '127.0.0.1:8787';
    const wsUrl = `${protocol}//${host}/api/v1/stream?token=${encodeURIComponent(token)}`;

    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        this.reconnectAttempts = 0;
        this.setState('CONNECTED');
        this.resetHeartbeatWatchdog();
      };

      this.socket.onmessage = (event: MessageEvent) => {
        this.resetHeartbeatWatchdog();
        try {
          const raw = JSON.parse(event.data);
          if (raw && typeof raw === 'object' && 'type' in raw) {
            const msg = raw as LiveStreamMessage;
            this.messageListeners.forEach((listener) => {
              try {
                listener(msg);
              } catch (err) {
                console.error('Error in message listener:', err);
              }
            });
          }
        } catch {
          // Malformed JSON isolation
        }
      };

      this.socket.onclose = (event: CloseEvent) => {
        this.clearHeartbeatWatchdog();
        if (event.code === 1008) {
          // Auth policy violation; clear session and retry
          AuthService.clearSession();
          if (!this.isExplicitlyClosed) {
            this.scheduleReconnect();
          } else {
            this.setState('ERROR');
          }
          return;
        }

        if (!this.isExplicitlyClosed) {
          this.scheduleReconnect();
        } else {
          this.setState('DISCONNECTED');
        }
      };

      this.socket.onerror = () => {
        // Handled in onclose
      };
    } catch {
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.clearHeartbeatWatchdog();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.setState('DISCONNECTED');
  }

  private scheduleReconnect(): void {
    this.setState('RECONNECTING');
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    // Exponential backoff: 1s, 2s, 4s, 8s, max 15s + jitter
    const delay = Math.min(15000, Math.pow(2, this.reconnectAttempts) * 1000 + Math.random() * 500);
    this.reconnectAttempts++;

    this.reconnectTimer = window.setTimeout(() => {
      this.connect();
    }, delay);
  }

  private resetHeartbeatWatchdog(): void {
    this.clearHeartbeatWatchdog();
    // If no message/heartbeat received within 15 seconds, connection is considered dead
    this.heartbeatTimer = window.setTimeout(() => {
      if (this.socket) {
        this.socket.close();
      }
    }, 15000);
  }

  private clearHeartbeatWatchdog(): void {
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private setState(newState: StreamConnectionState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.stateListeners.forEach((listener) => listener(newState));
    }
  }
}
