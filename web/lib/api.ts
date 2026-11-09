import type {
  CreateRunInput,
  Dashboard,
  MatchedPairsResponse,
  Progress,
  RunDetail,
  RunsResponse,
} from "./types";

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

async function postJson<T>(path: string, payload?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload !== undefined ? JSON.stringify(payload) : undefined,
  });
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

export function fetchProgress(runId: string): Promise<Progress> {
  return getJson<Progress>(`/runs/${runId}/progress`);
}

export function fetchPairs(
  runId: string,
  params?: {
    attribute?: string;
    group_a?: string;
    group_b?: string;
    model?: string;
    mitigation?: string;
    limit?: number;
    offset?: number;
  },
): Promise<MatchedPairsResponse> {
  const search = new URLSearchParams();
  if (params?.attribute) search.set("attribute", params.attribute);
  if (params?.group_a) search.set("group_a", params.group_a);
  if (params?.group_b) search.set("group_b", params.group_b);
  if (params?.model) search.set("model", params.model);
  if (params?.mitigation) search.set("mitigation", params.mitigation);
  if (params?.limit) search.set("limit", String(params.limit));
  if (params?.offset) search.set("offset", String(params.offset));
  const query = search.toString();
  return getJson<MatchedPairsResponse>(`/runs/${runId}/pairs${query ? `?${query}` : ""}`);
}

export function createRun(payload: CreateRunInput): Promise<RunDetail> {
  return postJson<RunDetail>("/runs", payload);
}

export function executeRun(runId: string): Promise<RunDetail> {
  return postJson<RunDetail>(`/runs/${runId}/execute`);
}

export function exportUrl(runId: string, kind: "csv" | "markdown"): string {
  return `${API_BASE}/runs/${runId}/export/${kind}`;
}

export function healthUrl(): string {
  return `${API_BASE}/health`;
}
