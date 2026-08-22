import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  Building2,
  FlaskConical,
  GitMerge,
  ShieldAlert,
  SlidersHorizontal,
} from 'lucide-react';
import {
  useAlerts,
  useDashboard,
  useFarmComplianceTable,
  useLedgerVerify,
  useResidueTests,
  useStatusOverview,
  useViolations,
} from '../../hooks/queries';
import {
  MonoLabel,
  PageBanner,
  Panel,
  SeverityBadge,
  Spinner,
  StatCard,
} from '../../components/badges';

/** Regulator view: enforcement — scoreboard, violations, lab pipeline, ledger. */
export default function RegulatorDashboard() {
  const { data: stats } = useDashboard();
  const { data: byFarm } = useFarmComplianceTable();
  const { data: overview } = useStatusOverview();
  const { data: violations } = useViolations();
  const { data: tests } = useResidueTests();
  const { data: ledger } = useLedgerVerify();
  const { data: alerts } = useAlerts();

  if (!stats || !byFarm) return <Spinner />;

  return (
    <div className="w-full space-y-8">
      <PageBanner
        accent="tertiary"
        eyebrow={
          <>
            <SlidersHorizontal className="h-4 w-4" />
            <span>REGULATOR WORKSPACE | FOOD SAFETY AUTHORITY</span>
          </>
        }
        title="State-wide AMU & MRL compliance"
        subtitle={`${(overview ?? []).length} registered farms under continuous monitoring · evidence frozen at sale time`}
        actions={
          <>
            <Link
              to="/violations"
              className="flex items-center gap-2 rounded-2xl bg-error px-4 py-2.5 text-sm font-semibold text-on-error shadow-md transition-colors hover:bg-error-container hover:text-on-error-container"
            >
              <ShieldAlert className="h-4 w-4" /> Violation Register
            </Link>
            <Link
              to="/lab-tests"
              className="flex items-center gap-2 rounded-2xl border border-outline-variant/40 bg-surface-container-lowest px-4 py-2.5 text-sm font-semibold text-primary shadow-sm transition-colors hover:bg-surface-container"
            >
              <FlaskConical className="h-4 w-4" /> Lab Console
            </Link>
          </>
        }
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Farms Monitored" value={(overview ?? []).length} to="/animals" icon={<Building2 className="h-4 w-4" />} />
        <StatCard label="Active Animals" value={stats.total_animals} to="/animals" />
        <StatCard label="MRL Violations" value={stats.violations_total} tone={stats.violations_total ? 'danger' : 'good'} sub="Frozen evidence" to="/violations" icon={<ShieldAlert className="h-4 w-4" />} />
        <StatCard label="Critical Alerts" value={stats.critical_alerts_open} tone={stats.critical_alerts_open ? 'warn' : 'good'} to="/alerts" icon={<AlertTriangle className="h-4 w-4" />} />
        <StatCard
          label="Traceability Ledger"
          value={ledger?.valid ? '✓ intact' : '✗ tampered'}
          tone={ledger?.valid ? 'good' : 'danger'}
          sub={`${ledger?.length ?? 0} blocks`}
          to="/ledger"
          icon={<GitMerge className="h-4 w-4" />}
        />
        <StatCard
          label="Lab Tests"
          value={`${(tests ?? []).filter((t: any) => t.result === 'fail').length}/${(tests ?? []).length}`}
          sub="failed / total"
          to="/lab-tests"
          icon={<FlaskConical className="h-4 w-4" />}
        />
      </div>

      {/* farm scoreboard */}
      <section>
        <MonoLabel className="mb-3 block text-outline">Farm compliance scoreboard · worst first</MonoLabel>
        <Panel className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-outline-variant/30 font-mono text-[11px] uppercase tracking-wider text-on-surface-variant">
                <th className="px-5 py-3.5">Farm</th>
                <th className="px-3 py-3.5">Animals</th>
                <th className="px-3 py-3.5">In withdrawal</th>
                <th className="px-3 py-3.5">AMU 30d</th>
                <th className="px-3 py-3.5">Vet-supervised</th>
                <th className="px-3 py-3.5">Violations</th>
                <th className="px-3 py-3.5">Critical alerts</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/20">
              {byFarm.map((f: any) => {
                const ov = (overview ?? []).find((x: any) => x.farm_id === f.farm_id);
                return (
                  <tr key={f.farm_id} className={`transition-colors hover:bg-surface-container-high ${f.violations_total > 0 ? 'bg-error-container/40' : ''}`}>
                    <td className="px-5 py-3.5">
                      <p className="font-semibold text-on-surface">{f.name}</p>
                      <p className="font-mono text-xs text-on-surface-variant">{f.district}, {f.state}</p>
                    </td>
                    <td className="px-3 py-3.5 font-mono tabular-nums">{f.total_animals}</td>
                    <td className="px-3 py-3.5 font-mono tabular-nums">{ov?.under_withdrawal ?? '—'}</td>
                    <td className="px-3 py-3.5 font-mono tabular-nums">{f.amu_30d}</td>
                    <td className="px-3 py-3.5 font-mono tabular-nums">
                      {f.supervised_share != null ? `${Math.round(f.supervised_share * 100)}%` : '—'}
                    </td>
                    <td className={`px-3 py-3.5 font-mono font-bold tabular-nums ${f.violations_total > 0 ? 'text-error' : 'text-primary'}`}>
                      {f.violations_total}
                    </td>
                    <td className="px-3 py-3.5 font-mono tabular-nums">{f.critical_alerts_open}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Panel>
      </section>

      <div className="grid gap-8 lg:grid-cols-12">
        {/* latest violations */}
        <section className="space-y-3 lg:col-span-6">
          <div className="flex items-center justify-between">
            <MonoLabel className="text-outline">Latest violation cases</MonoLabel>
            <Link to="/violations" className="text-xs font-semibold text-secondary hover:underline">Register →</Link>
          </div>
          {(violations ?? []).slice(0, 5).map((v: any) => (
            <Link
              key={v.sale_event_id}
              to="/violations"
              className="block rounded-2xl border border-error/20 bg-error-container/70 p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
            >
              <span className="font-mono text-xs font-bold text-on-error-container">{v.animal_tag ?? '(bulk)'}</span>
              {' — '}
              <span className="text-sm text-on-surface">
                {v.quantity} {v.unit} {v.product_type} sold{' '}
                {v.occurred_at ? new Date(v.occurred_at).toLocaleDateString('en-IN') : ''}
              </span>
              {(v.linked_administration_ids ?? []).length > 0 && (
                <span className="ml-1 font-mono text-xs text-error">
                  · treatments #{v.linked_administration_ids.join(', #')}
                </span>
              )}
            </Link>
          ))}
          {(violations ?? []).length === 0 && (
            <p className="rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-8 text-center text-sm text-outline">
              No violations on record.
            </p>
          )}
        </section>

        {/* alerts */}
        <section className="space-y-3 lg:col-span-6">
          <div className="flex items-center justify-between">
            <MonoLabel className="text-outline">Critical alert feed</MonoLabel>
            <Link to="/alerts" className="text-xs font-semibold text-secondary hover:underline">All alerts →</Link>
          </div>
          {(alerts ?? []).filter((a: any) => a.severity === 'critical').slice(0, 5).map((a: any) => (
            <div key={a.id} className="rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-4 shadow-sm">
              <SeverityBadge severity={a.severity} />{' '}
              <span className="text-sm font-semibold text-on-surface">{a.title}</span>
              <p className="mt-1 line-clamp-1 text-xs text-on-surface-variant">{a.message}</p>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
