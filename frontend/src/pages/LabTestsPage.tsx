import { useState } from 'react';
import { FlaskConical } from 'lucide-react';
import {
  useAnimals,
  useDrugs,
  useRecordResidueTest,
  useResidueTests,
  useSales,
} from '../hooks/queries';
import { MonoLabel, PageBanner, Panel, Spinner } from '../components/badges';

export default function LabTestsPage() {
  const { data: tests } = useResidueTests();
  const { data: drugs } = useDrugs();
  const { data: animals } = useAnimals();
  const { data: sales } = useSales();
  const create = useRecordResidueTest();

  const [drugId, setDrugId] = useState('');
  const [animalId, setAnimalId] = useState('');
  const [saleId, setSaleId] = useState('');
  const [method, setMethod] = useState('HPLC');
  const [measured, setMeasured] = useState('');
  const [result, setResult] = useState('fail');
  const [msg, setMsg] = useState('');

  const inputCls =
    'mt-1 w-full rounded-2xl border-none bg-surface-container-high px-4 py-2.5 text-sm outline-none transition-all focus:ring-2 focus:ring-secondary';

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg('');
    try {
      const res: any = await create.mutateAsync({
        sample_type: 'milk',
        drug_id: Number(drugId),
        animal_id: animalId ? Number(animalId) : null,
        sale_event_id: saleId ? Number(saleId) : null,
        method,
        measured_residue_ug_kg: measured ? Number(measured) : null,
        result,
      });
      setMsg(
        res.alerts_raised.includes('MRL_VIOLATION_CONFIRMED')
          ? '🚨 Result recorded — violation CONFIRMED, alert escalated.'
          : res.alerts_raised.includes('EARLY_CLEARANCE_EVIDENCED')
            ? '✅ Pass recorded — withdrawal windows cleared with lab evidence.'
            : 'Result recorded.'
      );
    } catch (err: any) {
      setMsg(`Error: ${err.message}`);
    }
  };

  if (!tests) return <Spinner />;

  return (
    <div className="grid gap-8 lg:grid-cols-12">
      <section className="lg:col-span-8">
        <PageBanner
          accent="secondary"
          eyebrow={<><FlaskConical className="h-4 w-4" /><span>LABORATORY | RESIDUE TESTING</span></>}
          title="Residue test results"
          subtitle="SNAP / ELISA / HPLC measurements vs FSSAI MRL references"
        />

        <Panel className="mt-6 overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-outline-variant/30 font-mono text-[11px] uppercase tracking-wider text-on-surface-variant">
                <th className="px-5 py-3.5">Tested</th>
                <th className="px-3 py-3.5">Animal</th>
                <th className="px-3 py-3.5">Drug / method</th>
                <th className="px-3 py-3.5">Measured vs MRL</th>
                <th className="px-3 py-3.5">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/20">
              {tests.map((t: any) => (
                <tr key={t.id} className="transition-colors hover:bg-surface-container-high">
                  <td className="px-5 py-3.5 font-mono text-xs text-on-surface-variant">
                    {t.tested_at ? new Date(t.tested_at).toLocaleDateString('en-IN') : ''}
                  </td>
                  <td className="px-3 py-3.5 font-mono text-xs font-bold text-primary">{t.animal_tag ?? '—'}</td>
                  <td className="px-3 py-3.5">
                    <span className="font-medium">{t.drug_name}</span>
                    <p className="font-mono text-xs text-outline">{t.method}</p>
                  </td>
                  <td className="px-3 py-3.5 font-mono tabular-nums">
                    {t.measured_residue_ug_kg ?? '?'} / {t.mrl_reference_ug_kg ?? '?'} µg/kg
                  </td>
                  <td className="px-3 py-3.5">
                    <span
                      className={`rounded-full px-2.5 py-1 font-mono text-[11px] font-bold ${
                        t.result === 'fail'
                          ? 'bg-error-container text-on-error-container'
                          : t.result === 'pass'
                            ? 'bg-primary-container text-on-primary-container'
                            : 'bg-surface-container-high text-on-surface-variant'
                      }`}
                    >
                      {t.result.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
              {tests.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-10 text-center text-sm text-outline">No tests yet.</td></tr>
              )}
            </tbody>
          </table>
        </Panel>
      </section>

      <section className="lg:col-span-4">
        <Panel tone="low" className="p-6">
          <MonoLabel className="text-outline">Record lab result (regulator)</MonoLabel>
          <form onSubmit={submit} className="mt-3 space-y-3">
            <select value={drugId} onChange={(e) => setDrugId(e.target.value)} required className={inputCls}>
              <option value="">— drug tested —</option>
              {(drugs ?? []).map((d: any) => (
                <option key={d.id} value={d.id}>{d.generic_name}</option>
              ))}
            </select>
            <select value={animalId} onChange={(e) => setAnimalId(e.target.value)} className={inputCls}>
              <option value="">— animal —</option>
              {(animals ?? []).map((a: any) => (
                <option key={a.id} value={a.id}>{a.tag_id}</option>
              ))}
            </select>
            <select value={saleId} onChange={(e) => setSaleId(e.target.value)} className={inputCls}>
              <option value="">— link to flagged sale (optional) —</option>
              {(sales ?? []).filter((s: any) => s.was_under_withdrawal).slice(0, 20).map((s: any) => (
                <option key={s.id} value={s.id}>
                  #{s.id} {s.product_type} {s.animal_tag ?? 'bulk'}{' '}
                  {new Date(s.occurred_at).toLocaleDateString('en-IN')}
                </option>
              ))}
            </select>
            <div className="grid grid-cols-2 gap-3">
              <select value={method} onChange={(e) => setMethod(e.target.value)} className={inputCls}>
                <option>SNAP</option>
                <option>ELISA</option>
                <option>HPLC</option>
              </select>
              <input type="number" step="0.1" value={measured} onChange={(e) => setMeasured(e.target.value)}
                placeholder="µg/kg" className={inputCls} />
            </div>
            <select value={result} onChange={(e) => setResult(e.target.value)} className={inputCls}>
              <option value="fail">FAIL (above MRL)</option>
              <option value="pass">PASS (within MRL)</option>
              <option value="pending">Pending</option>
            </select>
            {msg && <p className="rounded-2xl bg-surface-container-high p-3 text-xs font-medium">{msg}</p>}
            <button type="submit" disabled={create.isPending}
              className="w-full rounded-2xl bg-primary py-3 font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container disabled:opacity-50">
              Record result
            </button>
            <p className="text-[11px] leading-snug text-outline">
              A FAIL confirms the linked violation and escalates the alert. A PASS while a window is
              theoretically active clears it early with laboratory evidence.
            </p>
          </form>
        </Panel>
      </section>
    </div>
  );
}
