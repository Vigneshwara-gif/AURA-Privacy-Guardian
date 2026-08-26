import React, { useState } from 'react';
import { Check, Copy, X } from 'lucide-react';
import type { SecurityEventResponse } from '../../contracts/api';
import { ApiClient } from '../../services/apiClient';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { formatDateTime } from '../../utils/formatters';

export interface EventDetailDrawerProps {
  event: SecurityEventResponse | null;
  isOpen?: boolean;
  onClose: () => void;
  onAcknowledged?: () => void;
}

export const EventDetailDrawer: React.FC<EventDetailDrawerProps> = ({ event, isOpen = true, onClose, onAcknowledged }) => {
  const [isAcking, setIsAcking] = useState(false);
  const [ackSuccess, setAckSuccess] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!isOpen || !event) return null;

  const handleAck = async () => {
    setIsAcking(true);
    try {
      await ApiClient.acknowledgeEvent(event.event_id, '');
      setAckSuccess(true);
      if (onAcknowledged) onAcknowledged();
    } catch {
      // Handled
    } finally {
      setIsAcking(false);
    }
  };

  const copyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(event, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      role="dialog"
      aria-label="Security Event Investigation"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 90,
        backgroundColor: 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(2px)',
        display: 'flex',
        justifyContent: 'flex-end',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '520px',
          height: '100%',
          backgroundColor: 'var(--bg-surface)',
          borderLeft: '1px solid var(--border-subtle)',
          boxShadow: 'var(--shadow-modal)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: 'var(--space-5)',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Badge severity={event.severity}>{event.severity}</Badge>
            <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {event.event_type}
            </span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close drawer"
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, padding: 'var(--space-5)', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              EVENT SUMMARY
            </span>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginTop: '4px', lineHeight: 1.5 }}>
              {event.summary}
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', padding: '12px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)' }}>
            <div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>EVENT ID</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{event.event_id}</span>
            </div>
            <div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>TIMESTAMP</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{formatDateTime(event.timestamp)}</span>
            </div>
            <div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>RISK SCORE</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-primary-hover)' }}>{event.risk_score.toFixed(0)} / 100</span>
            </div>
            <div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>STATUS</span>
              <span style={{ fontSize: '0.75rem', color: event.is_resolved ? 'var(--severity-low)' : 'var(--severity-medium)' }}>
                {event.is_resolved ? 'RESOLVED' : 'ACTIVE INCIDENT'}
              </span>
            </div>
          </div>

          {/* Raw JSON Inspection */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                RAW EVENT JSON
              </span>
              <button
                onClick={copyJson}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: copied ? 'var(--severity-low)' : 'var(--accent-primary)',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
                {copied ? 'Copied' : 'Copy JSON'}
              </button>
            </div>
            <pre
              style={{
                margin: 0,
                padding: '12px',
                backgroundColor: 'var(--bg-surface-subtle)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-secondary)',
                overflowX: 'auto',
                maxHeight: '220px',
              }}
            >
              {JSON.stringify(event, null, 2)}
            </pre>
          </div>
        </div>

        {/* Footer Actions */}
        <div style={{ padding: 'var(--space-4) var(--space-5)', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
          {!event.is_resolved && (
            <Button variant="primary" size="sm" loading={isAcking} onClick={handleAck}>
              {ackSuccess ? 'Acknowledged' : 'Acknowledge Event'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
