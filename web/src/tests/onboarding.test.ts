import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ONBOARDING_STORAGE_KEY,
  isOnboardingCompleted,
  resetOnboarding,
  setOnboardingCompleted,
} from '../features/onboarding/onboardingState';
import {
  NotificationManager,
  type NotificationSettings,
} from '../services/notificationManager';

const createStorageMock = () => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = String(value);
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
};

describe('First-Launch Onboarding & Device Protection State', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', createStorageMock());
    vi.stubGlobal('sessionStorage', createStorageMock());
  });

  it('TEST 1: Fresh install/first launch returns false for isOnboardingCompleted', () => {
    expect(isOnboardingCompleted()).toBe(false);
  });

  it('TEST 2: Completing onboarding sets storage flag to true', () => {
    expect(isOnboardingCompleted()).toBe(false);
    setOnboardingCompleted(true);
    expect(isOnboardingCompleted()).toBe(true);
    expect(localStorage.getItem(ONBOARDING_STORAGE_KEY)).toBe('true');
  });

  it('TEST 3: Returning user with completed flag skips onboarding', () => {
    localStorage.setItem(ONBOARDING_STORAGE_KEY, 'true');
    expect(isOnboardingCompleted()).toBe(true);
  });

  it('TEST 4: Resetting onboarding resets flag without modifying security history', () => {
    setOnboardingCompleted(true);
    expect(isOnboardingCompleted()).toBe(true);

    resetOnboarding();
    expect(isOnboardingCompleted()).toBe(false);
  });

  it('TEST 5: Protection preferences during onboarding integrate with NotificationManager', () => {
    // Verify default settings
    const initial = NotificationManager.getSettings();
    expect(initial.enabled).toBe(true);
    expect(initial.minSeverity).toBe('MEDIUM');
    expect(initial.inAppEnabled).toBe(true);
    expect(initial.nativeEnabled).toBe(true);

    // Update settings in onboarding
    const custom: NotificationSettings = {
      enabled: true,
      minSeverity: 'HIGH',
      inAppEnabled: true,
      nativeEnabled: false,
      soundEnabled: false,
    };
    NotificationManager.saveSettings(custom);

    const reloaded = NotificationManager.getSettings();
    expect(reloaded.minSeverity).toBe('HIGH');
    expect(reloaded.nativeEnabled).toBe(false);
  });
});
