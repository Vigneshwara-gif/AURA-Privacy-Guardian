export const ONBOARDING_STORAGE_KEY = 'aura_onboarding_completed_v1';

export const isOnboardingCompleted = (): boolean => {
  try {
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem(ONBOARDING_STORAGE_KEY) === 'true';
    }
  } catch {
    // Fallback
  }
  return false;
};

export const setOnboardingCompleted = (completed: boolean): void => {
  try {
    if (typeof localStorage !== 'undefined') {
      if (completed) {
        localStorage.setItem(ONBOARDING_STORAGE_KEY, 'true');
      } else {
        localStorage.removeItem(ONBOARDING_STORAGE_KEY);
      }
    }
  } catch {
    // Fallback
  }
};

export const resetOnboarding = (): void => {
  setOnboardingCompleted(false);
};
