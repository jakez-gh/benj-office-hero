/**
 * App — root layout with sidebar navigation + routed pages.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Navigation } from './components/Navigation';
import { DispatchPage } from './pages/DispatchPage';
import { JobsPage } from './pages/JobsPage';
import { VehiclesPage } from './pages/VehiclesPage';
import { UsersPage } from './pages/UsersPage';

export function App() {
  return (
    <BrowserRouter>
      <div style={layoutStyle}>
        <Navigation />
        <main style={mainStyle}>
          <Routes>
            <Route path="/" element={<Navigate to="/dispatch" replace />} />
            <Route path="/dispatch" element={<DispatchPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/vehicles" element={<VehiclesPage />} />
            <Route path="/users" element={<UsersPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

const layoutStyle: React.CSSProperties = {
  display: 'flex',
  minHeight: '100vh',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
};

const mainStyle: React.CSSProperties = {
  flex: 1,
  padding: '2rem',
  background: '#f9fafb',
};
