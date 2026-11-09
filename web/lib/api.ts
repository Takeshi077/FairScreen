import type { Dashboard, RunsResponse } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchRuns(): Promise<RunsResponse> {
  return getJson<RunsResponse>("/runs?limit=50");
}

export function fetchDashboard(runId: string): Promise<Dashboard> {
  return getJson<Dashboard>(`/runs/${runId}/dashboard`);
}

export function exportUrl(runId: string, kind: "csv" | "markdown"): string {
  return `${API_BASE}/runs/${runId}/export/${kind}`;
}

export function healthUrl(): string {
  return `${API_BASE}/health`;
}
