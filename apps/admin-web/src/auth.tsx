import React, { createContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { login as apiLogin, LoginRequest } from '@office-hero/api-client';

interface AuthContextType {
  token: string | null;
  login: (creds: LoginRequest) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType>({
  token: null,
  login: async () => {},
  logout: () => {}
});

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem('access_token');
    if (stored) {
      setToken(stored);
      // optionally set default axios header
    }
  }, []);

  const login = async (creds: LoginRequest) => {
    const data = await apiLogin(creds);
    localStorage.setItem('access_token', data.access_token);
    setToken(data.access_token);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
