import React, { useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, AuthContext } from './auth';
import { LoginPage } from './components/LoginPage';
import { NavShell } from './components/NavShell';

const AppContent: React.FC = () => {
  const { token } = useContext(AuthContext);

  if (!token) {
    return <LoginPage />;
  }

  return (
    <BrowserRouter>
      <NavShell>
        <Routes>
          <Route path="/*" element={<div>Welcome to admin panel</div>} />
          <Route path="/login" element={<Navigate to="/" replace />} />
        </Routes>
      </NavShell>
    </BrowserRouter>
  );
};

export default () => (
  <AuthProvider>
    <AppContent />
  </AuthProvider>
);
