import React from 'react';
import { Card } from './Card';

export interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  sparkline?: React.ReactNode;
  style?: React.CSSProperties;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  subtitle,
  icon,
  badge,
  sparkline,
  style,
}) => {
  return (
    <Card style={style}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', fontWeight: 500 }}>{title}</span>
        {icon && <span style={{ color: 'var(--accent-primary)' }}>{icon}</span>}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', margin: '4px 0' }}>
        <span style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
          {value}
        </span>
        {unit && <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{unit}</span>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {subtitle && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{subtitle}</span>}
        {badge}
      </div>
      {sparkline && <div style={{ marginTop: '8px' }}>{sparkline}</div>}
    </Card>
  );
};
