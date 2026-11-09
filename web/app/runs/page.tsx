"use client";

import { useRouter } from "next/navigation";

import { useDashboard } from "@/components/DashboardProvider";
import {
  Badge,
  Card,
  ErrorState,
  LoadingPage,
  PageHeader,
} from "@/components/ui";
import { shortRunId } from "@/lib/format";

function formatDate(value: string | null): string {
  if (!value) return "n/a";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function RunsPage() {
  const { runs, runId, loading, error, refresh, selectRun } = useDashboard();
  const router = useRouter();

  if (loading && runs.length === 0) {
    return <LoadingPage label="Loading runs" />;
  }
  if (error && runs.length === 0) {
    return <ErrorState message={error} onRetry={() => void refresh()} />;
  }

  return (
    <>
      <PageHeader
        eyebrow="Runs"
        title="Every audit is a saved run"
        description="A run fixes the model, prompt, mitigation, seed and repeat count. This list makes the demo reproducible and shows which results are simulated."
      >
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="neutral">{runs.length} runs</Badge>
          <button
            type="button"
            onClick={() => void refresh()}
            className="rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-ink hover:border-teal/50"
          >
            Refresh list
          </button>
        </div>
      </PageHeader>

      {runs.length === 0 ? (
        <Card>
          <h2 className="text-xl text-ink">No runs yet</h2>
          <p className="mt-2 text-sm text-muted">
            Run <code className="rounded bg-surface-2 px-1.5 py-0.5">make seed</code> to create
            the demo run.
          </p>
        </Card>
      ) : (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[58rem] border-collapse text-left text-sm">
              <thead className="bg-surface-2 text-xs uppercase tracking-[0.08em] text-muted">
                <tr>
                  <th className="px-4 py-3 font-semibold">Run</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Provider</th>
                  <th className="px-4 py-3 text-right font-semibold">Sample size</th>
                  <th className="px-4 py-3 text-right font-semibold">Scores</th>
                  <th className="px-4 py-3 font-semibold">Created</th>
                  <th className="px-4 py-3 font-semibold">Source</th>
                  <th className="px-4 py-3 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr
                    key={run.id}
                    className={`border-t border-line ${
                      run.id === runId ? "bg-teal-soft/40" : ""
                    }`}
                  >
                    <td className="px-4 py-3">
                      <p className="font-medium text-ink">{run.name}</p>
                      <p className="text-xs text-muted">
                        {shortRunId(run.id)} / seed {run.seed} / {run.repeats} repeats
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={run.status === "completed" ? "good" : "warn"}>
                        {run.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-muted">{run.provider}</td>
                    <td className="px-4 py-3 text-right text-muted">
                      {run.variants.toLocaleString()} CVs
                    </td>
                    <td className="px-4 py-3 text-right text-muted">
                      {run.scores.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-muted">{formatDate(run.created_at)}</td>
                    <td className="px-4 py-3">
                      <Badge tone={run.is_simulated ? "warn" : "neutral"}>
                        {run.is_simulated ? "Simulated" : "Live provider"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => {
                          selectRun(run.id);
                          router.push("/");
                        }}
                        className="rounded-lg bg-teal px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-strong dark:text-canvas"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}
