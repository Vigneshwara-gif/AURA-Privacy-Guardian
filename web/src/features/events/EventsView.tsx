import React, { useState } from 'react';
import { ArrowUpRight, Search } from 'lucide-react';
import type { SecurityEventResponse } from '../../contracts/api';
import { Badge } from '../../components/ui/Badge';
import { SegmentedControl } from '../../components/ui/SegmentedControl';
import { useStream } from '../../context/StreamContext';
import { formatDateTime } from '../../utils/formatters';
import { EventDetailDrawer } from './EventDetailDrawer';

export const EventsView: React.FC = () => {
  const { recentEvents } = useStream();
  const [selectedEvent, setSelectedEvent] = useState<SecurityEventResponse | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredEvents = recentEvents.filter((e) => {
    if (severityFilter !== 'ALL' && e.severity !== severityFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        e.summary.toLowerCase().includes(q) ||
        e.event_type.toLowerCase().includes(q) ||
        e.event_id.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Header Controls */}
      <div
        style={{
          padding: 'var(--space-4) var(--space-5)',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
        }}
      >
        <SegmentedControl
          options={[
            { value: 'ALL', label: 'All Events', badge: recentEvents.length },
            { value: 'CRITICAL', label: 'Critical' },
            { value: 'HIGH', label: 'High' },
            { value: 'MEDIUM', label: 'Medium' },
            { value: 'LOW', label: 'Low' },
            { value: 'NORMAL', label: 'Normal' },
          ]}
          value={severityFilter}
          onChange={setSeverityFilter}
          size="sm"
        />

        <div style={{ position: 'relative', width: '280px' }}>
          <Search
            size={14}
            color="var(--text-muted)"
            style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }}
          />
          <input
            type="text"
            placeholder="Search events, types, IDs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '6px 12px 6px 32px',
              backgroundColor: 'var(--bg-surface-subtle)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontSize: '0.8rem',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Events Table */}
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
            display: 'grid',
            gridTemplateColumns: '150px 110px 180px 1fr 90px 40px',
            padding: '12px 20px',
            backgroundColor: 'var(--bg-surface-elevated)',
            borderBottom: '1px solid var(--border-subtle)',
            fontSize: '0.72rem',
            fontWeight: 700,
            letterSpacing: '0.05em',
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
          }}
        >
          <span>TIMESTAMP</span>
          <span>SEVERITY</span>
          <span>EVENT TYPE</span>
          <span>SUMMARY</span>
          <span style={{ textAlign: 'right' }}>RISK</span>
          <span></span>
        </div>

        {filteredEvents.length > 0 ? (
          filteredEvents.map((evt, idx) => (
            <div
              key={evt.event_id || idx}
              onClick={() => setSelectedEvent(evt)}
              style={{
                display: 'grid',
                gridTemplateColumns: '150px 110px 180px 1fr 90px 40px',
                alignItems: 'center',
                padding: '12px 20px',
                borderBottom: idx < filteredEvents.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                cursor: 'pointer',
                fontSize: '0.82rem',
                transition: 'background-color var(--transition-fast)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-hover)')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
            >
              <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.76rem' }}>
                {formatDateTime(evt.timestamp)}
              </span>
              <div>
                <Badge severity={evt.severity} size="sm">
                  {evt.severity}
                </Badge>
              </div>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {evt.event_type}
              </span>
              <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {evt.summary}
              </span>
              <span style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }} className="tabular-nums">
                {evt.risk_score.toFixed(0)}
              </span>
              <div style={{ textAlign: 'right' }}>
                <ArrowUpRight size={14} color="var(--text-muted)" />
              </div>
            </div>
          ))
        ) : (
          <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No security events matching the selected filters.
          </div>
        )}
      </div>

      <EventDetailDrawer
        event={selectedEvent}
        isOpen={selectedEvent !== null}
        onClose={() => setSelectedEvent(null)}
      />
    </div>
  );
};
