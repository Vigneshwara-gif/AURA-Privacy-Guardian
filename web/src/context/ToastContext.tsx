import React, { createContext, useContext, useState } from 'react';
import type { SeverityLevel } from '../utils/severity';

export interface ToastItem {
  id: string;
  title: string;
  message: string;
  severity: SeverityLevel;
  timestamp: string;
  riskScore?: number;
  eventId?: string;
  incidentId?: string;
  onInvestigate?: (eventId: string) => void;
}

interface ToastContextType {
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastItem, 'id' | 'timestamp'>) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const lastToastRef = React.useRef<{ key: string; time: number } | null>(null);

  const addToast = (t: Omit<ToastItem, 'id' | 'timestamp'>) => {
    const key = `${t.title}:${t.message}:${t.severity}`;
    const now = Date.now();
    if (lastToastRef.current && lastToastRef.current.key === key && now - lastToastRef.current.time < 3000) {
      // Deduplicate identical toast notifications within 3 seconds
      return;
    }
    lastToastRef.current = { key, time: now };

    const id = Math.random().toString(36).substring(2, 9);
    const newToast: ToastItem = {
      ...t,
      id,
      timestamp: new Date().toISOString(),
    };
    setToasts((prev) => [newToast, ...prev.slice(0, 4)]);
    setTimeout(() => removeToast(id), 5000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
    </ToastContext.Provider>
  );
};

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
};
