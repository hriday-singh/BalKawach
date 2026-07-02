import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import PageShell from './components/layout/PageShell';
import Dashboard from './pages/Dashboard';
import Children from './pages/Children';
import Hearings from './pages/Hearings';
import Alerts from './pages/Alerts';
import SystemStatus from './pages/SystemStatus';
import AuditLog from './pages/AuditLog';
import TranscriptionLogs from './pages/TranscriptionLogs';
import Login from './pages/Login';
import DummyPage from './pages/DummyPage';
import './index.css';

const ProtectedRoute = ({ allowedRoles, children }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/" replace />;
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    const defaultRoute = (user.role === 'cwc_member' || user.role === 'cci_staff') ? '/children' : '/dashboard';
    return <Navigate to={defaultRoute} replace />;
  }
  return children;
};

const getDefaultRoute = (role) => {
  if (role === 'cwc_member' || role === 'cci_staff') return '/children';
  return '/dashboard';
};

function AppRoutes() {
  const { user } = useAuth();

  if (!user) {
    return <Login />;
  }

  return (
    <Routes>
      <Route path="/" element={<PageShell />}>
        <Route index element={<Navigate to={getDefaultRoute(user.role)} replace />} />
        
        <Route path="dashboard" element={
          <ProtectedRoute allowedRoles={['system_admin', 'cwc_chairperson', 'dcpu_officer', 'wcd_official']}>
            <Dashboard />
          </ProtectedRoute>
        } />
        
        <Route path="children" element={
          <ProtectedRoute allowedRoles={['system_admin', 'cwc_chairperson', 'cwc_member', 'dcpu_officer', 'cci_staff']}>
            <Children />
          </ProtectedRoute>
        } />
        
        <Route path="hearings" element={
          <ProtectedRoute allowedRoles={['system_admin', 'cwc_chairperson', 'cwc_member']}>
            <Hearings />
          </ProtectedRoute>
        } />
        
        <Route path="alerts" element={
          <ProtectedRoute allowedRoles={['system_admin', 'cwc_chairperson', 'cwc_member', 'dcpu_officer', 'wcd_official']}>
            <Alerts />
          </ProtectedRoute>
        } />
        
        <Route path="system" element={
          <ProtectedRoute allowedRoles={['system_admin']}>
            <SystemStatus />
          </ProtectedRoute>
        } />
        
        <Route path="audit" element={
          <ProtectedRoute allowedRoles={['system_admin']}>
            <AuditLog />
          </ProtectedRoute>
        } />

        <Route path="transcription-logs" element={
          <ProtectedRoute allowedRoles={['system_admin']}>
            <TranscriptionLogs />
          </ProtectedRoute>
        } />

        <Route path="privacy" element={<DummyPage title="Privacy Policy" />} />
        <Route path="terms" element={<DummyPage title="Terms of Service" />} />
        <Route path="about" element={<DummyPage title="About Us" />} />
        <Route path="help" element={<DummyPage title="Help Center" />} />
        
        {/* Fallback */}
        <Route path="*" element={<Navigate to={getDefaultRoute(user.role)} replace />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

export default App;
