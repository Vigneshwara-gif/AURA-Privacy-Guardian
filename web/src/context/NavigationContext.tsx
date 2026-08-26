import React, { createContext, useContext, useState } from 'react';
import type { NavTab } from '../components/layout/Sidebar';

import { isOnboardingCompleted, setOnboardingCompleted } from '../features/onboarding/onboardingState';

interface NavigationContextType {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  activeEventId: string | null;
  navigateToEvent: (eventId: string) => void;
  clearActiveEvent: () => void;
  isOnboarding: boolean;
  startOnboarding: () => void;
  finishOnboarding: () => void;
}

const NavigationContext = createContext<NavigationContextType | undefined>(undefined);

export const NavigationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeTab, setActiveTab] = useState<NavTab>(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const tab = params.get('tab') as NavTab;
      if (tab) return tab;
    }
    return 'dashboard';
  });
  const [activeEventId, setActiveEventId] = useState<string | null>(null);
  const [isOnboarding, setIsOnboarding] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('tab')) return false;
      if (params.get('onboarding') === '1') return true;
    }
    return !isOnboardingCompleted();
  });

  const navigateToEvent = (eventId: string) => {
    setActiveEventId(eventId);
    setActiveTab('events');
  };

  const clearActiveEvent = () => {
    setActiveEventId(null);
  };

  const startOnboarding = () => {
    setOnboardingCompleted(false);
    setIsOnboarding(true);
  };

  const finishOnboarding = () => {
    setOnboardingCompleted(true);
    setIsOnboarding(false);
    setActiveTab('dashboard');
  };

  return (
    <NavigationContext.Provider
      value={{
        activeTab,
        setActiveTab,
        activeEventId,
        navigateToEvent,
        clearActiveEvent,
        isOnboarding,
        startOnboarding,
        finishOnboarding,
      }}
    >
      {children}
    </NavigationContext.Provider>
  );
};

export const useNavigation = (): NavigationContextType => {
  const context = useContext(NavigationContext);
  if (!context) throw new Error('useNavigation must be used within NavigationProvider');
  return context;
};
