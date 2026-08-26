import { describe, expect, it } from 'vitest';
import { getSeverityColor, normalizeSeverity } from '../utils/severity';

describe('severity', () => {
  it('normalizes severity strings', () => {
    expect(normalizeSeverity('critical')).toBe('CRITICAL');
    expect(normalizeSeverity('HIGH')).toBe('HIGH');
    expect(normalizeSeverity('warn')).toBe('MEDIUM');
    expect(normalizeSeverity('ok')).toBe('NORMAL');
    expect(normalizeSeverity(undefined)).toBe('INFO');
  });

  it('returns appropriate color variables', () => {
    expect(getSeverityColor('CRITICAL')).toBe('var(--severity-critical)');
    expect(getSeverityColor('HIGH')).toBe('var(--severity-high)');
    expect(getSeverityColor('NORMAL')).toBe('var(--severity-info)');
  });
});
