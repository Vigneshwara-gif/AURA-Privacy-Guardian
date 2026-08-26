import React from 'react';
import { getSeverityColor, normalizeSeverity } from '../../utils/severity';

export interface RadialGaugeProps {
  value: number; // 0 to 100
  size?: number;
  strokeWidth?: number;
  severity?: string;
}

export const RadialGauge: React.FC<RadialGaugeProps> = ({
  value,
  size = 140,
  strokeWidth = 10,
  severity,
}) => {
  const normVal = Math.max(0, Math.min(100, value));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (normVal / 100) * circumference;

  const sev = severity ? normalizeSeverity(severity) : normVal >= 75 ? 'CRITICAL' : normVal >= 50 ? 'HIGH' : normVal >= 25 ? 'MEDIUM' : 'NORMAL';
  const color = getSeverityColor(sev);

  return (
    <div style={{ position: 'relative', width: size, height: size, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="var(--border-subtle)"
          strokeWidth={strokeWidth}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          fill="none"
          style={{ transition: 'stroke-dashoffset 0.4s ease, stroke 0.4s ease' }}
        />
      </svg>
      <div style={{ position: 'absolute', textAlign: 'center' }}>
        <span style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
          {normVal.toFixed(0)}
        </span>
        <span style={{ fontSize: '0.75rem', display: 'block', color: 'var(--text-muted)', fontWeight: 600 }}>
          {sev}
        </span>
      </div>
    </div>
  );
};
