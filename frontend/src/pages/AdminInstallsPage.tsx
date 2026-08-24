import { useState } from 'react';
import { CalendarClock, Check, Wrench } from 'lucide-react';
import { useInstallVisits, useUpdateInstallVisit } from '../hooks/queries';
import { MonoLabel, PageBanner, Panel, Spinner, StatCard } from '../components/badges';
import type { InstallVisit } from '../types/models';

function StatusPill({ status }: { status: string }) {
  const style: Record<string, string> = {
    requested: 'bg-tertiary-container text-on-tertiary-container',
    scheduled: 'bg-secondary-container text-on-secondary-container',
    completed: 'bg-primary-container text-on-primary-container',
    cancelled: 'bg-surface-container-high text-on-surface-variant',
  };
  return (
    <span className={`rounded-full px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-wider ${style[status] ?? ''}`}>
      {status}
    </span>
  );
}

/** Inline confirm form for a pending request. */
function ConfirmForm({ visit }: { visit: InstallVisit }) {
  const update = useUpdateInstallVisit();
  const [official, setOfficial] = useState('Kiran Rathod');
  const [phone, setPhone] = useState('+91-9876500011');
  const [when, setWhen] = useState('');
  const [error, setError] = useState('');

  const confirm = async () => {
    setError('');
    if (!when) { setError('Pick a date & time'); return; }
    try {
      // treat the datetime-local input as IST (UTC+5:30)
      await update.mutateAsync({
        id: visit.id,
        status: 'scheduled',
        scheduled_at: new Date(`${when}:00+05:30`).toISOString(),
        official_name: official,
        official_phone: phone,
      });
    } catch (e: any) {
      setError(e.message);
    }
  };

  const inputCls =
    'mt-1 w-full rounded-xl border-none bg-surface-container-high px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-secondary';

  return (
    <div className="mt-3 grid gap-3 rounded-2xl bg-surface-container-lowest p-4 md:grid-cols-4">
      <div>
        <MonoLabel className="text-outline">Official</MonoLabel>
        <input value={official} onChange={(e) => setOfficial(e.target.value)} className={inputCls} />
      </div>
      <div>
        <MonoLabel className="text-outline">Phone</MonoLabel>
        <input value={phone} onChange={(e) => setPhone(e.target.value)} className={inputCls} />
      </div>
      <div>
        <MonoLabel className="text-outline">Final slot (IST)</MonoLabel>
        <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} className={inputCls} />
      </div>
      <div className="flex items-end">
        <button onClick={confirm} disabled={update.isPending}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-primary px-3 py-2.5 text-sm font-semibold text-on-primary shadow-sm hover:bg-primary-container disabled:opacity-50">
          <Check className="h-4 w-4" />{update.isPending ? 'Saving…' : 'Confirm visit'}
        </button>
      </div>
      {error && <p className="md:col-span-4 rounded-xl bg-error-container p-2 text-xs font-medium text-on-error-container">{error}</p>}
    </div>
  );
}

export default function AdminInstallsPage() {
  const { data: visits, isLoading } = useInstallVisits();
  const update = useUpdateInstallVisit();

  if (isLoading) return <Spinner />;
  const list = (visits ?? []) as InstallVisit[];
  const pending = list.filter((v) => v.status === 'requested');
  const upcoming = list.filter((v) => v.status === 'scheduled');
  const done = list.filter((v) => v.status === 'completed' || v.status === 'cancelled');

  return (
    <div className="space-y-6">
      <PageBanner
        eyebrow={<><CalendarClock className="h-4 w-4" /><span>OPS | INSTALLATION QUEUE</span></>}
        title="Sensor installation visits"
        subtitle="Confirm farmer requests by assigning an official and a final slot — the farmer is notified instantly."
      />

      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Pending" value={pending.length} tone="warn" icon={<Wrench className="h-5 w-5" />} />
        <StatCard label="Upcoming" value={upcoming.length} tone="good" icon={<CalendarClock className="h-5 w-5" />} />
        <StatCard label="Closed" value={done.length} />
      </div>

      {/* pending queue */}
      {pending.length > 0 && (
        <Panel className="space-y-3 p-6">
          <MonoLabel className="text-outline">Awaiting confirmation</MonoLabel>
          {pending.map((v) => (
            <div key={v.id} className="rounded-2xl border border-outline-variant/40 bg-surface-container-low p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-bold">{v.farm_name}</p>
                  <p className="font-mono text-[11px] uppercase tracking-wider text-on-surface-variant">
                    prefers {v.preferred_date_display} · {v.preferred_slot}
                  </p>
                </div>
                <StatusPill status={v.status} />
              </div>
              {v.notes && <p className="mt-2 text-xs italic text-on-surface-variant">“{v.notes}”</p>}
              <ConfirmForm visit={v} />
            </div>
          ))}
        </Panel>
      )}

      {/* upcoming */}
      {upcoming.length > 0 && (
        <Panel tone="low" className="p-6">
          <MonoLabel className="text-outline">Scheduled</MonoLabel>
          <div className="mt-2 divide-y divide-outline-variant/30">
            {upcoming.map((v) => (
              <div key={v.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div className="text-sm">
                  <b>{v.farm_name}</b> · {v.scheduled_at_display} · {v.official_name}
                  <span className="block font-mono text-[11px] text-on-surface-variant">{v.official_phone}</span>
                </div>
                <div className="flex items-center gap-2">
                  <StatusPill status={v.status} />
                  <button
                    onClick={() => update.mutate({ id: v.id, status: 'completed' })}
                    className="rounded-lg bg-primary px-2.5 py-1.5 text-[11px] font-bold text-on-primary hover:bg-primary-container"
                  >
                    Mark completed
                  </button>
                  <button
                    onClick={() => update.mutate({ id: v.id, status: 'cancelled', cancel_reason: 'Cancelled by ops' })}
                    className="rounded-lg bg-error-container px-2.5 py-1.5 text-[11px] font-bold text-on-error-container"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {/* closed */}
      {done.length > 0 && (
        <Panel tone="lowest" className="divide-y divide-outline-variant/30 p-2">
          {done.map((v) => (
            <div key={v.id} className="flex items-center justify-between px-4 py-3 text-sm">
              <div>
                <b>{v.farm_name}</b>
                {v.completed_at_display ? ` · completed ${v.completed_at_display}` : ` · requested ${v.preferred_date_display}`}
                {v.cancel_reason && ` · ${v.cancel_reason}`}
              </div>
              <StatusPill status={v.status} />
            </div>
          ))}
        </Panel>
      )}
    </div>
  );
}
