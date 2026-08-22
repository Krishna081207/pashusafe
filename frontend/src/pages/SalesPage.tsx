import { useState } from 'react';
import { AlertTriangle, ShoppingCart } from 'lucide-react';
import { useAnimals, useMe, useRecordSale, useSales } from '../hooks/queries';
import { MonoLabel, PageBanner, Panel, Spinner } from '../components/badges';

interface SaleWarning {
  warning: boolean;
  message: string;
}

export default function SalesPage() {
  const { data: me } = useMe();
  const { data: animals } = useAnimals();
  const { data: sales } = useSales();
  const record = useRecordSale();

  const [product, setProduct] = useState('milk');
  const [quantity, setQuantity] = useState(10);
  const [animalId, setAnimalId] = useState<string>('');
  const [buyer, setBuyer] = useState('Local Society');
  const [buyerType, setBuyerType] = useState('local_dairy');
  const [ack, setAck] = useState(false);
  const [pendingWarning, setPendingWarning] = useState<SaleWarning | null>(null);
  const [result, setResult] = useState('');

  const inputCls =
    'mt-1 w-full rounded-2xl border-none bg-surface-container-high px-4 py-2.5 text-sm outline-none transition-all focus:ring-2 focus:ring-secondary';

  const submit = async (acknowledge = false) => {
    setPendingWarning(null);
    setResult('');
    try {
      const res = await record.mutateAsync({
        product_type: product,
        quantity,
        animal_id: animalId ? Number(animalId) : null,
        buyer_name: buyer,
        buyer_type: buyerType,
        acknowledge_warning: acknowledge,
      });
      if (res.warning) {
        setPendingWarning(res);
        setAck(false);
      } else {
        setResult(
          res.is_violation
            ? '🚨 Recorded as an MRL VIOLATION. Regulators and the ledger have been notified.'
            : '✅ Sale recorded — compliant.'
        );
      }
    } catch (e: any) {
      setResult(`Error: ${e.message}`);
    }
  };

  if (!me || !animals) return <Spinner />;

  return (
    <div className="grid gap-8 lg:grid-cols-12">
      <section className="space-y-6 lg:col-span-5">
        <PageBanner
          eyebrow={<><ShoppingCart className="h-4 w-4" /><span>SALES LOG | MILK COLLECTION</span></>}
          title="Record sale"
          subtitle="The engine checks active withdrawal windows before accepting."
        />

        <Panel className="space-y-4 p-6">
          <div>
            <MonoLabel className="text-outline">Product</MonoLabel>
            <select value={product} onChange={(e) => setProduct(e.target.value)} className={inputCls}>
              <option value="milk">Milk</option>
              <option value="eggs">Eggs</option>
              <option value="meat">Meat</option>
              <option value="live_animal">Live animal (slaughter-bound)</option>
            </select>
          </div>
          <div>
            <MonoLabel className="text-outline">Animal · blank for bulk collection</MonoLabel>
            <select value={animalId} onChange={(e) => setAnimalId(e.target.value)} className={inputCls}>
              <option value="">— bulk (whole farm) —</option>
              {animals.map((a: any) => (
                <option key={a.id} value={a.id}>{a.tag_id} · {a.species}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <MonoLabel className="text-outline">Quantity</MonoLabel>
              <input type="number" min={0.1} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} className={inputCls} />
            </div>
            <div>
              <MonoLabel className="text-outline">Buyer type</MonoLabel>
              <select value={buyerType} onChange={(e) => setBuyerType(e.target.value)} className={inputCls}>
                <option value="local_dairy">Local dairy / society</option>
                <option value="mandi">Mandi</option>
                <option value="processor">Processor</option>
                <option value="individual">Individual</option>
              </select>
            </div>
          </div>
          <div>
            <MonoLabel className="text-outline">Buyer name</MonoLabel>
            <input value={buyer} onChange={(e) => setBuyer(e.target.value)} className={inputCls} />
          </div>

          <button
            onClick={() => submit(false)}
            disabled={record.isPending}
            className="w-full rounded-2xl bg-primary py-3 font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container disabled:opacity-50"
          >
            {record.isPending ? 'Recording…' : 'Record sale →'}
          </button>

          {pendingWarning && (
            <div className="rounded-2xl border-2 border-error bg-error-container p-4">
              <p className="flex items-center gap-1.5 font-bold text-on-error-container">
                <AlertTriangle className="h-4 w-4" /> Withdrawal active!
              </p>
              <p className="mt-1 text-sm text-on-error-container/90">{pendingWarning.message}</p>
              <label className="mt-3 flex items-start gap-2 text-sm text-on-error-container">
                <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} className="mt-0.5" />
                I understand this will be logged as an <b>MRL violation</b>
              </label>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => submit(true)}
                  disabled={!ack}
                  className="flex-1 rounded-xl bg-error px-4 py-2 text-sm font-bold text-on-error disabled:opacity-40"
                >
                  Confirm anyway
                </button>
                <button onClick={() => setPendingWarning(null)} className="rounded-xl border border-outline-variant/50 px-4 py-2 text-sm font-medium">
                  Cancel
                </button>
              </div>
            </div>
          )}

          {result && (
            <p className={`rounded-2xl p-3.5 text-sm font-medium ${
              result.includes('🚨')
                ? 'bg-error-container text-on-error-container'
                : 'bg-primary-container text-on-primary-container'
            }`}>
              {result}
            </p>
          )}
        </Panel>
      </section>

      <section className="lg:col-span-7">
        <MonoLabel className="mb-3 block text-outline">Recent sales</MonoLabel>
        <Panel className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-outline-variant/30 font-mono text-[11px] uppercase tracking-wider text-on-surface-variant">
                <th className="px-5 py-3.5">When</th>
                <th className="px-3 py-3.5">Product</th>
                <th className="px-3 py-3.5">Animal</th>
                <th className="px-3 py-3.5">Verdict</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/20">
              {(sales ?? []).slice(0, 15).map((s: any) => (
                <tr key={s.id} className={`transition-colors hover:bg-surface-container-high ${s.is_violation ? 'bg-error-container/40' : ''}`}>
                  <td className="px-5 py-3.5 font-mono text-xs text-on-surface-variant">
                    {s.occurred_at ? new Date(s.occurred_at).toLocaleDateString('en-IN') : ''}
                  </td>
                  <td className="px-3 py-3.5 capitalize">
                    <span className="font-medium">{s.product_type}</span>
                    <p className="font-mono text-xs text-outline">{s.quantity} {s.unit}</p>
                  </td>
                  <td className="px-3 py-3.5 font-mono text-xs">{s.animal_tag ?? 'bulk'}</td>
                  <td className="px-3 py-3.5">
                    {s.is_violation ? (
                      <span className="rounded-full bg-error-container px-2.5 py-1 font-mono text-[11px] font-bold text-on-error-container">VIOLATION</span>
                    ) : s.was_under_withdrawal ? (
                      <span className="font-mono text-xs text-tertiary">warned</span>
                    ) : (
                      <span className="font-mono text-xs text-primary">ok</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </section>
    </div>
  );
}
