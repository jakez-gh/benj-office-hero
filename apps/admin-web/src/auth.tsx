import React, { createContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { client } from '@office-hero/api-client';
import { login as apiLogin, refresh as apiRefresh, LoginRequest } from '@office-hero/api-client';
import type { AxiosError } from 'axios';

interface AuthContextType {
  token: string | null;
  login: (creds: LoginRequest) => Promise<void>;
  logout: () => void;
  isRefreshing: boolean;
}

export const AuthContext = createContext<AuthContextType>({
  token: null,
  login: async () => {},
  logout: () => {},
  isRefreshing: false
});

let isRefreshing = false;
let refreshPromise: Promise<string> | null = null;

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [isRefreshingState, setIsRefreshing] = useState(false);

  // Setup axios interceptor to handle 401 and refresh token
  useEffect(() => {
    const interceptor = client.interceptors.response.use(
      response => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as any;

        // Only retry once per request
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          if (!isRefreshing) {
            isRefreshing = true;
            setIsRefreshing(true);
            const storedRefreshToken = localStorage.getItem('refresh_token');

            if (storedRefreshToken) {
              try {
                const data = await apiRefresh({ refresh_token: storedRefreshToken });
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                setToken(data.access_token);
                setRefreshToken(data.refresh_token);

                // Update authorization header
                client.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
                originalRequest.headers['Authorization'] = `Bearer ${data.access_token}`;

                isRefreshing = false;
                setIsRefreshing(false);

                // Retry original request
                return client(originalRequest);
              } catch (refreshError) {
                // Refresh failed, clear tokens and reject
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                setToken(null);
                setRefreshToken(null);
                isRefreshing = false;
                setIsRefreshing(false);
                return Promise.reject(refreshError);
              }
            } else {
              // No refresh token, clear and reject
              localStorage.removeItem('access_token');
              setToken(null);
              isRefreshing = false;
              setIsRefreshing(false);
              return Promise.reject(error);
            }
          }
        }

        return Promise.reject(error);
      }
    );

    return () => {
      client.interceptors.response.eject(interceptor);
    };
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem('access_token');
    const storedRefresh = localStorage.getItem('refresh_token');
    if (stored) {
      setToken(stored);
      // Set default authorization header
      client.defaults.headers.common['Authorization'] = `Bearer ${stored}`;
    }
    if (storedRefresh) {
      setRefreshToken(storedRefresh);
    }
  }, []);

  const login = async (creds: LoginRequest) => {
    const data = await apiLogin(creds);
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    setToken(data.access_token);
    setRefreshToken(data.refresh_token);
    // Set default authorization header
    client.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setToken(null);
    setRefreshToken(null);
    delete client.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ token, login, logout, isRefreshing: isRefreshingState }}>
      {children}
    </AuthContext.Provider>
  );
};
