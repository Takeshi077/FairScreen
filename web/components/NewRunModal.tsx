"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createRun } from "@/lib/api";
import type { CreateRunInput, Mitigation } from "@/lib/types";

interface NewRunModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (runId: string) => void;
}

export function NewRunModal({ isOpen, onClose, onCreated }: NewRunModalProps) {
  const router = useRouter();
  const [name, setName] = useState("Smoke Audit (Fast)");
  const [preset, setPreset] = useState<"smoke" | "standard" | "full">("smoke");
  const [provider, setProvider] = useState("mock");
  const [modelChoice, setModelChoice] = useState("Mock-Screen-A, Mock-Screen-B, Mock-Screen-C");
  const [repeats, setRepeats] = useState(1);
  const [basesPerRole, setBasesPerRole] = useState(6);
  const [budgetCap, setBudgetCap] = useState(5.0);
  const [cutoff, setCutoff] = useState(7.0);
  const [mitigations, setMitigations] = useState<Mitigation[]>([
    "none",
    "anonymization",
    "skills_only",
    "combined",
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handlePresetChange(nextPreset: "smoke" | "standard" | "full") {
    setPreset(nextPreset);
    if (nextPreset === "smoke") {
      setName("Smoke Audit (Fast)");
      setBasesPerRole(6);
      setRepeats(1);
    } else if (nextPreset === "standard") {
      setName("Standard Audit");
      setBasesPerRole(11);
      setRepeats(2);
    } else if (nextPreset === "full") {
      setName("Full Certification Audit");
      setBasesPerRole(33);
      setRepeats(3);
    }
  }

  function handleProviderChange(nextProvider: string) {
    setProvider(nextProvider);
    if (nextProvider === "mock") {
      setModelChoice("Mock-Screen-A, Mock-Screen-B, Mock-Screen-C");
    } else if (nextProvider === "openai") {
      setModelChoice("gpt-4o-mini");
    } else if (nextProvider === "anthropic") {
      setModelChoice("claude-3-5-haiku-latest");
    } else if (nextProvider === "gemini") {
      setModelChoice("gemini-2.0-flash");
    }
  }

  // Close on Escape
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && isOpen && !loading) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, loading, onClose]);

  if (!isOpen) return null;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    const models = modelChoice
      .split(",")
      .map((m) => m.trim())
      .filter(Boolean);

    const payload: CreateRunInput = {
      name,
      provider,
      models: models.length > 0 ? models : undefined,
      mitigations,
      bases_per_role: basesPerRole,
      repeats,
      budget_cap_usd: budgetCap,
      shortlist_cutoff: cutoff,
      temperature: 0.2,
      execute: true,
    };

    try {
      const run = await createRun(payload);
      onCreated(run.id);
      onClose();
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create audit run");
    } finally {
      setLoading(false);
    }
  }

  function toggleMitigation(mit: Mitigation) {
    if (mit === "none") return; // Baseline is mandatory
    if (mitigations.includes(mit)) {
      setMitigations(mitigations.filter((m) => m !== mit));
    } else {
      setMitigations([...mitigations, mit]);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-run-title"
    >
      <div className="relative flex max-h-[90vh] w-full max-w-2xl flex-col rounded-2xl border border-line bg-surface shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="border-b border-line bg-surface-2 px-6 py-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-teal">
              Launch Configuration
            </p>
            <h2 id="new-run-title" className="text-xl font-serif text-ink sm:text-2xl">
              Configure New Audit Run
            </h2>
          </div>
          <button
            type="button"
            disabled={loading}
            onClick={onClose}
            className="rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-ink hover:border-teal/50 hover:bg-canvas transition disabled:opacity-40"
          >
            Cancel
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">
          {error && (
            <div className="rounded-xl border border-coral/30 bg-coral-soft p-4 text-xs text-coral">
              {error}
            </div>
          )}

          {/* Presets */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-muted mb-2">
              Audit Scale Preset
            </label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id: "smoke", label: "Smoke Test", desc: "6 base CVs / 1 repeat (~10s)" },
                { id: "standard", label: "Standard", desc: "11 base CVs / 2 repeats" },
                { id: "full", label: "Full Audit", desc: "33 base CVs / 3 repeats" },
              ].map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handlePresetChange(p.id as typeof preset)}
                  className={`rounded-xl border p-3 text-left transition ${
                    preset === p.id
                      ? "border-teal bg-teal-soft/40 shadow-sm"
                      : "border-line bg-canvas hover:border-teal/50"
                  }`}
                >
                  <p className="text-sm font-semibold text-ink">{p.label}</p>
                  <p className="mt-1 text-[0.7rem] text-muted">{p.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Name & Provider */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="run-name" className="block text-xs font-semibold text-muted mb-1">
                Run Name
              </label>
              <input
                id="run-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink focus:border-teal focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="run-provider" className="block text-xs font-semibold text-muted mb-1">
                LLM Provider
              </label>
              <select
                id="run-provider"
                value={provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink focus:border-teal focus:outline-none"
              >
                <option value="mock">Simulated Mock (Offline, Free)</option>
                <option value="openai">OpenAI Compatible (Requires API Key)</option>
                <option value="anthropic">Anthropic (Requires API Key)</option>
                <option value="gemini">Google Gemini (Requires API Key)</option>
              </select>
            </div>
          </div>

          {/* Models */}
          <div>
            <label htmlFor="run-models" className="block text-xs font-semibold text-muted mb-1">
              Models to Score (comma-separated)
            </label>
            <input
              id="run-models"
              type="text"
              value={modelChoice}
              onChange={(e) => setModelChoice(e.target.value)}
              required
              className="w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm font-mono text-ink focus:border-teal focus:outline-none"
            />
          </div>

          {/* Mitigations */}
          <div>
            <span className="block text-xs font-semibold text-muted mb-2">
              Audited Mitigations
            </span>
            <div className="flex flex-wrap gap-2">
              {[
                { id: "none", label: "Baseline (Raw CV)", mandatory: true },
                { id: "anonymization", label: "Anonymization", mandatory: false },
                { id: "skills_only", label: "Skills-Only Prompt", mandatory: false },
                { id: "combined", label: "Combined", mandatory: false },
              ].map((mit) => {
                const active = mitigations.includes(mit.id as Mitigation);
                return (
                  <button
                    key={mit.id}
                    type="button"
                    onClick={() => toggleMitigation(mit.id as Mitigation)}
                    className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                      active
                        ? "border-teal bg-teal-soft text-teal-strong dark:text-teal font-semibold"
                        : "border-line bg-canvas text-muted hover:border-line/80"
                    } ${mit.mandatory ? "cursor-default" : "cursor-pointer"}`}
                  >
                    {mit.label} {active ? "✓" : "+"}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Numerical parameters */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            <div>
              <label htmlFor="run-bases" className="block text-[0.7rem] font-semibold text-muted uppercase">
                Bases / Role
              </label>
              <input
                id="run-bases"
                type="number"
                min={1}
                max={50}
                value={basesPerRole}
                onChange={(e) => setBasesPerRole(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-line bg-canvas px-2.5 py-1.5 text-sm text-ink font-mono"
              />
            </div>

            <div>
              <label htmlFor="run-repeats" className="block text-[0.7rem] font-semibold text-muted uppercase">
                Repeats
              </label>
              <input
                id="run-repeats"
                type="number"
                min={1}
                max={5}
                value={repeats}
                onChange={(e) => setRepeats(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-line bg-canvas px-2.5 py-1.5 text-sm text-ink font-mono"
              />
            </div>

            <div>
              <label htmlFor="run-cutoff" className="block text-[0.7rem] font-semibold text-muted uppercase">
                Shortlist Cutoff
              </label>
              <input
                id="run-cutoff"
                type="number"
                step="0.5"
                min={0}
                max={10}
                value={cutoff}
                onChange={(e) => setCutoff(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-line bg-canvas px-2.5 py-1.5 text-sm text-ink font-mono"
              />
            </div>

            <div>
              <label htmlFor="run-budget" className="block text-[0.7rem] font-semibold text-muted uppercase">
                Budget Cap ($)
              </label>
              <input
                id="run-budget"
                type="number"
                step="0.5"
                min={0.5}
                max={50}
                value={budgetCap}
                onChange={(e) => setBudgetCap(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-line bg-canvas px-2.5 py-1.5 text-sm text-ink font-mono"
              />
            </div>
          </div>

          <div className="rounded-xl border border-line bg-canvas/60 p-3 text-xs text-muted flex items-center justify-between">
            <span>
              Total Variants: <strong className="text-ink">{basesPerRole * 6 * 10}</strong>
            </span>
            <span>
              Estimated Scores:{" "}
              <strong className="text-ink">
                {basesPerRole * 6 * 10 * repeats * modelChoice.split(",").filter(Boolean).length * mitigations.length}
              </strong>
            </span>
          </div>

          {/* Footer Submit */}
          <div className="pt-4 border-t border-line flex items-center justify-end gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={onClose}
              className="rounded-lg border border-line bg-surface px-4 py-2 text-xs font-semibold text-ink hover:bg-canvas transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-teal px-5 py-2 text-xs font-semibold text-white hover:bg-teal-strong transition dark:text-canvas disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="h-3 w-3 animate-spin rounded-full border border-white border-t-transparent" />
                  <span>Executing Audit...</span>
                </>
              ) : (
                <span>Launch Audit Run</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
