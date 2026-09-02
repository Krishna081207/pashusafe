import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  PawPrint,
  Syringe,
  Timer,
  ShoppingCart,
  Bell,
  FileSpreadsheet,
  AlertTriangle,
  FlaskConical,
  TrendingUp,
  GitMerge,
  ShieldCheck,
  LogOut,
  MapPinned,
  Wrench,
  CalendarClock,
  Languages,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { setToken } from '../api/client';
import { useAlerts, useMe } from '../hooks/queries';
import AssistantWidget from './AssistantWidget';
import { MonoLabel } from './badges';

interface NavItem {
  to: string;
  key: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: string[];
}

const NAV: NavItem[] = [
  { to: '/', key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/animals', key: 'animals', label: 'Livestock & Passports', icon: PawPrint },
  { to: '/treatments/new', key: 'treatments', label: 'Record Treatment', icon: Syringe, roles: ['farmer'] },
  { to: '/compliance', key: 'compliance', label: 'Withdrawal Monitor', icon: Timer, roles: ['farmer', 'vet'] },
  { to: '/sales', key: 'sales', label: 'Record Sale', icon: ShoppingCart, roles: ['farmer'] },
  { to: '/tracking', key: 'tracking', label: 'Live Tracking', icon: MapPinned, roles: ['farmer'] },
  { to: '/install', key: 'install', label: 'Sensor Installation', icon: Wrench, roles: ['farmer'] },
  { to: '/admin/installs', key: 'admin_installs', label: 'Installation Queue', icon: CalendarClock, roles: ['admin'] },
  { to: '/alerts', key: 'alerts', label: 'Alerts', icon: Bell },
  { to: '/prescriptions', key: 'prescriptions', label: 'Digital Prescriptions', icon: FileSpreadsheet, roles: ['vet', 'admin'] },
  { to: '/violations', key: 'violations', label: 'Violation Register', icon: AlertTriangle, roles: ['regulator', 'admin'] },
  { to: '/lab-tests', key: 'lab_tests', label: 'MRL Lab Console', icon: FlaskConical, roles: ['regulator', 'admin'] },
  { to: '/analytics', key: 'analytics', label: 'AMR Analytics', icon: TrendingUp },
  { to: '/ledger', key: 'ledger', label: 'Traceability Ledger', icon: GitMerge },
];

const ROLE_META: Record<string, { emoji: string; context: string; tint: string }> = {
  farmer: { emoji: '👨‍🌾', context: 'Farm Owner', tint: 'bg-primary-container text-on-primary-container' },
  vet: { emoji: '🩺', context: 'Veterinary Clinic', tint: 'bg-secondary-container text-on-secondary-container' },
  regulator: { emoji: '🏛️', context: 'Food Safety Authority', tint: 'bg-tertiary-container text-on-tertiary-container' },
  admin: { emoji: '⚙️', context: 'System Administrator', tint: 'bg-surface-container-high text-on-surface' },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const { data: me } = useMe();
  const { data: alerts } = useAlerts();
  const unread = (alerts ?? []).filter((a: any) => !a.resolved && a.severity !== 'info').length;

  const isHindi = i18n.language?.startsWith('hi');
  const toggleLanguage = () => {
    i18n.changeLanguage(isHindi ? 'en' : 'hi');
  };

  const items = NAV.filter((n) => !n.roles || (me && n.roles.includes(me.role)));
  const meta = me ? ROLE_META[me.role] : null;

  return (
    <div className="min-h-full bg-surface">
      {/* ---------------- top navbar ---------------- */}
      <header className="sticky top-0 z-40 w-full border-b border-outline-variant/30 bg-surface/90 shadow-[0_4px_16px_rgba(0,0,0,0.03)] backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-[1440px] items-center justify-between gap-4 px-4 md:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary shadow-md">
              <ShieldCheck className="h-6 w-6 text-primary-fixed" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-display text-lg font-bold tracking-tight text-primary">
                  {t('brand.name', 'PASHUSAFE')}
                </span>
                <span className="rounded-full bg-primary-container px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-on-primary-container">
                  AMU·MRL
                </span>
              </div>
              <span className="font-mono text-[11px] uppercase tracking-widest text-on-surface-variant">
                {t('brand.tagline', 'Livestock AMR & Residue Safety Chain')}
              </span>
            </div>
          </div>

          <button
            onClick={() => navigate('/animals')}
            className="hidden items-center gap-1.5 rounded-xl border border-outline-variant/40 bg-surface-container-high px-3 py-2 font-medium text-primary shadow-sm transition-colors hover:bg-surface-container-highest md:flex"
          >
            <PawPrint className="h-4 w-4" />
            <span>{t('nav.animals', 'Livestock Registry')}</span>
          </button>

          <div className="flex items-center gap-2 md:gap-3">
            {/* Language Switcher Pill */}
            <button
              onClick={toggleLanguage}
              className="flex items-center gap-1.5 rounded-xl border border-outline-variant/40 bg-surface-container px-3 py-1.5 text-xs font-semibold text-primary transition-all hover:bg-surface-container-high active:scale-95"
              title="Toggle Language / भाषा बदलें"
            >
              <Languages className="h-4 w-4 text-primary" />
              <span>{isHindi ? 'English' : 'हिन्दी'}</span>
            </button>

            {/* Alerts */}
            <button
              onClick={() => navigate('/alerts')}
              className="relative rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-container-high"
              title="Alerts"
            >
              <Bell className="h-5 w-5" />
              {unread > 0 && (
                <span className="absolute right-0.5 top-0.5 h-2.5 w-2.5 rounded-full bg-error ring-2 ring-surface" />
              )}
            </button>

            {/* Active User Context */}
            <div className="flex items-center gap-2 rounded-xl border border-outline-variant/40 bg-surface-container px-3 py-1.5">
              <span className="text-lg">{meta?.emoji}</span>
              <div className="hidden flex-col sm:flex">
                <MonoLabel className="text-outline">{t('common.active_context', 'Active Context')}</MonoLabel>
                <span className="max-w-[160px] truncate text-xs font-bold text-primary">
                  {me?.full_name}
                </span>
              </div>
            </div>

            {/* Sign Out */}
            <button
              onClick={() => {
                setToken(null);
                navigate('/login');
              }}
              className="flex items-center gap-1.5 rounded-xl border border-outline-variant/40 bg-surface-container px-3 py-2 font-medium text-on-surface shadow-sm transition-colors hover:bg-surface-container-high"
            >
              <LogOut className="h-4 w-4 text-error" />
              <span className="hidden sm:inline">{t('common.sign_out', 'Sign Out')}</span>
            </button>
          </div>
        </div>
      </header>

      {/* ---------------- body: sidebar + content ---------------- */}
      <div className="mx-auto flex max-w-[1440px] gap-0 px-4 md:px-6">
        <aside className="sticky top-24 hidden h-[calc(100vh-7rem)] w-64 select-none flex-col justify-between border-r border-outline-variant/30 bg-surface-container-low py-4 lg:flex">
          <nav className="space-y-6 overflow-y-auto pr-2">
            <div className="space-y-1">
              <div className="px-3 pb-2">
                <MonoLabel className="text-outline">{t('nav.main_modules', 'Main Modules')}</MonoLabel>
              </div>
              {items.map((n) => {
                const Icon = n.icon;
                return (
                  <NavLink
                    key={n.to}
                    to={n.to}
                    end={n.to === '/'}
                    className={({ isActive }) =>
                      `flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-sm transition-all ${
                        isActive
                          ? 'bg-primary font-semibold text-on-primary shadow-sm'
                          : 'font-medium text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
                      }`
                    }
                  >
                    <span className="flex items-center gap-3">
                      <Icon className="h-4 w-4" />
                      {t(`nav.${n.key}`, n.label)}
                    </span>
                  </NavLink>
                );
              })}
            </div>
          </nav>

          <div className="border-t border-outline-variant/30 p-2 text-center">
            <div className="rounded-xl bg-surface-container p-2.5 font-mono text-[11px] text-on-surface-variant">
              <span className="font-bold text-primary">PashuSafe v1.0</span>
              <br />
              {t('common.chain_active', 'AMU · MRL Chain Active')}
            </div>
          </div>
        </aside>

        {/* mobile nav chips */}
        <div className="fixed inset-x-0 bottom-0 z-40 flex gap-1 overflow-x-auto border-t border-outline-variant/30 bg-surface/95 p-2 backdrop-blur lg:hidden">
          {items.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === '/'}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-xl px-3 py-1.5 text-xs font-semibold ${
                  isActive ? 'bg-primary text-on-primary' : 'bg-surface-container text-on-surface-variant'
                }`
              }
            >
              {t(`nav.${n.key}`, n.label)}
            </NavLink>
          ))}
        </div>

        <main className="w-full space-y-8 pb-16 pt-6 lg:pl-8">{children}</main>
      </div>

      <AssistantWidget />
    </div>
  );
}