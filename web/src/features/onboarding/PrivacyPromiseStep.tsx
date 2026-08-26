import React from 'react';
import { ArrowLeft, ArrowRight, CheckCircle2, ShieldCheck, XCircle } from 'lucide-react';
import { Button } from '../../components/ui/Button';

interface PrivacyPromiseStepProps {
  onNext: () => void;
  onBack: () => void;
}

export const PrivacyPromiseStep: React.FC<PrivacyPromiseStepProps> = ({ onNext, onBack }) => {
  const whatAuraDoes = [
    'Samples host CPU & memory telemetry to detect abnormal execution loads',
    'Monitors network socket metadata (IPs/ports) to flag unauthorized connections',
    'Uses unsupervised ML (IsolationForest) on-device to score risk deviations',
    'Persists encrypted audit events strictly to your local Windows user directory',
    'Provides explainable signal attribution for every flagged security anomaly',
  ];

  const whatAuraNeverDoes = [
    'NEVER logs keystrokes, passwords, or clipboard contents',
    'NEVER records or captures raw microphone audio',
    'NEVER records or inspects camera video streams',
    'NEVER inspects packet payloads or private message contents',
    'NEVER uploads, sells, or exfiltrates telemetry data to any cloud service',
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)', maxWidth: '720px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 'var(--space-2)' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '3px 10px', borderRadius: 'var(--radius-full)', backgroundColor: 'var(--accent-primary-subtle)', border: '1px solid var(--accent-primary)', marginBottom: '8px' }}>
          <ShieldCheck size={13} color="var(--accent-primary)" />
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent-primary-hover)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            TRANSPARENCY GUARANTEE
          </span>
        </div>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
          The AURA Privacy Promise
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
          Clear, verifiable commitments on what AURA does—and what AURA never touches.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
        {/* What AURA Does */}
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--severity-low)' }}>
            <CheckCircle2 size={16} />
            <span style={{ fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              What AURA Does
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {whatAuraDoes.map((item, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '0.78rem', color: 'var(--text-primary)', lineHeight: 1.45 }}>
                <span style={{ color: 'var(--severity-low)', fontWeight: 700 }}>•</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>

        {/* What AURA Never Does */}
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--severity-high)' }}>
            <XCircle size={16} />
            <span style={{ fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              What AURA Never Does
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {whatAuraNeverDoes.map((item, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '0.78rem', color: 'var(--text-primary)', lineHeight: 1.45 }}>
                <span style={{ color: 'var(--severity-high)', fontWeight: 700 }}>•</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Navigation Actions */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 'var(--space-4)' }}>
        <Button variant="ghost" size="md" onClick={onBack} icon={<ArrowLeft size={16} />}>
          Back
        </Button>
        <Button variant="primary" size="md" onClick={onNext} icon={<ArrowRight size={16} />}>
          I Understand & Agree
        </Button>
      </div>
    </div>
  );
};
