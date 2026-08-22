import { Link } from 'react-router-dom';
import {
  FileSpreadsheet,
  PawPrint,
  ShieldCheck,
  Stethoscope,
  Timer,
  TrendingUp,
} from 'lucide-react';
import {
  useAmuAnalytics,
  usePrescriptions,
  useStatusOverview,
} from '../../hooks/queries';
import {
  AwareBadge,
  MonoLabel,
  PageBanner,
  Panel,
  StatCard,
} from '../../components/badges';

/** Veterinarian view: cross-farm patients, prescriptions, stewardship. */
export default function VetDashboard() {
  const { data: overview } = useStatusOverview();
  const { data: rx } = usePrescriptions();
  const { data: amu } = useAmuAnalytics();

  const totals = (overview ?? []).reduce(
    (acc: any, f: any) => ({
      animals: acc.animals + f.animal_count,
      withdrawal: acc.withdrawal + f.under_withdrawal,
      clearToday: acc.clearToday + f.clear_today,
    }),
    { animals: 0, withdrawal: 0, clearToday: 0 }
  );
  const watchShare =
    amu?.aware_breakdown?.find((b: any) => b.aware_class === 'Watch')?.share ?? 0;

  return (
    <div className="w-full space-y-8">
      <PageBanner
        accent="secondary"
        eyebrow={
          <>
            <Stethoscope className="h-4 w-4" />
            <span>VETERINARY WORKSPACE | CROSS-FARM CARE</span>
          </>
        }
        title="Your patients across all registered farms"
        subtitle={`${(overview ?? []).length} farms · advise owners on withdrawal hold periods before any sale`}
        actions={
          <Link
            to="/prescriptions"
            className="flex items-center gap-2 rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container"
          >
            <FileSpreadsheet className="h-4 w-4" /> Issue Prescription
          </Link>
        }
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Active Patients" value={totals.animals} sub="All farms" to="/animals" icon={<PawPrint className="h-4 w-4" />} />
        <StatCard label="In Withdrawal" value={totals.withdrawal} tone="warn" sub="Advise hold periods" to="/compliance" icon={<Timer className="h-4 w-4" />} />
        <StatCard label="Clear Today" value={totals.clearToday} tone="good" sub="Safe post-clearance" to="/compliance" />
        <StatCard label="Prescriptions" value={(rx ?? []).length} sub="On record" to="/prescriptions" icon={<FileSpreadsheet className="h-4 w-4" />} />
        <StatCard label="Watch Share" value={`${Math.round(watchShare * 100)}%`} tone={watchShare > 0.35 ? 'warn' : 'good'} sub="WHO target <35%" to="/analytics" icon={<TrendingUp className="h-4 w-4" />} />
        <StatCard label="Farms Served" value={(overview ?? []).length} sub="Registered with you" to="/animals" icon={<ShieldCheck className="h-4 w-4" />} />
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* farms */}
        <section className="space-y-3 lg:col-span-6">
          <MonoLabel className="text-outline">Farms under your care</MonoLabel>
          <div className="space-y-3">
            {(overview ?? []).map((f: any) => (
              <Link
                key={f.farm_id}
                to="/animals"
                className="flex items-center justify-between rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-secondary/40 hover:shadow-md"
              >
                <div>
                  <p className="text-sm font-bold text-on-surface">{f.name}</p>
                  <p className="font-mono text-xs text-on-surface-variant">{f.district}, {f.state}</p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-xs text-on-surface">{f.animal_count} animals</p>
                  {f.under_withdrawal > 0 ? (
                    <p className="font-mono text-xs font-bold text-error">{f.under_withdrawal} in withdrawal</p>
                  ) : (
                    <p className="font-mono text-xs font-bold text-primary">all clear</p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* recent prescriptions */}
        <section className="lg:col-span-6">
          <div className="mb-3 flex items-center justify-between">
            <MonoLabel className="text-outline">Recent prescriptions</MonoLabel>
            <Link to="/prescriptions" className="text-xs font-semibold text-secondary hover:underline">All →</Link>
          </div>
          <Panel className="overflow-hidden">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-outline-variant/20">
                {(rx ?? []).slice(0, 7).map((p: any) => (
                  <tr key={p.id} className="transition-colors hover:bg-surface-container-high">
                    <td className="px-4 py-3 font-mono text-xs font-bold text-primary">{p.animal_tag}</td>
                    <td className="px-4 py-3">
                      <span className="font-semibold text-on-surface">{p.drug_name}</span>{' '}
                      <AwareBadge aware={p.aware_class ?? 'Access'} />
                      <p className="text-xs text-on-surface-variant">{p.diagnosis}</p>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-on-surface-variant">
                      {p.dose_amount} mg/kg × {p.duration_days}d
                    </td>
                  </tr>
                ))}
                {(rx ?? []).length === 0 && (
                  <tr><td className="px-4 py-10 text-center text-sm text-outline">No prescriptions yet.</td></tr>
                )}
              </tbody>
            </table>
          </Panel>
        </section>
      </div>

      {/* stewardship */}
      <Panel tone="low" className="p-6 md:p-8">
        <div className="mb-4 flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-primary" />
          <h3 className="font-display text-lg font-bold text-on-surface">Antimicrobial Stewardship Snapshot</h3>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {(amu?.aware_breakdown ?? []).map((b: any) => (
            <div
              key={b.aware_class}
              className={`rounded-2xl border p-4 ${
                b.aware_class === 'Access'
                  ? 'border-primary/20 bg-primary-container'
                  : b.aware_class === 'Watch'
                    ? 'border-tertiary/30 bg-tertiary-container'
                    : 'border-error/20 bg-error-container'
              }`}
            >
              <MonoLabel>{b.aware_class} class</MonoLabel>
              <p className="mt-1 font-display text-3xl font-extrabold">
                {Math.round(b.share * 100)}%
              </p>
              <p className="text-xs font-medium opacity-80">{b.count} courses</p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs leading-relaxed text-on-surface-variant">
          💡 Prefer <b>Access</b> antimicrobials first-line; reserve <b>Watch</b>/<b>Reserve</b> for
          confirmed need — every Watch course raises MRL-violation and AMR risk for the farm.
        </p>
      </Panel>
    </div>
  );
}
