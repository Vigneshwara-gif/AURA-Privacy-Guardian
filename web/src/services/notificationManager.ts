import type { SecurityEventResponse } from '../contracts/api';
import type { SeverityLevel } from '../utils/severity';
import { normalizeSeverity } from '../utils/severity';

export interface NotificationSettings {
  enabled: boolean;
  minSeverity: SeverityLevel;
  inAppEnabled: boolean;
  nativeEnabled: boolean;
  soundEnabled: boolean;
}

export const DEFAULT_NOTIFICATION_SETTINGS: NotificationSettings = {
  enabled: true,
  minSeverity: 'MEDIUM',
  inAppEnabled: true,
  nativeEnabled: true,
  soundEnabled: false,
};

export interface TrackedIncident {
  incidentId: string;
  firstDetected: string;
  lastObserved: string;
  currentSeverity: SeverityLevel;
  notifiedSeverity: SeverityLevel | null;
  isResolved: boolean;
  occurrenceCount: number;
  lastEventId: string;
}

export type NotificationDecision =
  | { type: 'NEW_INCIDENT'; event: SecurityEventResponse; severity: SeverityLevel }
  | { type: 'ESCALATION'; event: SecurityEventResponse; severity: SeverityLevel; previousSeverity: SeverityLevel }
  | { type: 'SUPPRESSED'; reason: string };

const SEVERITY_WEIGHTS: Record<SeverityLevel, number> = {
  NORMAL: 0,
  INFO: 0,
  LOW: 1,
  MEDIUM: 2,
  HIGH: 3,
  CRITICAL: 4,
};

const STORAGE_KEY = 'aura_incident_notification_state_v1';
const SETTINGS_KEY = 'aura_notification_settings_v1';

export class NotificationManager {
  private static incidents: Map<string, TrackedIncident> = new Map();
  private static initialized = false;

  private static ensureLoaded(): void {
    if (this.initialized) return;
    try {
      if (typeof sessionStorage !== 'undefined') {
        const stored = sessionStorage.getItem(STORAGE_KEY);
        if (stored) {
          const parsed = JSON.parse(stored) as Record<string, TrackedIncident>;
          Object.entries(parsed).forEach(([k, v]) => this.incidents.set(k, v));
        }
      }
    } catch {
      // Ignore storage read error
    }
    this.initialized = true;
  }

  private static save(): void {
    try {
      if (typeof sessionStorage !== 'undefined') {
        const obj: Record<string, TrackedIncident> = {};
        this.incidents.forEach((v, k) => {
          obj[k] = v;
        });
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
      }
    } catch {
      // Ignore storage write error
    }
  }

  public static getSettings(): NotificationSettings {
    try {
      if (typeof localStorage !== 'undefined') {
        const raw = localStorage.getItem(SETTINGS_KEY);
        if (raw) {
          return { ...DEFAULT_NOTIFICATION_SETTINGS, ...JSON.parse(raw) };
        }
      }
    } catch {
      // Fallback
    }
    return DEFAULT_NOTIFICATION_SETTINGS;
  }

  public static saveSettings(settings: NotificationSettings): void {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
      }
    } catch {
      // Fallback
    }
  }

  public static sanitizeSummary(text: string, maxLen = 140): string {
    if (!text) return '';
    // Redact Bearer tokens, hex strings >= 32 chars, passwords
    let clean = text.replace(/[A-Fa-f0-9]{32,}/g, '[REDACTED_HASH]');
    clean = clean.replace(/bearer\s+[^\s]+/gi, 'Bearer [REDACTED_TOKEN]');
    clean = clean.replace(/password\s*=\s*[^\s]+/gi, 'password=[REDACTED]');
    return clean.length > maxLen ? `${clean.substring(0, maxLen - 3)}...` : clean;
  }

  public static evaluateEvent(
    event: SecurityEventResponse,
    customSettings?: NotificationSettings
  ): NotificationDecision {
    this.ensureLoaded();
    const settings = customSettings || this.getSettings();

    if (!settings.enabled || !settings.inAppEnabled) {
      return { type: 'SUPPRESSED', reason: 'notifications_disabled' };
    }

    const eventSev = normalizeSeverity(event.severity);
    const eventWeight = SEVERITY_WEIGHTS[eventSev] ?? 0;
    const minWeight = SEVERITY_WEIGHTS[settings.minSeverity] ?? 2;

    const incidentId = event.incident_id || `inc_${event.event_type.toLowerCase()}`;
    const existing = this.incidents.get(incidentId);

    // 1. Normal / Info / Resolved
    if (eventWeight <= 0 || event.is_resolved) {
      if (existing && !existing.isResolved) {
        existing.isResolved = true;
        existing.currentSeverity = eventSev;
        existing.notifiedSeverity = null;
        existing.lastObserved = event.timestamp;
        this.save();
      }
      return { type: 'SUPPRESSED', reason: 'incident_resolved_or_nominal' };
    }

    // 2. Below minimum severity threshold
    if (eventWeight < minWeight) {
      if (existing) {
        existing.currentSeverity = eventSev;
        existing.lastObserved = event.timestamp;
        this.save();
      }
      return { type: 'SUPPRESSED', reason: 'below_min_severity' };
    }

    // 3. New incident or reappearance after resolution
    if (!existing || existing.isResolved) {
      const state: TrackedIncident = {
        incidentId,
        firstDetected: event.timestamp,
        lastObserved: event.timestamp,
        currentSeverity: eventSev,
        notifiedSeverity: eventSev,
        isResolved: false,
        occurrenceCount: 1,
        lastEventId: event.event_id,
      };
      this.incidents.set(incidentId, state);
      this.save();
      return { type: 'NEW_INCIDENT', event, severity: eventSev };
    }

    // 4. Existing incident - check escalation
    const notifiedWeight = SEVERITY_WEIGHTS[existing.notifiedSeverity || 'NORMAL'] ?? 0;
    if (eventWeight > notifiedWeight) {
      const prev = existing.notifiedSeverity || 'NORMAL';
      existing.notifiedSeverity = eventSev;
      existing.currentSeverity = eventSev;
      existing.lastObserved = event.timestamp;
      existing.occurrenceCount += 1;
      existing.lastEventId = event.event_id;
      this.save();
      return { type: 'ESCALATION', event, severity: eventSev, previousSeverity: prev };
    }

    // 5. Unchanged / minor fluctuation -> Deduplicate
    existing.currentSeverity = eventSev;
    existing.lastObserved = event.timestamp;
    existing.occurrenceCount += 1;
    existing.lastEventId = event.event_id;
    this.save();
    return { type: 'SUPPRESSED', reason: 'deduplicated_same_severity' };
  }

  public static reset(): void {
    this.incidents.clear();
    this.initialized = false;
    try {
      if (typeof sessionStorage !== 'undefined') {
        sessionStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // Ignore
    }
  }
}
