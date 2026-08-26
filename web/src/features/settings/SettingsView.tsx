import React, { useState } from 'react';
import {
  Bell,
  Cpu,
  Eye,
  HardDrive,
  Info,
  RotateCcw,
  Shield,
  Sliders,
} from 'lucide-react';
import { NotificationManager, type NotificationSettings } from '../../services/notificationManager';
import { resetOnboarding } from '../onboarding/onboardingState';
import { AuraLogo } from '../../components/brand/AuraLogo';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { SegmentedControl } from '../../components/ui/SegmentedControl';
import { ToggleSwitch } from '../../components/ui/ToggleSwitch';
import { useNavigation } from '../../context/NavigationContext';
import { useStream } from '../../context/StreamContext';
import { useTheme } from '../../context/ThemeContext';
import { formatDuration } from '../../utils/formatters';

type SettingsTab =
  | 'general'
  | 'notifications'
  | 'sentinels'
  | 'storage'
  | 'engine'
  | 'about';

export const SettingsView: React.FC = () => {
  const { startOnboarding } = useNavigation();
  const { agentStatus, latestTelemetry, sensors } = useStream();
  const { theme, setTheme } = useTheme();

  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const [notifSettings, setNotifSettings] = useState<NotificationSettings>(() => NotificationManager.getSettings());
  const [showResetModal, setShowResetModal] = useState(false);
  const [autoStartEnabled, setAutoStartEnabled] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('aura_autostart_enabled') !== 'false';
    }
    return true;
  });
  const [telemetrySamplingRate, setTelemetrySamplingRate] = useState<'5s' | '10s' | '15s'>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('aura_sampling_rate') as '5s' | '10s' | '15s') || '5s';
    }
    return '5s';
  });

  const handleAutoStartChange = (enabled: boolean) => {
    setAutoStartEnabled(enabled);
    if (typeof window !== 'undefined') {
      localStorage.setItem('aura_autostart_enabled', String(enabled));
    }
  };

  const handleSamplingRateChange = (rate: '5s' | '10s' | '15s') => {
    setTelemetrySamplingRate(rate);
    if (typeof window !== 'undefined') {
      localStorage.setItem('aura_sampling_rate', rate);
    }
  };

  const handleUpdateNotif = (patch: Partial<NotificationSettings>) => {
    const updated = { ...notifSettings, ...patch };
    setNotifSettings(updated);
    NotificationManager.saveSettings(updated);
  };

  const handleConfirmReset = () => {
    resetOnboarding();
    setShowResetModal(false);
    startOnboarding();
  };

  const tabs: Array<{ id: SettingsTab; label: string; icon: React.ReactNode; badge?: string }> = [
    { id: 'general', label: 'General & Desktop Protection', icon: <Shield size={16} /> },
    { id: 'notifications', label: 'Incident & Alert Policy', icon: <Bell size={16} /> },
    { id: 'sentinels', label: 'Sensors & Hardware Sentinels', icon: <Eye size={16} />, badge: `${sensors.length}` },
    { id: 'storage', label: 'Storage & Audit Ledger', icon: <HardDrive size={16} /> },
    { id: 'engine', label: 'Detection & ML Baseline', icon: <Cpu size={16} /> },
    { id: 'about', label: 'Diagnostics & System Info', icon: <Info size={16} /> },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
      {/* Top Breadcrumb Header */}
      <div
        style={{
          padding: 'var(--space-4) var(--space-6)',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--accent-primary-subtle)',
              border: '1px solid var(--accent-primary-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-primary)',
            }}
          >
            <Sliders size={20} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.01em' }}>
              Application & Sentinel Configuration
            </h1>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
              Windows endpoint protection policies, hardware sentinels, local persistence, and incident dispatch rules.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Badge severity={agentStatus?.state === 'RUNNING' ? 'LOW' : 'CRITICAL'}>
            {agentStatus?.state === 'RUNNING' ? 'AGENT ONLINE' : 'AGENT OFFLINE'}
          </Badge>
        </div>
      </div>

      {/* 2-Pane Windows Desktop Settings Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 'var(--space-5)', alignItems: 'start' }}>
        {/* Left Navigation Pane */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            padding: 'var(--space-3)',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
          }}
        >
          <div style={{ padding: '8px 12px 6px', fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            CONFIGURATION DOMAINS
          </div>

          {tabs.map((t) => {
            const isSelected = activeTab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setActiveTab(t.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: isSelected ? 'var(--accent-primary-subtle)' : 'transparent',
                  border: isSelected ? '1px solid var(--accent-primary-border)' : '1px solid transparent',
                  color: isSelected ? 'var(--accent-primary-hover)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '0.82rem',
                  fontWeight: isSelected ? 700 : 500,
                  textAlign: 'left',
                  transition: 'all var(--transition-fast)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ color: isSelected ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
                    {t.icon}
                  </span>
                  <span>{t.label}</span>
                </div>
                {t.badge && (
                  <span
                    style={{
                      fontSize: '0.68rem',
                      padding: '1px 6px',
                      borderRadius: 'var(--radius-full)',
                      backgroundColor: isSelected ? 'var(--accent-primary)' : 'var(--bg-surface-subtle)',
                      color: isSelected ? '#ffffff' : 'var(--text-muted)',
                      fontWeight: 700,
                    }}
                  >
                    {t.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Right Detail Pane */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            padding: 'var(--space-6)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-6)',
          }}
        >
          {/* TAB 1: GENERAL */}
          {activeTab === 'general' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                  General & Desktop Protection
                </h2>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                  Core Windows agent daemon execution parameters and desktop environment integration.
                </p>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-4)' }}>
                {/* Auto-start */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Start AURA on Windows Sign-In
                    </div>
                    <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Register background monitoring daemon in Windows Startup Registry.
                    </div>
                  </div>
                  <ToggleSwitch checked={autoStartEnabled} onChange={handleAutoStartChange} />
                </div>

                {/* Sampling Cadence */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Sensor Telemetry Sampling Cadence
                    </div>
                    <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Frequency at which CPU, memory, socket flows, and process trees are sampled.
                    </div>
                  </div>
                  <SegmentedControl
                    options={[
                      { value: '5s', label: '5s (Default)' },
                      { value: '10s', label: '10s' },
                      { value: '15s', label: '15s (Power Saver)' },
                    ]}
                    value={telemetrySamplingRate}
                    onChange={handleSamplingRateChange}
                    size="sm"
                  />
                </div>

                {/* Theme Mode */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Visual Interface Theme
                    </div>
                    <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Switch between high-contrast dark cybersecurity mode and light mode.
                    </div>
                  </div>
                  <SegmentedControl
                    options={[
                      { value: 'dark', label: 'Dark Mode' },
                      { value: 'light', label: 'Light Mode' },
                    ]}
                    value={theme === 'system' ? 'dark' : theme}
                    onChange={(val) => setTheme(val as 'dark' | 'light')}
                    size="sm"
                  />
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: NOTIFICATIONS */}
          {activeTab === 'notifications' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                  Incident Alert & Notification Policy
                </h2>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                  Incident-aware deduplication prevents alert floods while ensuring critical threats reach you immediately.
                </p>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-4)' }}>
                {/* Master Alert Switch */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '36px', height: '36px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--accent-primary-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-primary)' }}>
                      <Bell size={18} />
                    </div>
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        Master Real-Time Notifications
                      </div>
                      <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                        Globally enable/disable notification dispatching across all channels.
                      </div>
                    </div>
                  </div>
                  <ToggleSwitch
                    checked={notifSettings.enabled}
                    onChange={(val) => handleUpdateNotif({ enabled: val })}
                  />
                </div>

                {/* In-App Banners */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      In-App Interactive Toast Banners
                    </div>
                    <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Show actionable alerts inside the bottom-right corner of the dashboard.
                    </div>
                  </div>
                  <ToggleSwitch
                    checked={notifSettings.inAppEnabled}
                    onChange={(val) => handleUpdateNotif({ inAppEnabled: val })}
                    disabled={!notifSettings.enabled}
                  />
                </div>

                {/* Native Windows Toasts */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Native Windows Desktop Toast Alerts
                    </div>
                    <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Dispatch native OS banners via Windows Action Center.
                    </div>
                  </div>
                  <ToggleSwitch
                    checked={notifSettings.nativeEnabled}
                    onChange={(val) => handleUpdateNotif({ nativeEnabled: val })}
                    disabled={!notifSettings.enabled}
                  />
                </div>

                {/* Sound */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Audible Alert Chime
                    </div>
                    <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Play subtle alert chime when high or critical incidents occur.
                    </div>
                  </div>
                  <ToggleSwitch
                    checked={notifSettings.soundEnabled}
                    onChange={(val) => handleUpdateNotif({ soundEnabled: val })}
                    disabled={!notifSettings.enabled}
                  />
                </div>

                {/* Min Severity Threshold */}
                <div style={{ padding: '14px 16px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Minimum Notification Severity Filter
                    </div>
                    <Badge severity={notifSettings.minSeverity} size="sm">{notifSettings.minSeverity}</Badge>
                  </div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                    Incidents below this severity will be logged into the audit ledger silently.
                  </div>
                  <div style={{ marginTop: '6px' }}>
                    <SegmentedControl
                      options={[
                        { value: 'LOW', label: 'Low (All)' },
                        { value: 'MEDIUM', label: 'Medium' },
                        { value: 'HIGH', label: 'High & Critical' },
                        { value: 'CRITICAL', label: 'Critical Only' },
                      ]}
                      value={notifSettings.minSeverity}
                      onChange={(val) => handleUpdateNotif({ minSeverity: val })}
                      size="sm"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: SENSORS */}
          {activeTab === 'sentinels' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                  Sensors & Hardware Sentinels
                </h2>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                  AURA monitors Windows hardware endpoint descriptor states non-intrusively. No raw media capture.
                </p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-4)' }}>
                {sensors.map((s, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '14px',
                      backgroundColor: 'var(--bg-surface-elevated)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        {s.name}
                      </span>
                      <Badge severity={s.status === 'OK' ? 'LOW' : 'MEDIUM'} size="sm">
                        {s.status}
                      </Badge>
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                      {s.detail}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)', marginTop: 'auto' }}>
                      Probe Health: Active
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: STORAGE */}
          {activeTab === 'storage' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                  Local Storage & Audit Ledger
                </h2>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                  All telemetry records and security event logs persist strictly to local encrypted SQLite storage in %LOCALAPPDATA%.
                </p>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-4)' }}>
                <div style={{ padding: '14px 16px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      DATABASE PATH
                    </span>
                    <div style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '4px', wordBreak: 'break-all' }}>
                      %LOCALAPPDATA%\AURA\data\aura.db
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      JOURNAL MODE
                    </span>
                    <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--severity-low)', marginTop: '4px' }}>
                      WAL (Write-Ahead Logging) Active
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      RETENTION PRUNING POLICY
                    </span>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                      30-Day Rolling Window (Automated Cleanup)
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      LOCAL DISK SPACE
                    </span>
                    <div style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '4px' }}>
                      {latestTelemetry?.disk_free_gb?.toFixed(1) ?? '—'} GB free of {latestTelemetry?.disk_total_gb?.toFixed(1) ?? '—'} GB
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: ENGINE */}
          {activeTab === 'engine' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                  Detection Engine & Behavioral Baseline
                </h2>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                  Unsupervised Machine Learning algorithms running completely on-device without cloud dependence.
                </p>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-4)' }}>
                <div style={{ padding: '14px 16px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      PRIMARY MODEL
                    </span>
                    <div style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--accent-primary)', marginTop: '4px' }}>
                      Isolation Forest (Ensemble Estimator)
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      DENSITY CORRELATOR
                    </span>
                    <div style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
                      Local Outlier Factor (LOF)
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      MODEL PERSISTENCE
                    </span>
                    <div style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      %LOCALAPPDATA%\AURA\models\baseline.joblib
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      STATISTICAL RESILIENCE
                    </span>
                    <div style={{ fontSize: '0.8rem', color: 'var(--severity-low)', fontWeight: 600, marginTop: '4px' }}>
                      NaN / Infinity Jitter Guard Active
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: ABOUT */}
          {activeTab === 'about' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                  Subsystem Diagnostics & Device Setup
                </h2>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                  Hardware environment verification, process daemon status, and setup wizard management.
                </p>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-4)' }}>
                <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <AuraLogo size={48} />
                  <div>
                    <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                      AURA Privacy Guardian — Master Edition
                    </div>
                    <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
                      Version 2.0.0-PROD • Build Release: Windows-x64-Standalone
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      Host Daemon PID: <strong style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{agentStatus?.pid ?? 'Active'}</strong> • Uptime: <strong style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{formatDuration(agentStatus?.uptime_seconds ?? 0)}</strong>
                    </div>
                  </div>
                </div>

                <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Re-Run Device Protection Setup Wizard
                    </div>
                    <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Re-opens the 6-step first-launch onboarding. Preserves existing SQLite records, security logs, and baselines.
                    </div>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => setShowResetModal(true)} icon={<RotateCcw size={14} />}>
                    Launch Wizard
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {showResetModal && (
        <Modal
          isOpen={true}
          onClose={() => setShowResetModal(false)}
          title="Run Device Protection Setup Again"
          description="This will re-open the initial onboarding and hardware capability check wizard. Your existing SQLite database, security event logs, and baseline models will remain completely intact."
        >
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <Button variant="ghost" size="sm" onClick={() => setShowResetModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleConfirmReset}>
              Proceed to Setup
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
};
