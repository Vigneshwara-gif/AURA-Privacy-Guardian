import React from 'react';
import { Badge } from '../../components/ui/Badge';
import { Card } from '../../components/ui/Card';
import { RadialGauge } from '../../components/ui/RadialGauge';
import { useStream } from '../../context/StreamContext';

export const RiskIntelligenceView: React.FC = () => {
  const { currentRisk } = useStream();

  const evidence = currentRisk?.evidence || [];
  const riskScore = currentRisk?.risk_score || 0;
  const severity = currentRisk?.severity || 'NORMAL';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--space-5)' }}>
        <Card
          title="Current Composite Risk Assessment"
          subtitle="Triage score generated from Isolation Forest ML & heuristic models"
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-around', padding: '12px 0' }}>
            <RadialGauge value={riskScore} severity={severity} size={150} />
            <div>
              <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {severity} Risk Band
              </span>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Score: {riskScore.toFixed(1)} / 100
              </p>
            </div>
          </div>
        </Card>

        <Card
          title="ML Anomaly & Feature Weight Breakdown"
          subtitle="Real-time explainable signal weights contributing to the risk score"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {evidence.length > 0 ? (
              evidence.map((e, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-surface-subtle)',
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  <div>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {e.signal}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>
                      {e.value !== undefined ? `Value: ${e.value} ${e.unit || ''}` : 'Measured anomaly'}
                    </span>
                  </div>
                  <Badge severity={e.severity}>+{e.weight} pts</Badge>
                </div>
              ))
            ) : (
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                Zero active anomaly weights. System baseline is normal.
              </p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
