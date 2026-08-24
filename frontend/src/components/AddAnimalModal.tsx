import { useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { useAnimals, useCreateAnimal } from '../hooks/queries';
import { MonoLabel } from './badges';

const SPECIES = ['cattle', 'buffalo', 'goat', 'sheep', 'pig', 'poultry'];
const TAG_PREFIX: Record<string, string> = {
  cattle: 'CAT', buffalo: 'BUF', goat: 'GOA',
  sheep: 'SHE', pig: 'PIG', poultry: 'POU',
};

export default function AddAnimalModal({ onClose }: { onClose: () => void }) {
  const { data: animals } = useAnimals();
  const create = useCreateAnimal();

  const [species, setSpecies] = useState('cattle');
  const [breed, setBreed] = useState('');
  const [sex, setSex] = useState('female');
  const [status, setStatus] = useState('lactating');
  const [weight, setWeight] = useState('');
  const [error, setError] = useState('');

  // suggest the next free tag for the chosen species
  const suggestedTag = useMemo(() => {
    const prefix = TAG_PREFIX[species];
    const existing = (animals ?? [])
      .map((a: any) => a.tag_id)
      .filter((t: string) => t.startsWith(`${prefix}-`))
      .map((t: string) => parseInt(t.slice(prefix.length + 1), 10) || 0);
    return `${prefix}-${String(Math.max(0, ...existing) + 1).padStart(3, '0')}`;
  }, [species, animals]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await create.mutateAsync({
        tag_id: suggestedTag,
        species,
        breed: breed || null,
        sex,
        production_status: status,
        weight_kg: weight ? Number(weight) : null,
      });
      onClose();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const inputCls =
    'mt-1 w-full rounded-2xl border-none bg-surface-container-high px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-secondary';

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
      <form
        onSubmit={submit}
        className="w-full max-w-md space-y-4 rounded-3xl border border-outline-variant/40 bg-surface-container-lowest p-6 shadow-2xl"
      >
        <div className="flex items-center justify-between">
          <MonoLabel className="text-outline">Register a new animal</MonoLabel>
          <button type="button" onClick={onClose} className="rounded-full p-1.5 hover:bg-surface-container-high">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-on-surface">Species</label>
            <select value={species} onChange={(e) => setSpecies(e.target.value)} className={inputCls}>
              {SPECIES.map((s) => <option key={s} value={s} className="capitalize">{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-on-surface">Ear tag</label>
            <input value={suggestedTag} readOnly
              className={`${inputCls} font-mono font-bold text-primary`} />
          </div>
          <div>
            <label className="text-sm font-medium text-on-surface">Breed</label>
            <input value={breed} onChange={(e) => setBreed(e.target.value)}
              placeholder="e.g. Gir" className={inputCls} />
          </div>
          <div>
            <label className="text-sm font-medium text-on-surface">Weight (kg)</label>
            <input type="number" min={0} step="0.1" value={weight}
              onChange={(e) => setWeight(e.target.value)} placeholder="optional"
              className={inputCls} />
          </div>
          <div>
            <label className="text-sm font-medium text-on-surface">Sex</label>
            <select value={sex} onChange={(e) => setSex(e.target.value)} className={inputCls}>
              <option value="female">Female</option>
              <option value="male">Male</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-on-surface">Production stage</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)} className={`${inputCls} capitalize`}>
              {['lactating', 'dry', 'laying', 'growing', 'fattening'].map((s) =>
                <option key={s} value={s} className="capitalize">{s}</option>)}
            </select>
          </div>
        </div>

        {error && (
          <p className="rounded-xl bg-error-container p-2.5 text-sm font-medium text-on-error-container">{error}</p>
        )}
        <button type="submit" disabled={create.isPending}
          className="w-full rounded-2xl bg-primary py-3 font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container disabled:opacity-50">
          {create.isPending ? 'Saving…' : `Add ${suggestedTag} to registry`}
        </button>
      </form>
    </div>
  );
}
