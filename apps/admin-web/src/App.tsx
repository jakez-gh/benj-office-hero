import React, { useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, AuthContext } from './auth';
import { LoginPage } from './components/LoginPage';
import { NavShell } from './components/NavShell';
import { JobsPage } from './pages/JobsPage';
import { DispatchPage } from './pages/DispatchPage';
import { VehiclesPage } from './pages/VehiclesPage';
import { UsersPage } from './pages/UsersPage';
import { ShowcasePage } from './pages/_design/ShowcasePage';

// __IS_DEV__ is replaced at Vite build time and set in setupTests for jest.
const IS_DEV = __IS_DEV__;

const AppContent: React.FC = () => {
  const { token } = useContext(AuthContext);

  // Dev-only design system showcase. Available at /_design without auth so
  // reviewers can render the primitives. Not linked from production nav.
  if (IS_DEV && window.location.pathname === '/_design') {
    return <ShowcasePage />;
  }

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
          {IS_DEV && <Route path="/_design" element={<ShowcasePage />} />}
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
