import { Link, useNavigate } from 'react-router-dom';
import {
  Plus,
  QrCode,
  ShieldCheck,
  HeartPulse,
  Syringe,
  Timer,
  AlertTriangle,
  Sparkles,
  ChevronRight,
} from 'lucide-react';
import { useAlerts, useDashboard, useFarm, useFarmStatus, useMe } from '../../hooks/queries';
import {
  MonoLabel,
  OverallBadge,
  PageBanner,
  Panel,
  SeverityBadge,
  StatCard,
  TissueCountdown,
} from '../../components/badges';

/** Farmer view: MY farm — banner, KPI tiles, safety gauge, countdowns. */
export default function FarmerDashboard() {
  const navigate = useNavigate();
  const { data: me } = useMe();
  const { data: farm } = useFarm(me?.farm_id);
  const { data: status } = useFarmStatus(me?.farm_id);
  const { data: alerts } = useAlerts();
  const { data: stats } = useDashboard();

  const underWithdrawal = status?.animals.filter((r: any) => r.under_withdrawal) ?? [];
  const total = farm?.animal_count ?? 0;
  const clearPct = total > 0 ? Math.round(((total - underWithdrawal.length) / total) * 100) : 100;
  // circular gauge math (r=54)
  const circumference = 2 * Math.PI * 54;
  const offset = circumference * (1 - clearPct / 100);
  const criticalCount = (alerts ?? []).filter((a: any) => a.severity === 'critical').length;

  return (
    <div className="w-full space-y-8">
      {/* header banner */}
      <PageBanner
        eyebrow={
          <>
            <ShieldCheck className="h-4 w-4" />
            <span>FARMER DASHBOARD | {(farm?.name ?? 'MY FARM').toUpperCase()}</span>
          </>
        }
        title={`Welcome back, ${me?.full_name?.split(' ')[0] ?? 'Farmer'}`}
        subtitle={
          underWithdrawal.length > 0
            ? `Live AMR surveillance active. ${underWithdrawal.length} withdrawal period(s) enforced for food safety.`
            : 'Live AMR surveillance active. All animals clear — safe to sell.'
        }
        actions={
          <>
            <Link
              to="/treatments/new"
              className="flex items-center gap-2 rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container"
            >
              <Plus className="h-4 w-4" /> Record Treatment
            </Link>
            <Link
              to="/sales"
              className="flex items-center gap-2 rounded-2xl border border-outline-variant/40 bg-surface-container-lowest px-4 py-2.5 text-sm font-semibold text-primary shadow-sm transition-colors hover:bg-surface-container"
            >
              <QrCode className="h-4 w-4" /> Record Sale
            </Link>
          </>
        }
      />

      {/* safety stop-banner */}
      {underWithdrawal.length > 0 && (
        <div className="rounded-3xl border border-error/20 bg-error-container p-5">
          <p className="font-bold text-on-error-container">
            🛑 Do NOT sell milk / meat / eggs from these animals until clocks clear:
          </p>
          <div className="mt-3 flex flex-wrap gap-3">
            {underWithdrawal.slice(0, 6).map((r: any) => (
              <span key={r.animal_id} className="flex flex-wrap items-center gap-2 rounded-2xl bg-surface-container-lowest px-3 py-1.5 shadow-sm">
                <MonoLabel className="text-primary">{r.tag_id}</MonoLabel>
                {r.tissues.map((t: any) => (
                  <TissueCountdown key={t.tissue} t={t} />
                ))}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Total Animals" value={total} sub="Active livestock" to="/animals" icon={<HeartPulse className="h-4 w-4" />} />
        <StatCard label="Compliance" value={`${clearPct}%`} tone="good" sub="Animals MRL-clear" to="/compliance" />
        <StatCard label="Under Withdrawal" value={underWithdrawal.length} tone="warn" sub="Milk/meat hold" to="/compliance" icon={<Timer className="h-4 w-4" />} />
        <StatCard label="Clears Today" value={status?.counts.clear_today ?? 0} sub="After clearance time" to="/compliance" />
        <StatCard label="AMU Month" value={stats?.amu_30d ?? '—'} sub="Antibiotic courses" to="/analytics" icon={<Syringe className="h-4 w-4" />} />
        <StatCard label="MRL Alerts" value={(alerts ?? []).length || 0} tone={criticalCount ? 'danger' : 'good'} sub={criticalCount ? 'Critical warnings' : 'All resolved'} to="/alerts" icon={<AlertTriangle className="h-4 w-4" />} />
      </div>

      {/* gauge + countdowns */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* safety gauge */}
        <Panel tone="low" className="flex flex-col items-center gap-8 p-6 sm:flex-row md:p-8 lg:col-span-6">
          <div className="relative flex h-44 w-44 flex-shrink-0 items-center justify-center">
            <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="54" className="stroke-surface-container-highest" strokeWidth="10" fill="none" />
              <circle
                cx="60" cy="60" r="54"
                className={clearPct >= 90 ? 'stroke-primary' : clearPct >= 70 ? 'stroke-secondary' : 'stroke-error'}
                strokeWidth="10" fill="none" strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-display text-4xl font-extrabold text-on-surface">{clearPct}</span>
              <MonoLabel className="text-on-surface-variant">/ 100 safe-sale</MonoLabel>
            </div>
          </div>
          <div className="flex-1 space-y-3 text-center sm:text-left">
            <div className="inline-flex items-center gap-1.5 rounded-full bg-primary-container px-3 py-1 font-mono text-xs font-semibold text-on-primary-container">
              <Sparkles className="h-3.5 w-3.5" />
              Farm Safety Index
            </div>
            <h3 className="font-display text-xl font-bold text-on-surface">
              {clearPct >= 90 ? 'Fully compliant with FSSAI MRL' : 'Withdrawal restrictions in force'}
            </h3>
            <p className="text-xs leading-relaxed text-on-surface-variant">
              Every treatment starts an automatic tissue-wise clock; sales during a window are
              frozen as violations and chained to the traceability ledger.
            </p>
            <Link to="/ledger" className="mx-auto inline-flex items-center gap-1 text-xs font-semibold text-secondary hover:text-on-secondary-container sm:mx-0">
              Inspect Traceability Badge <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
        </Panel>

        {/* active countdowns */}
        <Panel className="space-y-4 p-6 md:p-8 lg:col-span-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Timer className="h-5 w-5 text-tertiary" />
              <h3 className="font-display text-lg font-bold text-on-surface">Active Withdrawal Countdowns</h3>
            </div>
            <span className="rounded-full bg-tertiary-container px-2.5 py-1 font-mono text-xs font-semibold text-on-tertiary-container">
              {underWithdrawal.length} Active Timers
            </span>
          </div>
          <div className="max-h-64 space-y-3 overflow-y-auto pr-1">
            {underWithdrawal.length === 0 && (
              <p className="py-10 text-center text-sm text-outline">✅ No active timers — every animal is clear.</p>
            )}
            {underWithdrawal.map((r: any) => (
              <button
                key={r.animal_id}
                onClick={() => navigate(`/animals/${r.animal_id}`)}
                className="flex w-full items-center justify-between gap-4 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-4 text-left transition-colors hover:border-primary/40"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <MonoLabel className="text-primary">{r.tag_id}</MonoLabel>
                    <span className="text-xs capitalize text-on-surface">{r.species}</span>
                  </div>
                  <span className="block font-mono text-xs text-on-surface-variant">
                    {r.tissues.map((t: any) => t.drug_name).filter(Boolean).join(', ') || '—'}
                  </span>
                </div>
                <div className="flex flex-wrap justify-end gap-1.5">
                  {r.tissues.map((t: any) => (
                    <TissueCountdown key={t.tissue} t={t} />
                  ))}
                </div>
              </button>
            ))}
          </div>
        </Panel>
      </div>

      {/* alerts strip */}
      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-lg font-bold text-on-surface">Recent Alerts</h3>
          <Link to="/alerts" className="text-xs font-semibold text-secondary hover:underline">View all →</Link>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(alerts ?? []).slice(0, 6).map((a: any) => (
            <Link
              key={a.id}
              to="/alerts"
              className={`block rounded-2xl border p-4 shadow-sm transition-shadow hover:shadow-md ${
                a.severity === 'critical'
                  ? 'border-error/20 bg-error-container'
                  : a.severity === 'warning'
                    ? 'border-tertiary/20 bg-tertiary-container/60'
                    : 'border-outline-variant/40 bg-surface-container-lowest'
              }`}
            >
              <div className="flex items-center gap-2">
                <SeverityBadge severity={a.severity} />
                <p className="truncate text-sm font-semibold text-on-surface">{a.title}</p>
              </div>
              <p className="mt-1 line-clamp-2 text-xs text-on-surface-variant">{a.message}</p>
            </Link>
          ))}
          {(alerts ?? []).length === 0 && (
            <p className="rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-8 text-center text-sm text-outline md:col-span-2 xl:col-span-3">
              No open alerts ✅
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
