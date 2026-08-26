import React from 'react';
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { getSeverityBorder, getSeverityColor } from '../../utils/severity';

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        zIndex: 999,
        maxWidth: '380px',
      }}
    >
      {toasts.map((t) => {
        const color = getSeverityColor(t.severity);
        const border = getSeverityBorder(t.severity);

        return (
          <div
            key={t.id}
            role="alert"
            aria-live={t.severity === 'CRITICAL' || t.severity === 'HIGH' ? 'assertive' : 'polite'}
            style={{
              backgroundColor: 'var(--bg-surface-elevated)',
              border: `1px solid ${border}`,
              borderLeft: `4px solid ${color}`,
              borderRadius: 'var(--radius-md)',
              padding: '12px 16px',
              boxShadow: 'var(--shadow-card)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <div style={{ color, flexShrink: 0, marginTop: '2px' }}>
                {t.severity === 'CRITICAL' || t.severity === 'HIGH' ? (
                  <AlertCircle size={16} />
                ) : t.severity === 'NORMAL' || t.severity === 'INFO' ? (
                  <CheckCircle size={16} />
                ) : (
                  <Info size={16} />
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                    {t.title}
                  </h4>
                  {typeof t.riskScore === 'number' && t.riskScore > 0 && (
                    <span
                      style={{
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        padding: '1px 6px',
                        borderRadius: 'var(--radius-sm)',
                        backgroundColor: 'var(--bg-surface-subtle)',
                        color,
                        border: `1px solid ${border}`,
                      }}
                    >
                      Risk: {Math.round(t.riskScore)}
                    </span>
                  )}
                </div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '4px 0 0', lineHeight: 1.4 }}>
                  {t.message}
                </p>
              </div>
              <button
                onClick={() => removeToast(t.id)}
                aria-label="Dismiss alert"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '2px',
                }}
              >
                <X size={14} />
              </button>
            </div>

            {t.onInvestigate && t.eventId && (
              <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '4px', borderTop: '1px solid var(--border-subtle)' }}>
                <button
                  onClick={() => {
                    t.onInvestigate!(t.eventId!);
                    removeToast(t.id);
                  }}
                  style={{
                    backgroundColor: 'transparent',
                    border: `1px solid ${border}`,
                    color,
                    borderRadius: 'var(--radius-sm)',
                    padding: '4px 10px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Investigate →
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
