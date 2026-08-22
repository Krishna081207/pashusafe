import { Navigate, Route, Routes } from 'react-router-dom';
import { useMe } from './hooks/queries';
import { getToken } from './api/client';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import type { Role } from './types/models';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import AnimalsPage from './pages/AnimalsPage';
import AnimalDetailPage from './pages/AnimalDetailPage';
import RecordTreatmentPage from './pages/RecordTreatmentPage';
import CompliancePage from './pages/CompliancePage';
import SalesPage from './pages/SalesPage';
import AlertsPage from './pages/AlertsPage';
import PrescriptionsPage from './pages/PrescriptionsPage';
import ViolationsPage from './pages/ViolationsPage';
import LabTestsPage from './pages/LabTestsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import LedgerPage from './pages/LedgerPage';
import PublicTracePage from './pages/PublicTracePage';

function Protected({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

/** Route-level RBAC: wrong role gets bounced to their own dashboard. */
function RoleRoute({ allow, children }: { allow: Role[]; children: React.ReactNode }) {
  const { data: me } = useMe();
  if (!getToken()) return <Navigate to="/login" replace />;
  if (me && !allow.includes(me.role)) return <Navigate to="/" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <ErrorBoundary>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/trace/:qrCode" element={<PublicTracePage />} />

      <Route path="/" element={<Protected><DashboardPage /></Protected>} />
      <Route path="/animals" element={<Protected><AnimalsPage /></Protected>} />
      <Route path="/animals/:id" element={<Protected><AnimalDetailPage /></Protected>} />
      <Route path="/treatments/new" element={<RoleRoute allow={['farmer']}><RecordTreatmentPage /></RoleRoute>} />
      <Route path="/compliance" element={<RoleRoute allow={['farmer', 'vet']}><CompliancePage /></RoleRoute>} />
      <Route path="/sales" element={<RoleRoute allow={['farmer']}><SalesPage /></RoleRoute>} />
      <Route path="/alerts" element={<Protected><AlertsPage /></Protected>} />
      <Route path="/prescriptions" element={<RoleRoute allow={['vet', 'admin']}><PrescriptionsPage /></RoleRoute>} />
      <Route path="/violations" element={<RoleRoute allow={['regulator', 'admin']}><ViolationsPage /></RoleRoute>} />
      <Route path="/lab-tests" element={<RoleRoute allow={['regulator', 'admin']}><LabTestsPage /></RoleRoute>} />
      <Route path="/analytics" element={<Protected><AnalyticsPage /></Protected>} />
      <Route path="/ledger" element={<Protected><LedgerPage /></Protected>} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </ErrorBoundary>
  );
}
