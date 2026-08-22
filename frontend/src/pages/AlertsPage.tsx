import { Bell } from 'lucide-react';
import { useAlerts, useResolveAlert } from '../hooks/queries';
import { MonoLabel, PageBanner, Panel, SeverityBadge, Spinner } from '../components/badges';

export default function AlertsPage() {
  const { data: alerts } = useAlerts();
  const resolve = useResolveAlert();

  if (!alerts) return <Spinner />;

  return (
    <div className="w-full space-y-8">
      <PageBanner
        accent="tertiary"
        eyebrow={<><Bell className="h-4 w-4" /><span>ALERT &amp; NOTIFICATION SYSTEM</span></>}
        title="Alerts"
        subtitle="MRL violations · prohibited drugs · sensor anomalies · clearance reminders"
      />

      {alerts.length === 0 && (
        <Panel tone="lowest" className="p-12 text-center text-sm text-outline">
          No unresolved alerts 🎉
        </Panel>
      )}

      <div className="space-y-3">
        {alerts.map((a: any) => (
          <div
            key={a.id}
            className={`flex items-start justify-between gap-4 rounded-3xl border p-5 shadow-sm ${
              a.severity === 'critical'
                ? 'border-error/20 bg-error-container'
                : a.severity === 'warning'
                  ? 'border-tertiary/20 bg-tertiary-container/60'
                  : 'border-outline-variant/40 bg-surface-container-lowest'
            }`}
          >
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <SeverityBadge severity={a.severity} />
                <MonoLabel className={a.severity === 'critical' ? '' : 'text-outline'}>{a.type}</MonoLabel>
                {!a.resolved && <span className="text-[11px] font-bold text-error">● open</span>}
              </div>
              <p className="mt-2 font-display font-bold text-on-surface">{a.title}</p>
              <p className={`mt-1 text-sm ${a.severity === 'critical' ? 'text-on-error-container/90' : 'text-on-surface-variant'}`}>
                {a.message}
              </p>
            </div>
            <div className="shrink-0 text-right">
              <p className="mb-2 font-mono text-[11px] text-outline">
                {a.created_at ? new Date(a.created_at).toLocaleString('en-IN') : ''}
              </p>
              {!a.resolved && (
                <button
                  onClick={() => resolve.mutate(a.id)}
                  disabled={resolve.isPending}
                  className="rounded-xl border border-outline-variant/50 bg-surface px-3.5 py-1.5 text-xs font-semibold shadow-sm transition-colors hover:bg-surface-container-high disabled:opacity-50"
                >
                  Resolve
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
