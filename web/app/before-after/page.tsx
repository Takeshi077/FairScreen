"use client";

import { useMemo, useState } from "react";

import { BeforeAfterChart, type BeforeAfterDatum } from "@/components/charts";
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

function key(row: AuditRow): string {
  return `${row.attribute}|${row.group_a}|${row.group_b}`;
}

function BeforeAfterContent({ data }: { data: Dashboard }) {
  const models = data.verdict.models.map((model) => ({
    value: model.model,
    label: model.display_name,
  }));
  const [model, setModel] = useState(models[0]?.value ?? "");
  const selected = models.some((item) => item.value === model)
    ? model
    : (models[0]?.value ?? "");
  const verdict = data.verdict.models.find((item) => item.model === selected);

  const { chartData, table, maxSample } = useMemo(() => {
    const baseline = data.audits.filter(
      (row) => row.model === selected && row.mitigation === "none" && row.significant,
    );
    const keys = new Set(baseline.map(key));
    const before = baseline.length
      ? baseline.reduce((sum, row) => sum + Math.abs(row.mean_gap), 0) / baseline.length
      : 0;
    const rows = data.mitigations
      .filter((option) => option.value !== "none")
      .map((option) => {
        const current = data.audits.filter(
          (row) =>
            row.model === selected &&
            row.mitigation === option.value &&
            keys.has(key(row)),
        );
        const after = current.length
          ? current.reduce((sum, row) => sum + Math.abs(row.mean_gap), 0) / current.length
          : before;
        const reductions = current
          .map((row) => row.reduction_vs_baseline)
          .filter((value): value is number => value !== null);
        const meanReduction = reductions.length
          ? reductions.reduce((sum, value) => sum + value, 0) / reductions.length
          : null;
        const supported = current.filter((row) => row.reduction_supported).length;
        return {
          key: option.value,
          label: option.label,
          before,
          after,
          reduction: meanReduction,
          supported,
          total: current.length,
        };
      });
    const max = baseline.reduce((value, row) => Math.max(value, row.n_pairs), 0);
    return {
      chartData: rows.map<BeforeAfterDatum>((row) => ({
        label: row.label,
        before: row.before,
        after: row.after,
      })),
      table: rows,
      maxSample: max,
    };
  }, [data.audits, data.mitigations, selected]);

  const chosen = table.find((row) => row.key === verdict?.chosen_mitigation);

  return (
    <>
      <PageHeader
        eyebrow="Before vs after"
        title="Does the fix close the gap?"
        description="The before bar is the mean absolute gap across significant baseline comparisons. The after bar applies the same comparisons under each mitigation."
      >
        <div className="flex flex-wrap items-center gap-3">
          <ModelPicker options={models} value={selected} onChange={setModel} />
          <Badge tone="neutral">Chosen mitigation: {verdict?.chosen_label ?? "n/a"}</Badge>
        </div>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <ChartCard
          title="Absolute gap before and after each mitigation"
          description="A working fix moves the after bar toward zero while keeping ranking accuracy inside the quality gate."
          sampleSize={maxSample}
          simulated={data.run.is_simulated}
          footnote="Bars use the same baseline-flagged comparisons for an apples-to-apples view."
        >
          <BeforeAfterChart data={chartData} />
        </ChartCard>

        <div className="space-y-4">
          <Card>
            <h2 className="text-xl leading-tight text-ink">Chosen fix</h2>
            {chosen ? (
              <div className="mt-3 space-y-2 text-sm leading-6 text-muted">
                <p className="font-semibold text-ink">{chosen.label}</p>
                <p>
                  Mean absolute gap moved from {fmt(chosen.before)} to {fmt(chosen.after)} points.
                </p>
                <p>
                  Supported reductions: {chosen.supported} of {chosen.total} affected
                  comparisons.
                </p>
                <p>
                  Average reduction:{" "}
                  {chosen.reduction === null ? "n/a" : `${signed(chosen.reduction)} points`}.
                </p>
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted">
                This model has no mitigation selected for the verdict.
              </p>
            )}
          </Card>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
            <Metric
              label="Baseline mean gap"
              value={`${fmt(chosen?.before ?? 0)} pts`}
              hint="Across significant comparisons"
            />
            <Metric
              label="After chosen fix"
              value={`${fmt(chosen?.after ?? 0)} pts`}
              hint="Same comparison set"
            />
          </div>
        </div>
      </div>

      <Card className="mt-5 overflow-hidden p-0">
        <div className="border-b border-line p-5">
          <h2 className="text-xl leading-tight text-ink">Mitigation table</h2>
          <p className="mt-1 text-sm text-muted">
            A reduction is supported when the bootstrap interval for the reduction stays above
            zero.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[42rem] border-collapse text-left text-sm">
            <thead className="bg-surface-2 text-xs uppercase tracking-[0.08em] text-muted">
              <tr>
                <th className="px-4 py-3 font-semibold">Mitigation</th>
                <th className="px-4 py-3 text-right font-semibold">Before</th>
                <th className="px-4 py-3 text-right font-semibold">After</th>
                <th className="px-4 py-3 text-right font-semibold">Mean reduction</th>
                <th className="px-4 py-3 text-right font-semibold">Supported</th>
              </tr>
            </thead>
            <tbody>
              {table.map((row) => (
                <tr key={row.key} className="border-t border-line">
                  <td className="px-4 py-3 font-medium text-ink">
                    {row.label}
                    {row.key === verdict?.chosen_mitigation ? (
                      <span className="ml-2 align-middle">
                        <Badge tone="teal">Chosen</Badge>
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-right text-muted">{fmt(row.before)}</td>
                  <td className="px-4 py-3 text-right text-muted">{fmt(row.after)}</td>
                  <td className="px-4 py-3 text-right text-muted">
                    {row.reduction === null ? "n/a" : signed(row.reduction)}
                  </td>
                  <td className="px-4 py-3 text-right text-muted">
                    {row.supported} / {row.total}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

export default function BeforeAfterPage() {
  return <DashboardGate>{(data) => <BeforeAfterContent data={data} />}</DashboardGate>;
}
