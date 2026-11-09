"use client";

import { useMemo, useState } from "react";

import { GapWhiskerChart, type WhiskerDatum } from "@/components/charts";
import { PairInspectorModal } from "@/components/PairInspectorModal";
import {
  Badge,
  Card,
  ChartCard,
  DashboardGate,
  Metric,
  ModelPicker,
  PageHeader,
} from "@/components/ui";
import { fmt, signed } from "@/lib/format";
import type { AuditRow, Dashboard } from "@/lib/types";

function GapsContent({ data }: { data: Dashboard }) {
  const models = data.verdict.models.map((model) => ({
    value: model.model,
    label: model.display_name,
  }));
  const [model, setModel] = useState(models[0]?.value ?? "");
  const [inspectPair, setInspectPair] = useState<AuditRow | null>(null);
  const selected = models.some((item) => item.value === model)
    ? model
    : (models[0]?.value ?? "");

  const rows = useMemo(
    () =>
      data.audits
        .filter((row) => row.model === selected && row.mitigation === "none")
        .sort((a, b) => Math.abs(b.mean_gap) - Math.abs(a.mean_gap)),
    [data.audits, selected],
  );

  const chartData: WhiskerDatum[] = rows.map((row) => ({
    label: row.comparison_label,
    gap: row.mean_gap,
    error: [row.mean_gap - row.ci_low, row.ci_high - row.mean_gap],
    low: row.ci_low,
    high: row.ci_high,
    significant: row.significant,
    n: row.n_pairs,
  }));
  const significant = rows.filter((row) => row.significant);
  const maxSample = rows.reduce((max, row) => Math.max(max, row.n_pairs), 0);
  const noiseFloor = rows.reduce((max, row) => Math.max(max, row.noise_floor), 0);

  return (
    <>
      <PageHeader
        eyebrow="Gap by group"
        title="Which comparisons move the score?"
        description="Each dot is a paired mean gap. The whisker is a 95 percent bootstrap confidence interval. Positive values mean the first group scores higher."
      >
        <div className="flex flex-wrap items-center gap-3">
          <ModelPicker options={models} value={selected} onChange={setModel} />
          <Badge tone="neutral">Baseline scores</Badge>
          <Badge tone="neutral">{rows.length} comparisons</Badge>
        </div>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[1.75fr_1fr]">
        <ChartCard
          title="Paired mean gaps with 95 percent confidence intervals"
          description="A comparison is flagged when the interval excludes zero. Hover a point for the interval and sample size."
          sampleSize={maxSample}
          simulated={data.run.is_simulated}
          footnote="Red dots are outside the 95 percent interval. Teal dots include zero."
        >
          <GapWhiskerChart data={chartData} />
        </ChartCard>

        <div className="space-y-4">
          <Card>
            <h2 className="text-xl leading-tight text-ink">Reading the result</h2>
            <div className="mt-3 space-y-2 text-sm leading-6 text-muted">
              <p>
                <strong className="text-ink">Flagged comparisons:</strong>{" "}
                {significant.length} of {rows.length}.
              </p>
              <p>
                <strong className="text-ink">Repeat noise floor:</strong> {fmt(noiseFloor)} points.
                A single score can move by about this much on repeat runs.
              </p>
              <p>
                <strong className="text-ink">Sample size:</strong> {maxSample} matched pairs per
                comparison. The sample is base CVs, not individual scores.
              </p>
              <p>
                Confidence intervals and p-values cover the mean gap. The noise floor covers a
                single score. They answer different questions.
              </p>
            </div>
          </Card>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
            <Metric
              label="Largest absolute gap"
              value={`${fmt(Math.max(0, ...rows.map((row) => Math.abs(row.mean_gap))))} pts`}
            />
            <Metric
              label="Flagged comparisons"
              value={`${significant.length} / ${rows.length}`}
            />
          </div>
        </div>
      </div>

      <Card className="mt-5 overflow-hidden p-0">
        <div className="border-b border-line p-5">
          <h2 className="text-xl leading-tight text-ink">Comparison table</h2>
          <p className="mt-1 text-sm text-muted">
            Holm-adjusted p-values across all comparisons and models in this mitigation.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[52rem] border-collapse text-left text-sm">
            <thead className="bg-surface-2 text-xs uppercase tracking-[0.08em] text-muted">
              <tr>
                <th className="px-4 py-3 font-semibold">Comparison</th>
                <th className="px-4 py-3 text-right font-semibold">Mean gap</th>
                <th className="px-4 py-3 text-right font-semibold">95 percent CI</th>
                <th className="px-4 py-3 text-right font-semibold">n</th>
                <th className="px-4 py-3 text-right font-semibold">p adjusted</th>
                <th className="px-4 py-3 text-right font-semibold">Effect size</th>
                <th className="px-4 py-3 text-right font-semibold">Noise floor</th>
                <th className="px-4 py-3 font-semibold">Flag</th>
                <th className="px-4 py-3 text-right font-semibold">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-line">
                  <td className="px-4 py-3 font-medium text-ink">{row.comparison_label}</td>
                  <td className="px-4 py-3 text-right text-ink">{signed(row.mean_gap)}</td>
                  <td className="px-4 py-3 text-right text-muted">
                    {signed(row.ci_low)} to {signed(row.ci_high)}
                  </td>
                  <td className="px-4 py-3 text-right text-muted">{row.n_pairs}</td>
                  <td className="px-4 py-3 text-right text-muted">{fmt(row.p_adjusted, 4)}</td>
                  <td className="px-4 py-3 text-right text-muted">{fmt(row.effect_size)}</td>
                  <td className="px-4 py-3 text-right text-muted">{fmt(row.noise_floor)}</td>
                  <td className="px-4 py-3">
                    <Badge tone={row.significant ? "bad" : "good"}>
                      {row.significant ? "Outside CI" : "Inside CI"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => setInspectPair(row)}
                      className="inline-flex items-center gap-1 rounded-md border border-line bg-surface px-2.5 py-1 text-xs font-semibold text-teal hover:border-teal/50 hover:bg-teal-soft/30 transition"
                    >
                      Inspect CVs &rarr;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <PairInspectorModal
        isOpen={inspectPair !== null}
        onClose={() => setInspectPair(null)}
        runId={data.run.id}
        model={inspectPair?.model ?? selected}
        mitigation={inspectPair?.mitigation ?? "none"}
        attribute={inspectPair?.attribute ?? ""}
        groupA={inspectPair?.group_a ?? ""}
        groupB={inspectPair?.group_b ?? ""}
        title={inspectPair ? `${inspectPair.comparison_label} (${inspectPair.model})` : ""}
      />
    </>
  );
}

export default function GapsPage() {
  return <DashboardGate>{(data) => <GapsContent data={data} />}</DashboardGate>;
}
