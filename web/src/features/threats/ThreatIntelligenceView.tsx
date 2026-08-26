import React from 'react';
import {
  AlertTriangle,
  Brain,
  CheckCircle2,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { useStream } from '../../context/StreamContext';

export const ThreatIntelligenceView: React.FC = () => {
  const { currentRisk, sensors } = useStream();

  const riskScore = currentRisk?.risk_score ?? 0;
  const severity = currentRisk?.severity ?? 'NORMAL';
  const evidence = currentRisk?.evidence ?? [];
  const reasons = currentRisk?.reasons ?? [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
      {/* Top Threat Intelligence Banner */}
      <div
        style={{
          padding: 'var(--space-5) var(--space-6)',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--accent-primary-subtle)',
              border: '1px solid var(--accent-primary-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-primary)',
              flexShrink: 0,
            }}
          >
            <Brain size={22} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.01em' }}>
              Threat Intelligence & ML Explainability
            </h1>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
              Multi-signal statistical isolation envelope correlation with real-time signal weight attribution.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Badge severity={severity} size="md">
            {severity} RISK ({riskScore.toFixed(0)}/100)
          </Badge>
        </div>
      </div>

      {/* Behavioral Explainability Banner */}
      <div
        style={{
          padding: '16px 20px',
          backgroundColor: 'var(--bg-surface-elevated)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
        }}
      >
        <div style={{ color: severity === 'CRITICAL' || severity === 'HIGH' ? 'var(--severity-critical)' : 'var(--severity-low)' }}>
          {severity === 'CRITICAL' || severity === 'HIGH' ? <AlertTriangle size={20} /> : <CheckCircle2 size={20} />}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Behavioral Risk Explainability Summary
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            {reasons.length > 0
              ? reasons.join(' • ')
              : 'Host metrics are operating within verified statistical baseline envelopes. No behavioral anomalies detected.'}
          </div>
        </div>
      </div>

      {/* Signal Contributions Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 'var(--space-4)' }}>
        {sensors.map((sensor, idx) => {
          const matchedEvidence = evidence.find((e) => e.signal.toLowerCase().includes(sensor.name.toLowerCase()));
          const weight = matchedEvidence ? matchedEvidence.weight : 0;
          const isAnomaly = weight > 0;

          return (
            <div
              key={idx}
              style={{
                padding: 'var(--space-4)',
                backgroundColor: 'var(--bg-surface)',
                borderRadius: 'var(--radius-lg)',
                border: isAnomaly ? '1px solid var(--severity-high-border)' : '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {sensor.name}
                </span>
                <Badge severity={isAnomaly ? 'HIGH' : 'LOW'} size="sm">
                  {isAnomaly ? `+${weight} PTS` : 'NOMINAL'}
                </Badge>
              </div>

              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                {sensor.detail}
              </div>

              <div style={{ marginTop: 'auto', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                <span>Health: {sensor.status}</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>Sensor ID #{idx + 1}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Multi-Layered Intelligence Reasoning Chain */}
      <div
        style={{
          padding: 'var(--space-5)',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <span style={{ fontSize: '0.85rem', fontWeight: 700, letterSpacing: '0.04em', color: 'var(--text-primary)', textTransform: 'uppercase' }}>
          MULTI-LAYERED INTELLIGENCE REASONING CHAIN
        </span>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-3)' }}>
          <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase' }}>
              STEP 1: SENSOR INGESTION
            </span>
            <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
              Micro-Cadence Sampling
            </div>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '4px 0 0 0', lineHeight: 1.4 }}>
              Process trees, socket states, and CPU/RAM vectors sampled non-intrusively every 5 seconds.
            </p>
          </div>

          <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase' }}>
              STEP 2: BASELINE DRIFT
            </span>
            <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
              Isolation Forest Scoring
            </div>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '4px 0 0 0', lineHeight: 1.4 }}>
              Unsupervised tree partitioning identifies topological outliers without predefined signatures.
            </p>
          </div>

          <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase' }}>
              STEP 3: LOCAL DENSITY
            </span>
            <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
              Local Outlier Factor (LOF)
            </div>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '4px 0 0 0', lineHeight: 1.4 }}>
              Calculates relative density of metric clusters to eliminate temporary legitimate workload spikes.
            </p>
          </div>

          <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase' }}>
              STEP 4: RISK SYNTHESIS
            </span>
            <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
              Evidence Synthesis
            </div>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '4px 0 0 0', lineHeight: 1.4 }}>
              Weighted attribution maps anomaly contributions and dispatches deduplicated incident notifications.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
