import React, { createContext, useContext, useEffect, useState } from 'react';
import type { AuthScope, AuthSessionStatus } from '../contracts/auth';
import { ApiClient } from '../services/apiClient';
import { AuthService } from '../services/authService';

interface AuthContextType {
  status: AuthSessionStatus;
  token: string | null;
  scope: AuthScope;
  loginWithBootstrap: (bootstrapCode: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<AuthSessionStatus>('UNAUTHENTICATED');
  const [token, setToken] = useState<string | null>(null);
  const [scope, setScope] = useState<AuthScope>('OPERATOR');

  const loginWithBootstrap = async (code: string): Promise<boolean> => {
    try {
      const res = await ApiClient.exchangeSession(code);
      AuthService.setSession(res);
      setToken(res.session_id);
      setScope(res.scope);
      setStatus('AUTHENTICATED');
      return true;
    } catch {
      setStatus('UNAUTHENTICATED');
      return false;
    }
  };

  useEffect(() => {
    AuthService.ensureAuthenticated().then((tokenVal) => {
      if (tokenVal) {
        setToken(tokenVal);
        setScope((AuthService.getScope() as AuthScope) || 'OPERATOR');
        setStatus('AUTHENTICATED');
      } else {
        setStatus('UNAUTHENTICATED');
      }
    });
  }, []);

  const logout = () => {
    AuthService.clearSession();
    setToken(null);
    setStatus('UNAUTHENTICATED');
  };

  return (
    <AuthContext.Provider value={{ status, token, scope, loginWithBootstrap, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
