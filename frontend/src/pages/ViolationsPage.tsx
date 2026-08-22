import { ShieldAlert } from 'lucide-react';
import { useViolations } from '../hooks/queries';
import { MonoLabel, PageBanner, Panel, Spinner } from '../components/badges';

export default function ViolationsPage() {
  const { data: violations } = useViolations();

  if (!violations) return <Spinner />;

  return (
    <div className="w-full space-y-8">
      <PageBanner
        accent="error"
        eyebrow={<><ShieldAlert className="h-4 w-4" /><span>ENFORCEMENT | EVIDENCE REGISTER</span></>}
        title={`MRL Violation Register (${violations.length})`}
        subtitle="Every sale recorded while a withdrawal window was active — evidence frozen at record time"
      />

      {violations.length === 0 ? (
        <Panel tone="lowest" className="p-12 text-center text-sm text-outline">
          No violations on record.
        </Panel>
      ) : (
        <Panel className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-outline-variant/30 bg-error-container/40 font-mono text-[11px] uppercase tracking-wider text-on-error-container">
                <th className="px-5 py-3.5">When</th>
                <th className="px-3 py-3.5">Farm</th>
                <th className="px-3 py-3.5">Animal</th>
                <th className="px-3 py-3.5">Product</th>
                <th className="px-3 py-3.5">Linked treatments</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/20">
              {violations.map((v: any) => (
                <tr key={v.sale_event_id} className="transition-colors hover:bg-error-container/30">
                  <td className="px-5 py-4 font-mono text-xs text-on-surface-variant">
                    {v.occurred_at ? new Date(v.occurred_at).toLocaleString('en-IN') : ''}
                  </td>
                  <td className="px-3 py-4 font-mono">#{v.farm_id}</td>
                  <td className="px-3 py-4 font-mono font-bold text-primary">{v.animal_tag ?? '(bulk)'}</td>
                  <td className="px-3 py-4 capitalize">
                    <span className="font-medium">{v.product_type}</span>
                    <p className="font-mono text-xs text-outline">{v.quantity} {v.unit} · {v.buyer_name}</p>
                  </td>
                  <td className="px-3 py-4 font-mono text-xs text-on-surface-variant">
                    {(v.linked_administration_ids ?? []).length
                      ? `adm#${(v.linked_administration_ids ?? []).join(', #adm')}`
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}
    </div>
  );
}
