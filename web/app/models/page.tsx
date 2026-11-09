"use client";

import { useMemo } from "react";

import { ModelComparisonChart, type ModelComparisonDatum } from "@/components/charts";
import {
  Badge,
  Card,
  ChartCard,
  DashboardGate,
  Metric,
  PageHeader,
} from "@/components/ui";
import { fmt } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

const COLORS = ["var(--teal)", "var(--amber)", "var(--coral)", "var(--blue)"];

function ModelComparisonContent({ data }: { data: Dashboard }) {
  const models = data.verdict.models.map((model) => model.model);
  const baseline = data.audits.filter((row) => row.mitigation === "none");

  const labels = useMemo(() => {
    const seen: string[] = [];
    for (const model of models) {
      for (const row of baseline.filter((item) => item.model === model)) {
        if (!seen.includes(row.comparison_label)) {
          seen.push(row.comparison_label);
        }
      }
    }
    return seen;
  }, [baseline, models]);

  const chartData: ModelComparisonDatum[] = labels.map((label) => {
    const entry: ModelComparisonDatum = { label };
    for (const model of models) {
      const row = baseline.find(
        (item) => item.model === model && item.comparison_label === label,
      );
      entry[model] = row ? row.mean_gap : 0;
    }
    return entry;
  });

  const sampleSize = baseline.reduce((max, row) => Math.max(max, row.n_pairs), 0);

  return (
    <>
      <PageHeader
        eyebrow="Model comparison"
        title="Do the screeners move together?"
        description="Baseline gaps for each comparison, grouped by simulated model. A longer bar means a larger gap for that comparison."
      >
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="neutral">{models.length} models</Badge>
          <Badge tone="neutral">Baseline scores</Badge>
          <Badge tone="neutral">{labels.length} comparisons</Badge>
        </div>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[1.8fr_1fr]">
        <ChartCard
          title="Baseline mean gap by model"
          description="Positive values mean the first group scores higher. Negative values mean it scores lower."
          sampleSize={sampleSize}
          simulated={data.run.is_simulated}
          footnote="Values come from each model's baseline scoring pass on the same matched CVs."
        >
          <ModelComparisonChart data={chartData} models={models} colors={COLORS} />
        </ChartCard>

        <div className="space-y-4">
          {data.verdict.models.map((model) => (
            <Card key={model.model}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg leading-tight text-ink">{model.display_name}</h2>
                <Badge tone={model.gap_found ? "bad" : "good"}>
                  {model.gap_found ? "Gap found" : "No gap"}
                </Badge>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <Metric label="Largest gap" value={`${fmt(model.max_abs_gap)} pts`} />
                <Metric label="Chosen fix" value={model.chosen_label} />
                <Metric label="Fix worked" value={model.fix_worked ? "Yes" : "No"} />
                <Metric label="Quality kept" value={model.quality_kept ? "Yes" : "No"} />
              </div>
            </Card>
          ))}
        </div>
      </div>
    </>
  );
}

export default function ModelComparisonPage() {
  return (
    <DashboardGate>
      {(data) => <ModelComparisonContent data={data} />}
    </DashboardGate>
  );
}
