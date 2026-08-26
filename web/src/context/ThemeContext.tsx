import React, { createContext, useContext, useEffect, useState } from 'react';

export type Theme = 'dark' | 'light' | 'system';

interface ThemeContextType {
  theme: Theme;
  effectiveTheme: 'dark' | 'light';
  setTheme: (theme: Theme) => void;
  reducedMotion: boolean;
  setReducedMotion: (reduced: boolean) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('aura_theme') as Theme) || 'dark';
    }
    return 'dark';
  });

  const [reducedMotion, setReducedMotionState] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('aura_reduced_motion') === 'true' ||
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
    return false;
  });

  const [systemIsDark, setSystemIsDark] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return true;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const listener = (e: MediaQueryListEvent) => setSystemIsDark(e.matches);
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
  }, []);

  const effectiveTheme: 'dark' | 'light' = theme === 'system' ? (systemIsDark ? 'dark' : 'light') : theme;

  useEffect(() => {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;
    root.classList.remove('dark', 'light');
    root.classList.add(effectiveTheme);
    root.setAttribute('data-theme', effectiveTheme);

    if (document.body) {
      document.body.classList.remove('dark', 'light');
      document.body.classList.add(effectiveTheme);
      document.body.setAttribute('data-theme', effectiveTheme);
    }
  }, [effectiveTheme]);

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    if (typeof window !== 'undefined') {
      localStorage.setItem('aura_theme', newTheme);
    }
  };

  const setReducedMotion = (reduced: boolean) => {
    setReducedMotionState(reduced);
    if (typeof window !== 'undefined') {
      localStorage.setItem('aura_reduced_motion', String(reduced));
    }
  };

  return (
    <ThemeContext.Provider value={{ theme, effectiveTheme, setTheme, reducedMotion, setReducedMotion }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};
