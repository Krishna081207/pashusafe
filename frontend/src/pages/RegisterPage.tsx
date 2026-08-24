import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Check, ChevronRight, ChevronLeft, ShieldCheck } from 'lucide-react';
import { api, setToken } from '../api/client';
import { MonoLabel } from '../components/badges';

const SPECIES = ['cattle', 'buffalo', 'goat', 'sheep', 'pig', 'poultry'] as const;
const SLOTS = ['morning', 'afternoon', 'evening'] as const;
const STEP_LABELS = ['Account', 'Farm & Location', 'Livestock'];

export default function RegisterPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    full_name: '', email: '', phone: '', password: '',
    farm_name: '', village: '', district: '', state: '', pincode: '',
  });
  const [speciesOwned, setSpeciesOwned] = useState<string[]>([]);
  const [speciesCounts, setSpeciesCounts] = useState<Record<string, number>>({});
  const [mainBreeds, setMainBreeds] = useState('');
  const [visitDate, setVisitDate] = useState('');
  const [visitSlot, setVisitSlot] = useState<string>('morning');

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  const toggleSpecies = (s: string) => {
    const next = speciesOwned.includes(s)
      ? speciesOwned.filter((x) => x !== s)
      : [...speciesOwned, s];
    setSpeciesOwned(next);
    if (!next.includes(s)) {
      const counts = { ...speciesCounts };
      delete counts[s];
      setSpeciesCounts(counts);
    }
  };

  const totalHeads = Object.values(speciesCounts).reduce((a, b) => a + (b || 0), 0);

  const step1Valid = form.full_name.length >= 2 && /.+@.+\..+/.test(form.email) && form.password.length >= 8;
  const step2Valid = form.farm_name.length >= 2;

  const today = new Date().toISOString().slice(0, 10);

  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      const payload: any = { ...form };
      if (speciesOwned.length > 0 || mainBreeds) {
        payload.profile = {
          species_owned: speciesOwned,
          species_counts: speciesCounts,
          main_breeds: mainBreeds || null,
        };
      }
      if (visitDate) {
        payload.install_visit = { preferred_date: visitDate, preferred_slot: visitSlot };
      }
      const res = await api('/auth/register', { method: 'POST', body: JSON.stringify(payload) });
      setToken(res.access_token);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setBusy(false);
    }
  };

  const field = (label: string, key: keyof typeof form, type = 'text', required = false) => (
    <div>
      <label className="text-sm font-medium text-on-surface">{label}</label>
      <input
        type={type}
        value={form[key]}
        onChange={set(key)}
        required={required}
        className="mt-1 w-full rounded-2xl border-none bg-surface-container-high px-4 py-2.5 text-sm outline-none transition-all focus:ring-2 focus:ring-secondary"
      />
    </div>
  );

  return (
    <div className="flex min-h-full items-center justify-center bg-surface p-6">
      <div className="w-full max-w-xl">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary shadow-lg shadow-primary/30">
            <ShieldCheck className="h-7 w-7 text-primary-fixed" />
          </div>
          <h1 className="font-display text-xl font-extrabold tracking-tight text-primary">Register your farm</h1>
          <p className="font-mono text-[11px] uppercase tracking-widest text-on-surface-variant">
            Farmer account · farm profile · livestock details
          </p>
        </div>

        {/* stepper */}
        <ol className="mb-5 flex gap-2">
          {STEP_LABELS.map((label, i) => (
            <li
              key={label}
              className={`flex flex-1 items-center gap-2 rounded-2xl border px-3 py-2.5 text-xs font-semibold ${
                step >= i
                  ? 'border-primary/20 bg-primary-container text-on-primary-container'
                  : 'border-outline-variant/40 bg-surface-container-lowest text-outline'
              }`}
            >
              {step > i ? <Check className="h-3.5 w-3.5" /> : <span className="font-mono">{i + 1}</span>}
              {label}
            </li>
          ))}
        </ol>

        {/* NB: onSubmit only swallows implicit submissions (Enter key); the real
            submit is the Create-account button's onClick. A form-level submit
            path let a mid-click DOM swap register half-filled forms. */}
        <form
          onSubmit={(e) => e.preventDefault()}
          className="space-y-4 rounded-3xl border border-outline-variant/40 bg-surface-container-lowest p-8 shadow-xl"
        >
          {/* ---------------- step 0: account ---------------- */}
          {step === 0 && (
            <>
              <MonoLabel className="text-outline">Who is registering?</MonoLabel>
              <div className="grid grid-cols-2 gap-4">
                {field('Your name', 'full_name', 'text', true)}
                {field('Email', 'email', 'email', true)}
                {field('Phone', 'phone')}
                {field('Password (min 8 chars)', 'password', 'password', true)}
              </div>
            </>
          )}

          {/* ---------------- step 1: farm ---------------- */}
          {step === 1 && (
            <>
              <MonoLabel className="text-outline">Where is the farm?</MonoLabel>
              <div className="grid grid-cols-2 gap-4">
                {field('Farm name', 'farm_name', 'text', true)}
                {field('Village', 'village')}
                {field('District', 'district')}
                {field('State', 'state')}
                {field('PIN code', 'pincode')}
              </div>
            </>
          )}

          {/* ---------------- step 2: livestock + install + review --------- */}
          {step === 2 && (
            <div className="space-y-5">
              <div>
                <MonoLabel className="text-outline">Which animals do you own?</MonoLabel>
                <div className="mt-2 flex flex-wrap gap-2">
                  {SPECIES.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => toggleSpecies(s)}
                      className={`rounded-full px-3 py-1.5 text-xs font-bold capitalize transition-colors ${
                        speciesOwned.includes(s)
                          ? 'bg-primary text-on-primary shadow-sm'
                          : 'bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest'
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
                {speciesOwned.length === 0 ? (
                  <p className="mt-2 rounded-xl bg-tertiary-container/60 px-3 py-2 text-xs font-semibold text-on-tertiary-container">
                    👈 Select at least one species — these animals are created automatically in your registry.
                  </p>
                ) : (
                  <p className="mt-2 text-xs font-medium text-secondary">
                    ✓ We'll create tagged, trackable records for them right after signup.
                  </p>
                )}
              </div>

              {speciesOwned.length > 0 && (
                <div>
                  <MonoLabel className="text-outline">How many of each?</MonoLabel>
                  <div className="mt-2 grid grid-cols-3 gap-3">
                    {speciesOwned.map((s) => (
                      <div key={s}>
                        <label className="text-xs font-semibold capitalize text-on-surface-variant">{s}</label>
                        <input
                          type="number" min={0}
                          value={speciesCounts[s] ?? ''}
                          onChange={(e) =>
                            setSpeciesCounts({ ...speciesCounts, [s]: Number(e.target.value) })}
                          placeholder="0"
                          className="mt-1 w-full rounded-2xl border-none bg-surface-container-high px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-secondary"
                        />
                      </div>
                    ))}
                  </div>
                  {totalHeads > 0 && (
                    <span className="mt-2 inline-block rounded-full bg-secondary-container px-2.5 py-1 font-mono text-[11px] font-bold text-on-secondary-container">
                      Total ≈ {totalHeads} animals
                    </span>
                  )}
                </div>
              )}

              <div>
                <label className="text-sm font-medium text-on-surface">Main breeds</label>
                <input
                  value={mainBreeds}
                  onChange={(e) => setMainBreeds(e.target.value)}
                  placeholder="e.g. Gir, Murrah, Jamunapari"
                  className="mt-1 w-full rounded-2xl border-none bg-surface-container-high px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-secondary"
                />
              </div>

              <div className="rounded-2xl border border-outline-variant/40 bg-surface-container-low p-4">
                <MonoLabel className="text-outline">IoT sensor installation (optional)</MonoLabel>
                <p className="mt-1 text-xs text-on-surface-variant">
                  Pick a preferred day — an official will visit to fit collars/sensors on your animals.
                </p>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-on-surface-variant">Preferred date</label>
                    <input
                      type="date" min={today} value={visitDate}
                      onChange={(e) => setVisitDate(e.target.value)}
                      className="mt-1 w-full rounded-2xl border-none bg-surface-container-high px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-secondary"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-on-surface-variant">Time of day</label>
                    <div className="mt-1 flex gap-1.5">
                      {SLOTS.map((s) => (
                        <button
                          key={s} type="button" onClick={() => setVisitSlot(s)}
                          className={`flex-1 rounded-xl px-2 py-2 text-[11px] font-bold capitalize ${
                            visitSlot === s
                              ? 'bg-primary text-on-primary'
                              : 'bg-surface-container-high text-on-surface-variant'
                          }`}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* review */}
              <div className="rounded-2xl bg-primary-container/60 p-4 text-sm text-on-primary-container">
                <MonoLabel>Review</MonoLabel>
                <p className="mt-1"><b>{form.full_name}</b> · {form.email}{form.phone && ` · ${form.phone}`}</p>
                <p>{form.farm_name}{form.village && `, ${form.village}`}{form.district && `, ${form.district}`}</p>
                <p className="text-xs opacity-90">
                  {totalHeads > 0 && `${totalHeads} animals`}{mainBreeds && ` · ${mainBreeds}`}
                  {!totalHeads && !mainBreeds && 'Livestock details skipped'}
                </p>
              </div>
            </div>
          )}

          {error && (
            <p className="rounded-xl bg-error-container p-2.5 text-sm font-medium text-on-error-container">{error}</p>
          )}

          <div className="flex gap-3 pt-1">
            {step > 0 && (
              <button
                type="button" key="back" onClick={() => setStep(step - 1)}
                className="flex items-center gap-1 rounded-2xl bg-surface-container-high px-5 py-3 font-semibold text-on-surface"
              >
                <ChevronLeft className="h-4 w-4" /> Back
              </button>
            )}
            {step < 2 ? (
              <button
                type="button" key="next"
                disabled={step === 0 ? !step1Valid : !step2Valid}
                onClick={() => setStep(step + 1)}
                className="flex flex-1 items-center justify-center gap-1 rounded-2xl bg-primary py-3 font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container disabled:opacity-50"
              >
                Next <ChevronRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                type="button" key="create" disabled={busy} onClick={submit}
                className="flex-1 rounded-2xl bg-primary py-3 font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container disabled:opacity-50"
              >
                {busy ? 'Creating…' : 'Create account'}
              </button>
            )}
          </div>
        </form>

        <p className="mt-5 text-center text-xs text-on-surface-variant">
          Already registered?{' '}
          <Link to="/login" className="font-semibold text-secondary hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
