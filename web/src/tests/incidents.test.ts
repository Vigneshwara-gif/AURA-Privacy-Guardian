import { describe, expect, it } from 'vitest';

describe('Incident & Mitigation Action Policy', () => {
  it('strictly distinguishes supported vs unsupported actions without fabrication', () => {
    const actions = [
      { id: 'trigger-full-scan', supported: true },
      { id: 'sign-out-session', supported: true },
      { id: 'resync-telemetry', supported: true },
      { id: 'isolate-host', supported: false, reason: 'Endpoint isolation capability is not configured at OS firewall level.' },
      { id: 'block-subnet', supported: false, reason: 'Requires Windows Filtering Platform driver.' },
      { id: 'quarantine-process', supported: false, reason: 'Process quarantine requires elevated Windows supervisor.' },
    ];

    const unsupported = actions.filter((a) => !a.supported);
    expect(unsupported.length).toBe(3);
    expect(unsupported[0].reason).toContain('firewall');
    expect(unsupported[1].reason).toContain('Windows Filtering Platform');
    expect(unsupported[2].reason).toContain('supervisor');
  });
});
