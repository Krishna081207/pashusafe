import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, LogIn } from 'lucide-react';
import { loginForm, setToken } from '../api/client';
import { MonoLabel } from '../components/badges';

const DEMO_ACCOUNTS = [
  { email: 'ravi@demo.in', role: 'Farmer · Gujarat dairy' },
  { email: 'sunita@demo.in', role: 'Farmer · TN poultry' },
  { email: 'dr.priya@demo.in', role: 'Veterinarian' },
  { email: 'inspector@fssai-demo.in', role: 'Regulator · FSSAI' },
  { email: 'admin@demo.in', role: 'Administrator' },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('ravi@demo.in');
  const [password, setPassword] = useState('Demo@1234');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const res = await loginForm(email, password);
      setToken(res.access_token);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-full items-center justify-center bg-surface p-6">
      <div className="w-full max-w-md">
        {/* brand header */}
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary shadow-lg shadow-primary/30">
            <ShieldCheck className="h-8 w-8 text-primary-fixed" />
          </div>
          <h1 className="font-display text-2xl font-extrabold tracking-tight text-primary">PASHUSAFE</h1>
          <p className="font-mono text-[11px] uppercase tracking-widest text-on-surface-variant">
            Livestock AMR &amp; Residue Safety Chain
          </p>
        </div>

        <div className="rounded-3xl border border-outline-variant/40 bg-surface-container-lowest p-8 shadow-xl">
          <MonoLabel className="text-outline">Sign in to your workspace</MonoLabel>
          <form onSubmit={submit} className="mt-4 space-y-4">
            <div>
              <label className="text-sm font-medium text-on-surface">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="mt-1 w-full rounded-2xl border-none bg-surface-container-high px-4 py-2.5 text-sm outline-none transition-all focus:ring-2 focus:ring-secondary"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-on-surface">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="mt-1 w-full rounded-2xl border-none bg-surface-container-high px-4 py-2.5 text-sm outline-none transition-all focus:ring-2 focus:ring-secondary"
              />
            </div>
            {error && (
              <p className="rounded-xl bg-error-container px-3 py-2 text-sm font-medium text-on-error-container">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={busy}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-primary py-3 font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container disabled:opacity-50"
            >
              <LogIn className="h-4 w-4" />
              {busy ? 'Signing in…' : 'Enter Portal'}
            </button>
          </form>

          <div className="mt-6 rounded-2xl border border-outline-variant/40 bg-surface p-4">
            <MonoLabel className="text-primary">Demo accounts · Demo@1234</MonoLabel>
            <div className="mt-2 grid gap-0.5">
              {DEMO_ACCOUNTS.map((d) => (
                <button
                  key={d.email}
                  onClick={() => {
                    setEmail(d.email);
                    setPassword('Demo@1234');
                  }}
                  className={`flex justify-between rounded-xl px-2.5 py-1.5 text-left text-xs transition-colors ${
                    email === d.email ? 'bg-primary-container text-on-primary-container' : 'hover:bg-surface-container-high'
                  }`}
                >
                  <span className="font-mono">{d.email}</span>
                  <span className={email === d.email ? 'text-primary-fixed' : 'text-outline'}>{d.role}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="mt-5 text-center text-xs text-on-surface-variant">
          New farmer?{' '}
          <Link to="/register" className="font-semibold text-secondary hover:underline">
            Register your farm →
          </Link>
        </p>
        <p className="mt-6 text-center font-mono text-[10px] uppercase tracking-widest text-outline">
          Smart India Hackathon · synthetic demo data
        </p>
      </div>
    </div>
  );
}
