"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { fetchDashboard, fetchRuns } from "@/lib/api";
import type { Dashboard, RunSummary } from "@/lib/types";

interface DashboardContextValue {
  runs: RunSummary[];
  runId: string | null;
  data: Dashboard | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  lastUpdated: Date | null;
  selectRun: (runId: string) => void;
  refresh: () => Promise<void>;
}

const DashboardContext = createContext<DashboardContextValue | null>(null);

function pickRun(runs: RunSummary[], current: string | null): string | null {
  if (current && runs.some((run) => run.id === current)) {
    return current;
  }
  const completed = runs.find((run) => run.status === "completed");
  return completed?.id ?? runs[0]?.id ?? null;
}

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const response = await fetchRuns();
        if (cancelled) return;
        setRuns(response.items);
        setRunId((current) => pickRun(response.items, current));
        if (response.items.length === 0) {
          setLoading(false);
        }
      } catch (cause) {
        if (cancelled) return;
        setError(cause instanceof Error ? cause.message : "Could not reach the FairScreen API.");
        setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    async function load() {
      try {
        const dashboard = await fetchDashboard(runId as string);
        if (cancelled) return;
        setData(dashboard);
        setLastUpdated(new Date());
        setLoading(false);
      } catch (cause) {
        if (cancelled) return;
        setError(cause instanceof Error ? cause.message : "Could not load this run.");
        setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  const runStatus = data?.run.status;

  // Live polling for running or pending audits
  useEffect(() => {
    if (!runId || !runStatus) return;
    if (runStatus !== "running" && runStatus !== "pending") return;

    const timer = setInterval(async () => {
      try {
        const dashboard = await fetchDashboard(runId);
        setData(dashboard);
        setLastUpdated(new Date());
      } catch {
        // Continue polling
      }
    }, 2500);

    return () => clearInterval(timer);
  }, [runId, runStatus]);

  const selectRun = useCallback((nextRunId: string) => {
    setRunId(nextRunId);
    setLoading(true);
    setError(null);
  }, []);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const response = await fetchRuns();
      setRuns(response.items);
      const target = pickRun(response.items, runId);
      setRunId(target);
      if (target) {
        const dashboard = await fetchDashboard(target);
        setData(dashboard);
        setLastUpdated(new Date());
      } else {
        setData(null);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not refresh the dashboard.");
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, [runId]);

  const value = useMemo<DashboardContextValue>(
    () => ({
      runs,
      runId,
      data,
      loading,
      refreshing,
      error,
      lastUpdated,
      selectRun,
      refresh,
    }),
    [runs, runId, data, loading, refreshing, error, lastUpdated, selectRun, refresh],
  );

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard(): DashboardContextValue {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error("useDashboard must be used inside DashboardProvider");
  }
  return context;
}
