import React, { useState } from 'react';
import { AlertCircle, Flame } from 'lucide-react';
import { AuthService } from '../../services/authService';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { useStream } from '../../context/StreamContext';

interface IncidentAction {
  id: string;
  name: string;
  description: string;
  supported: boolean;
  unsupportedReason?: string;
  isDestructive: boolean;
  actionType: 'SCAN' | 'SYNC' | 'SIGNOUT' | 'ISOLATE' | 'BLOCK' | 'QUARANTINE';
}

export const IncidentsView: React.FC = () => {
  const { triggerScan, refreshState } = useStream();
  const [selectedAction, setSelectedAction] = useState<IncidentAction | null>(null);
  const [actionHistory, setActionHistory] = useState<Array<{ timestamp: string; action: string; target: string; status: string }>>([
    { timestamp: new Date().toLocaleTimeString(), action: 'System Sentinel Initialized', target: 'Host Enclave', status: 'SUCCESS' },
  ]);
  const [executing, setExecuting] = useState(false);

  const actions: IncidentAction[] = [
    {
      id: 'trigger-full-scan',
      name: 'Trigger Immediate Deep Host Scan',
      description: 'Executes an immediate comprehensive multi-signal correlation scan across all sensor layers.',
      supported: true,
      isDestructive: false,
      actionType: 'SCAN',
    },
    {
      id: 'sign-out-session',
      name: 'Sign Out Active Client Session',
      description: 'Clears locally stored authentication tokens from browser storage and disconnects the active telemetry stream.',
      supported: true,
      isDestructive: true,
      actionType: 'SIGNOUT',
    },
    {
      id: 'resync-telemetry',
      name: 'Resynchronize Telemetry State',
      description: 'Queries local daemon REST endpoints to synchronize the latest host telemetry and risk evaluation into the dashboard.',
      supported: true,
      isDestructive: false,
      actionType: 'SYNC',
    },
    {
      id: 'isolate-host',
      name: 'Isolate Host Endpoint (WFP)',
      description: 'Sever all non-loopback network communication via Windows Filtering Platform firewall rules.',
      supported: false,
      unsupportedReason: 'Requires Windows Filtering Platform (WFP) driver integration.',
      isDestructive: true,
      actionType: 'ISOLATE',
    },
    {
      id: 'block-subnet',
      name: 'Block Remote Subnet CIDR',
      description: 'Dynamically drop inbound/outbound packets to flagged malicious external IP ranges.',
      supported: false,
      unsupportedReason: 'Requires kernel network filter driver.',
      isDestructive: true,
      actionType: 'BLOCK',
    },
    {
      id: 'quarantine-process',
      name: 'Quarantine Process Binary',
      description: 'Terminate process execution and isolate binary payload into secure staging vault.',
      supported: false,
      unsupportedReason: 'Requires elevated Windows supervisor daemon.',
      isDestructive: true,
      actionType: 'QUARANTINE',
    },
  ];

  const handleExecuteAction = async () => {
    if (!selectedAction) return;
    setExecuting(true);
    let resultStatus = 'SUCCESS';
    try {
      if (selectedAction.actionType === 'SCAN') {
        await triggerScan(true, true, false);
      } else if (selectedAction.actionType === 'SIGNOUT') {
        AuthService.clearSession();
      } else if (selectedAction.actionType === 'SYNC') {
        await refreshState();
      }

      setActionHistory((prev) => [
        {
          timestamp: new Date().toLocaleTimeString(),
          action: selectedAction.name,
          target: 'Local Endpoint',
          status: resultStatus,
        },
        ...prev,
      ]);
    } catch (err) {
      resultStatus = 'FAILED';
      setActionHistory((prev) => [
        {
          timestamp: new Date().toLocaleTimeString(),
          action: selectedAction.name,
          target: 'Local Endpoint',
          status: 'FAILED',
        },
        ...prev,
      ]);
    } finally {
      setExecuting(false);
      setSelectedAction(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Header Banner */}
      <div
        style={{
          padding: 'var(--space-5) var(--space-6)',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
        }}
      >
        <div
          style={{
            width: '40px',
            height: '40px',
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
          <Flame size={20} />
        </div>
        <div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.01em' }}>
            Incident Studio & Containment Console
          </h1>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
            Execute authenticated mitigation workflows and inspect OS containment capability boundaries.
          </p>
        </div>
      </div>

      {/* Action Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 'var(--space-4)' }}>
        {actions.map((act) => (
          <div
            key={act.id}
            style={{
              padding: 'var(--space-5)',
              backgroundColor: 'var(--bg-surface)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '14px',
              opacity: act.supported ? 1 : 0.7,
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {act.name}
                </span>
                <Badge severity={act.supported ? (act.isDestructive ? 'HIGH' : 'LOW') : 'MEDIUM'} size="sm">
                  {act.supported ? (act.isDestructive ? 'DESTRUCTIVE' : 'SUPPORTED') : 'UNAVAILABLE'}
                </Badge>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                {act.description}
              </p>
              {!act.supported && act.unsupportedReason && (
                <div style={{ marginTop: '8px', fontSize: '0.72rem', color: 'var(--severity-medium)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <AlertCircle size={12} />
                  <span>{act.unsupportedReason}</span>
                </div>
              )}
            </div>

            <Button
              variant={act.isDestructive ? 'danger' : 'primary'}
              size="sm"
              disabled={!act.supported}
              onClick={() => setSelectedAction(act)}
            >
              {act.supported ? 'Execute Workflow' : 'Capability Unavailable'}
            </Button>
          </div>
        ))}
      </div>

      {/* Audit History Table */}
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
            fontSize: '0.75rem',
            fontWeight: 700,
            color: 'var(--text-primary)',
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          }}
        >
          CONTAINMENT AUDIT LOG
        </div>

        {actionHistory.map((item, idx) => (
          <div
            key={idx}
            style={{
              display: 'grid',
              gridTemplateColumns: '120px 1fr 140px 100px',
              padding: '10px 20px',
              borderBottom: idx < actionHistory.length - 1 ? '1px solid var(--border-subtle)' : 'none',
              fontSize: '0.8rem',
            }}
          >
            <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{item.timestamp}</span>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{item.action}</span>
            <span style={{ color: 'var(--text-secondary)' }}>{item.target}</span>
            <div style={{ textAlign: 'right' }}>
              <Badge severity={item.status === 'SUCCESS' ? 'LOW' : item.status === 'EXECUTED' ? 'INFO' : 'CRITICAL'} size="sm">
                {item.status}
              </Badge>
            </div>
          </div>
        ))}
      </div>

      {/* Action Execution Confirmation Modal */}
      {selectedAction && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedAction(null)}
          title={`Confirm Action: ${selectedAction.name}`}
          description={selectedAction.description}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {selectedAction.isDestructive && (
              <div
                style={{
                  padding: '10px 12px',
                  backgroundColor: 'var(--severity-high-bg)',
                  border: '1px solid var(--severity-high-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--severity-high)',
                  fontSize: '0.78rem',
                }}
              >
                Warning: This action clears your local session tokens from browser storage and disconnects the live stream.
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
              <Button variant="ghost" size="sm" onClick={() => setSelectedAction(null)}>
                Cancel
              </Button>
              <Button
                variant={selectedAction.isDestructive ? 'danger' : 'primary'}
                size="sm"
                loading={executing}
                onClick={handleExecuteAction}
              >
                Confirm & Execute
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
