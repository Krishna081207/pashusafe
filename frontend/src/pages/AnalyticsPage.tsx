import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Download, TrendingUp } from 'lucide-react';
import { useAmuAnalytics, useSalesAnalytics } from '../hooks/queries';
import {
  AwareBadge,
  MonoLabel,
  PageBanner,
  Panel,
  Spinner,
  StatCard,
} from '../components/badges';

const AWARE_COLORS: Record<string, string> = {
  Access: '#003527',
  Watch: '#6b342d',
  Reserve: '#ba1a1a',
};

export default function AnalyticsPage() {
  const { data } = useAmuAnalytics();
  const { data: sales } = useSalesAnalytics();

  if (!data) return <Spinner />;

  const awareData = data.aware_breakdown.map((b: any) => ({
    name: b.aware_class,
    value: b.count,
    share: b.share,
  }));

  return (
    <div className="w-full space-y-8">
      <PageBanner
        eyebrow={<><TrendingUp className="h-4 w-4" /><span>AMR SURVEILLANCE | STEWARDSHIP ANALYTICS</span></>}
        title="AMU Analytics"
        subtitle="WHO AWaRe mix · drug leaderboard · monthly trend · product-sales compliance"
      />

      {/* ---------- AMU section ---------- */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        <Panel tone="low" className="p-6 md:p-8 lg:col-span-4">
          <MonoLabel className="text-outline">AWaRe classification · 6 months</MonoLabel>
          {awareData.length ? (
            <>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={awareData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85}>
                    {awareData.map((e: any) => (
                      <Cell key={e.name} fill={AWARE_COLORS[e.name] ?? '#707974'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: any, n: any) => [`${v} courses`, n]} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
              <p className="mt-2 text-xs leading-snug text-on-surface-variant">
                Stewardship goal: maximize <b>Access</b>, minimize <b>Watch</b>, eliminate{' '}
                <b>Reserve</b>.
              </p>
            </>
          ) : (
            <p className="py-10 text-center text-sm text-outline">No treatment data.</p>
          )}
        </Panel>

        <Panel tone="low" className="p-6 md:p-8 lg:col-span-8">
          <MonoLabel className="mb-4 block text-outline">Treatments &amp; violations per month</MonoLabel>
          {data.monthly_trend.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.monthly_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e1e3e0" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="#707974" />
                <YAxis tick={{ fontSize: 11 }} stroke="#707974" />
                <Tooltip />
                <Legend />
                <Bar dataKey="treatments" fill="#003527" radius={[6, 6, 0, 0]} />
                <Bar dataKey="violations" fill="#ba1a1a" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="py-10 text-center text-sm text-outline">No history yet.</p>
          )}
        </Panel>

        <Panel className="p-6 md:p-8 lg:col-span-12">
          <div className="mb-3 flex items-center justify-between">
            <MonoLabel className="text-outline">Most-used antimicrobials</MonoLabel>
            <a
              href="/api/v1/analytics/export.csv"
              download
              className="flex items-center gap-1.5 rounded-xl border border-outline-variant/40 bg-surface-container-lowest px-3 py-1.5 text-xs font-semibold text-primary shadow-sm hover:bg-surface-container"
            >
              <Download className="h-3.5 w-3.5" /> Export AMU register (CSV)
            </a>
          </div>
          <ul className="divide-y divide-outline-variant/20 text-sm">
            {data.drug_leaderboard.map((d: any, i: number) => (
              <li key={d.drug_name} className="flex items-center justify-between px-1 py-2.5">
                <span>
                  <span className="mr-2 font-mono text-xs text-outline">{String(i + 1).padStart(2, '0')}</span>
                  <span className="font-medium">{d.drug_name}</span>
                  <span className="ml-2 font-mono text-xs text-outline">{d.drug_class}</span>
                </span>
                <span className="flex items-center gap-3">
                  <AwareBadge aware={d.aware_class} />
                  <span className="font-mono font-bold tabular-nums text-on-surface">{d.uses}</span>
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      {/* ---------- product sales ---------- */}
      {sales && (
        <section className="space-y-5 pt-2">
          <h2 className="font-display text-xl font-extrabold text-on-surface">🛒 Animal-Product Sales</h2>

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Revenue 6 mo" value={`₹${(sales.revenue_total_inr / 1000).toFixed(1)}k`} />
            <StatCard
              label="Clean Sales"
              value={sales.compliance.clean_sales}
              tone="good"
              sub={`${sales.compliance.clean_sales + sales.compliance.violating_sales} recorded`}
              to="/sales"
            />
            <StatCard
              label="Violating Sales"
              value={sales.compliance.violating_sales}
              tone={sales.compliance.violating_sales > 0 ? 'danger' : 'good'}
              to="/violations"
            />
            <StatCard
              label="Safe-Sale Rate"
              value={`${
                sales.compliance.clean_sales + sales.compliance.violating_sales > 0
                  ? Math.round(
                      (100 * sales.compliance.clean_sales) /
                        (sales.compliance.clean_sales + sales.compliance.violating_sales)
                    )
                  : 100
              }%`}
              tone={
                sales.compliance.violating_sales === 0 ||
                sales.compliance.clean_sales / Math.max(1, sales.compliance.clean_sales + sales.compliance.violating_sales) > 0.9
                  ? 'good'
                  : 'warn'
              }
            />
          </div>

          <div className="grid gap-8 lg:grid-cols-12">
            <Panel tone="low" className="p-6 md:p-8 lg:col-span-8">
              <MonoLabel className="mb-4 block text-outline">Volumes by month · milk (L), eggs (trays)</MonoLabel>
              {sales.monthly.length ? (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={sales.monthly}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e1e3e0" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="#707974" />
                    <YAxis tick={{ fontSize: 11 }} stroke="#707974" />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="milk_litres" name="Milk (L)" fill="#006780" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="eggs_trays" name="Eggs (trays)" fill="#6b342d" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-10 text-center text-sm text-outline">No sales in this window.</p>
              )}
            </Panel>

            <Panel tone="low" className="p-6 md:p-8 lg:col-span-4">
              <MonoLabel className="mb-2 block text-outline">Sale compliance split</MonoLabel>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Clean', value: sales.compliance.clean_sales },
                      { name: 'Violating', value: sales.compliance.violating_sales },
                    ]}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={50}
                    outerRadius={80}
                  >
                    <Cell fill="#003527" />
                    <Cell fill="#ba1a1a" />
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
              <p className="text-center text-xs leading-snug text-on-surface-variant">
                Every violating sale was frozen as evidence at record time and chained to the ledger.
              </p>
            </Panel>
          </div>

          {sales.monthly.some((m: any) => m.revenue_inr > 0) && (
            <Panel tone="low" className="p-6 md:p-8">
              <MonoLabel className="mb-4 block text-outline">Sales revenue per month (₹)</MonoLabel>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={sales.monthly}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e1e3e0" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="#707974" />
                  <YAxis tick={{ fontSize: 11 }} stroke="#707974" />
                  <Tooltip formatter={(v: any) => `₹${Number(v).toLocaleString('en-IN')}`} />
                  <Line type="monotone" dataKey="revenue_inr" name="Revenue" stroke="#003527" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </Panel>
          )}

          <a
            href="/api/v1/analytics/report/monthly"
            target="_blank"
            rel="noreferrer"
            className="inline-block rounded-xl border border-outline-variant/40 bg-surface-container-lowest px-4 py-2 text-sm font-semibold shadow-sm hover:bg-surface-container"
          >
            Open printable monthly report (JSON) →
          </a>
        </section>
      )}
    </div>
  );
}
