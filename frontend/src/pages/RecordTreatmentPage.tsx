import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Check, ChevronRight, Syringe } from 'lucide-react';
import { useAnimals, useDrugs, useRecordAdministration } from '../hooks/queries';
import { AwareBadge, MonoLabel, PageBanner, Panel, Spinner } from '../components/badges';

export default function RecordTreatmentPage() {
  const navigate = useNavigate();
  const { data: animals } = useAnimals();
  const { data: drugs } = useDrugs();
  const record = useRecordAdministration();

  const [animalId, setAnimalId] = useState<number | null>(null);
  const [drugId, setDrugId] = useState<number | null>(null);
  const [courseDays, setCourseDays] = useState(5);
  const [doseAmount, setDoseAmount] = useState(7.5);
  const [route, setRoute] = useState('im');
  const [batch, setBatch] = useState('');
  const [error, setError] = useState('');

  const animal = (animals ?? []).find((a) => a.id === animalId);
  const drug = (drugs ?? []).find((d) => d.id === drugId);

  const applicableRule = useMemo(() => {
    if (!drug || !animal) return null;
    return drug.rules.find((r: any) => r.species === animal.species) ?? null;
  }, [drug, animal]);

  const step = animalId == null ? 1 : drugId == null ? 2 : 3;

  const submit = async () => {
    setError('');
    try {
      await record.mutateAsync({
        animal_id: animalId,
        drug_id: drugId,
        course_days: courseDays,
        dose_amount: doseAmount,
        route,
        batch_number: batch || null,
      });
      navigate('/compliance?recorded=1');
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (!animals || !drugs) return <Spinner />;

  const inputCls =
    'mt-1 w-full rounded-2xl border-none bg-surface-container-high px-4 py-2.5 text-sm outline-none transition-all focus:ring-2 focus:ring-secondary';

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <PageBanner
        accent="secondary"
        eyebrow={<><Syringe className="h-4 w-4" /><span>AMU LOG | TREATMENT WIZARD</span></>}
        title="Record antimicrobial treatment"
        subtitle="The MRL engine computes withdrawal clocks automatically on save."
      />

      {/* stepper */}
      <ol className="flex gap-2">
        {['Animal', 'Drug', 'Course'].map((label, i) => (
          <li
            key={label}
            className={`flex flex-1 items-center gap-2 rounded-2xl border px-3 py-2.5 text-xs font-semibold ${
              step > i
                ? 'border-primary/20 bg-primary-container text-on-primary-container'
                : 'border-outline-variant/40 bg-surface-container-lowest text-outline'
            }`}
          >
            {step > i + 1 ? <Check className="h-3.5 w-3.5" /> : <span className="font-mono">{i + 1}</span>}
            {label}
            {step > i && step <= i + 1 && <ChevronRight className="ml-auto h-3.5 w-3.5" />}
          </li>
        ))}
      </ol>

      {/* step 1 */}
      <Panel className="p-6">
        <MonoLabel className="text-outline">1 · Select animal</MonoLabel>
        <select value={animalId ?? ''} onChange={(e) => setAnimalId(Number(e.target.value) || null)} className={inputCls}>
          <option value="">— choose —</option>
          {animals.map((a) => (
            <option key={a.id} value={a.id}>
              {a.tag_id} · {a.species} ({a.production_status})
            </option>
          ))}
        </select>
      </Panel>

      {/* step 2 */}
      {animal && (
        <Panel className="p-6">
          <MonoLabel className="text-outline">2 · Select antimicrobial</MonoLabel>
          <select
            value={drugId ?? ''}
            onChange={(e) => setDrugId(Number(e.target.value) || null)}
            className={inputCls}
          >
            <option value="">— choose —</option>
            {drugs.map((dg: any) => {
              const usable = dg.rules.some((r: any) => r.species === animal.species);
              const banned = dg.prohibited_in_food_animals;
              return (
                <option key={dg.id} value={dg.id} disabled={!usable && !banned}>
                  {dg.generic_name}
                  {banned ? ' — ⛔ PROHIBITED' : usable ? '' : ' (no rule for species)'}
                </option>
              );
            })}
          </select>

          {drug && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <AwareBadge aware={drug.aware_class} />
              <span className="rounded-full bg-surface-container-high px-2.5 py-0.5 font-mono text-[11px] text-on-surface-variant">
                {drug.drug_class}
              </span>
              {drug.prohibited_in_food_animals && (
                <span className="rounded-full bg-error-container px-2.5 py-0.5 font-mono text-[11px] font-bold text-on-error-container">
                  ⛔ banned in food animals
                </span>
              )}
              {applicableRule && (
                <span className="rounded-full bg-secondary-container px-2.5 py-0.5 font-mono text-[11px] font-semibold text-on-secondary-container">
                  WP:{' '}
                  {[
                    applicableRule.withdrawal_milk_days != null && `milk ${applicableRule.withdrawal_milk_days}d`,
                    applicableRule.withdrawal_meat_days != null && `meat ${applicableRule.withdrawal_meat_days}d`,
                    applicableRule.withdrawal_eggs_days != null && `eggs ${applicableRule.withdrawal_eggs_days}d`,
                  ].filter(Boolean).join(' · ')}
                </span>
              )}
            </div>
          )}
        </Panel>
      )}

      {/* step 3 */}
      {drug && animal && (
        <Panel className="p-6">
          <MonoLabel className="text-outline">3 · Course details</MonoLabel>
          <div className="mt-3 grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-on-surface-variant">Course length (days)</label>
              <input type="number" min={1} max={60} value={courseDays}
                onChange={(e) => setCourseDays(Number(e.target.value))} className={inputCls} />
            </div>
            <div>
              <label className="text-sm text-on-surface-variant">Dose (mg/kg)</label>
              <input type="number" step="0.5" min={0.5} value={doseAmount}
                onChange={(e) => setDoseAmount(Number(e.target.value))} className={inputCls} />
            </div>
            <div>
              <label className="text-sm text-on-surface-variant">Route</label>
              <select value={route} onChange={(e) => setRoute(e.target.value)} className={inputCls}>
                {['im', 'iv', 'sc', 'oral', 'intra_mammary', 'in_water'].map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-on-surface-variant">Medicine batch #</label>
              <input value={batch} onChange={(e) => setBatch(e.target.value)} placeholder="optional" className={inputCls} />
            </div>
          </div>

          <p className="mt-4 rounded-2xl bg-secondary-container p-3.5 text-sm font-medium text-on-secondary-container">
            💡 Withdrawal clock starts on the <b>first dose day</b> and ends N full days after the
            last dose — plan sales accordingly.
          </p>

          {error && (
            <p className="mt-3 rounded-2xl bg-error-container p-3 text-sm font-medium text-on-error-container">{error}</p>
          )}
          <button
            onClick={submit}
            disabled={record.isPending}
            className="mt-4 w-full rounded-2xl bg-primary py-3 font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container disabled:opacity-50"
          >
            {record.isPending ? 'Recording…' : 'Record treatment →'}
          </button>
        </Panel>
      )}

      <Link to="/compliance" className="block text-center text-xs font-semibold text-secondary hover:underline">
        View current compliance instead
      </Link>
    </div>
  );
}
