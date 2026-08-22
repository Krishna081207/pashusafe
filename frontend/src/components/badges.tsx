import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import type { TissueStatus } from '../types/models';

/* ------------------------------------------------------------------ */
/* Shared Material-3 style primitives (Krishinode Sentinel language)   */
/* ------------------------------------------------------------------ */

export function MonoLabel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={`text-[10px] font-mono uppercase tracking-widest font-bold ${className}`}>
      {children}
    </span>
  );
}

/** Big rounded panel used as the base surface for every section. */
export function Panel({
  children,
  className = '',
  tone = 'container',
}: {
  children: React.ReactNode;
  className?: string;
  tone?: 'container' | 'low' | 'lowest';
}) {
  const tones = {
    container: 'bg-surface-container border-outline-variant/40',
    low: 'bg-surface-container-low border-outline-variant/40',
    lowest: 'bg-surface-container-lowest border-outline-variant/40',
  };
  return (
    <div className={`rounded-3xl border shadow-sm ${tones[tone]} ${className}`}>{children}</div>
  );
}

export function OverallBadge({ overall }: { overall: string }) {
  const map: Record<string, string> = {
    WITHDRAWAL_ACTIVE: 'bg-error-container text-on-error-container',
    CLEAR_TODAY: 'bg-secondary-container text-on-secondary-container',
    CLEAR: 'bg-primary-container text-on-primary-container',
  };
  const label: Record<string, string> = {
    WITHDRAWAL_ACTIVE: 'Withdrawal active',
    CLEAR_TODAY: 'Clears today',
    CLEAR: 'Clear',
  };
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-1 text-[11px] font-bold ${map[overall] ?? 'bg-surface-container-high text-on-surface-variant'}`}
    >
      {label[overall] ?? overall}
    </span>
  );
}

export function TissueCountdown({ t }: { t: TissueStatus }) {
  const color =
    t.tissue === 'milk'
      ? 'bg-secondary-container text-on-secondary-container'
      : t.tissue === 'eggs'
        ? 'bg-tertiary-container text-on-tertiary-container'
        : 'bg-error-container text-on-error-container';
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-xl px-2 py-1 text-[11px] font-semibold ${color}`}>
      <span className="capitalize">{t.tissue}</span>
      <span className="font-mono tabular-nums">{t.countdown} left</span>
    </span>
  );
}

export function AwareBadge({ aware }: { aware: string }) {
  const map: Record<string, string> = {
    Access: 'bg-primary-container text-on-primary-container',
    Watch: 'bg-tertiary-container text-on-tertiary-container',
    Reserve: 'bg-error-container text-on-error-container',
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wide ${map[aware] ?? 'bg-surface-container-high text-on-surface-variant'}`}>
      {aware}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    critical: 'bg-error-container text-on-error-container',
    warning: 'bg-tertiary-container text-on-tertiary-container',
    info: 'bg-secondary-container text-on-secondary-container',
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wide ring-1 ring-inset ${map[severity] ?? ''} ring-black/10`}>
      {severity}
    </span>
  );
}

/** KPI card matching the prototype's h-32 stat tiles. */
export function StatCard({
  label,
  value,
  sub,
  tone = 'default',
  to,
  icon,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  tone?: 'default' | 'danger' | 'warn' | 'good';
  to?: string;
  icon?: React.ReactNode;
}) {
  const tones: Record<string, string> = {
    default: 'bg-surface-container border-outline-variant/40 text-on-surface',
    danger: 'bg-error-container border-error/20 text-on-error-container',
    warn: 'bg-tertiary-container border-tertiary/30 text-on-tertiary-container',
    good: 'bg-primary-container border-primary/20 text-on-primary-container',
  };
  const labelTone =
    tone === 'default' ? 'text-on-surface-variant' : '';
  const inner = (
    <>
      <div className="flex items-start justify-between">
        <MonoLabel className={labelTone || undefined}>{label}</MonoLabel>
        {icon && (
          <span className={tone === 'default' ? 'text-outline' : ''}>{icon}</span>
        )}
        {!icon && to && <ChevronRight className={`w-4 h-4 ${tone === 'default' ? 'text-outline-variant' : 'opacity-60'}`} />}
      </div>
      <div className="mt-auto">
        <span className="text-3xl font-extrabold font-display tabular-nums leading-none">{value}</span>
        {sub && (
          <span className="mt-1 block text-[11px] opacity-80 font-medium">{sub}</span>
        )}
      </div>
    </>
  );
  const cls = `flex h-32 flex-col justify-between rounded-2xl border p-4 shadow-sm transition-shadow hover:shadow-md ${tones[tone]}`;
  if (to) {
    return (
      <Link to={to} className={cls}>
        {inner}
      </Link>
    );
  }
  return <div className={cls}>{inner}</div>;
}

export function RiskBadge({ band, risk }: { band: string; risk: number }) {
  const map: Record<string, string> = {
    low: 'bg-primary-container text-on-primary-container',
    medium: 'bg-tertiary-container text-on-tertiary-container',
    high: 'bg-error-container text-on-error-container',
  };
  return (
    <span className={`rounded-xl px-2 py-0.5 text-xs font-bold font-mono tabular-nums ${map[band] ?? ''}`}>
      {(risk * 100).toFixed(0)}% · {band}
    </span>
  );
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <p className="py-10 text-center font-mono text-sm uppercase tracking-widest text-outline">
      {label}
    </p>
  );
}

/** Page header banner in the prototype's hero style. */
export function PageBanner({
  eyebrow,
  title,
  subtitle,
  actions,
  accent = 'primary',
}: {
  eyebrow: React.ReactNode;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  accent?: 'primary' | 'secondary' | 'tertiary' | 'error';
}) {
  const accents = {
    primary: 'text-primary',
    secondary: 'text-secondary',
    tertiary: 'text-tertiary',
    error: 'text-error',
  };
  return (
    <div className="flex flex-col justify-between gap-6 rounded-3xl border border-outline-variant/40 bg-surface-container p-6 shadow-sm md:flex-row md:items-center md:p-8">
      <div>
        <div className={`mb-1 flex items-center gap-2 font-mono text-xs uppercase tracking-wider ${accents[accent]}`}>
          {eyebrow}
        </div>
        <h1 className="font-display text-2xl font-extrabold tracking-tight text-on-background md:text-3xl">
          {title}
        </h1>
        {subtitle && <p className="mt-1 text-sm text-on-surface-variant">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
    </div>
  );
}
