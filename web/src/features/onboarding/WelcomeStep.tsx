import React, { useState } from 'react';
import { ArrowRight, Cpu, Eye, Info, Lock, Sparkles } from 'lucide-react';
import { AuraLogo } from '../../components/brand/AuraLogo';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';

interface WelcomeStepProps {
  onNext: () => void;
}

export const WelcomeStep: React.FC<WelcomeStepProps> = ({ onNext }) => {
  const [showLearnModal, setShowLearnModal] = useState(false);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        maxWidth: '560px',
        margin: '0 auto',
        padding: 'var(--space-6) var(--space-4)',
      }}
    >
      {/* Brand Hero Shield */}
      <div style={{ marginBottom: 'var(--space-5)' }}>
        <AuraLogo size={64} glow={true} />
      </div>

      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '3px 10px', borderRadius: 'var(--radius-full)', backgroundColor: 'var(--accent-primary-subtle)', border: '1px solid var(--accent-primary)', marginBottom: 'var(--space-3)' }}>
        <Sparkles size={13} color="var(--accent-primary)" />
        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent-primary-hover)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          AUTONOMOUS LOCAL INTELLIGENCE
        </span>
      </div>

      <h1
        style={{
          fontSize: '1.75rem',
          fontWeight: 800,
          letterSpacing: '-0.02em',
          color: 'var(--text-primary)',
          margin: '0 0 var(--space-2) 0',
          lineHeight: 1.25,
        }}
      >
        Your device. Your data. Your protection.
      </h1>

      <p
        style={{
          fontSize: '0.92rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.6,
          margin: '0 0 var(--space-6) 0',
        }}
      >
        AURA protects this Windows computer in real time against behavioral anomalies, unauthorized telemetry, and privacy intrusions with strictly local on-device intelligence.
      </p>

      {/* Feature Highlights Grid */}
      <div
        style={{
          width: '100%',
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 'var(--space-3)',
          marginBottom: 'var(--space-8)',
          textAlign: 'left',
        }}
      >
        <div
          style={{
            padding: 'var(--space-3)',
            backgroundColor: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <Cpu size={18} color="var(--accent-primary)" />
          <h4 style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', margin: '6px 0 2px 0' }}>
            Local-First
          </h4>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', margin: 0, lineHeight: 1.4 }}>
            100% on-device ML scoring without cloud telemetry.
          </p>
        </div>

        <div
          style={{
            padding: 'var(--space-3)',
            backgroundColor: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <Eye size={18} color="var(--accent-info)" />
          <h4 style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', margin: '6px 0 2px 0' }}>
            Passive Sentinels
          </h4>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', margin: 0, lineHeight: 1.4 }}>
            Passive hardware sentinels. No raw recording.
          </p>
        </div>

        <div
          style={{
            padding: 'var(--space-3)',
            backgroundColor: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <Lock size={18} color="var(--severity-low)" />
          <h4 style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', margin: '6px 0 2px 0' }}>
            Local Storage
          </h4>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', margin: 0, lineHeight: 1.4 }}>
            Encrypted SQLite WAL in %LOCALAPPDATA%.
          </p>
        </div>
      </div>

      {/* Primary Action Buttons */}
      <div style={{ display: 'flex', flexDirection: 'column', width: '100%', gap: 'var(--space-3)' }}>
        <Button
          variant="primary"
          size="lg"
          onClick={onNext}
          icon={<ArrowRight size={16} />}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          Protect This Device
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowLearnModal(true)}
          icon={<Info size={14} />}
          style={{ width: '100%', justifyContent: 'center', color: 'var(--text-secondary)' }}
        >
          Learn How AURA Works
        </Button>
      </div>

      {/* Learn How AURA Works Modal */}
      {showLearnModal && (
        <Modal
          isOpen={true}
          onClose={() => setShowLearnModal(false)}
          title="AURA Privacy Architecture & Design Principles"
          description="AURA is an on-device cybersecurity system designed from first principles for total local privacy."
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>1. Local-Only Execution:</strong> All sensor sampling, telemetry correlation, and unsupervised anomaly scoring execute locally on your processor.
            </div>
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>2. Metadata-Only Inspection:</strong> AURA inspects socket metadata and process states. It never captures keystrokes, audio recordings, or video frames.
            </div>
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>3. Isolated Persistence:</strong> Telemetry and risk metrics are stored strictly inside your local Windows user profile (`%LOCALAPPDATA%\\AURA`).
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-2)' }}>
              <Button variant="primary" size="sm" onClick={() => setShowLearnModal(false)}>
                Got It
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
