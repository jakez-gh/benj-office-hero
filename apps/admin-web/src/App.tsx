import React, { useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, AuthContext } from './auth';
import { LoginPage } from './components/LoginPage';
import { NavShell } from './components/NavShell';
import { JobsPage } from './pages/JobsPage';
import { DispatchPage } from './pages/DispatchPage';
import { VehiclesPage } from './pages/VehiclesPage';
import { UsersPage } from './pages/UsersPage';

const AppContent: React.FC = () => {
  const { token } = useContext(AuthContext);

  if (!token) {
    return <LoginPage />;
  }

  return (
    <BrowserRouter>
      <NavShell>
        <Routes>
          <Route path="/" element={<JobsPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/dispatch" element={<DispatchPage />} />
          <Route path="/vehicles" element={<VehiclesPage />} />
          <Route path="/users" element={<UsersPage />} />
          <Route path="/login" element={<Navigate to="/" replace />} />
          <Route path="/*" element={<Navigate to="/" replace />} />
        </Routes>
      </NavShell>
    </BrowserRouter>
  );
};

const App: React.FC = () => (
  <AuthProvider>
    <AppContent />
  </AuthProvider>
);

export default App;
