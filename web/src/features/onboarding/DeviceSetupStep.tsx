import React from 'react';
import { ArrowLeft, ArrowRight, Laptop, Server } from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { useStream } from '../../context/StreamContext';

interface DeviceSetupStepProps {
  onNext: () => void;
  onBack: () => void;
}

export const DeviceSetupStep: React.FC<DeviceSetupStepProps> = ({ onNext, onBack }) => {
  const { latestTelemetry, agentStatus } = useStream();

  const hostname = 'WINDOWS-DEVICE';
  const platform = 'Windows 11 (x64)';
  const agentPid = agentStatus?.pid ? `PID: ${agentStatus.pid}` : 'Daemon Active';
  const dbPath = latestTelemetry?.disk_path ? `%LOCALAPPDATA%\\AURA\\data\\aura.db` : 'Isolated SQLite WAL';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)', maxWidth: '640px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 'var(--space-2)' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '3px 10px', borderRadius: 'var(--radius-full)', backgroundColor: 'var(--accent-primary-subtle)', border: '1px solid var(--accent-primary)', marginBottom: '8px' }}>
          <Laptop size={13} color="var(--accent-primary)" />
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent-primary-hover)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            HARDWARE IDENTITY
          </span>
        </div>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
          Device Setup & Sentinel Binding
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
          AURA binds its autonomous monitoring daemon to this specific Windows device.
        </p>
      </div>

      {/* Identity Card */}
      <div
        style={{
          padding: 'var(--space-5)',
          backgroundColor: 'var(--bg-surface-elevated)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-4)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 'var(--space-3)', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Server size={20} color="var(--accent-primary)" />
            <div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                DEVICE HOST IDENTIFIER
              </span>
              <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                {hostname}
              </div>
            </div>
          </div>
          <Badge severity="LOW">BOUND</Badge>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)', fontSize: '0.8rem' }}>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem', fontWeight: 600 }}>PLATFORM</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{platform}</span>
          </div>

          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem', fontWeight: 600 }}>MONITORING DAEMON</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{agentPid}</span>
          </div>

          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem', fontWeight: 600 }}>LOCAL STORAGE LAYER</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>{dbPath}</span>
          </div>

          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem', fontWeight: 600 }}>KERNEL GUARD</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Single-Instance Mutex</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 'var(--space-4)' }}>
        <Button variant="ghost" size="md" onClick={onBack} icon={<ArrowLeft size={16} />}>
          Back
        </Button>
        <Button variant="primary" size="md" onClick={onNext} icon={<ArrowRight size={16} />}>
          Run Capability Check
        </Button>
      </div>
    </div>
  );
};
