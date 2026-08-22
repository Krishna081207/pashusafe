import { useParams, Link } from 'react-router-dom';
import QRCode from 'react-qr-code';
import { ShieldCheck } from 'lucide-react';
import { usePublicTrace } from '../hooks/queries';
import { AwareBadge, MonoLabel, Panel, Spinner } from '../components/badges';

/** Fully public supply-chain page shown after scanning the animal's QR code. */
export default function PublicTracePage() {
  const { qrCode } = useParams();
  const { data: t } = usePublicTrace(qrCode);

  return (
    <div className="min-h-full bg-surface p-6">
      <div className="mx-auto max-w-3xl space-y-5 pb-12">
        {/* header */}
        <div className="rounded-3xl border border-outline-variant/40 bg-surface-container-lowest p-6 shadow-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary shadow-md">
                <ShieldCheck className="h-6 w-6 text-primary-fixed" />
              </div>
              <div>
                <p className="font-display font-bold tracking-tight text-primary">PASHUSAFE TRACE</p>
                <MonoLabel className="text-on-surface-variant">farm-to-consumer transparency</MonoLabel>
              </div>
            </div>
            <Link to="/login" className="font-mono text-[11px] font-semibold uppercase tracking-widest text-secondary hover:underline">
              Portal login →
            </Link>
          </div>

          {!t ? (
            <Spinner label="Fetching animal history…" />
          ) : (
            <>
              <h1 className="mt-5 font-mono text-2xl font-extrabold text-on-surface">{t.tag_id}</h1>
              <p className="text-sm capitalize text-on-surface-variant">
                {t.species} · {t.breed ?? ''} ({t.production_status})
              </p>
              <div className="mt-4 flex flex-wrap gap-2 font-mono text-sm font-bold">
                <span
                  className={`rounded-2xl px-3.5 py-1.5 ${
                    t.ledger_integrity
                      ? 'bg-primary-container text-on-primary-container'
                      : 'bg-error-container text-on-error-container'
                  }`}
                >
                  {t.ledger_integrity ? '⛓️ LEDGER VERIFIED' : '⚠️ LEDGER TAMPER DETECTED'}
                </span>
                <span
                  className={`rounded-2xl px-3.5 py-1.5 ${
                    t.violation_count === 0
                      ? 'bg-primary-container text-on-primary-container'
                      : 'bg-error-container text-on-error-container'
                  }`}
                >
                  {t.violation_count === 0 ? '✅ NO MRL VIOLATIONS' : `🚨 ${t.violation_count} VIOLATION(S)`}
                </span>
              </div>
            </>
          )}
        </div>

        {t && (
          <>
            {/* medicine history */}
            <Panel tone="lowest" className="p-6">
              <h2 className="mb-3 font-display font-bold text-on-surface">💉 Medicine History</h2>
              {t.medicine_history.length === 0 ? (
                <p className="text-sm text-outline">No antimicrobial treatments recorded.</p>
              ) : (
                <ul className="divide-y divide-outline-variant/20 text-sm">
                  {t.medicine_history.map((m: any, i: number) => (
                    <li key={i} className="flex flex-wrap items-center justify-between gap-2 py-3">
                      <span className="font-semibold text-on-surface">
                        {m.drug_name} {m.aware_class && <AwareBadge aware={m.aware_class} />}
                      </span>
                      <span className="font-mono text-xs text-on-surface-variant">
                        {m.dose_mg_kg} mg/kg × {m.course_days}d
                        {m.supervised ? ' · 📋 vet-prescribed' : ' · ⚠️ self-treated'}
                      </span>
                      <span className="font-mono text-xs text-outline">
                        {m.started_at ? new Date(m.started_at).toLocaleDateString('en-IN') : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            {t.residue_tests.length > 0 && (
              <Panel tone="lowest" className="p-6">
                <h2 className="mb-3 font-display font-bold text-on-surface">🧪 Residue Test Results</h2>
                <ul className="divide-y divide-outline-variant/20 text-sm">
                  {t.residue_tests.map((r: any, i: number) => (
                    <li key={i} className="flex justify-between py-3">
                      <span className="text-on-surface">
                        {r.drug_name ?? '?'} · {r.method} ·{' '}
                        <span className="font-mono">{r.measured_ug_kg ?? '?'}/{r.mrl_reference_ug_kg ?? '?'} µg/kg</span>
                      </span>
                      <span
                        className={`rounded-full px-2.5 py-0.5 font-mono text-[11px] font-bold ${
                          r.result === 'fail'
                            ? 'bg-error-container text-on-error-container'
                            : 'bg-primary-container text-on-primary-container'
                        }`}
                      >
                        {r.result.toUpperCase()}
                      </span>
                    </li>
                  ))}
                </ul>
              </Panel>
            )}

            {t.sale_history.length > 0 && (
              <Panel tone="lowest" className="p-6">
                <h2 className="mb-3 font-display font-bold text-on-surface">🛒 Product Sale History</h2>
                <ul className="divide-y divide-outline-variant/20 text-sm">
                  {t.sale_history.map((s: any, i: number) => (
                    <li key={i} className="flex justify-between py-3">
                      <span className="capitalize text-on-surface">
                        {s.quantity} {s.unit} {s.product_type}
                      </span>
                      <span className="font-mono text-xs text-on-surface-variant">
                        {s.occurred_at ? new Date(s.occurred_at).toLocaleDateString('en-IN') : ''}
                        {s.is_violation && (
                          <b className="ml-1 text-error">· sold during withdrawal 🚨</b>
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              </Panel>
            )}

            {t.ledger_events?.length > 0 && (
              <Panel tone="lowest" className="p-6">
                <h2 className="mb-3 font-display font-bold text-on-surface">⛓️ Blockchain Events</h2>
                <ul className="space-y-1 font-mono text-[11px] text-on-surface-variant">
                  {t.ledger_events.map((e: any) => (
                    <li key={e.seq}>
                      #{e.seq} {e.event_type} — {String(e.hash)}
                    </li>
                  ))}
                </ul>
              </Panel>
            )}

            {/* mini QR so a printed screenshot still scans */}
            <div className="flex flex-col items-center rounded-3xl border border-outline-variant/40 bg-surface-container-lowest p-6">
              <QRCode value={`${window.location.origin}/trace/${qrCode}`} size={110} />
              <MonoLabel className="mt-2 text-outline">scan to re-verify anytime</MonoLabel>
            </div>
          </>
        )}

        <footer className="pb-8 text-center font-mono text-[10px] uppercase tracking-widest text-outline">
          Powered by PashuSafe — Smart India Hackathon demo · synthetic data
        </footer>
      </div>
    </div>
  );
}
