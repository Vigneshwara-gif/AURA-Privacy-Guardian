import React from 'react';
import { AppShell } from './components/layout/AppShell';
import type { NavTab } from './components/layout/Sidebar';
import { ToastContainer } from './components/feedback/ToastContainer';
import { AuthProvider } from './context/AuthContext';
import { NavigationProvider } from './context/NavigationContext';
import { StreamProvider } from './context/StreamContext';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { useNavigation } from './context/NavigationContext';
import { OnboardingWizard } from './features/onboarding/OnboardingWizard';
import { ActivityView } from './features/activity/ActivityView';
import { DashboardView } from './features/dashboard/DashboardView';
import { EventsView } from './features/events/EventsView';
import { IncidentsView } from './features/incidents/IncidentsView';
import { PrivacyView } from './features/privacy/PrivacyView';
import { ReportsView } from './features/reports/ReportsView';
import { ThreatIntelligenceView } from './features/threats/ThreatIntelligenceView';
import { SettingsView } from './features/settings/SettingsView';

export const AppContent: React.FC = () => {
  const { isOnboarding, finishOnboarding } = useNavigation();

  const renderView = (tab: NavTab) => {
    switch (tab) {
      case 'privacy':
        return <PrivacyView />;
      case 'threats':
        return <ThreatIntelligenceView />;
      case 'events':
        return <EventsView />;
      case 'incidents':
        return <IncidentsView />;
      case 'activity':
        return <ActivityView />;
      case 'reports':
        return <ReportsView />;
      case 'settings':
        return <SettingsView />;
      case 'dashboard':
      default:
        return <DashboardView />;
    }
  };

  if (isOnboarding) {
    return (
      <>
        <OnboardingWizard onFinish={finishOnboarding} />
        <ToastContainer />
      </>
    );
  }

  return (
    <AppShell>
      {(activeTab) => (
        <>
          {renderView(activeTab)}
          <ToastContainer />
        </>
      )}
    </AppShell>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <NavigationProvider>
        <ToastProvider>
          <AuthProvider>
            <StreamProvider>
              <AppContent />
            </StreamProvider>
          </AuthProvider>
        </ToastProvider>
      </NavigationProvider>
    </ThemeProvider>
  );
};

export default App;
