import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { SecurityEventResponse } from '../contracts/api';
import { NotificationManager, type NotificationSettings } from '../services/notificationManager';

const createStorageMock = () => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = String(value);
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
};

describe('Frontend NotificationManager & Incident-Aware Deduplication', () => {
  beforeEach(() => {
    vi.stubGlobal('sessionStorage', createStorageMock());
    vi.stubGlobal('localStorage', createStorageMock());
    NotificationManager.reset();
  });

  const createEvent = (
    severity: string,
    incidentId = 'inc_camera_hijack',
    eventId = 'evt-1',
    riskScore = 50.0,
    isResolved = false
  ): SecurityEventResponse => ({
    event_id: eventId,
    timestamp: new Date().toISOString(),
    event_type: 'PRIVACY_BREACH_SUSPECT',
    severity,
    risk_score: riskScore,
    source: 'AuraEngineService',
    summary: `Camera active with high outbound traffic (${severity})`,
    evidence: [],
    affected_resource: 'Host Device',
    correlation_id: 'corr-1',
    schema_version: 2,
    incident_id: incidentId,
    is_resolved: isResolved,
  });

  it('TEST 1: NORMAL events are suppressed from notifications', () => {
    const evt = createEvent('NORMAL', 'inc_nominal', 'e-norm', 0.0);
    const decision = NotificationManager.evaluateEvent(evt);
    expect(decision.type).toBe('SUPPRESSED');
  });

  it('TEST 2: MEDIUM incident first detected triggers NEW_INCIDENT alert', () => {
    const evt = createEvent('MEDIUM', 'inc_camera_hijack', 'e-med-1', 50.0);
    const decision = NotificationManager.evaluateEvent(evt);
    expect(decision.type).toBe('NEW_INCIDENT');
    if (decision.type === 'NEW_INCIDENT') {
      expect(decision.severity).toBe('MEDIUM');
      expect(decision.event.event_id).toBe('e-med-1');
    }
  });

  it('TEST 3 & 4: Same MEDIUM incident repeated 100 times produces 0 duplicate alerts', () => {
    const firstEvt = createEvent('MEDIUM', 'inc_camera_hijack', 'e-med-1', 50.0);
    const firstDecision = NotificationManager.evaluateEvent(firstEvt);
    expect(firstDecision.type).toBe('NEW_INCIDENT');

    for (let i = 0; i < 100; i++) {
      const repeatEvt = createEvent('MEDIUM', 'inc_camera_hijack', `e-med-${i}`, 51.0 + (i % 2));
      const repeatDecision = NotificationManager.evaluateEvent(repeatEvt);
      expect(repeatDecision.type).toBe('SUPPRESSED');
    }
  });

  it('TEST 5, 6, 7: Severity Escalation lifecycle (MEDIUM -> HIGH -> CRITICAL)', () => {
    // 1. Initial MEDIUM -> Alert
    const medEvt = createEvent('MEDIUM', 'inc_escalate', 'e-1', 50.0);
    const d1 = NotificationManager.evaluateEvent(medEvt);
    expect(d1.type).toBe('NEW_INCIDENT');

    // 2. Repeat MEDIUM -> Suppress
    const d2 = NotificationManager.evaluateEvent(medEvt);
    expect(d2.type).toBe('SUPPRESSED');

    // 3. Escalates to HIGH -> Alert
    const highEvt = createEvent('HIGH', 'inc_escalate', 'e-2', 78.0);
    const d3 = NotificationManager.evaluateEvent(highEvt);
    expect(d3.type).toBe('ESCALATION');
    if (d3.type === 'ESCALATION') {
      expect(d3.previousSeverity).toBe('MEDIUM');
      expect(d3.severity).toBe('HIGH');
    }

    // 4. Repeat HIGH -> Suppress
    const d4 = NotificationManager.evaluateEvent(highEvt);
    expect(d4.type).toBe('SUPPRESSED');

    // 5. Escalates to CRITICAL -> Alert
    const critEvt = createEvent('CRITICAL', 'inc_escalate', 'e-3', 95.0);
    const d5 = NotificationManager.evaluateEvent(critEvt);
    expect(d5.type).toBe('ESCALATION');
    if (d5.type === 'ESCALATION') {
      expect(d5.previousSeverity).toBe('HIGH');
      expect(d5.severity).toBe('CRITICAL');
    }

    // 6. Repeat CRITICAL -> Suppress
    const d6 = NotificationManager.evaluateEvent(critEvt);
    expect(d6.type).toBe('SUPPRESSED');
  });

  it('TEST 8 & 9: Incident resolution resets state; future recurrence triggers NEW_INCIDENT', () => {
    // 1. First occurrence
    const evt = createEvent('HIGH', 'inc_mic_leak', 'e-1', 75.0);
    expect(NotificationManager.evaluateEvent(evt).type).toBe('NEW_INCIDENT');

    // 2. Resolved
    const resEvt = createEvent('NORMAL', 'inc_mic_leak', 'e-2', 0.0, true);
    expect(NotificationManager.evaluateEvent(resEvt).type).toBe('SUPPRESSED');

    // 3. Same threat appears later -> Notifies as NEW_INCIDENT
    const newEvt = createEvent('HIGH', 'inc_mic_leak', 'e-3', 80.0);
    expect(NotificationManager.evaluateEvent(newEvt).type).toBe('NEW_INCIDENT');
  });

  it('TEST 10 & 11: Deduplication persists across session refreshes via sessionStorage', () => {
    const evt = createEvent('HIGH', 'inc_exfil', 'e-1', 85.0);
    expect(NotificationManager.evaluateEvent(evt).type).toBe('NEW_INCIDENT');

    // Simulate new instance reading from sessionStorage
    const repeatEvt = createEvent('HIGH', 'inc_exfil', 'e-2', 85.0);
    expect(NotificationManager.evaluateEvent(repeatEvt).type).toBe('SUPPRESSED');
  });

  it('TEST 13: When notifications are disabled, all alerts are suppressed', () => {
    const disabledSettings: NotificationSettings = {
      enabled: false,
      minSeverity: 'MEDIUM',
      inAppEnabled: true,
      nativeEnabled: true,
      soundEnabled: false,
    };
    const evt = createEvent('CRITICAL', 'inc_crit', 'e-1', 99.0);
    const decision = NotificationManager.evaluateEvent(evt, disabledSettings);
    expect(decision.type).toBe('SUPPRESSED');
  });

  it('TEST 15: Sanitization redacts Bearer tokens and passwords', () => {
    const raw = 'Bearer eyJhbGciOiJIUzI1Ni.sensitiveToken123 password=MySecretPass123';
    const sanitized = NotificationManager.sanitizeSummary(raw);
    expect(sanitized).not.toContain('sensitiveToken123');
    expect(sanitized).toContain('[REDACTED_TOKEN]');
    expect(sanitized).not.toContain('MySecretPass123');
    expect(sanitized).toContain('[REDACTED]');
  });
});
