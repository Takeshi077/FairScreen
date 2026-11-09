"use client";

import { useMemo, useState } from "react";

import { useDashboard } from "@/components/DashboardProvider";
import { ShortlistChart, type ShortlistDatum } from "@/components/charts";
import {
  Badge,
  Card,
  ChartCard,
  DashboardGate,
  ModelPicker,
  PageHeader,
} from "@/components/ui";
import { fmt, percent } from "@/lib/format";
import type { Dashboard, Mitigation } from "@/lib/types";

function ShortlistContent({ data }: { data: Dashboard }) {
  const models = data.verdict.models.map((model) => ({
    value: model.model,
    label: model.display_name,
  }));
  const [model, setModel] = useState(models[0]?.value ?? "");
  const [mitigation, setMitigation] = useState<Mitigation>("none");
  const selected = models.some((item) => item.value === model)
    ? model
    : (models[0]?.value ?? "");

  const rows = useMemo(
    () =>
      data.shortlist
        .filter(
          (row) =>
            row.model === selected &&
            row.mitigation === mitigation &&
            row.shortlist_ratio !== null,
        )
        .sort((a, b) => (a.shortlist_ratio ?? 0) - (b.shortlist_ratio ?? 0)),
    [data.shortlist, mitigation, selected],
  );

  const allRows = data.shortlist.filter(
    (row) => row.model === selected && row.mitigation === mitigation,
  );
  const chartData: ShortlistDatum[] = rows.map((row) => ({
    label: row.comparison_label,
    ratio: row.shortlist_ratio ?? 0,
    gap: row.rate_a - row.rate_b,
  }));
  const sampleSize = allRows.reduce((max, row) => Math.max(max, row.n_pairs), 0);

  return (
    <>
      <PageHeader
        eyebrow="Shortlist ratio"
        title="Who reaches the cutoff?"
        description="The shortlist rate is the share of group variants with a mean score at or above the cutoff. The ratio divides group A's rate by group B's rate."
      >
        <div className="flex flex-wrap items-center gap-3">
          <ModelPicker options={models} value={selected} onChange={setModel} />
          <label className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-muted">
            Mitigation
            <select
              value={mitigation}
              onChange={(event) => setMitigation(event.target.value as Mitigation)}
              className="max-w-[14rem] rounded-lg border border-line bg-surface px-3 py-2 text-sm font-medium normal-case tracking-normal text-ink"
            >
              {data.mitigations.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[1.7fr_1fr]">
        <ChartCard
          title="Shortlist-rate ratio by comparison"
          description="The dashed line at 0.8 is the four-fifths reference marker. It is a screening signal, not a legal conclusion."
          sampleSize={sampleSize}
          simulated={data.run.is_simulated}
          footnote="Ratios below 0.8 are coral; ratios at or above 0.8 are teal."
        >
          {chartData.length ? (
            <ShortlistChart data={chartData} />
          ) : (
            <p className="py-12 text-center text-sm text-muted">
              No shortlist ratios for this model and mitigation.
            </p>
          )}
        </ChartCard>

        <Card>
          <h2 className="text-xl leading-tight text-ink">Cutoff context</h2>
          <div className="mt-3 space-y-2 text-sm leading-6 text-muted">
            <p>
              Shortlist cutoff:{" "}
              <strong className="text-ink">
                {allRows[0]?.shortlist_cutoff ??
                  Number(data.run.settings.shortlist_cutoff ?? 7)}
              </strong>{" "}
              out of 10.
            </p>
            <p>
              Ratios shown: {rows.length} of {allRows.length}. Comparisons with a zero
              reference rate cannot form a ratio and are excluded.
            </p>
            <p>
              A ratio of 1.0 means both groups reach the cutoff at the same rate. A ratio below
              0.8 means group A reaches it less often than group B.
            </p>
            <p>
              Rates use paired base CVs. They are not population estimates for real applicants.
            </p>
          </div>
        </Card>
      </div>

      <Card className="mt-5 overflow-hidden p-0">
        <div className="border-b border-line p-5">
          <h2 className="text-xl leading-tight text-ink">Shortlist rates</h2>
          <p className="mt-1 text-sm text-muted">
            Mean score at or above the cutoff, grouped by name, origin or age signal.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[44rem] border-collapse text-left text-sm">
            <thead className="bg-surface-2 text-xs uppercase tracking-[0.08em] text-muted">
              <tr>
                <th className="px-4 py-3 font-semibold">Comparison</th>
                <th className="px-4 py-3 text-right font-semibold">Rate A</th>
                <th className="px-4 py-3 text-right font-semibold">Rate B</th>
                <th className="px-4 py-3 text-right font-semibold">Ratio</th>
                <th className="px-4 py-3 text-right font-semibold">n</th>
                <th className="px-4 py-3 font-semibold">Reference</th>
              </tr>
            </thead>
            <tbody>
              {allRows.map((row) => (
                <tr key={`${row.attribute}-${row.group_a}-${row.group_b}`} className="border-t border-line">
                  <td className="px-4 py-3 font-medium text-ink">{row.comparison_label}</td>
                  <td className="px-4 py-3 text-right text-muted">{percent(row.rate_a)}</td>
                  <td className="px-4 py-3 text-right text-muted">{percent(row.rate_b)}</td>
                  <td className="px-4 py-3 text-right text-ink">
                    {row.shortlist_ratio === null ? "n/a" : fmt(row.shortlist_ratio)}
                  </td>
                  <td className="px-4 py-3 text-right text-muted">{row.n_pairs}</td>
                  <td className="px-4 py-3">
                    <Badge
                      tone={
                        row.shortlist_ratio === null
                          ? "neutral"
                          : row.shortlist_ratio < 0.8
                            ? "bad"
                            : "good"
                      }
                    >
                      {row.shortlist_ratio === null
                        ? "Cannot compute"
                        : row.shortlist_ratio < 0.8
                          ? "Below 0.8"
                          : "At or above 0.8"}
                    </Badge>
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

export default function ShortlistPage() {
  return <DashboardGate>{(data) => <ShortlistContent data={data} />}</DashboardGate>;
}
