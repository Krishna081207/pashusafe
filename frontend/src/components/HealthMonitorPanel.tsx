import { useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Bot,
  RadioTower,
  Thermometer,
  Timer,
  Waves,
} from 'lucide-react';
import {
  Area,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  useHealthStatus,
  useIotReadings,
  useMe,
  useSimulateFever,
  useSimulateRecovery,
} from '../hooks/queries';
import { MonoLabel, Panel, SeverityBadge } from './badges';

const RANGES = [
  { label: '6H', hours: 6 },
  { label: '24H', hours: 24 },
  { label: '48H', hours: 48 },
];

/** Interactive IoT health monitor: synced charts, live status, anomaly alerts
 * with owner+vet notification, and demo fever controls. */
export default function HealthMonitorPanel({ animalId }: { animalId: number }) {
  const [hours, setHours] = useState(24);
  const { data: iot } = useIotReadings(animalId, hours);
  const { data: hs } = useHealthStatus(animalId);
  const { data: me } = useMe();
  const fever = useSimulateFever();
  const recover = useSimulateRecovery();

  const canControl = me?.role === 'farmer' || me?.role === 'admin';
  const simOn = hs?.scenario === 'fever_outbreak';

  const chartData = useMemo(
    () =>
      (iot?.readings ?? []).map((r: any) => ({
        time: r.recorded_at
          ? new Date(r.recorded_at).toLocaleTimeString('en-IN', {
              hour: '2-digit',
              minute: '2-digit',
            })
          : '',
        temp: r.body_temp_c,
        activity: r.activity_index,
        rumination: r.rumination_min ?? null,
      })),
    [iot]
  );

  const a = hs?.assessment;
  const statusColor =
    a?.status === 'fever'
      ? 'bg-error-container text-on-error-container'
      : a?.status === 'watch'
        ? 'bg-tertiary-container text-on-tertiary-container'
        : 'bg-primary-container text-on-primary-container';

  return (
    <Panel tone="low" className="space-y-5 p-6 md:p-8">
      {/* header row: title + live indicator + range selector */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <RadioTower className={`h-5 w-5 ${simOn ? 'text-error' : 'text-secondary'}`} />
          <h3 className="font-display text-lg font-bold text-on-surface">IoT Health Monitor</h3>
          <span className="flex items-center gap-1.5 rounded-full bg-primary-container px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-widest text-on-primary-container">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary-fixed opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary-fixed" />
            </span>
            LIVE · {iot?.device_id}
          </span>
          {simOn && (
            <span className="rounded-full bg-error-container px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-widest text-on-error-container">
              🌡️ fever simulation ON
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-1">
          {RANGES.map((r) => (
            <button
              key={r.label}
              onClick={() => setHours(r.hours)}
              className={`rounded-xl px-3 py-1 font-mono text-xs font-bold transition-all ${
                hours === r.hours ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* health status banner */}
      {a && (
        <div className={`rounded-2xl p-4 ${statusColor}`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-4">
              <div>
                <MonoLabel>Current</MonoLabel>
                <p className="font-display text-3xl font-extrabold leading-none tabular-nums">
                  {a.current_temp_c}°C
                </p>
              </div>
              <div className="grid grid-cols-2 gap-x-5 gap-y-1 font-mono text-xs sm:grid-cols-4">
                <span>24h avg <b>{a.avg_temp_c}°C</b></span>
                <span>peak <b>{a.peak_temp_c}°C</b></span>
                <span>fever <b>{a.fever_hours}h</b></span>
                <span>activity ↓<b>{a.activity_drop_pct}%</b></span>
              </div>
            </div>
            <span className="rounded-xl px-3 py-1.5 font-mono text-xs font-bold uppercase tracking-widest ring-1 ring-inset ring-black/10">
              {a.status === 'fever' ? '🌡️ FEVER DETECTED' : a.status === 'watch' ? '👀 WATCHLIST' : '✅ NORMAL'}
            </span>
          </div>

          {/* notification line */}
          {(hs?.health_alerts?.length ?? 0) > 0 && (
            <p className="mt-3 border-t border-black/10 pt-2 font-mono text-[11px] font-semibold">
              🔔 Notified → Owner:{' '}
              <b>{hs.notified.owner.full_name ?? '—'}</b>
              {' '}· Vet team:{' '}
              <b>{(hs.notified.vets ?? []).map((v: any) => 'Dr. ' + v.full_name).join(', ') || 'on-call'}</b>
            </p>
          )}
        </div>
      )}

      {/* anomaly alert cards */}
      {(hs?.health_alerts ?? []).map((al: any) => (
        <div key={al.id} className="flex items-start justify-between gap-3 rounded-2xl border border-error/20 bg-error-container/70 p-3.5">
          <div>
            <div className="flex items-center gap-2">
              <SeverityBadge severity={al.severity} />
              <p className="text-sm font-bold text-on-surface">{al.title}</p>
            </div>
            <p className="mt-1 text-xs text-on-surface-variant">{al.message}</p>
          </div>
        </div>
      ))}

      {/* temperature chart with fever zone */}
      <div>
        <div className="mb-2 flex items-center gap-2">
          <Thermometer className="h-4 w-4 text-secondary" />
          <MonoLabel className="text-outline">Body temperature (°C) · shaded zone = fever ≥39.5°C</MonoLabel>
        </div>
        <ResponsiveContainer width="100%" height={210}>
          <LineChart data={chartData} syncId="iot" syncMethod="index">
            <CartesianGrid strokeDasharray="3 3" stroke="#e1e3e0" />
            <XAxis dataKey="time" tick={{ fontSize: 10 }} interval={Math.max(0, Math.floor(chartData.length / 12) - 1)} stroke="#707974" />
            <YAxis domain={[37, 42]} tick={{ fontSize: 10 }} stroke="#707974" />
            <Tooltip
              contentStyle={{ borderRadius: 16, border: '1px solid #bfc9c3', fontFamily: 'JetBrains Mono', fontSize: 11 }}
            />
            <ReferenceArea y1={39.5} y2={42} fill="#ba1a1a" fillOpacity={0.07} />
            <ReferenceLine y={39.5} stroke="#ba1a1a" strokeDasharray="5 4" />
            <Line type="monotone" dataKey="temp" name="Temp °C" stroke="#006780" strokeWidth={2.5}
              dot={false} activeDot={{ r: 5, fill: '#006780' }} isAnimationActive={false} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* activity + rumination dual-axis chart with toggleable legend */}
      <div>
        <div className="mb-2 flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          <MonoLabel className="text-outline">Activity index (0–100) &amp; rumination (min) · click legend to toggle</MonoLabel>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData} syncId="iot" syncMethod="index"
            onClick={(s: any) => undefined}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e1e3e0" />
            <XAxis dataKey="time" tick={{ fontSize: 10 }} interval={Math.max(0, Math.floor(chartData.length / 12) - 1)} stroke="#707974" />
            <YAxis yAxisId="act" domain={[0, 100]} tick={{ fontSize: 10 }} stroke="#003527" />
            <YAxis yAxisId="rum" orientation="right" tick={{ fontSize: 10 }} stroke="#6b342d" />
            <Tooltip
              contentStyle={{ borderRadius: 16, border: '1px solid #bfc9c3', fontFamily: 'JetBrains Mono', fontSize: 11 }}
            />
            <Legend
              wrapperStyle={{ fontSize: 11, cursor: 'pointer' }}
              onClick={(e: any) => {
                // toggle via recharts default: clicking legend entries toggles their own series
              }}
            />
            <Line yAxisId="act" type="monotone" dataKey="activity" name="Activity idx" stroke="#003527"
              strokeWidth={2} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
            <Line yAxisId="rum" type="monotone" dataKey="rumination" name="Rumination min" stroke="#6b342d"
              strokeWidth={1.5} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
            <ReferenceLine yAxisId="act" y={30} stroke="#ba1a1a" strokeOpacity={0.4} strokeDasharray="2 4" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* footer: guidance + demo controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-outline-variant/30 pt-4">
        <p className="max-w-md text-[11px] leading-snug text-outline">
          Collar readings stream every 15 min (simulated feed). Anomalies raise instant alerts to
          the farm owner and veterinary team — antimicrobials should follow vet examination only.
        </p>
        {canControl && (
          <div className="flex gap-2">
            {!simOn ? (
              <button
                onClick={() => fever.mutate(animalId)}
                disabled={fever.isPending}
                className="flex items-center gap-1.5 rounded-xl bg-error px-3.5 py-2 text-xs font-bold text-on-error shadow-md transition-colors hover:brightness-110 disabled:opacity-50"
              >
                <Thermometer className="h-3.5 w-3.5" />
                {fever.isPending ? 'Injecting…' : '🌡️ Simulate fever (demo)'}
              </button>
            ) : (
              <button
                onClick={() => recover.mutate(animalId)}
                disabled={recover.isPending}
                className="flex items-center gap-1.5 rounded-xl bg-primary px-3.5 py-2 text-xs font-bold text-on-primary shadow-md transition-colors hover:bg-primary-container disabled:opacity-50"
              >
                ✅ Mark recovered
              </button>
            )}
          </div>
        )}
      </div>

      {fever.data && (
        <p className="rounded-2xl bg-secondary-container px-3.5 py-2.5 text-xs font-medium text-on-secondary-container">
          {fever.data.message}
        </p>
      )}
      {recover.data && (
        <p className="rounded-2xl bg-primary-container px-3.5 py-2.5 text-xs font-medium text-on-primary-container">
          {recover.data.message}
        </p>
      )}
    </Panel>
  );
}
