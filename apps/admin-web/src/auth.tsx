import React, { createContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { client } from '@office-hero/api-client';
import { login as apiLogin, refresh as apiRefresh, LoginRequest, AuthUser } from '@office-hero/api-client';
import type { AxiosError, InternalAxiosRequestConfig } from 'axios';

interface AuthContextType {
  token: string | null;
  user: AuthUser | null;
  login: (creds: LoginRequest) => Promise<void>;
  logout: () => void;
  isRefreshing: boolean;
}

export const AuthContext = createContext<AuthContextType>({
  token: null,
  user: null,
  login: async () => {},
  logout: () => {},
  isRefreshing: false
});

let isRefreshing = false;

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => {
    const stored = localStorage.getItem('access_token');
    if (stored) {
      client.defaults.headers.common['Authorization'] = `Bearer ${stored}`;
    }
    return stored;
  });
  const [user, setUser] = useState<AuthUser | null>(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        return JSON.parse(storedUser) as AuthUser;
      } catch {
        localStorage.removeItem('user');
      }
    }
    return null;
  });
  const [isRefreshingState, setIsRefreshing] = useState(false);

  // Setup axios interceptor to handle 401 and refresh token
  useEffect(() => {
    const interceptor = client.interceptors.response.use(
      response => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        // Only retry once per request
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          if (!isRefreshing) {
            isRefreshing = true;
            setIsRefreshing(true);
            const storedRefreshToken = localStorage.getItem('refresh_token');

            if (storedRefreshToken) {
              try {
                // refresh() returns {access_token, user} — refresh_token is unchanged
                const data = await apiRefresh({ refresh_token: storedRefreshToken });
                localStorage.setItem('access_token', data.access_token);
                setToken(data.access_token);
                setUser(data.user);

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
                setUser(null);
                isRefreshing = false;
                setIsRefreshing(false);
                return Promise.reject(refreshError);
              }
            } else {
              // No refresh token, clear and reject
              localStorage.removeItem('access_token');
              setToken(null);
              setUser(null);
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

  const login = async (creds: LoginRequest) => {
    const data = await apiLogin(creds);
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
    client.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    delete client.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ token, user, login, logout, isRefreshing: isRefreshingState }}>
      {children}
    </AuthContext.Provider>
  );
};
