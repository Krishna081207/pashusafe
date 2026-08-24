import { useState } from 'react';
import { CalendarClock, Phone, UserCheck, Wrench } from 'lucide-react';
import { useCancelInstallVisit, useInstallVisits, useRequestInstallVisit } from '../hooks/queries';
import { MonoLabel, PageBanner, Panel, Spinner } from '../components/badges';
import type { InstallVisit } from '../types/models';

const STATUS_STYLE: Record<string, string> = {
  requested: 'bg-tertiary-container text-on-tertiary-container',
  scheduled: 'bg-secondary-container text-on-secondary-container',
  completed: 'bg-primary-container text-on-primary-container',
  cancelled: 'bg-surface-container-high text-on-surface-variant',
};

function StatusPill({ status }: { status: string }) {
  return (
    <span className={`rounded-full px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-wider ${STATUS_STYLE[status] ?? ''}`}>
      {status}
    </span>
  );
}

export default function InstallVisitPage() {
  const { data: visits, isLoading } = useInstallVisits();
  const request = useRequestInstallVisit();
  const cancel = useCancelInstallVisit();

  const [date, setDate] = useState('');
  const [slot, setSlot] = useState('morning');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');

  if (isLoading) return <Spinner />;
  const list = (visits ?? []) as InstallVisit[];
  const open = list.find((v) => v.status === 'requested' || v.status === 'scheduled');
  const history = list.filter((v) => v.id !== open?.id);
  const today = new Date().toISOString().slice(0, 10);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await request.mutateAsync({ preferred_date: date, preferred_slot: slot, notes: notes || undefined });
      setDate(''); setNotes('');
    } catch (err: any) {
      setError(err.message);
    }
  };

  const inputCls =
    'mt-1 w-full rounded-2xl border-none bg-surface-container-high px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-secondary';

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <PageBanner
        accent="secondary"
        eyebrow={<><Wrench className="h-4 w-4" /><span>SENSOR INSTALLATION | MY FARM</span></>}
        title="IoT sensor installation"
        subtitle="An installation official visits your farm to fit health collars and GPS sensors on your animals."
      />

      {/* current status */}
      {open && (
        <Panel className="p-6">
          <div className="flex items-center justify-between">
            <MonoLabel className="text-outline">Current request</MonoLabel>
            <StatusPill status={open.status} />
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div>
              <MonoLabel className="text-outline">Preferred</MonoLabel>
              <p className="mt-1 text-sm font-semibold">
                {open.preferred_date_display} · <span className="capitalize">{open.preferred_slot}</span>
              </p>
            </div>
            {open.status === 'scheduled' && (
              <>
                <div>
                  <MonoLabel className="text-outline">Confirmed slot</MonoLabel>
                  <p className="mt-1 flex items-center gap-1.5 text-sm font-semibold">
                    <CalendarClock className="h-4 w-4 text-secondary" />
                    {open.scheduled_at_display}
                  </p>
                </div>
                <div>
                  <MonoLabel className="text-outline">Installation official</MonoLabel>
                  <p className="mt-1 flex items-center gap-1.5 text-sm font-semibold">
                    <UserCheck className="h-4 w-4 text-secondary" />{open.official_name}
                  </p>
                  <p className="flex items-center gap-1.5 font-mono text-xs text-on-surface-variant">
                    <Phone className="h-3 w-3" />{open.official_phone}
                  </p>
                </div>
              </>
            )}
          </div>
          {open.notes && (
            <p className="mt-4 rounded-xl bg-surface-container-high p-3 text-xs text-on-surface-variant">
              Your note: {open.notes}
            </p>
          )}
          <button
            onClick={() => cancel.mutate({ id: open.id })}
            disabled={cancel.isPending}
            className="mt-4 rounded-xl border border-error/30 bg-error-container px-3 py-1.5 text-xs font-bold text-on-error-container transition-opacity hover:opacity-80"
          >
            Cancel this request
          </button>
        </Panel>
      )}

      {/* new request form */}
      {!open && (
        <Panel tone="lowest" className="p-6">
          <form onSubmit={submit} className="space-y-4">
            <MonoLabel className="text-outline">Request an installation visit</MonoLabel>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-on-surface">Preferred date</label>
                <input type="date" min={today} value={date} required
                  onChange={(e) => setDate(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className="text-sm font-medium text-on-surface">Time of day</label>
                <div className="mt-1 flex gap-2">
                  {['morning', 'afternoon', 'evening'].map((s) => (
                    <button key={s} type="button" onClick={() => setSlot(s)}
                      className={`flex-1 rounded-xl px-2 py-2.5 text-xs font-bold capitalize ${
                        slot === s ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface-variant'
                      }`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-on-surface">Notes for the official</label>
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2}
                placeholder="e.g. gate code, parking, how many sheds…"
                className={`${inputCls} resize-none`} />
            </div>
            {error && (
              <p className="rounded-xl bg-error-container p-2.5 text-sm font-medium text-on-error-container">{error}</p>
            )}
            <button type="submit" disabled={!date || request.isPending}
              className="w-full rounded-2xl bg-primary py-3 font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container disabled:opacity-50">
              {request.isPending ? 'Sending…' : 'Request visit'}
            </button>
          </form>
        </Panel>
      )}

      {/* history */}
      {history.length > 0 && (
        <Panel tone="low" className="divide-y divide-outline-variant/30 p-2">
          {history.map((v) => (
            <div key={v.id} className="flex items-center justify-between px-4 py-3">
              <div className="text-sm">
                <span className="font-semibold">{v.preferred_date_display}</span>
                {v.scheduled_at_display && <span className="text-on-surface-variant"> · confirmed {v.scheduled_at_display}</span>}
                {v.cancel_reason && <span className="text-on-surface-variant"> · {v.cancel_reason}</span>}
              </div>
              <StatusPill status={v.status} />
            </div>
          ))}
        </Panel>
      )}

      <p className="text-center font-mono text-[10px] uppercase tracking-widest text-outline">
        Demo-grade scheduling — visits are handled by the PashuSafe ops team
      </p>
    </div>
  );
}
