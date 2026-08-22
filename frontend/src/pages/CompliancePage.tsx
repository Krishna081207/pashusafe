import { Link, useSearchParams } from 'react-router-dom';
import { Timer } from 'lucide-react';
import { useFarmStatus, useMe, useStatusOverview } from '../hooks/queries';
import { MonoLabel, OverallBadge, PageBanner, Panel, Spinner, StatCard, TissueCountdown } from '../components/badges';

export default function CompliancePage() {
  const { data: me } = useMe();
  const [params] = useSearchParams();
  const justRecorded = params.get('recorded');
  const { data: status } = useFarmStatus(me?.farm_id);
  const { data: overview } = useStatusOverview();

  // Vets get the cross-farm withdrawal picture.
  if (me?.role === 'vet') {
    if (!overview) return <Spinner />;
    return (
      <div className="w-full space-y-8">
        <PageBanner
          accent="secondary"
          eyebrow={<><Timer className="h-4 w-4" /><span>WITHDRAWAL MONITOR | ALL FARMS</span></>}
          title="Cross-farm withdrawal status"
          subtitle="Advise owners not to sell until clocks clear"
        />
        <div className="grid gap-4 sm:grid-cols-2">
          {overview.map((f: any) => (
            <div key={f.farm_id} className={`rounded-3xl border p-6 shadow-sm ${f.under_withdrawal > 0 ? 'border-error/20 bg-error-container/50' : 'border-outline-variant/40 bg-surface-container'}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-display font-bold text-on-surface">{f.name}</p>
                  <p className="font-mono text-xs text-on-surface-variant">{f.district}, {f.state} · {f.animal_count} animals</p>
                </div>
                {f.under_withdrawal > 0 ? (
                  <span className="rounded-full bg-error-container px-3 py-1 font-mono text-xs font-bold text-on-error-container">
                    {f.under_withdrawal} in withdrawal
                  </span>
                ) : (
                  <span className="rounded-full bg-primary-container px-3 py-1 font-mono text-xs font-bold text-on-primary-container">all clear</span>
                )}
              </div>
              {f.clear_today > 0 && (
                <p className="mt-3 font-mono text-xs text-secondary">⏳ {f.clear_today} clear today — advise collection only after clearance time</p>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (me?.role !== 'farmer' || me.farm_id == null) {
    return (
      <Panel tone="lowest" className="mx-auto max-w-xl p-10 text-center">
        <p className="text-sm text-on-surface-variant">
          Compliance countdown board is farmer/vet scoped. Regulators: see{' '}
          <Link to="/violations" className="font-semibold text-secondary hover:underline">Violation Register</Link>.
        </p>
      </Panel>
    );
  }
  if (!status) return <Spinner />;

  return (
    <div className="w-full space-y-8">
      <PageBanner
        eyebrow={<><Timer className="h-4 w-4" /><span>WITHDRAWAL MONITOR | LIVE CLOCKS</span></>}
        title="MRL Compliance Board"
        subtitle="Live withdrawal countdowns · refreshes every minute · clock starts on first dose day (IST)"
        actions={
          justRecorded ? (
            <span className="rounded-2xl bg-primary-container px-4 py-2.5 text-sm font-semibold text-on-primary-container">
              ✅ Treatment recorded — clocks running below
            </span>
          ) : undefined
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Withdrawal Active" value={status.counts.withdrawal_active} tone="danger" sub="Do not sell" to="/animals" />
        <StatCard label="Clears Today" value={status.counts.clear_today} tone="warn" sub="Wait for clearance time" />
        <StatCard label="Clear" value={status.counts.clear} tone="good" sub="Safe to sell" to="/sales" />
      </div>

      <Panel className="overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-outline-variant/30 font-mono text-[11px] uppercase tracking-wider text-on-surface-variant">
              <th className="px-5 py-3.5">Animal</th>
              <th className="px-3 py-3.5">Status</th>
              <th className="px-3 py-3.5">Tissue countdowns</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/20">
            {status.animals.map((row: any) => (
              <tr key={row.animal_id} className={`transition-colors hover:bg-surface-container-high ${row.overall === 'WITHDRAWAL_ACTIVE' ? 'bg-error-container/30' : ''}`}>
                <td className="px-5 py-3.5">
                  <MonoLabel className="text-primary">{row.tag_id}</MonoLabel>
                  <p className="text-xs capitalize text-on-surface-variant">{row.species} · {row.breed}</p>
                </td>
                <td className="px-3 py-3.5"><OverallBadge overall={row.overall} /></td>
                <td className="px-3 py-3.5">
                  {row.tissues.length === 0 ? (
                    <span className="font-mono text-xs text-outline">—</span>
                  ) : (
                    <div className="flex flex-wrap gap-1.5">
                      {row.tissues.map((t: any) => (
                        <TissueCountdown key={t.tissue} t={t} />
                      ))}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <p className="font-mono text-xs leading-relaxed text-outline">
        Convention: unsafe interval runs from the FIRST dose through end of the Nth full day after
        the last dose (N = labelled withdrawal days, rounded up — safe side).
      </p>
    </div>
  );
}
