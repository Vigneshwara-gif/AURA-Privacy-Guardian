/**
 * Formatting helpers for telemetry, data sizes, bandwidth, and timestamps.
 */

export function formatBytes(bytes: number, decimals = 1): string {
  if (bytes <= 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
}

export function formatBitrate(kbps: number): string {
  if (kbps < 1000) {
    return `${kbps.toFixed(1)} KB/s`;
  }
  return `${(kbps / 1024).toFixed(2)} MB/s`;
}

export function formatPercent(value: number, decimals = 1): string {
  return `${Math.max(0, Math.min(100, value)).toFixed(decimals)}%`;
}

export function formatDuration(seconds: number): string {
  const sec = Math.floor(seconds);
  const hrs = Math.floor(sec / 3600);
  const mins = Math.floor((sec % 3600) / 60);
  const remSec = sec % 60;

  if (hrs > 0) {
    return `${hrs}h ${mins}m ${remSec}s`;
  }
  if (mins > 0) {
    return `${mins}m ${remSec}s`;
  }
  return `${remSec}s`;
}

export function formatTimestamp(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return isoString;
  }
}

export function formatDateTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour12: false })}`;
  } catch {
    return isoString;
  }
}
