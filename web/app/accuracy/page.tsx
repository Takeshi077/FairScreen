"use client";

import { useMemo, useState } from "react";

import { useDashboard } from "@/components/DashboardProvider";
import { AccuracyChart, type AccuracyDatum } from "@/components/charts";
import {
  Badge,
  Card,
  ChartCard,
  DashboardGate,
  Metric,
  ModelPicker,
  PageHeader,
  StatusChip,
} from "@/components/ui";
import { percent, points } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

function AccuracyContent({ data }: { data: Dashboard }) {
  const models = data.verdict.models.map((model) => ({
    value: model.model,
    label: model.display_name,
  }));
  const [model, setModel] = useState(models[0]?.value ?? "");
  const selected = models.some((item) => item.value === model)
    ? model
    : (models[0]?.value ?? "");
  const verdict = data.verdict.models.find((item) => item.model === selected);
  const chosen = verdict?.chosen_mitigation ?? "none";
  const baseline = data.accuracy.find(
    (row) => row.model === selected && row.mitigation === "none",
  );
  const after = data.accuracy.find(
    (row) => row.model === selected && row.mitigation === chosen,
  );
  const chosenLabel =
    data.mitigations.find((item) => item.value === chosen)?.label ?? "Mitigation";

  const chartData = useMemo<AccuracyDatum[]>(
    () => [
      { label: "Baseline", accuracy: baseline?.pairwise_accuracy ?? 0 },
      { label: chosenLabel, accuracy: after?.pairwise_accuracy ?? 0 },
    ],
    [after?.pairwise_accuracy, baseline?.pairwise_accuracy, chosenLabel],
  );

  const tableRows = data.verdict.models.map((item) => {
    const base = data.accuracy.find(
      (row) => row.model === item.model && row.mitigation === "none",
    );
    const fixed = data.accuracy.find(
      (row) => row.model === item.model && row.mitigation === item.chosen_mitigation,
    );
    const drop =
      base && fixed ? base.pairwise_accuracy - fixed.pairwise_accuracy : null;
    return {
      model: item.display_name,
      baseline: base?.pairwise_accuracy ?? null,
      after: fixed?.pairwise_accuracy ?? null,
      drop,
      pass: drop !== null && drop <= item.accuracy_drop_gate,
      chosen: item.chosen_label,
    };
  });

  return (
    <>
      <PageHeader
        eyebrow="Accuracy"
        title="Did the fix keep the good candidates on top?"
        description="Pairwise accuracy checks whether higher-quality tiers score above lower-quality tiers. The quality gate allows a drop of at most 2 percentage points versus baseline."
      >
        <ModelPicker options={models} value={selected} onChange={setModel} />
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <ChartCard
          title="Pairwise accuracy before and after mitigation"
          description="Scores should still rank strong CVs above average and weak CVs. Ties count as half a correct pair."
          sampleSize={baseline?.n_items ?? 0}
          simulated={data.run.is_simulated}
          footnote="Accuracy uses known synthetic tiers, not recruiter decisions."
        >
          <AccuracyChart
            data={chartData}
            afterTone={verdict?.quality_kept ? "teal" : "coral"}
          />
        </ChartCard>

        <div className="space-y-4">
          <Card>
            <h2 className="text-xl leading-tight text-ink">Quality gate</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusChip
                label="Quality kept"
                value={verdict?.quality_kept ? "Yes" : "No"}
                tone={verdict?.quality_kept ? "good" : "bad"}
              />
              <StatusChip
                label="Chosen fix"
                value={chosenLabel}
                tone="neutral"
              />
            </div>
            <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
              <Metric
                label="Baseline accuracy"
                value={percent(baseline?.pairwise_accuracy)}
                hint={`${baseline?.n_pairs ?? 0} tier pairs`}
              />
              <Metric
                label={`After ${chosenLabel}`}
                value={percent(after?.pairwise_accuracy)}
                hint={`${after?.n_pairs ?? 0} tier pairs`}
              />
              <Metric
                label="Drop"
                value={points(verdict?.accuracy_drop)}
                hint={`Gate: ${points(verdict?.accuracy_drop_gate)}`}
              />
            </div>
          </Card>
          <Card>
            <h2 className="text-lg leading-tight text-ink">Why this matters</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              A fix can lower a group gap while also flattening real quality differences. The
              quality gate catches that trade-off. A model that fails here needs a better fix,
              not a lower bar.
            </p>
          </Card>
        </div>
      </div>

      <Card className="mt-5 overflow-hidden p-0">
        <div className="border-b border-line p-5">
          <h2 className="text-xl leading-tight text-ink">Accuracy by model</h2>
          <p className="mt-1 text-sm text-muted">
            Baseline against each model&apos;s chosen mitigation. The gate is a drop of 2
            percentage points or less.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[42rem] border-collapse text-left text-sm">
            <thead className="bg-surface-2 text-xs uppercase tracking-[0.08em] text-muted">
              <tr>
                <th className="px-4 py-3 font-semibold">Model</th>
                <th className="px-4 py-3 text-right font-semibold">Baseline</th>
                <th className="px-4 py-3 text-right font-semibold">After</th>
                <th className="px-4 py-3 text-right font-semibold">Drop</th>
                <th className="px-4 py-3 font-semibold">Gate</th>
              </tr>
            </thead>
            <tbody>
              {tableRows.map((row) => (
                <tr key={row.model} className="border-t border-line">
                  <td className="px-4 py-3 font-medium text-ink">
                    {row.model}
                    <span className="ml-2 text-xs text-muted">({row.chosen})</span>
                  </td>
                  <td className="px-4 py-3 text-right text-muted">{percent(row.baseline)}</td>
                  <td className="px-4 py-3 text-right text-muted">{percent(row.after)}</td>
                  <td className="px-4 py-3 text-right text-ink">{points(row.drop)}</td>
                  <td className="px-4 py-3">
                    <Badge tone={row.pass ? "good" : "bad"}>
                      {row.pass ? "Pass" : "Fail"}
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

export default function AccuracyPage() {
  return <DashboardGate>{(data) => <AccuracyContent data={data} />}</DashboardGate>;
}
