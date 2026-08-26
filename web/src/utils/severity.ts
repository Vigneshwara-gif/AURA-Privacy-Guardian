/**
 * Severity mappings, accessible color codes, and badge utilities.
 */

export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO' | 'NORMAL';

export function normalizeSeverity(severity: string | undefined): SeverityLevel {
  if (!severity) return 'INFO';
  const s = severity.toUpperCase().trim();
  if (s === 'CRITICAL') return 'CRITICAL';
  if (s === 'HIGH') return 'HIGH';
  if (s === 'MEDIUM' || s === 'WARN' || s === 'WARNING') return 'MEDIUM';
  if (s === 'LOW') return 'LOW';
  if (s === 'NORMAL' || s === 'OK') return 'NORMAL';
  return 'INFO';
}

export function getSeverityColor(severity: SeverityLevel): string {
  switch (severity) {
    case 'CRITICAL':
      return 'var(--severity-critical)';
    case 'HIGH':
      return 'var(--severity-high)';
    case 'MEDIUM':
      return 'var(--severity-medium)';
    case 'LOW':
      return 'var(--severity-low)';
    case 'NORMAL':
    case 'INFO':
    default:
      return 'var(--severity-info)';
  }
}

export function getSeverityBg(severity: SeverityLevel): string {
  switch (severity) {
    case 'CRITICAL':
      return 'var(--severity-critical-bg)';
    case 'HIGH':
      return 'var(--severity-high-bg)';
    case 'MEDIUM':
      return 'var(--severity-medium-bg)';
    case 'LOW':
      return 'var(--severity-low-bg)';
    case 'NORMAL':
    case 'INFO':
    default:
      return 'var(--severity-info-bg)';
  }
}

export function getSeverityBorder(severity: SeverityLevel): string {
  switch (severity) {
    case 'CRITICAL':
      return 'var(--severity-critical-border)';
    case 'HIGH':
      return 'var(--severity-high-border)';
    case 'MEDIUM':
      return 'var(--severity-medium-border)';
    case 'LOW':
      return 'var(--severity-low-border)';
    case 'NORMAL':
    case 'INFO':
    default:
      return 'var(--severity-info-border)';
  }
}
