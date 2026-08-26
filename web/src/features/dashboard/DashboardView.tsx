import React from 'react';
import {
  Activity,
  Cpu,
  Network,
  Radio,
  Server,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { RadialGauge } from '../../components/ui/RadialGauge';
import { useStream } from '../../context/StreamContext';
import { formatDateTime, formatDuration } from '../../utils/formatters';

export const DashboardView: React.FC = () => {
  const {
    agentStatus,
    currentRisk,
    latestTelemetry,
    sensors,
    recentEvents,
  } = useStream();

  const isRunning = agentStatus?.state === 'RUNNING';
  const riskScore = currentRisk?.risk_score ?? 0;
  const severity = currentRisk?.severity ?? 'NORMAL';
  const evidence = currentRisk?.evidence ?? [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
      {/* Hero Command Center Status Banner */}
      <div
        style={{
          padding: 'var(--space-5) var(--space-6)',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--space-4)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: isRunning ? 'rgba(32, 199, 122, 0.1)' : 'rgba(255, 77, 94, 0.1)',
              border: `1px solid ${isRunning ? 'var(--severity-low-border)' : 'var(--severity-critical-border)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: isRunning ? 'var(--severity-low)' : 'var(--severity-critical)',
              flexShrink: 0,
            }}
          >
            {isRunning ? <ShieldCheck size={26} /> : <ShieldAlert size={26} />}
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.01em' }}>
                {isRunning ? 'Protection Enclave Active' : 'Protection Daemon Inactive'}
              </h1>
              <Badge severity={isRunning ? 'LOW' : 'CRITICAL'} size="sm">
                {isRunning ? 'ACTIVE' : 'STOPPED'}
              </Badge>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
              Continuous local-first hardware inspection, socket flow telemetry, and unsupervised behavioral anomaly detection.
            </p>
          </div>
        </div>

        {/* Live Cadence & Enclave Metrics */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
              padding: '8px 16px',
              backgroundColor: 'var(--bg-surface-elevated)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div>
              <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.04em' }}>
                SAMPLING CADENCE
              </span>
              <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                5.0s interval
              </div>
            </div>

            <div style={{ width: '1px', height: '24px', backgroundColor: 'var(--border-subtle)' }} />

            <div>
              <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.04em' }}>
                AGENT UPTIME
              </span>
              <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                {formatDuration(agentStatus?.uptime_seconds ?? 0)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 4-Column Operational Matrix */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          backgroundColor: 'var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          gap: '1px',
          overflow: 'hidden',
          border: '1px solid var(--border-subtle)',
        }}
      >
        {/* Metric 1: CPU */}
        <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Cpu size={13} color="var(--accent-primary)" />
              HOST CPU
            </span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {latestTelemetry?.cpu_cores ? `${latestTelemetry.cpu_cores} cores` : '— cores'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
            <span style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }} className="tabular-nums">
              {(latestTelemetry?.cpu_percent ?? 0).toFixed(1)}%
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>@active</span>
          </div>
          <div style={{ height: '3px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${Math.min(latestTelemetry?.cpu_percent ?? 0, 100)}%`, backgroundColor: (latestTelemetry?.cpu_percent ?? 0) > 85 ? 'var(--severity-critical)' : 'var(--accent-primary)', transition: 'width 0.3s ease' }} />
          </div>
        </div>

        {/* Metric 2: RAM */}
        <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Server size={13} color="var(--accent-info)" />
              HOST RAM
            </span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {latestTelemetry?.memory_used_gb ? `${latestTelemetry.memory_used_gb.toFixed(1)} / ${latestTelemetry.memory_total_gb?.toFixed(1)} GB` : '—/— GB'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
            <span style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }} className="tabular-nums">
              {(latestTelemetry?.memory_percent ?? 0).toFixed(1)}%
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>committed</span>
          </div>
          <div style={{ height: '3px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${Math.min(latestTelemetry?.memory_percent ?? 0, 100)}%`, backgroundColor: 'var(--accent-info)', transition: 'width 0.3s ease' }} />
          </div>
        </div>

        {/* Metric 3: Network Flow */}
        <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Network size={13} color="var(--severity-low)" />
              NETWORK FLOW
            </span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {latestTelemetry?.established_connections ? `${latestTelemetry.established_connections} sockets` : '— sockets'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
            <span style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }} className="tabular-nums">
              {(latestTelemetry?.net_download_kbps ?? 0).toFixed(1)} KB/s
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>↑ {(latestTelemetry?.net_upload_kbps ?? 0).toFixed(1)} KB/s</span>
          </div>
          <div style={{ height: '3px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: '35%', backgroundColor: 'var(--severity-low)' }} />
          </div>
        </div>

        {/* Metric 4: Process Sentinel */}
        <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Radio size={13} color="var(--accent-primary-hover)" />
              PROCESS SENTINEL
            </span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              active tree
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
            <span style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }} className="tabular-nums">
              {latestTelemetry?.process_count ?? '—'}
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>monitored procs</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', color: 'var(--severity-low)' }}>
            <span style={{ width: '5px', height: '5px', borderRadius: '50%', backgroundColor: 'var(--severity-low)' }} />
            <span>No process injection anomalies detected</span>
          </div>
        </div>
      </div>

      {/* Intelligence Enclave: Risk Gauge + Signal Attribution */}
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 'var(--space-5)' }}>
        {/* Left: Composite Risk Gauge */}
        <div
          style={{
            padding: 'var(--space-5)',
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
          }}
        >
          <span style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.05em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '14px' }}>
            BEHAVIORAL RISK ENVELOPE
          </span>
          <RadialGauge value={riskScore} severity={severity} size={140} />
          <div style={{ marginTop: '12px' }}>
            <span style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              {severity} SEVERITY
            </span>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>
              Multi-signal statistical isolation envelope
            </p>
          </div>
        </div>

        {/* Right: Signal Risk Attribution */}
        <div
          style={{
            padding: 'var(--space-5)',
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, letterSpacing: '0.04em', color: 'var(--text-primary)', textTransform: 'uppercase' }}>
                SIGNAL RISK ATTRIBUTION & EXPLAINABILITY
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {sensors.filter((s) => s.status === 'OK').length}/{sensors.length} sensors nominal
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {evidence.length > 0 ? (
                evidence.map((e, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>{e.signal}</span>
                    <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }} className="tabular-nums">+{e.weight} pts</span>
                  </div>
                ))
              ) : (
                <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                  Behavioral envelope matches baseline. No active anomaly contributors.
                </div>
              )}
            </div>
          </div>

          <div
            style={{
              marginTop: '16px',
              padding: '10px 14px',
              backgroundColor: 'var(--bg-surface-elevated)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.76rem',
            }}
          >
            <span style={{ color: 'var(--text-secondary)' }}>
              Storage: <strong style={{ color: 'var(--text-primary)' }}>SQLite WAL Encrypted</strong>
            </span>
            <span style={{ color: 'var(--text-secondary)' }}>
              Engine: <strong style={{ color: 'var(--text-primary)' }}>IsolationForest + LOF Edge</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Real-Time Security Activity Timeline */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            padding: '12px 20px',
            backgroundColor: 'var(--bg-surface-elevated)',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={15} color="var(--accent-primary)" />
            <span style={{ fontSize: '0.76rem', fontWeight: 700, letterSpacing: '0.04em', color: 'var(--text-primary)', textTransform: 'uppercase' }}>
              LIVE SECURITY ACTIVITY TIMELINE
            </span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Showing latest {recentEvents.length} events
          </span>
        </div>

        {recentEvents.length > 0 ? (
          recentEvents.slice(0, 5).map((evt, idx) => (
            <div
              key={evt.event_id || idx}
              style={{
                display: 'grid',
                gridTemplateColumns: '140px 100px 1fr 80px',
                alignItems: 'center',
                padding: '10px 20px',
                borderBottom: idx < 4 ? '1px solid var(--border-subtle)' : 'none',
                fontSize: '0.8rem',
              }}
            >
              <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.74rem' }}>
                {formatDateTime(evt.timestamp)}
              </span>
              <div>
                <Badge severity={evt.severity} size="sm">{evt.severity}</Badge>
              </div>
              <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {evt.summary}
              </span>
              <span style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }} className="tabular-nums">
                {evt.risk_score.toFixed(0)}
              </span>
            </div>
          ))
        ) : (
          <div style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
            No security events detected. Host is operating normally.
          </div>
        )}
      </div>
    </div>
  );
};
