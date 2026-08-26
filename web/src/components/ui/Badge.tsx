import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle, Info, ShieldAlert } from 'lucide-react';

export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO' | 'NORMAL' | 'SAFE' | 'WARN' | 'DANGER' | string;

interface BadgeProps {
  severity?: SeverityLevel;
  size?: 'sm' | 'md';
  children: React.ReactNode;
  showIcon?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  severity = 'INFO',
  size = 'md',
  children,
  showIcon = false,
}) => {
  const getSeverityStyle = () => {
    const sev = (severity || 'INFO').toUpperCase();
    switch (sev) {
      case 'CRITICAL':
      case 'DANGER':
        return {
          color: 'var(--severity-critical)',
          backgroundColor: 'var(--severity-critical-bg)',
          borderColor: 'var(--severity-critical-border)',
          icon: <ShieldAlert size={12} />,
        };
      case 'HIGH':
        return {
          color: 'var(--severity-high)',
          backgroundColor: 'var(--severity-high-bg)',
          borderColor: 'var(--severity-high-border)',
          icon: <AlertTriangle size={12} />,
        };
      case 'MEDIUM':
      case 'WARN':
        return {
          color: 'var(--severity-medium)',
          backgroundColor: 'var(--severity-medium-bg)',
          borderColor: 'var(--severity-medium-border)',
          icon: <AlertCircle size={12} />,
        };
      case 'LOW':
      case 'OK':
        return {
          color: 'var(--severity-low)',
          backgroundColor: 'var(--severity-low-bg)',
          borderColor: 'var(--severity-low-border)',
          icon: <CheckCircle size={12} />,
        };
      case 'INFO':
      case 'NORMAL':
      case 'SAFE':
      default:
        return {
          color: 'var(--severity-info)',
          backgroundColor: 'var(--severity-info-bg)',
          borderColor: 'var(--severity-info-border)',
          icon: <Info size={12} />,
        };
    }
  };

  const style = getSeverityStyle();
  const isSm = size === 'sm';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: isSm ? '2px 6px' : '3px 8px',
        borderRadius: 'var(--radius-sm)',
        fontSize: isSm ? '0.7rem' : '0.75rem',
        fontWeight: 600,
        letterSpacing: '0.02em',
        textTransform: 'uppercase',
        border: `1px solid ${style.borderColor}`,
        backgroundColor: style.backgroundColor,
        color: style.color,
        fontFamily: 'var(--font-sans)',
        lineHeight: 1.2,
      }}
    >
      {showIcon && style.icon}
      {children}
    </span>
  );
};
