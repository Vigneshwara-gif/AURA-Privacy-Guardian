import { describe, expect, it } from 'vitest';
import { formatBitrate, formatBytes, formatDuration, formatPercent } from '../utils/formatters';

describe('formatters', () => {
  it('formats bytes properly', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(1024)).toBe('1 KB');
    expect(formatBytes(1024 * 1024 * 5)).toBe('5 MB');
  });

  it('formats bitrates properly', () => {
    expect(formatBitrate(500)).toBe('500.0 KB/s');
    expect(formatBitrate(2048)).toBe('2.00 MB/s');
  });

  it('formats percentages properly', () => {
    expect(formatPercent(45.678)).toBe('45.7%');
    expect(formatPercent(0)).toBe('0.0%');
    expect(formatPercent(120)).toBe('100.0%');
  });

  it('formats durations properly', () => {
    expect(formatDuration(45)).toBe('45s');
    expect(formatDuration(125)).toBe('2m 5s');
    expect(formatDuration(3665)).toBe('1h 1m 5s');
  });
});
