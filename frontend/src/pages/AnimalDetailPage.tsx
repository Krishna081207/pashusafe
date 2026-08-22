import { Link, useParams } from 'react-router-dom';
import QRCode from 'react-qr-code';
import {
  Bot,
  FlaskConical,
  Syringe,
  Timer,
} from 'lucide-react';
import {
  useAnimalDossier,
  useAnimalPrediction,
} from '../hooks/queries';
import HealthMonitorPanel from '../components/HealthMonitorPanel';
import {
  AwareBadge,
  MonoLabel,
  OverallBadge,
  PageBanner,
  Panel,
  RiskBadge,
  Spinner,
  TissueCountdown,
} from '../components/badges';

export default function AnimalDetailPage() {
  const { id } = useParams();
  const animalId = Number(id);
  const { data: d } = useAnimalDossier(animalId);
  const { data: pred } = useAnimalPrediction(animalId);

  if (!d) return <Spinner />;

  return (
    <div className="w-full space-y-8">
      <PageBanner
        eyebrow={
          <>
            <Timer className="h-4 w-4" />
            <span>LIVESTOCK PASSPORT | {d.species.toUpperCase()}</span>
          </>
        }
        title={<span className="font-mono">{d.tag_id}</span>}
        subtitle={`${d.breed ?? ''} · ${d.production_status} · ${d.weight_kg ?? '?'} kg`}
        actions={<OverallBadge overall={d.overall} />}
      />

      {/* withdrawal clocks */}
      <Panel className="p-6 md:p-8">
        <div className="mb-4 flex items-center gap-2">
          <Timer className="h-5 w-5 text-tertiary" />
          <h3 className="font-display text-lg font-bold text-on-surface">Withdrawal Clocks</h3>
        </div>
        {d.tissues.length === 0 ? (
          <p className="rounded-2xl bg-primary-container px-4 py-3 text-sm font-semibold text-on-primary-container">
            ✅ All tissues clear — safe to sell.
          </p>
        ) : (
          <div className="flex flex-wrap gap-3">
            {d.tissues.map((t: any) => (
              <div key={t.tissue} className="rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-4">
                <TissueCountdown t={t} />
                <p className="mt-2 font-mono text-xs text-on-surface-variant">
                  clears {t.clears_at_display} · drug:{' '}
                  <strong className="text-tertiary">{t.drug_name ?? '?'}</strong>
                </p>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* left column */}
        <section className="space-y-8 lg:col-span-8">
          {/* treatments */}
          <Panel className="overflow-hidden p-0">
            <h3 className="flex items-center gap-2 border-b border-outline-variant/30 px-6 py-4">
              <Syringe className="h-5 w-5 text-secondary" />
              <span className="font-display text-lg font-bold text-on-surface">Treatment History</span>
            </h3>
            <table className="w-full text-sm">
              <tbody className="divide-y divide-outline-variant/20">
                {d.administrations.map((a: any) => (
                  <tr key={a.id} className="transition-colors hover:bg-surface-container-high">
                    <td className="px-6 py-3.5 font-semibold text-on-surface">{a.drug_name}</td>
                    <td className="px-3 py-3.5"><AwareBadge aware={a.aware_class ?? 'Access'} /></td>
                    <td className="px-3 py-3.5 font-mono tabular-nums text-on-surface-variant">
                      {a.dose_amount} mg/kg · {a.course_days}d
                    </td>
                    <td className="px-3 py-3.5 text-xs">
                      {a.supervised ? (
                        <span className="rounded-full bg-primary-container px-2.5 py-1 font-semibold text-on-primary-container">📋 prescribed</span>
                      ) : (
                        <span className="rounded-full bg-error-container px-2.5 py-1 font-semibold text-on-error-container">⚠️ self-treated</span>
                      )}
                    </td>
                    <td className="px-6 py-3.5 text-right font-mono text-xs text-outline">
                      {a.started_at ? new Date(a.started_at).toLocaleDateString('en-IN') : ''}
                    </td>
                  </tr>
                ))}
                {d.administrations.length === 0 && (
                  <tr><td colSpan={5} className="px-6 py-10 text-center text-sm text-outline">No treatments recorded.</td></tr>
                )}
              </tbody>
            </table>
          </Panel>

          {/* interactive IoT health monitor */}
          <HealthMonitorPanel animalId={animalId} />
        </section>

        {/* right rail */}
        <section className="space-y-6 lg:col-span-4">
          {/* ML prediction */}
          <Panel className="p-6">
            <div className="mb-3 flex items-center gap-2">
              <Bot className="h-5 w-5 text-primary" />
              <h3 className="font-display font-bold text-on-surface">AI Risk Profile</h3>
            </div>
            {pred?.mrl_violation_risk ? (
              <div className="space-y-4">
                <div>
                  <MonoLabel className="text-outline">MRL violation risk (30d)</MonoLabel>
                  <div className="mt-1"><RiskBadge band={pred.mrl_violation_risk.band} risk={pred.mrl_violation_risk.risk} /></div>
                </div>
                {pred.outbreak_risk && (
                  <div>
                    <MonoLabel className="text-outline">Disease outbreak risk</MonoLabel>
                    <div className="mt-1"><RiskBadge band={pred.outbreak_risk.band} risk={pred.outbreak_risk.risk} /></div>
                  </div>
                )}
                <ul className="space-y-1 text-xs text-on-surface-variant">
                  {(pred.mrl_violation_risk.top_factors ?? []).map((f: any) => (
                    <li key={f.factor}>• {f.factor}</li>
                  ))}
                </ul>
                <MonoLabel className="block text-outline">synthetic-data demo model</MonoLabel>
              </div>
            ) : (
              <p className="text-sm text-outline">Model not trained yet — run seed.</p>
            )}
          </Panel>

          {/* QR passport */}
          <Panel className="p-6 text-center">
            <MonoLabel className="text-outline">Supply-chain QR</MonoLabel>
            <div className="mx-auto mt-3 w-fit rounded-2xl border border-outline-variant/40 bg-white p-3">
              <QRCode value={`${window.location.origin}/trace/${d.qr_code}`} size={140} />
            </div>
            <Link
              to={`/trace/${d.qr_code}`}
              className="mt-4 block rounded-2xl bg-primary py-2.5 text-sm font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container"
            >
              Open public trace page →
            </Link>
          </Panel>

          {/* residue tests */}
          <Panel className="p-6">
            <div className="mb-3 flex items-center gap-2">
              <FlaskConical className="h-5 w-5 text-tertiary" />
              <h3 className="font-display font-bold text-on-surface">Residue Tests</h3>
            </div>
            {d.residue_tests.length === 0 ? (
              <p className="text-sm text-outline">No lab tests on record.</p>
            ) : (
              <ul className="divide-y divide-outline-variant/20 text-sm">
                {d.residue_tests.map((t: any) => (
                  <li key={t.id} className="flex justify-between py-2.5">
                    <span className="text-on-surface">{t.sample_type} · {t.method}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 font-mono text-[11px] font-bold ${
                        t.result === 'fail'
                          ? 'bg-error-container text-on-error-container'
                          : t.result === 'pass'
                            ? 'bg-primary-container text-on-primary-container'
                            : 'bg-surface-container-high text-on-surface-variant'
                      }`}
                    >
                      {t.result.toUpperCase()}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </section>
      </div>
    </div>
  );
}
