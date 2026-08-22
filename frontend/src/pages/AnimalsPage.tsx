import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ExternalLink, Plus, PawPrint, QrCode, Search, X } from 'lucide-react';
import QRCode from 'react-qr-code';
import { useAnimals, useCreateAnimal, useFarmStatus, useMe } from '../hooks/queries';
import { MonoLabel, OverallBadge, PageBanner, Panel, Spinner } from '../components/badges';
import QrModal from '../components/QrModal';

const SPECIES = ['cattle', 'buffalo', 'goat', 'sheep', 'pig', 'poultry'];
const SEX = ['female', 'male'];
const PRODUCTION_STATUS = ['dry', 'lactating', 'laying', 'growing', 'fattening'];

function AddAnimalModal({ onClose }: { onClose: () => void }) {
  const createAnimal = useCreateAnimal();
  const [form, setForm] = useState({
    tag_id: '',
    species: 'cattle',
    breed: '',
    sex: 'female',
    production_status: 'lactating',
    weight_kg: '',
  });
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    createAnimal.mutate(
      {
        ...form,
        breed: form.breed || null,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
      },
      {
        onSuccess: () => onClose(),
        onError: (err: any) => setError(err?.message ?? 'Could not add animal'),
      }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-scrim/50 p-4">
      <div className="w-full max-w-md rounded-2xl bg-surface-container-lowest p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-on-surface">Register New Animal</h2>
          <button onClick={onClose} className="rounded-full p-1 hover:bg-surface-container-high">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-semibold text-on-surface-variant">Ear Tag ID *</label>
            <input
              required
              value={form.tag_id}
              onChange={(e) => setForm({ ...form, tag_id: e.target.value })}
              placeholder="e.g. MUR-014"
              className="w-full rounded-xl border border-outline-variant/40 bg-surface px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-secondary"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-on-surface-variant">Species *</label>
              <select
                value={form.species}
                onChange={(e) => setForm({ ...form, species: e.target.value })}
                className="w-full rounded-xl border border-outline-variant/40 bg-surface px-3 py-2 text-sm capitalize outline-none focus:ring-2 focus:ring-secondary"
              >
                {SPECIES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-on-surface-variant">Sex</label>
              <select
                value={form.sex}
                onChange={(e) => setForm({ ...form, sex: e.target.value })}
                className="w-full rounded-xl border border-outline-variant/40 bg-surface px-3 py-2 text-sm capitalize outline-none focus:ring-2 focus:ring-secondary"
              >
                {SEX.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-on-surface-variant">Breed</label>
              <input
                value={form.breed}
                onChange={(e) => setForm({ ...form, breed: e.target.value })}
                placeholder="Optional"
                className="w-full rounded-xl border border-outline-variant/40 bg-surface px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-secondary"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-on-surface-variant">Weight (kg)</label>
              <input
                type="number"
                step="0.1"
                value={form.weight_kg}
                onChange={(e) => setForm({ ...form, weight_kg: e.target.value })}
                placeholder="Optional"
                className="w-full rounded-xl border border-outline-variant/40 bg-surface px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-secondary"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-on-surface-variant">Production Status</label>
            <select
              value={form.production_status}
              onChange={(e) => setForm({ ...form, production_status: e.target.value })}
              className="w-full rounded-xl border border-outline-variant/40 bg-surface px-3 py-2 text-sm capitalize outline-none focus:ring-2 focus:ring-secondary"
            >
              {PRODUCTION_STATUS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          {error && <p className="text-xs font-semibold text-error">{error}</p>}
          <button
            type="submit"
            disabled={createAnimal.isPending}
            className="w-full rounded-xl bg-primary py-2.5 text-sm font-bold text-on-primary shadow-sm transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {createAnimal.isPending ? 'Adding…' : 'Add Animal'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function AnimalsPage() {
  const { data: animals } = useAnimals();
  const { data: me } = useMe();
  const { data: status } = useFarmStatus(me?.farm_id);
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [speciesFilter, setSpeciesFilter] = useState('ALL');
  const [qrAnimal, setQrAnimal] = useState<any | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);

  const complianceByTag = useMemo(() => {
    const map: Record<string, any> = {};
    for (const row of status?.animals ?? []) map[row.tag_id] = row;
    return map;
  }, [status]);

  const speciesOptions = useMemo(
    () => ['ALL', ...Array.from(new Set((animals ?? []).map((a) => a.species)))],
    [animals]
  );

  const filtered = (animals ?? []).filter(
    (a) =>
      (speciesFilter === 'ALL' || a.species === speciesFilter) &&
      a.tag_id.toLowerCase().includes(q.toLowerCase())
  );

  if (!animals) return <Spinner />;

  return (
    <div className="w-full space-y-8">
      <PageBanner
        eyebrow={
          <>
            <PawPrint className="h-4 w-4" />
            <span>LIVESTOCK REGISTRY | DIGITAL PASSPORTS</span>
          </>
        }
        title={`Livestock & Passports (${animals.length})`}
        subtitle="Click any animal tag to inspect its health dossier · click the QR chip for its traceability code."
        actions={
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface-variant" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search tag IDs…"
                className="w-56 rounded-full border-none bg-surface-container-high py-2.5 pl-10 pr-4 text-sm outline-none transition-all placeholder:text-outline focus:ring-2 focus:ring-secondary"
              />
            </div>
            {(me?.role === 'farmer' || me?.role === 'admin') && (
              <button
                onClick={() => setShowAddModal(true)}
                className="flex items-center gap-1.5 rounded-full bg-primary px-4 py-2.5 text-sm font-bold text-on-primary shadow-sm transition-opacity hover:opacity-90"
              >
                <Plus className="h-4 w-4" /> Add Animal
              </button>
            )}
          </div>
        }
      />

      {/* species filter tabs */}
      <div className="flex items-center gap-1 self-start rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-1">
        {speciesOptions.map((sp) => (
          <button
            key={sp}
            onClick={() => setSpeciesFilter(sp)}
            className={`rounded-xl px-3.5 py-1.5 text-xs font-semibold capitalize transition-all ${
              speciesFilter === sp
                ? 'bg-primary text-on-primary shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            {sp}
          </button>
        ))}
      </div>

      <Panel className="overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-outline-variant/30 font-mono text-[11px] uppercase tracking-wider text-on-surface-variant">
              <th className="px-5 py-3.5">Ear Tag ID</th>
              <th className="px-3 py-3.5">Species &amp; Breed</th>
              <th className="px-3 py-3.5">Status</th>
              <th className="px-3 py-3.5">Weight</th>
              <th className="px-3 py-3.5">MRL Compliance</th>
              <th className="px-3 py-3.5 text-right">QR · Passport</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/20">
            {filtered.map((a) => {
              const c = complianceByTag[a.tag_id];
              return (
                <tr
                  key={a.id}
                  className="group cursor-pointer transition-colors hover:bg-surface-container-high"
                  onClick={() => navigate(`/animals/${a.id}`)}
                >
                  <td className="px-5 py-4 font-mono text-xs font-bold text-primary">
                    <span className="flex items-center gap-2">
                      <QrCode className="h-4 w-4 text-outline-variant transition-colors group-hover:text-primary" />
                      {a.tag_id}
                    </span>
                  </td>
                  <td className="px-3 py-4">
                    <span className="block font-semibold capitalize text-on-surface">{a.species}</span>
                    <span className="block text-xs text-on-surface-variant">{a.breed} • {a.weight_kg ?? '—'} kg</span>
                  </td>
                  <td className="px-3 py-4">
                    <span className="inline-flex rounded-full bg-secondary-container px-2.5 py-1 text-[11px] font-bold capitalize text-on-secondary-container">
                      {a.production_status}
                    </span>
                  </td>
                  <td className="px-3 py-4 font-mono tabular-nums text-on-surface-variant">{a.weight_kg ?? '—'} kg</td>
                  <td className="px-3 py-4" onClick={(e) => e.stopPropagation()}>
                    {c ? (
                      <OverallBadge overall={c.overall} />
                    ) : me?.role === 'farmer' ? (
                      <OverallBadge overall="CLEAR" />
                    ) : (
                      <span className="text-xs text-outline">—</span>
                    )}
                  </td>
                  <td className="px-3 py-4" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setQrAnimal(a)}
                        title="Show supply-chain QR"
                        className="rounded-xl border border-outline-variant/30 bg-surface p-1.5 transition-colors hover:border-primary/40"
                      >
                        <QRCode value={`${window.location.origin}/trace/${a.qr_code}`} size={20} />
                      </button>
                      <button
                        onClick={() => navigate(`/animals/${a.id}`)}
                        className="flex items-center gap-1 rounded-xl border border-outline-variant/30 bg-surface px-3 py-1.5 text-xs font-semibold text-primary shadow-sm hover:border-primary/40"
                      >
                        Passport <ExternalLink className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>

      {qrAnimal && (
        <QrModal tagId={qrAnimal.tag_id} qrCode={qrAnimal.qr_code} onClose={() => setQrAnimal(null)} />
      )}
      {showAddModal && <AddAnimalModal onClose={() => setShowAddModal(false)} />}
    </div>
  );
}
