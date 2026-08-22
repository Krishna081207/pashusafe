import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { api, setToken } from '../api/client';
import { MonoLabel } from '../components/badges';

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    password: '',
    farm_name: '',
    village: '',
    district: '',
    state: '',
    pincode: '',
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const res = await api('/auth/register', { method: 'POST', body: JSON.stringify(form) });
      setToken(res.access_token);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setBusy(false);
    }
  };

  const field = (label: string, key: keyof typeof form, type = 'text', required = false) => (
    <div>
      <label className="text-sm font-medium text-on-surface">{label}</label>
      <input
        type={type}
        value={form[key]}
        onChange={set(key)}
        required={required}
        minLength={key === 'password' ? 8 : undefined}
        className="mt-1 w-full rounded-2xl border-none bg-surface-container-high px-4 py-2.5 text-sm outline-none transition-all focus:ring-2 focus:ring-secondary"
      />
    </div>
  );

  return (
    <div className="flex min-h-full items-center justify-center bg-surface p-6">
      <div className="w-full max-w-lg">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary shadow-lg shadow-primary/30">
            <ShieldCheck className="h-7 w-7 text-primary-fixed" />
          </div>
          <h1 className="font-display text-xl font-extrabold tracking-tight text-primary">Register your farm</h1>
          <p className="font-mono text-[11px] uppercase tracking-widest text-on-surface-variant">
            Creates your farmer account + farm profile in one step
          </p>
        </div>

        <form onSubmit={submit} className="grid grid-cols-2 gap-4 rounded-3xl border border-outline-variant/40 bg-surface-container-lowest p-8 shadow-xl">
          {field('Your name', 'full_name', 'text', true)}
          {field('Email', 'email', 'email', true)}
          {field('Phone', 'phone')}
          {field('Password (min 8 chars)', 'password', 'password', true)}
          {field('Farm name', 'farm_name', 'text', true)}
          {field('Village', 'village')}
          {field('District', 'district')}
          {field('State', 'state')}
          {field('PIN code', 'pincode')}
          <div />
          {error && (
            <p className="col-span-2 rounded-xl bg-error-container p-2.5 text-sm font-medium text-on-error-container">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={busy}
            className="col-span-2 rounded-2xl bg-primary py-3 font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container disabled:opacity-50"
          >
            {busy ? 'Creating…' : 'Create account'}
          </button>
        </form>

        <p className="mt-5 text-center text-xs text-on-surface-variant">
          Already registered?{' '}
          <Link to="/login" className="font-semibold text-secondary hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
