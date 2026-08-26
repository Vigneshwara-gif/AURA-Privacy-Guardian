import React from 'react';
import { Moon, RefreshCw, Sun, Wifi } from 'lucide-react';
import { useStream } from '../../context/StreamContext';
import { useTheme } from '../../context/ThemeContext';
import { Button } from '../ui/Button';

export const TopBar: React.FC = () => {
  const { connectionState, agentStatus, isScanning, triggerScan, sensors, latestTelemetry } = useStream();
  const { theme, setTheme } = useTheme();

  const isConnected = connectionState === 'CONNECTED';
  const isRunning = agentStatus?.state === 'RUNNING';

  const getProtectionState = () => {
    if (!isRunning) {
      return {
        label: 'PROTECTION STOPPED',
        severity: 'CRITICAL' as const,
        bg: 'var(--severity-critical-bg)',
        border: 'var(--severity-critical-border)',
        color: 'var(--severity-critical)',
      };
    }
    if (!isConnected) {
      return {
        label: 'SYNC DISCONNECTED',
        severity: 'MEDIUM' as const,
        bg: 'var(--severity-medium-bg)',
        border: 'var(--severity-medium-border)',
        color: 'var(--severity-medium)',
      };
    }
    const hasDegraded = sensors.some((s) => s.status === 'FAIL' || s.status === 'UNAVAILABLE');
    if (hasDegraded) {
      return {
        label: 'MONITORING (DEGRADED)',
        severity: 'HIGH' as const,
        bg: 'var(--severity-high-bg)',
        border: 'var(--severity-high-border)',
        color: 'var(--severity-high)',
      };
    }
    return {
      label: 'PROTECTED & MONITORING',
      severity: 'LOW' as const,
      bg: 'rgba(32, 199, 122, 0.08)',
      border: 'rgba(32, 199, 122, 0.3)',
      color: 'var(--severity-low)',
    };
  };

  const state = getProtectionState();

  return (
    <header
      style={{
        height: '62px',
        backgroundColor: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 var(--space-6)',
        position: 'sticky',
        top: 0,
        zIndex: 10,
      }}
    >
      {/* Left: Dominant Device Protection State */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '5px 12px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: state.bg,
            border: `1px solid ${state.border}`,
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: state.color,
              boxShadow: `0 0 8px ${state.color}`,
              flexShrink: 0,
            }}
          />
          <span style={{ fontSize: '0.82rem', fontWeight: 700, letterSpacing: '0.04em', color: state.color }}>
            {state.label}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          <Wifi size={14} color={isConnected ? 'var(--accent-primary)' : 'var(--text-muted)'} />
          <span>{isConnected ? 'Live WebSocket Active' : 'Offline / Reconnecting'}</span>
          {latestTelemetry?.disk_path && (
            <span style={{ marginLeft: '6px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              • Local Host ({latestTelemetry.disk_path})
            </span>
          )}
        </div>
      </div>

      {/* Right: Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <Button
          variant="outline"
          size="sm"
          loading={isScanning}
          disabled={isScanning}
          onClick={() => triggerScan(false, false, false)}
          icon={<RefreshCw size={13} />}
          style={{
            borderColor: 'var(--border-default)',
            color: 'var(--text-primary)',
            fontSize: '0.8rem',
            padding: '6px 14px',
          }}
        >
          {isScanning ? 'Scanning System...' : 'Run Security Scan'}
        </Button>

        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          style={{
            backgroundColor: 'transparent',
            border: '1px solid var(--border-default)',
            color: 'var(--text-secondary)',
            padding: '6px 8px',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all var(--transition-fast)',
          }}
          aria-label="Toggle visual theme"
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  );
};
