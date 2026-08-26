import React from 'react';
import {
  Activity,
  AlertTriangle,
  Brain,
  Eye,
  FileText,
  Flame,
  LayoutDashboard,
  Settings,
} from 'lucide-react';
import { AuraLogo } from '../brand/AuraLogo';
import { useNavigation } from '../../context/NavigationContext';
import { useStream } from '../../context/StreamContext';

export type NavTab =
  | 'dashboard'
  | 'threats'
  | 'privacy'
  | 'events'
  | 'incidents'
  | 'activity'
  | 'reports'
  | 'settings';

export interface SidebarProps {
  activeTab?: NavTab;
  onSelectTab?: (tab: NavTab) => void;
}

interface NavItem {
  id: NavTab;
  label: string;
  icon: React.ReactNode;
  badge?: number | string;
}

interface NavGroup {
  section: string;
  items: NavItem[];
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab: propActiveTab, onSelectTab: propOnSelectTab }) => {
  const { activeTab: ctxActiveTab, setActiveTab: ctxSetActiveTab } = useNavigation();
  const { agentStatus, connectionState, recentEvents } = useStream();

  const currentTab = propActiveTab || ctxActiveTab;
  const selectTab = propOnSelectTab || ctxSetActiveTab;

  const isConnected = connectionState === 'CONNECTED';
  const isRunning = agentStatus?.state === 'RUNNING';

  const criticalHighCount = recentEvents.filter(
    (e) => e.severity === 'CRITICAL' || e.severity === 'HIGH'
  ).length;

  const navGroups: NavGroup[] = [
    {
      section: 'INTELLIGENCE',
      items: [
        { id: 'dashboard', label: 'Mission Control', icon: <LayoutDashboard size={17} /> },
        { id: 'threats', label: 'Threat Intelligence', icon: <Brain size={17} /> },
        { id: 'privacy', label: 'Privacy Sentinel', icon: <Eye size={17} /> },
      ],
    },
    {
      section: 'OPERATIONS',
      items: [
        {
          id: 'events',
          label: 'Security Events',
          icon: <AlertTriangle size={17} />,
          badge: criticalHighCount > 0 ? criticalHighCount : undefined,
        },
        { id: 'incidents', label: 'Incident Studio', icon: <Flame size={17} /> },
        { id: 'activity', label: 'Activity History', icon: <Activity size={17} /> },
      ],
    },
    {
      section: 'SYSTEM',
      items: [
        { id: 'reports', label: 'Audit Reports', icon: <FileText size={17} /> },
        { id: 'settings', label: 'Settings & Policy', icon: <Settings size={17} /> },
      ],
    },
  ];

  return (
    <aside
      style={{
        width: '250px',
        backgroundColor: 'var(--bg-sidebar)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        position: 'sticky',
        top: 0,
        zIndex: 20,
        userSelect: 'none',
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: '20px 20px 16px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}
      >
        <AuraLogo size={32} glow={true} />
        <div>
          <div style={{ fontSize: '1rem', fontWeight: 800, letterSpacing: '0.06em', color: 'var(--text-primary)' }}>
            AURA
          </div>
          <div style={{ fontSize: '0.66rem', color: 'var(--accent-primary-hover)', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            PRIVACY GUARDIAN
          </div>
        </div>
      </div>

      {/* Navigation Group List */}
      <nav
        style={{
          flex: 1,
          padding: '16px 12px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
        }}
      >
        {navGroups.map((group) => (
          <div key={group.section} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <div
              style={{
                fontSize: '0.66rem',
                fontWeight: 700,
                color: 'var(--text-muted)',
                letterSpacing: '0.08em',
                padding: '4px 10px 6px 10px',
                textTransform: 'uppercase',
              }}
            >
              {group.section}
            </div>

            {group.items.map((item) => {
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => selectTab(item.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-md)',
                    border: 'none',
                    backgroundColor: isActive ? 'var(--accent-primary-subtle)' : 'transparent',
                    color: isActive ? 'var(--accent-primary-hover)' : 'var(--text-secondary)',
                    fontWeight: isActive ? 700 : 500,
                    fontSize: '0.83rem',
                    cursor: 'pointer',
                    transition: 'all var(--transition-fast)',
                    position: 'relative',
                    textAlign: 'left',
                    width: '100%',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.backgroundColor = 'var(--bg-hover)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  {/* Left Active Accent Indicator */}
                  {isActive && (
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        top: '6px',
                        bottom: '6px',
                        width: '3px',
                        borderRadius: '0 2px 2px 0',
                        backgroundColor: 'var(--accent-primary)',
                        boxShadow: '0 0 8px var(--accent-primary)',
                      }}
                    />
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ color: isActive ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                  </div>

                  {item.badge !== undefined && (
                    <span
                      style={{
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        padding: '1px 6px',
                        borderRadius: 'var(--radius-full)',
                        backgroundColor: 'var(--severity-critical-bg)',
                        color: 'var(--severity-critical)',
                        border: '1px solid var(--severity-critical-border)',
                      }}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer Agent Status */}
      <div
        style={{
          padding: '14px 16px',
          borderTop: '1px solid var(--border-subtle)',
          backgroundColor: 'var(--bg-surface-inset)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: isRunning ? 'var(--severity-low)' : 'var(--severity-critical)',
              boxShadow: `0 0 8px ${isRunning ? 'var(--severity-low)' : 'var(--severity-critical)'}`,
            }}
          />
          <div style={{ fontSize: '0.74rem', color: 'var(--text-primary)', fontWeight: 600 }}>
            {isRunning ? 'Agent Active' : 'Agent Inactive'}
          </div>
        </div>

        <span
          style={{
            fontSize: '0.68rem',
            padding: '2px 6px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: isConnected ? 'var(--accent-primary-subtle)' : 'var(--severity-medium-bg)',
            color: isConnected ? 'var(--accent-primary-hover)' : 'var(--severity-medium)',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
          }}
        >
          {isConnected ? 'WS LIVE' : 'SYNC OFF'}
        </span>
      </div>
    </aside>
  );
};
