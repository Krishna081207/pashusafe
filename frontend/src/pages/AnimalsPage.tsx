import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ExternalLink, PawPrint, Plus, QrCode, Search } from 'lucide-react';
import QRCode from 'react-qr-code';
import { useAnimals, useFarmStatus, useMe } from '../hooks/queries';
import { MonoLabel, OverallBadge, PageBanner, Panel, Spinner } from '../components/badges';
import QrModal from '../components/QrModal';
import AddAnimalModal from '../components/AddAnimalModal';

export default function AnimalsPage() {
  const { data: animals } = useAnimals();
  const { data: me } = useMe();
  const { data: status } = useFarmStatus(me?.farm_id);
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [speciesFilter, setSpeciesFilter] = useState('ALL');
  const [qrAnimal, setQrAnimal] = useState<any | null>(null);
  const [adding, setAdding] = useState(false);
  const canAddAnimal = me?.role === 'farmer' || me?.role === 'admin';

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
          <>
            <div className="relative">
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface-variant" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search tag IDs…"
                className="w-56 rounded-full border-none bg-surface-container-high py-2.5 pl-10 pr-4 text-sm outline-none transition-all placeholder:text-outline focus:ring-2 focus:ring-secondary"
              />
            </div>
            {canAddAnimal && (
              <button
                onClick={() => setAdding(true)}
                className="flex items-center gap-1.5 rounded-full bg-primary px-4 py-2.5 text-sm font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container"
              >
                <Plus className="h-4 w-4" /> Add Animal
              </button>
            )}
          </>
        }
      />

      {/* friendly empty state instead of a bare table */}
      {animals.length === 0 && (
        <Panel tone="lowest" className="p-12 text-center">
          <PawPrint className="mx-auto h-10 w-10 text-outline-variant" />
          <h3 className="mt-3 font-display text-lg font-bold text-on-surface">No animals in your registry yet</h3>
          <p className="mx-auto mt-1 max-w-md text-sm text-on-surface-variant">
            {canAddAnimal
              ? 'Add your first animal to start tracking treatments, withdrawal clocks and live location.'
              : 'This farm has not registered any animals yet.'}
          </p>
          {canAddAnimal && (
            <button
              onClick={() => setAdding(true)}
              className="mt-5 inline-flex items-center gap-1.5 rounded-2xl bg-primary px-5 py-2.5 text-sm font-semibold text-on-primary shadow-md hover:bg-primary-container"
            >
              <Plus className="h-4 w-4" /> Add your first animal
            </button>
          )}
        </Panel>
      )}

      {/* species filter tabs */}
      {animals.length > 0 && (
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
      )}

      <Panel className={`overflow-x-auto p-0 ${animals.length === 0 ? 'hidden' : ''}`}>
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

      {adding && <AddAnimalModal onClose={() => setAdding(false)} />}
    </div>
  );
}
