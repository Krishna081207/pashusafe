import { useState } from 'react';
import { FilePlus2, FileSpreadsheet } from 'lucide-react';
import { useAnimals, useDrugs, usePrescriptions, useRecordPrescription } from '../hooks/queries';
import { AwareBadge, MonoLabel, PageBanner, Panel, Spinner } from '../components/badges';

export default function PrescriptionsPage() {
  const { data: rx } = usePrescriptions();
  const { data: animals } = useAnimals();
  const { data: drugs } = useDrugs();
  const create = useRecordPrescription();

  const [animalId, setAnimalId] = useState('');
  const [drugId, setDrugId] = useState('');
  const [diagnosis, setDiagnosis] = useState('');
  const [dose, setDose] = useState(10);
  const [duration, setDuration] = useState(5);
  const [msg, setMsg] = useState('');

  const inputCls =
    'mt-1 w-full rounded-2xl border-none bg-surface-container-high px-4 py-2.5 text-sm outline-none transition-all focus:ring-2 focus:ring-secondary';

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg('');
    try {
      await create.mutateAsync({
        animal_id: Number(animalId),
        drug_id: Number(drugId),
        diagnosis,
        dose_amount: dose,
        route: 'im',
        duration_days: duration,
      });
      setMsg('✅ Prescription issued');
      setDiagnosis('');
    } catch (err: any) {
      setMsg(`Error: ${err.message}`);
    }
  };

  if (!rx) return <Spinner />;

  return (
    <div className="grid gap-8 lg:grid-cols-12">
      <section className="lg:col-span-8">
        <PageBanner
          accent="secondary"
          eyebrow={<><FileSpreadsheet className="h-4 w-4" /><span>VETERINARY | DIGITAL PRESCRIPTIONS</span></>}
          title="Digital Prescriptions"
          subtitle="Every supervised course links a vet to the treatment — unsupervised use is flagged in analytics"
        />

        <Panel className="mt-6 overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-outline-variant/30 font-mono text-[11px] uppercase tracking-wider text-on-surface-variant">
                <th className="px-5 py-3.5">Issued</th>
                <th className="px-3 py-3.5">Animal</th>
                <th className="px-3 py-3.5">Drug</th>
                <th className="px-3 py-3.5">Diagnosis</th>
                <th className="px-3 py-3.5">Course</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/20">
              {rx.map((p: any) => (
                <tr key={p.id} className="transition-colors hover:bg-surface-container-high">
                  <td className="px-5 py-3.5 font-mono text-xs text-on-surface-variant">
                    {p.issued_at ? new Date(p.issued_at).toLocaleDateString('en-IN') : ''}
                  </td>
                  <td className="px-3 py-3.5 font-mono text-xs font-bold text-primary">{p.animal_tag}</td>
                  <td className="px-3 py-3.5">
                    <span className="font-medium">{p.drug_name}</span> <AwareBadge aware={p.aware_class ?? 'Access'} />
                  </td>
                  <td className="px-3 py-3.5">{p.diagnosis}</td>
                  <td className="px-3 py-3.5 font-mono tabular-nums text-on-surface-variant">
                    {p.dose_amount} mg/kg × {p.duration_days}d
                  </td>
                </tr>
              ))}
              {rx.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-10 text-center text-sm text-outline">No prescriptions yet.</td></tr>
              )}
            </tbody>
          </table>
        </Panel>
      </section>

      <section className="lg:col-span-4">
        <Panel tone="low" className="p-6">
          <div className="mb-1 flex items-center gap-2">
            <FilePlus2 className="h-5 w-5 text-primary" />
            <h3 className="font-display font-bold text-on-surface">Issue new prescription</h3>
          </div>
          <form onSubmit={submit} className="mt-3 space-y-3">
            <select value={animalId} onChange={(e) => setAnimalId(e.target.value)} required className={inputCls}>
              <option value="">— animal —</option>
              {(animals ?? []).map((a: any) => (
                <option key={a.id} value={a.id}>{a.tag_id} · {a.species}</option>
              ))}
            </select>
            <select value={drugId} onChange={(e) => setDrugId(e.target.value)} required className={inputCls}>
              <option value="">— antimicrobial —</option>
              {(drugs ?? []).map((d: any) => (
                <option key={d.id} value={d.id}>
                  {d.generic_name}{d.prohibited_in_food_animals ? ' ⛔' : ''}
                </option>
              ))}
            </select>
            <input value={diagnosis} onChange={(e) => setDiagnosis(e.target.value)} required
              placeholder="Diagnosis" className={inputCls} />
            <div className="grid grid-cols-2 gap-3">
              <div>
                <MonoLabel className="text-outline">Dose mg/kg</MonoLabel>
                <input type="number" step="0.5" min={0.5} value={dose}
                  onChange={(e) => setDose(Number(e.target.value))} className={inputCls} />
              </div>
              <div>
                <MonoLabel className="text-outline">Duration days</MonoLabel>
                <input type="number" min={1} max={60} value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))} className={inputCls} />
              </div>
            </div>
            {msg && <p className="rounded-xl bg-surface-container-high p-2.5 text-xs font-medium">{msg}</p>}
            <button type="submit" disabled={create.isPending}
              className="w-full rounded-2xl bg-primary py-3 font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container disabled:opacity-50">
              Issue prescription
            </button>
          </form>
        </Panel>
      </section>
    </div>
  );
}
