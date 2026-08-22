import { useMe } from '../hooks/queries';
import { Spinner } from '../components/badges';
import FarmerDashboard from './dashboards/FarmerDashboard';
import VetDashboard from './dashboards/VetDashboard';
import RegulatorDashboard from './dashboards/RegulatorDashboard';
import AdminDashboard from './dashboards/AdminDashboard';

/** Role router: each persona gets a purpose-built dashboard. */
export default function DashboardPage() {
  const { data: me, isLoading } = useMe();

  if (isLoading || !me) return <Spinner label="Loading your dashboard…" />;

  switch (me.role) {
    case 'farmer':
      return <FarmerDashboard />;
    case 'vet':
      return <VetDashboard />;
    case 'regulator':
      return <RegulatorDashboard />;
    case 'admin':
    default:
      return <AdminDashboard />;
  }
}
