import React from 'react';
import { useNavigation } from '../../context/NavigationContext';
import { Sidebar, type NavTab } from './Sidebar';
import { TopBar } from './TopBar';

interface AppShellProps {
  children: (activeTab: NavTab) => React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const { activeTab, setActiveTab } = useNavigation();

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg-app)' }}>
      <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <TopBar />
        <main style={{ flex: 1, padding: 'var(--space-6)', maxWidth: '1440px', width: '100%', margin: '0 auto' }}>
          {children(activeTab)}
        </main>
      </div>
    </div>
  );
};
