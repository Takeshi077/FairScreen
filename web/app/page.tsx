"use client";

import Link from "next/link";

import {
  Badge,
  Card,
  DashboardGate,
  ExportButtons,
  Metric,
  PageHeader,
  StatusChip,
} from "@/components/ui";
import { useDashboard } from "@/components/DashboardProvider";
import type { VerdictModel } from "@/lib/types";
import { fmt, percent, points, shortRunId, signed } from "@/lib/format";

function fixTone(value: boolean | null) {
  if (value === null) return "neutral" as const;
  return value ? ("good" as const) : ("bad" as const);
}

function ModelVerdictCard({ model }: { model: VerdictModel }) {
  return (
    <Card className="flex h-full flex-col">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.15em] text-teal">
            Model
          </p>
          <h2 className="mt-1 text-2xl leading-tight text-ink">{model.display_name}</h2>
        </div>
        <Badge tone="neutral">{model.chosen_label}</Badge>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <StatusChip
          label="Gap found"
          value={model.gap_found ? "Yes" : "No"}
          tone={model.gap_found ? "bad" : "good"}
        />
        <StatusChip
          label="Fix worked"
          value={model.fix_worked === null ? "Not needed" : model.fix_worked ? "Yes" : "No"}
          tone={fixTone(model.fix_worked)}
        />
        <StatusChip
          label="Quality kept"
          value={model.quality_kept ? "Yes" : "No"}
          tone={model.quality_kept ? "good" : "bad"}
        />
      </div>

      <p className="mt-4 flex-1 text-sm leading-6 text-ink">{model.summary}</p>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <Metric
          label="Largest gap"
          value={`${fmt(model.max_abs_gap)} pts`}
          hint={`${model.sample_size} matched pairs per comparison`}
        />
        <Metric
          label="Mean gap"
          value={`${fmt(model.mean_abs_gap_before)} to ${fmt(model.mean_abs_gap_after)}`}
          hint="Before to after the chosen mitigation"
        />
        <Metric
          label="Accuracy"
          value={`${percent(model.accuracy_baseline)} to ${percent(model.accuracy_after)}`}
          hint={`Drop of ${points(model.accuracy_drop)} / gate ${points(model.accuracy_drop_gate)}`}
        />
        <Metric
          label="Reduction"
          value={model.mean_reduction === null ? "n/a" : `${signed(model.mean_reduction)} pts`}
          hint="Average significant comparison"
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-3 border-t border-line pt-3 text-sm font-semibold">
        <Link href="/gaps" className="text-teal hover:underline">
          See group gaps
        </Link>
        <Link href="/before-after" className="text-teal hover:underline">
          See the fix
        </Link>
        <Link href="/accuracy" className="text-teal hover:underline">
          Check quality
        </Link>
      </div>
    </Card>
  );
}

export default function OverviewPage() {
  const { runs, runId, selectRun } = useDashboard();

  return (
    <DashboardGate>
      {(data) => (
        <>
          <PageHeader
            eyebrow={`Run ${shortRunId(data.run.id)} / ${data.run.name}`}
            title="Same candidate. Same score?"
            description="FairScreen scores matched CV pairs that differ only in a name, name origin, or age signal. It reports the gap that remains after mitigation and whether ranking quality survived."
          >
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={data.run.status === "completed" ? "good" : "warn"}>
                {data.run.status}
              </Badge>
              {data.run.is_simulated ? <Badge tone="warn">Simulated data</Badge> : null}
              <Badge tone="neutral">Provider: {data.run.provider}</Badge>
              <Badge tone="neutral">Seed: {data.run.seed}</Badge>
              <Badge tone="neutral">Repeats: {data.run.repeats}</Badge>
              <Badge tone="neutral">{data.run.variants.toLocaleString()} variants</Badge>
            </div>
          </PageHeader>

          {data.run.is_simulated ? (
            <div className="mb-5 rounded-xl border border-amber/40 bg-amber-soft p-4 text-sm leading-6 text-ink">
              <strong className="font-semibold">Simulated data.</strong> These scores come
              from deterministic mock models, not a live vendor model. The dashboard
              demonstrates the audit method and the fix quality gate. It does not make a
              claim about any real vendor.
            </div>
          ) : null}

          {data.run.status === "running" || data.run.status === "pending" ? (
            <div className="mb-6 rounded-xl border border-teal/40 bg-teal-soft/40 p-5 shadow-sm">
              <div className="flex items-center justify-between gap-3 mb-2">
                <div className="flex items-center gap-2">
                  <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-teal" />
                  <span className="text-sm font-semibold text-ink">
                    Audit In Progress ({data.progress.percent.toFixed(1)}%)
                  </span>
                </div>
                <span className="text-xs text-muted font-mono">
                  {data.progress.completed.toLocaleString()} / {data.progress.total.toLocaleString()} scores
                </span>
              </div>
              <div className="h-2.5 w-full rounded-full bg-surface-2 overflow-hidden">
                <div
                  className="h-full bg-teal transition-all duration-300 rounded-full"
                  style={{ width: `${Math.max(4, Math.min(100, data.progress.percent))}%` }}
                />
              </div>
            </div>
          ) : null}

          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-muted">Report and data:</span>
              <ExportButtons runId={data.run.id} />
            </div>
            {runs.length > 1 && runId ? (
              <label className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-muted">
                Run
                <select
                  value={runId}
                  onChange={(event) => selectRun(event.target.value)}
                  className="max-w-[18rem] rounded-lg border border-line bg-surface px-3 py-2 text-sm font-medium normal-case tracking-normal text-ink"
                >
                  {runs.map((run) => (
                    <option key={run.id} value={run.id}>
                      {run.name} ({shortRunId(run.id)})
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            {data.verdict.models.map((model) => (
              <ModelVerdictCard key={model.model} model={model} />
            ))}
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
            <Card>
              <h2 className="text-xl leading-tight text-ink">What this test covers</h2>
              <div className="mt-4 grid gap-4 text-sm leading-6 text-muted sm:grid-cols-2">
                <div>
                  <p className="font-semibold text-ink">Matched pairs</p>
                  <p>
                    Gender-coded names hold the surname constant. Origin names hold gender
                    constant. Age variants change only graduation year and stated experience.
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-ink">Repeat scoring</p>
                  <p>
                    Every variant is scored {data.run.repeats} times. Repeats provide a
                    noise floor and reduce transient variance in the comparison.
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-ink">Uncertainty</p>
                  <p>
                    Gaps use paired bootstrap confidence intervals, paired permutation tests,
                    Holm correction, and Cohen&apos;s dz.
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-ink">Quality gate</p>
                  <p>
                    Ranking accuracy is checked against known tiers. A fix passes only when
                    accuracy drops by 2 percentage points or less.
                  </p>
                </div>
              </div>
            </Card>
            <Card>
              <h2 className="text-xl leading-tight text-ink">Run facts</h2>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                <Metric label="Base CVs" value={data.run.variants / 10} />
                <Metric label="Variants" value={data.run.variants.toLocaleString()} />
                <Metric label="Scores" value={data.run.scores.toLocaleString()} />
                <Metric label="Audits" value={data.run.audit_count} />
                <Metric label="Models" value={new Set(data.run.models.map((m) => m.model)).size} />
                <Metric label="Mitigations" value={data.run.models.length / (new Set(data.run.models.map((m) => m.model)).size || 1)} />
              </div>
              <p className="mt-4 border-t border-line pt-3 text-xs leading-5 text-muted">
                Shortlist cutoff: {String(data.run.settings.shortlist_cutoff ?? 7)} out of 10.
                Results apply to this model, prompt and test set.
              </p>
            </Card>
          </div>
        </>
      )}
    </DashboardGate>
  );
}
