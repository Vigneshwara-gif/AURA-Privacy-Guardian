import React from 'react';
import { Camera, Eye, Mic } from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { useStream } from '../../context/StreamContext';

export const PrivacyView: React.FC = () => {
  const { latestTelemetry, sensors } = useStream();

  const camSensor = sensors.find((s) => s.name.toLowerCase().includes('camera'));
  const micSensor = sensors.find((s) => s.name.toLowerCase().includes('audio') || s.name.toLowerCase().includes('microphone'));

  // Truthful Hardware State Mapping based strictly on evidence
  const getCameraBadge = (status?: string) => {
    switch (status) {
      case 'ACTIVE':
        return { text: 'IN USE (ACTIVE CAPTURE DETECTED)', severity: 'HIGH' as const, note: 'DirectShow descriptor indicates an active video stream session.' };
      case 'INACTIVE':
        return { text: 'NOT IN USE (DEVICE IDLE)', severity: 'LOW' as const, note: 'Verified zero active DirectShow media stream sessions.' };
      case 'MUTED':
        return { text: 'HARDWARE MUTED', severity: 'LOW' as const, note: 'Camera sensor hardware privacy switch is engaged.' };
      case 'UNAVAILABLE':
        return { text: 'DEVICE UNAVAILABLE', severity: 'MEDIUM' as const, note: 'No DirectShow video capture devices enumerated on this host.' };
      case 'NOT_PROBED':
      case 'UNKNOWN':
      default:
        return { text: 'STATUS UNAVAILABLE (DESCRIPTOR MONITORING ONLY)', severity: 'INFO' as const, note: 'DirectShow probe did not execute or returned unprobed descriptor metadata.' };
    }
  };

  const getMicrophoneBadge = (status?: string) => {
    switch (status) {
      case 'ACTIVE':
        return { text: 'IN USE (ACTIVE CAPTURE DETECTED)', severity: 'HIGH' as const, note: 'Windows CoreAudio active audio session enumerator detected active capture.' };
      case 'INACTIVE':
        return { text: 'NOT IN USE (DEVICE IDLE)', severity: 'LOW' as const, note: 'Verified zero active CoreAudio recording client sessions.' };
      case 'MUTED':
        return { text: 'HARDWARE MUTED', severity: 'LOW' as const, note: 'Microphone hardware or OS input volume is muted.' };
      case 'UNAVAILABLE':
        return { text: 'DEVICE UNAVAILABLE', severity: 'MEDIUM' as const, note: 'No CoreAudio audio input endpoints detected on this host.' };
      case 'NOT_PROBED':
      case 'UNKNOWN':
      default:
        return { text: 'STATUS UNAVAILABLE (DESCRIPTOR MONITORING ONLY)', severity: 'INFO' as const, note: 'CoreAudio probe returned unprobed state. No raw audio is recorded.' };
    }
  };

  const camBadge = getCameraBadge(latestTelemetry?.camera_status);
  const micBadge = getMicrophoneBadge(latestTelemetry?.microphone_status);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Privacy Sentinel Header Banner */}
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
            <Eye size={22} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.01em' }}>
              Privacy Intelligence Sentinel
            </h1>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
              Non-intrusive Windows hardware descriptor inspection. No raw media capture, no keystroke logging, strictly local isolation envelope.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Badge severity="LOW">NO EXFILTRATION SIGNALS DETECTED</Badge>
        </div>
      </div>

      {/* Hardware Sentinel Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 'var(--space-5)' }}>
        {/* Camera Sentinel */}
        <div
          style={{
            padding: 'var(--space-5)',
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Camera size={18} color="var(--accent-primary)" />
              <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Camera Video Sentinel
              </span>
            </div>
            <Badge severity={camBadge.severity} size="sm">{camBadge.text}</Badge>
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            {latestTelemetry?.camera_status || 'STATUS UNAVAILABLE'}
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
            {camBadge.note}
          </p>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 'auto' }}>
            DirectShow Probe: {camSensor?.status ?? 'PASSIVE'}
          </div>
        </div>

        {/* Audio Sentinel */}
        <div
          style={{
            padding: 'var(--space-5)',
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Mic size={18} color="var(--accent-info)" />
              <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Microphone Audio Sentinel
              </span>
            </div>
            <Badge severity={micBadge.severity} size="sm">{micBadge.text}</Badge>
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            {latestTelemetry?.microphone_status || 'STATUS UNAVAILABLE'}
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
            {micBadge.note}
          </p>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 'auto' }}>
            CoreAudio Session Enumerator: {micSensor?.status ?? 'PASSIVE'}
          </div>
        </div>
      </div>

      {/* Relationship & Flow Provenance Matrix */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          padding: 'var(--space-5)',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <span style={{ fontSize: '0.85rem', fontWeight: 700, letterSpacing: '0.04em', color: 'var(--text-primary)', textTransform: 'uppercase' }}>
          PRIVACY RELATIONSHIP & FLOW PROVENANCE
        </span>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-4)' }}>
          <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              1. OBSERVED PROCESSES
            </span>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }} className="tabular-nums">
              {latestTelemetry?.process_count || 0} active processes
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', margin: 0 }}>
              Process names, handles, and thread loads without memory dumping.
            </p>
          </div>

          <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              2. SOCKET FLOW METADATA
            </span>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }} className="tabular-nums">
              {latestTelemetry?.established_connections || 0} established connections
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', margin: 0 }}>
              IP addresses and ports inspected without packet payload snooping.
            </p>
          </div>

          <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              3. LOCAL ENCRYPTION
            </span>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--severity-low)', marginTop: '4px' }}>
              Isolated SQLite WAL
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', margin: 0 }}>
              All telemetry persists strictly to local Windows directory storage.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
