"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchPairs } from "@/lib/api";
import { fmt, signed } from "@/lib/format";
import type { MatchedPairItem, MatchedPairsResponse } from "@/lib/types";
import { Badge } from "./ui";

export interface PairInspectorProps {
  runId: string;
  model: string;
  mitigation: string;
  attribute: string;
  groupA: string;
  groupB: string;
  title: string;
  isOpen: boolean;
  onClose: () => void;
}

export function PairInspectorModal({
  runId,
  model,
  mitigation,
  attribute,
  groupA,
  groupB,
  title,
  isOpen,
  onClose,
}: PairInspectorProps) {
  const [data, setData] = useState<MatchedPairsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;

    Promise.resolve()
      .then(() => {
        if (!cancelled) {
          setLoading(true);
          setError(null);
        }
        return fetchPairs(runId, {
          attribute,
          group_a: groupA,
          group_b: groupB,
          model,
          mitigation,
          limit: 30,
        });
      })
      .then((res) => {
        if (cancelled) return;
        setData(res);
        setSelectedIndex(0);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load matched pairs");
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, runId, model, mitigation, attribute, groupA, groupB]);

  // Handle escape key
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && isOpen) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const currentPair: MatchedPairItem | null = data?.items[selectedIndex] ?? null;

  const diffLines = useMemo(() => {
    if (!currentPair) return null;
    const linesA = currentPair.text_a.split("\n");
    const linesB = currentPair.text_b.split("\n");
    const maxLen = Math.max(linesA.length, linesB.length);
    const result: Array<{
      lineA: string;
      lineB: string;
      isDiff: boolean;
      num: number;
    }> = [];

    for (let i = 0; i < maxLen; i++) {
      const a = linesA[i] ?? "";
      const b = linesB[i] ?? "";
      result.push({
        num: i + 1,
        lineA: a,
        lineB: b,
        isDiff: a.trim() !== b.trim(),
      });
    }
    return result;
  }, [currentPair]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 sm:p-5 backdrop-blur-sm animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="pair-inspector-title"
    >
      <div className="relative flex h-full max-h-[92vh] w-full max-w-6xl flex-col rounded-2xl border border-line bg-surface shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface-2 px-5 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-teal">
              Matched Pair Evidence Inspector
            </p>
            <h2 id="pair-inspector-title" className="text-xl font-serif text-ink sm:text-2xl">
              {title}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone="neutral">Model: {model}</Badge>
            <Badge tone="neutral">Mitigation: {mitigation}</Badge>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-ink hover:border-teal/50 hover:bg-canvas transition"
              aria-label="Close dialog"
            >
              Close (Esc)
            </button>
          </div>
        </div>

        {/* Sub-header / Pair navigation */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-canvas/60 px-5 py-3 text-sm">
          {loading ? (
            <p className="text-muted">Loading matched synthetic pairs...</p>
          ) : error ? (
            <p className="text-coral">{error}</p>
          ) : data && data.items.length > 0 ? (
            <>
              <div className="flex items-center gap-3">
                <span className="font-semibold text-ink">
                  Pair {selectedIndex + 1} of {data.total}
                </span>
                <Badge tone="neutral">Role: {currentPair?.role}</Badge>
                <Badge tone={currentPair?.tier === "strong" ? "good" : currentPair?.tier === "average" ? "warn" : "neutral"}>
                  Tier: {currentPair?.tier}
                </Badge>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={selectedIndex === 0}
                  onClick={() => setSelectedIndex((prev) => Math.max(0, prev - 1))}
                  className="rounded-lg border border-line bg-surface px-3 py-1 text-xs font-medium text-ink disabled:opacity-40 disabled:cursor-not-allowed hover:border-teal/50 transition"
                >
                  &larr; Previous Pair
                </button>
                <button
                  type="button"
                  disabled={!data || selectedIndex >= data.items.length - 1}
                  onClick={() => setSelectedIndex((prev) => prev + 1)}
                  className="rounded-lg border border-line bg-surface px-3 py-1 text-xs font-medium text-ink disabled:opacity-40 disabled:cursor-not-allowed hover:border-teal/50 transition"
                >
                  Next Pair &rarr;
                </button>
              </div>
            </>
          ) : (
            <p className="text-muted">No matched pairs found for this comparison.</p>
          )}
        </div>

        {/* Main Side-by-side View */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {loading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-teal border-t-transparent" />
            </div>
          ) : error ? (
            <div className="rounded-xl border border-coral/30 bg-coral-soft p-4 text-coral text-sm">
              {error}
            </div>
          ) : currentPair && diffLines ? (
            <div className="space-y-4">
              {/* Score Comparison Banner */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 rounded-xl border border-line bg-canvas p-4 text-center">
                <div className="rounded-lg border border-line/60 bg-surface p-3">
                  <p className="text-xs uppercase tracking-wider text-muted font-semibold">
                    Group A: {currentPair.label_a}
                  </p>
                  <p className="mt-1 font-serif text-2xl text-ink">
                    {fmt(currentPair.score_a)} <span className="text-sm font-sans text-muted">/ 10</span>
                  </p>
                </div>

                <div className="rounded-lg border border-line/60 bg-surface p-3 flex flex-col justify-center">
                  <p className="text-xs uppercase tracking-wider text-muted font-semibold">Score Gap</p>
                  <p className={`mt-1 font-serif text-2xl font-bold ${
                    Math.abs(currentPair.gap) > 0.05
                      ? currentPair.gap > 0
                        ? "text-teal"
                        : "text-coral"
                      : "text-ink"
                  }`}>
                    {signed(currentPair.gap)} <span className="text-sm font-sans font-normal text-muted">pts</span>
                  </p>
                </div>

                <div className="rounded-lg border border-line/60 bg-surface p-3">
                  <p className="text-xs uppercase tracking-wider text-muted font-semibold">
                    Group B: {currentPair.label_b}
                  </p>
                  <p className="mt-1 font-serif text-2xl text-ink">
                    {fmt(currentPair.score_b)} <span className="text-sm font-sans text-muted">/ 10</span>
                  </p>
                </div>
              </div>

              {/* Diff Explainer */}
              <div className="flex items-center gap-2 text-xs text-muted">
                <span className="inline-block h-2 w-2 rounded-full bg-amber" />
                <span>Lines highlighted in amber show the exactly matched differences between variants. All other lines are strictly identical.</span>
              </div>

              {/* Side by side code / CV view */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Column A */}
                <div className="rounded-xl border border-line bg-canvas overflow-hidden">
                  <div className="border-b border-line bg-surface-2 px-4 py-2 text-xs font-semibold text-ink flex items-center justify-between">
                    <span>Variant A ({currentPair.label_a})</span>
                    <Badge tone="neutral">Base CV #{currentPair.base_cv_id}</Badge>
                  </div>
                  <pre className="p-3 text-xs leading-5 font-mono overflow-x-auto text-ink">
                    {diffLines.map((line) => (
                      <div
                        key={`a-${line.num}`}
                        className={`px-1 py-0.5 rounded transition ${
                          line.isDiff
                            ? "bg-amber-soft border-l-2 border-amber font-semibold text-amber-900 dark:text-amber-200"
                            : "text-ink/80"
                        }`}
                      >
                        <span className="inline-block w-6 text-muted/50 select-none">{line.num}</span>
                        {line.lineA || "\u00A0"}
                      </div>
                    ))}
                  </pre>
                </div>

                {/* Column B */}
                <div className="rounded-xl border border-line bg-canvas overflow-hidden">
                  <div className="border-b border-line bg-surface-2 px-4 py-2 text-xs font-semibold text-ink flex items-center justify-between">
                    <span>Variant B ({currentPair.label_b})</span>
                    <Badge tone="neutral">Base CV #{currentPair.base_cv_id}</Badge>
                  </div>
                  <pre className="p-3 text-xs leading-5 font-mono overflow-x-auto text-ink">
                    {diffLines.map((line) => (
                      <div
                        key={`b-${line.num}`}
                        className={`px-1 py-0.5 rounded transition ${
                          line.isDiff
                            ? "bg-amber-soft border-l-2 border-amber font-semibold text-amber-900 dark:text-amber-200"
                            : "text-ink/80"
                        }`}
                      >
                        <span className="inline-block w-6 text-muted/50 select-none">{line.num}</span>
                        {line.lineB || "\u00A0"}
                      </div>
                    ))}
                  </pre>
                </div>
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="border-t border-line bg-surface-2 px-5 py-3 text-right">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-teal px-4 py-1.5 text-xs font-semibold text-white hover:bg-teal-strong transition dark:text-canvas"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
