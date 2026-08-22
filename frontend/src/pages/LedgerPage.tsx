import { Bomb, GitMerge } from 'lucide-react';
import { useDemoTamper, useLedgerEvents, useLedgerVerify, useMe } from '../hooks/queries';
import { MonoLabel, PageBanner, Spinner } from '../components/badges';

export default function LedgerPage() {
  const { data: verify } = useLedgerVerify();
  const { data: events } = useLedgerEvents();
  const tamper = useDemoTamper();
  const { data: me } = useMe();

  return (
    <div className="w-full space-y-8">
      <PageBanner
        eyebrow={<><GitMerge className="h-4 w-4" /><span>SUPPLY CHAIN | TAMPER-EVIDENT LEDGER</span></>}
        title="Traceability Ledger"
        subtitle="sha256 hash chain · hashₙ = sha256(prev + payload + seq) · every treatment & sale is chained atomically"
        actions={
          <>
            {verify && (
              <span
                className={`rounded-2xl px-4 py-2.5 font-mono text-sm font-bold ${
                  verify.valid
                    ? 'bg-primary-container text-on-primary-container'
                    : 'bg-error-container text-on-error-container'
                }`}
              >
                {verify.valid
                  ? `✓ Chain verified · ${verify.length} blocks`
                  : `✗ TAMPERED at block #${verify.first_invalid_seq}`}
              </span>
            )}
            {me?.role === 'admin' && (
              <button
                onClick={() => tamper.mutate()}
                disabled={tamper.isPending}
                className="flex items-center gap-1.5 rounded-2xl border border-error/30 bg-error-container px-3.5 py-2.5 font-mono text-xs font-bold text-on-error-container transition-colors hover:brightness-95"
                title="Demo: corrupt one payload to show detection"
              >
                <Bomb className="h-4 w-4" /> Demo-tamper
              </button>
            )}
          </>
        }
      />

      {!events ? (
        <Spinner />
      ) : (
        <div className="space-y-2">
          {events.map((e: any) => (
            <div
              key={e.seq}
              className="flex items-start gap-3 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-3.5 font-mono text-xs shadow-sm transition-colors hover:border-primary/40"
            >
              <span className="w-10 shrink-0 rounded-lg bg-primary px-1.5 py-1 text-center font-bold text-on-primary">
                {e.seq}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-secondary-container px-2 py-0.5 font-bold text-on-secondary-container">
                    {e.event_type}
                  </span>
                  <span className="text-outline">
                    {e.recorded_at ? new Date(e.recorded_at).toLocaleString('en-IN') : ''}
                  </span>
                </div>
                <p className="mt-1 truncate text-on-surface-variant" title={e.payload}>
                  {e.payload}
                </p>
                <p className="mt-0.5 truncate text-outline">
                  hash: {e.hash.slice(0, 24)}… ← prev: {e.prev_hash.slice(0, 16)}…
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
