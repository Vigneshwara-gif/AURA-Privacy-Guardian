import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, Sliders } from 'lucide-react';
import { NotificationManager, type NotificationSettings } from '../../services/notificationManager';
import { Button } from '../../components/ui/Button';

interface ProtectionPreferencesStepProps {
  onNext: () => void;
  onBack: () => void;
}

export const ProtectionPreferencesStep: React.FC<ProtectionPreferencesStepProps> = ({ onNext, onBack }) => {
  const [settings, setSettings] = useState<NotificationSettings>(NotificationManager.getSettings());

  const handleToggle = (key: keyof NotificationSettings) => {
    const updated = { ...settings, [key]: !settings[key] };
    setSettings(updated);
    NotificationManager.saveSettings(updated);
  };

  const handleSeverityChange = (minSev: NotificationSettings['minSeverity']) => {
    const updated = { ...settings, minSeverity: minSev };
    setSettings(updated);
    NotificationManager.saveSettings(updated);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)', maxWidth: '640px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 'var(--space-2)' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '3px 10px', borderRadius: 'var(--radius-full)', backgroundColor: 'var(--accent-primary-subtle)', border: '1px solid var(--accent-primary)', marginBottom: '8px' }}>
          <Sliders size={13} color="var(--accent-primary)" />
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent-primary-hover)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            NOTIFICATION POLICY
          </span>
        </div>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
          Protection Preferences
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
          Configure real-time alerting thresholds and notification delivery channels.
        </p>
      </div>

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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Master Real-Time Alerting
            </span>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0 }}>
              Deliver incident notifications when behavioral anomalies occur
            </p>
          </div>
          <input
            type="checkbox"
            checked={settings.enabled}
            onChange={() => handleToggle('enabled')}
            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Native Windows Toast Notifications
            </span>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0 }}>
              Dispatch native desktop toast banners via Windows Action Center
            </p>
          </div>
          <input
            type="checkbox"
            checked={settings.nativeEnabled}
            onChange={() => handleToggle('nativeEnabled')}
            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              In-App Interactive Banners
            </span>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0 }}>
              Show interactive top toast banners inside the AURA dashboard
            </p>
          </div>
          <input
            type="checkbox"
            checked={settings.inAppEnabled}
            onChange={() => handleToggle('inAppEnabled')}
            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
          />
        </div>

        <div style={{ paddingTop: 'var(--space-3)', borderTop: '1px solid var(--border-subtle)' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', display: 'block', marginBottom: '8px' }}>
            Minimum Severity Threshold:
          </span>
          <div style={{ display: 'flex', gap: '8px' }}>
            {(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const).map((sev) => (
              <button
                key={sev}
                onClick={() => handleSeverityChange(sev)}
                style={{
                  flex: 1,
                  padding: '7px 0',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid',
                  borderColor: settings.minSeverity === sev ? 'var(--accent-primary)' : 'var(--border-subtle)',
                  backgroundColor: settings.minSeverity === sev ? 'var(--accent-primary-subtle)' : 'transparent',
                  color: settings.minSeverity === sev ? 'var(--accent-primary-hover)' : 'var(--text-secondary)',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 'var(--space-4)' }}>
        <Button variant="ghost" size="md" onClick={onBack} icon={<ArrowLeft size={16} />}>
          Back
        </Button>
        <Button variant="primary" size="md" onClick={onNext} icon={<ArrowRight size={16} />}>
          Start Protection & Scan
        </Button>
      </div>
    </div>
  );
};
