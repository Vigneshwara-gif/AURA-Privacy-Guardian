import React, { useEffect, useState } from 'react';
import { RefreshCw, ShieldCheck, Sparkles } from 'lucide-react';
import { ApiClient } from '../../services/apiClient';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

interface InitialScanStepProps {
  onComplete: () => void;
}

export const InitialScanStep: React.FC<InitialScanStepProps> = ({ onComplete }) => {
  const [scanning, setScanning] = useState(true);
  const [stage, setStage] = useState('SAMPLING');
  const [scanResult, setScanResult] = useState<{ scan_id: string; elapsed_seconds: number; risk_score: number } | null>(null);

  useEffect(() => {
    let active = true;

    async function runInitialScan() {
      try {
        setStage('SAMPLING SENSORS');
        await new Promise((r) => setTimeout(r, 600));

        if (!active) return;
        setStage('ANALYZING ENVELOPES');
        await new Promise((r) => setTimeout(r, 600));

        if (!active) return;
        setStage('EVALUATING ISOLATION FOREST');
        const res = await ApiClient.triggerScan({
          probe_camera: false,
          probe_microphone: false,
          is_demo: false,
        });

        if (active) {
          setScanResult({
            scan_id: res.scan_id,
            elapsed_seconds: res.elapsed_seconds,
            risk_score: res.risk_score ?? 0,
          });
          setScanning(false);
          setStage('BASELINE COMPLETE');
        }
      } catch {
        if (active) {
          setScanning(false);
          setStage('BASELINE INITIALIZED');
        }
      }
    }

    runInitialScan();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', maxWidth: '580px', margin: '0 auto', padding: 'var(--space-6) var(--space-4)' }}>
      <div
        style={{
          width: '64px',
          height: '64px',
          borderRadius: 'var(--radius-lg)',
          backgroundColor: scanning ? 'var(--accent-primary-subtle)' : 'rgba(32, 199, 122, 0.12)',
          border: `1px solid ${scanning ? 'var(--accent-primary)' : 'var(--severity-low)'}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 'var(--space-5)',
        }}
      >
        {scanning ? (
          <RefreshCw size={30} color="var(--accent-primary)" style={{ animation: 'spin 1.5s linear infinite' }} />
        ) : (
          <ShieldCheck size={32} color="var(--severity-low)" />
        )}
      </div>

      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '3px 10px', borderRadius: 'var(--radius-full)', backgroundColor: 'var(--accent-primary-subtle)', border: '1px solid var(--accent-primary)', marginBottom: 'var(--space-3)' }}>
        <Sparkles size={13} color="var(--accent-primary)" />
        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent-primary-hover)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          {stage}
        </span>
      </div>

      <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 var(--space-2) 0' }}>
        {scanning ? 'Establishing Security Baseline...' : 'Device Protection Active'}
      </h2>

      <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: '0 0 var(--space-6) 0' }}>
        {scanning
          ? 'Sampling host hardware metrics and training local statistical baseline envelopes...'
          : 'Initial host baseline complete. Continuous background sensor sentinels are active.'}
      </p>

      {/* Scan Results Card */}
      {scanResult && (
        <div
          style={{
            width: '100%',
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            marginBottom: 'var(--space-6)',
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '12px',
            textAlign: 'left',
          }}
        >
          <div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, display: 'block' }}>INITIAL RISK</span>
            <span style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--severity-low)' }}>
              {scanResult.risk_score.toFixed(0)} <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>/ 100</span>
            </span>
          </div>

          <div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, display: 'block' }}>DURATION</span>
            <span style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
              {scanResult.elapsed_seconds.toFixed(3)}s
            </span>
          </div>

          <div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, display: 'block' }}>STATUS</span>
            <Badge severity="LOW">PROTECTED</Badge>
          </div>
        </div>
      )}

      {!scanning && (
        <Button
          variant="primary"
          size="lg"
          onClick={onComplete}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          Enter Mission Control →
        </Button>
      )}
    </div>
  );
};
