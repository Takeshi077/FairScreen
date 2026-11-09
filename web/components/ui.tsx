"use client";

import type { ReactNode } from "react";

import { exportUrl } from "@/lib/api";
import type { Dashboard } from "@/lib/types";
import { useDashboard } from "./DashboardProvider";

type Tone = "good" | "warn" | "bad" | "neutral" | "teal";

const toneClasses: Record<Tone, string> = {
  good: "border-teal/30 bg-teal-soft text-teal-strong dark:text-teal",
  warn: "border-amber/40 bg-amber-soft text-amber dark:text-amber",
  bad: "border-coral/40 bg-coral-soft text-coral",
  neutral: "border-line bg-surface-2 text-muted",
  teal: "border-teal/30 bg-teal-soft text-teal-strong dark:text-teal",
};

const toneSymbols: Record<Tone, string> = {
  good: "OK",
  warn: "!",
  bad: "X",
  neutral: "i",
  teal: "i",
};

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-xl border border-line bg-surface p-5 shadow-[0_1px_0_rgba(255,255,255,0.35)_inset,0_18px_40px_-34px_rgba(15,35,30,0.45)] sm:p-6 ${className}`}
    >
      {children}
    </section>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <header className="mb-7 border-b border-line pb-6">
      <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-teal">
        {eyebrow}
      </p>
      <h1 className="max-w-4xl text-3xl leading-tight text-ink sm:text-4xl lg:text-5xl">
        {title}
      </h1>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-muted sm:text-base">
        {description}
      </p>
      {children ? <div className="mt-5">{children}</div> : null}
    </header>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[0.7rem] font-semibold uppercase tracking-[0.08em] ${toneClasses[tone]}`}
    >
      {children}
    </span>
  );
}

export function StatusChip({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  tone?: Tone;
}) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold ${toneClasses[tone]}`}
    >
      <span
        aria-hidden="true"
        className="inline-flex h-4 min-w-4 items-center justify-center rounded-full border border-current px-1 text-[0.55rem] leading-none"
      >
        {toneSymbols[tone]}
      </span>
      <span className="text-muted">{label}:</span>
      <span>{value}</span>
    </span>
  );
}

export function Metric({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div className="rounded-lg border border-line bg-canvas/50 p-3">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-muted">
        {label}
      </p>
      <p className="mt-1 font-serif text-xl leading-none text-ink">{value}</p>
      {hint ? <p className="mt-1.5 text-xs leading-5 text-muted">{hint}</p> : null}
    </div>
  );
}

export function ChartCard({
  title,
  description,
  sampleSize,
  simulated,
  children,
  footnote,
  actions,
}: {
  title: string;
  description: string;
  sampleSize: number;
  simulated: boolean;
  children: ReactNode;
  footnote?: string;
  actions?: ReactNode;
}) {
  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl leading-tight text-ink">{title}</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">{description}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {simulated ? <Badge tone="warn">Simulated data</Badge> : null}
          <Badge tone="neutral">n = {sampleSize}</Badge>
          {actions}
        </div>
      </div>
      <div className="min-w-0">{children}</div>
      <p className="mt-4 border-t border-line pt-3 text-xs leading-5 text-muted">
        Results apply to this model, prompt and test set.
        {footnote ? ` ${footnote}` : ""}
      </p>
    </Card>
  );
}

export function ModelPicker({
  options,
  value,
  onChange,
  label = "Model",
}: {
  options: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
  label?: string;
}) {
  return (
    <label className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-muted">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="max-w-[16rem] rounded-lg border border-line bg-surface px-3 py-2 text-sm font-medium normal-case tracking-normal text-ink"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function ExportButtons({ runId }: { runId: string }) {
  return (
    <div className="flex flex-wrap gap-2">
      <a
        href={exportUrl(runId, "csv")}
        download
        className="inline-flex items-center rounded-lg bg-teal px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-teal-strong focus-visible:outline-offset-4 dark:text-canvas"
      >
        Download CSV
      </a>
      <a
        href={exportUrl(runId, "markdown")}
        download
        className="inline-flex items-center rounded-lg border border-teal/30 bg-teal-soft px-3.5 py-2 text-sm font-semibold text-teal-strong transition hover:border-teal/60 dark:text-teal"
      >
        Download Markdown
      </a>
    </div>
  );
}

export function LoadingPage({ label = "Loading dashboard" }: { label?: string }) {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-4">
      <div className="skeleton h-10 w-64" />
      <div className="skeleton h-5 w-full max-w-2xl" />
      <div className="grid gap-4 md:grid-cols-3">
        <div className="skeleton h-56" />
        <div className="skeleton h-56" />
        <div className="skeleton h-56" />
      </div>
      <p className="text-sm text-muted">{label}</p>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <Card className="border-coral/40">
      <Badge tone="bad">Connection error</Badge>
      <h2 className="mt-3 text-2xl text-ink">The dashboard could not load.</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{message}</p>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
        Start the API and make sure the demo is seeded, then try again.
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 rounded-lg bg-teal px-4 py-2 text-sm font-semibold text-white hover:bg-teal-strong dark:text-canvas"
      >
        Retry
      </button>
    </Card>
  );
}

export function EmptyState() {
  return (
    <Card>
      <Badge tone="neutral">No run found</Badge>
      <h2 className="mt-3 text-2xl text-ink">Seed the demo to begin.</h2>
      <p className="mt-2 text-sm leading-6 text-muted">
        Run <code className="rounded bg-surface-2 px-1.5 py-0.5">make seed</code> from the
        project root, then reload this page.
      </p>
    </Card>
  );
}

export function DashboardGate({
  children,
}: {
  children: (data: Dashboard) => ReactNode;
}) {
  const { data, loading, error, refresh } = useDashboard();
  if (loading && !data) {
    return <LoadingPage />;
  }
  if (error && !data) {
    return <ErrorState message={error} onRetry={() => void refresh()} />;
  }
  if (!data) {
    return <EmptyState />;
  }
  return <>{children(data)}</>;
}
