import { Link } from 'react-router-dom';
import {
  Bot,
  GitMerge,
  SlidersHorizontal,
} from 'lucide-react';
import {
  useDashboard,
  useLedgerEvents,
  useLedgerVerify,
  useModelInfo,
  useStatusOverview,
} from '../../hooks/queries';
import { MonoLabel, PageBanner, Panel, StatCard } from '../../components/badges';

/** Admin view: system health, ML registry, ledger console. */
export default function AdminDashboard() {
  const { data: stats } = useDashboard();
  const { data: overview } = useStatusOverview();
  const { data: ledger } = useLedgerVerify();
  const { data: events } = useLedgerEvents();
  const { data: models } = useModelInfo();

  return (
    <div className="w-full space-y-8">
      <PageBanner
        eyebrow={
          <>
            <SlidersHorizontal className="h-4 w-4" />
            <span>SYSTEM ADMINISTRATOR | PLATFORM CONTROL</span>
          </>
        }
        title="Platform overview"
        subtitle="Model registry · ledger integrity · cross-farm activity"
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Farms" value={(overview ?? []).length} to="/animals" />
        <StatCard label="Active Animals" value={stats?.total_animals ?? '—'} to="/animals" />
        <StatCard label="AMU 30d" value={stats?.amu_30d ?? '—'} to="/analytics" />
        <StatCard label="Violations" value={stats?.violations_total ?? '—'} tone={(stats?.violations_total ?? 0) > 0 ? 'danger' : 'good'} to="/violations" />
        <StatCard
          label="Ledger Blocks"
          value={ledger?.length ?? 0}
          tone={ledger?.valid ? 'good' : 'danger'}
          sub={ledger?.valid ? 'chain intact' : `tampered at #${ledger?.first_invalid_seq}`}
          to="/ledger"
          icon={<GitMerge className="h-4 w-4" />}
        />
        <StatCard label="Critical Alerts" value={stats?.critical_alerts_open ?? '—'} tone={(stats?.critical_alerts_open ?? 0) > 0 ? 'warn' : 'good'} to="/alerts" />
      </div>

      <div className="grid gap-8 lg:grid-cols-12">
        {/* ML model registry */}
        <Panel tone="low" className="p-6 md:p-8 lg:col-span-6">
          <div className="mb-4 flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            <h3 className="font-display text-lg font-bold text-on-surface">ML Model Registry</h3>
          </div>
          {models?.models && Object.keys(models.models).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(models.models).map(([name, m]: any) => (
                <div key={name} className="flex items-center justify-between rounded-2xl border border-outline-variant/30 bg-surface-container-lowest px-4 py-3">
                  <span className="font-mono text-xs font-bold text-primary">{name}</span>
                  <span className="font-mono text-xs text-on-surface-variant">
                    v{m.version} · AUC {m.metrics?.roc_auc ?? '?'} ·{' '}
                    {m.trained_at ? new Date(m.trained_at).toLocaleDateString('en-IN') : ''}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-outline">Models not trained yet — run scripts/seed.py.</p>
          )}
          <p className="mt-4 rounded-2xl bg-secondary-container p-3 text-xs font-medium text-on-secondary-container">
            ⚠️ {models?.trained_on}: {models?.disclaimer}
          </p>
          <Link
            to="/ledger"
            className="mt-4 block rounded-2xl bg-primary py-2.5 text-center text-sm font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container"
          >
            Open Ledger &amp; Demo-Tamper Console →
          </Link>
        </Panel>

        {/* latest chain */}
        <Panel className="p-6 md:p-8 lg:col-span-6">
          <div className="mb-4 flex items-center gap-2">
            <GitMerge className="h-5 w-5 text-primary" />
            <h3 className="font-display text-lg font-bold text-on-surface">Latest Ledger Blocks</h3>
          </div>
          <ul className="space-y-1.5 overflow-hidden font-mono text-[11px] text-on-surface-variant">
            {(events ?? []).slice(0, 10).map((e: any) => (
              <li key={e.seq} className="flex items-center gap-2 rounded-xl px-2 py-1.5 transition-colors hover:bg-surface-container-high">
                <span className="rounded-lg bg-primary-container px-1.5 py-0.5 font-bold text-on-primary-container">{e.seq}</span>
                <span className="w-24 truncate font-semibold text-on-surface">{e.event_type}</span>
                <span className="truncate text-outline">{e.hash.slice(0, 20)}…</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
