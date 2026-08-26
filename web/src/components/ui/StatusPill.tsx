import React from 'react';

export interface StatusPillProps {
  status: 'ACTIVE' | 'PROTECTED' | 'RUNNING' | 'WARNING' | 'DEGRADED' | 'STOPPED' | 'OFFLINE' | 'DISCONNECTED';
  label?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({ status, label }) => {
  const isHealthy = status === 'ACTIVE' || status === 'PROTECTED' || status === 'RUNNING';
  const isWarning = status === 'WARNING' || status === 'DEGRADED';
  const color = isHealthy ? 'var(--severity-info)' : isWarning ? 'var(--severity-high)' : 'var(--severity-critical)';
  const bg = isHealthy ? 'var(--severity-info-bg)' : isWarning ? 'var(--severity-high-bg)' : 'var(--severity-critical-bg)';
  const border = isHealthy ? 'var(--severity-info-border)' : isWarning ? 'var(--severity-high-border)' : 'var(--severity-critical-border)';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '3px 10px',
        fontSize: '0.75rem',
        fontWeight: 600,
        borderRadius: 'var(--radius-full)',
        backgroundColor: bg,
        border: `1px solid ${border}`,
        color,
      }}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: color,
        }}
      />
      {label || status}
    </span>
  );
};
