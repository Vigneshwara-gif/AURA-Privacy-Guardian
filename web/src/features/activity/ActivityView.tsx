import React from 'react';
import { Activity } from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { useStream } from '../../context/StreamContext';
import { formatDateTime } from '../../utils/formatters';

export const ActivityView: React.FC = () => {
  const { recentEvents } = useStream();

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
          <Activity size={20} />
        </div>
        <div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.01em' }}>
            Operational Activity History
          </h1>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
            Unified chronological record of state changes, background sampling cycles, and security events.
          </p>
        </div>
      </div>

      {/* Timeline Stream */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          padding: 'var(--space-5)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {recentEvents.length > 0 ? (
            recentEvents.map((evt, idx) => (
              <div
                key={evt.event_id || idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '14px',
                  padding: '12px 14px',
                  backgroundColor: 'var(--bg-surface-subtle)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div style={{ marginTop: '2px' }}>
                  <Badge severity={evt.severity} size="sm">{evt.severity}</Badge>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {evt.event_type}
                    </span>
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {formatDateTime(evt.timestamp)}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                    {evt.summary}
                  </p>
                </div>
              </div>
            ))
          ) : (
            <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              No operational events recorded in the current session window.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
