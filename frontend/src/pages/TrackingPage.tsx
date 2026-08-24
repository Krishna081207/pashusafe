import { useEffect, useState } from 'react';
import { MapPinned, RotateCcw, Save, TriangleAlert } from 'lucide-react';
import FarmMap from '../components/FarmMap';
import {
  useAlerts,
  useGeofence,
  useLiveTracking,
  useTrackingHistory,
  useUpdateGeofence,
} from '../hooks/queries';
import { MonoLabel, PageBanner, Panel, Spinner } from '../components/badges';

export default function TrackingPage() {
  const { data, isLoading } = useLiveTracking();
  const { data: fenceData } = useGeofence();
  const updateFence = useUpdateGeofence();
  const alerts = useAlerts(15_000);

  // editor state (local until Saved)
  const [center, setCenter] = useState<[number, number] | null>(null);
  const [radius, setRadius] = useState<number>(300);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { data: history } = useTrackingHistory(selectedId ?? undefined, 120);

  useEffect(() => {
    if (!center && fenceData) setCenter([fenceData.center_lat, fenceData.center_lng]);
  }, [fenceData, center]);
  useEffect(() => {
    if (fenceData) setRadius(fenceData.radius_m);
  }, [fenceData?.radius_m]);

  if (isLoading || !data || !fenceData) return <Spinner />;

  const animals = data.animals;
  const breaching = animals.filter((a) => a.breach);
  const breachAlerts = (alerts.data ?? []).filter((a: any) => a.type === 'GEOFENCE_BREACH');

  const dirty =
    center != null &&
    (Math.abs(center[0] - fenceData.center_lat) > 1e-9 ||
      Math.abs(center[1] - fenceData.center_lng) > 1e-9 ||
      radius !== fenceData.radius_m);

  const save = () =>
    center &&
    updateFence.mutate({
      center_lat: Number(center[0].toFixed(6)),
      center_lng: Number(center[1].toFixed(6)),
      radius_m: radius,
      enabled: true,
    });

  return (
    <div className="space-y-6">
      <PageBanner
        accent="secondary"
        eyebrow={<><MapPinned className="h-4 w-4" /><span>LIVE TRACKING | SIMULATED GPS FEED · DEMO-GRADE</span></>}
        title="Where are my animals?"
        subtitle="Positions refresh every few seconds from IoT collars. Set your farm boundary — only you are alerted when an animal steps out."
      />

      {/* breach banner */}
      {breaching.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-error/30 bg-error-container p-4 text-on-error-container shadow-sm">
          <TriangleAlert className="h-6 w-6" />
          <div className="text-sm font-semibold">
            {breaching.map((a) => a.tag_id).join(', ')}{' '}
            {breaching.length === 1 ? 'has' : 'have'} left the safe zone!
          </div>
          <span className="ml-auto font-mono text-[11px] uppercase tracking-wider opacity-80">
            Notified: you only
          </span>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
        {/* map */}
        <Panel tone="lowest" className="p-4">
          <FarmMap
            fence={data.geofence}
            animals={animals}
            center={center ?? [fenceData.center_lat, fenceData.center_lng]}
            radiusM={radius}
            onCenterMoved={(lat, lng) => setCenter([lat, lng])}
            onSelect={(id) => setSelectedId(id === selectedId ? null : id)}
            selectedId={selectedId}
            history={history}
          />

          {/* geofence editor */}
          <div className="mt-4 space-y-3 px-2 pb-1">
            <div className="flex items-center justify-between">
              <MonoLabel className="text-outline">Boundary · drag the pin or use the slider</MonoLabel>
              <span className="font-mono text-xs font-bold tabular-nums text-primary">{radius} m</span>
            </div>
            <input
              type="range" min={50} max={2000} step={10}
              value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
              className="w-full accent-primary"
            />
            <div className="flex gap-2">
              <button
                onClick={save}
                disabled={!dirty || updateFence.isPending}
                className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-on-primary shadow-sm hover:bg-primary-container disabled:opacity-40"
              >
                <Save className="h-3.5 w-3.5" />{updateFence.isPending ? 'Saving…' : 'Save boundary'}
              </button>
              <button
                onClick={() => {
                  setCenter([fenceData.center_lat, fenceData.center_lng]);
                  setRadius(fenceData.radius_m);
                }}
                disabled={!dirty}
                className="flex items-center gap-1.5 rounded-xl bg-surface-container-high px-4 py-2 text-xs font-bold text-on-surface disabled:opacity-40"
              >
                <RotateCcw className="h-3.5 w-3.5" />Reset
              </button>
              {dirty && (
                <span className="self-center font-mono text-[10px] uppercase tracking-widest text-tertiary">
                  unsaved changes — breach checks use the saved boundary
                </span>
              )}
            </div>
          </div>
        </Panel>

        {/* right rail: alerts + herd list */}
        <div className="space-y-6">
          <Panel tone="low" className="p-5">
            <MonoLabel className="text-outline">Boundary alerts · farmer-only</MonoLabel>
            {(breachAlerts as any[]).length === 0 ? (
              <p className="mt-2 text-sm text-on-surface-variant">All animals inside the boundary ✅</p>
            ) : (
              <ul className="mt-2 space-y-2">
                {(breachAlerts as any[]).slice(0, 5).map((a) => (
                  <li key={a.id} className="rounded-xl bg-surface-container-lowest p-3 text-xs">
                    <b>{a.title}</b>
                    <p className="mt-0.5 text-on-surface-variant">{a.message}</p>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel className="p-5">
            <MonoLabel className="text-outline">Herd ({animals.length})</MonoLabel>
            <div className="mt-2 max-h-[320px] space-y-1.5 overflow-y-auto pr-1">
              {animals.map((a) => (
                <button
                  key={a.animal_id}
                  onClick={() => setSelectedId(a.animal_id === selectedId ? null : a.animal_id)}
                  className={`flex w-full items-center gap-3 rounded-xl p-2.5 text-left transition-colors ${
                    a.breach
                      ? 'bg-error-container/70'
                      : a.animal_id === selectedId
                        ? 'bg-secondary-container'
                        : 'hover:bg-surface-container-highest'
                  }`}
                >
                  <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${a.breach ? 'bg-error' : 'bg-primary'}`} />
                  <span className="w-20 shrink-0 font-mono text-xs font-bold">{a.tag_id}</span>
                  <span className="min-w-0 flex-1 truncate text-xs text-on-surface-variant">
                    {a.species}{a.breed ? ` · ${a.breed}` : ''}
                  </span>
                  <span className="shrink-0 font-mono text-[11px] tabular-nums text-outline">
                    {Math.round(a.distance_from_center_m)}m
                  </span>
                </button>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
