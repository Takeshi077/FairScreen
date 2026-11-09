export type Mitigation = "none" | "anonymization" | "skills_only" | "combined";

export interface RunModelInfo {
  model: string;
  display_name: string;
  mitigation: Mitigation;
  mitigation_label: string;
  temperature: number;
  status: string;
}

export interface RunSummary {
  id: string;
  name: string;
  provider: string;
  status: string;
  seed: number;
  repeats: number;
  budget_cap_usd: number;
  cost_usd: number;
  is_simulated: boolean;
  prompt_version: string;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  variants: number;
  scores: number;
  total_scores: number;
  percent: number;
  models: RunModelInfo[];
  settings: Record<string, unknown>;
}

export interface RunDetail extends RunSummary {
  audit_count: number;
  accuracy_count: number;
}

export interface AuditRow {
  id: number;
  model: string;
  mitigation: Mitigation;
  attribute: string;
  group_a: string;
  group_b: string;
  comparison_label: string;
  n_pairs: number;
  mean_gap: number;
  ci_low: number;
  ci_high: number;
  p_value: number;
  p_adjusted: number;
  effect_size: number;
  noise_floor: number;
  shortlist_cutoff: number;
  rate_a: number;
  rate_b: number;
  shortlist_ratio: number | null;
  significant: boolean;
  reduction_vs_baseline: number | null;
  reduction_ci_low: number | null;
  reduction_ci_high: number | null;
  reduction_supported: boolean | null;
}

export interface AccuracyRow {
  id: number;
  model: string;
  mitigation: Mitigation;
  mitigation_label: string;
  pairwise_accuracy: number;
  auc: number;
  n_items: number;
  n_pairs: number;
}

export interface ShortlistRow {
  model: string;
  mitigation: Mitigation;
  mitigation_label: string;
  attribute: string;
  comparison_label: string;
  group_a: string;
  group_b: string;
  n_pairs: number;
  shortlist_cutoff: number;
  rate_a: number;
  rate_b: number;
  shortlist_ratio: number | null;
  significant: boolean;
}

export interface VerdictModel {
  model: string;
  display_name: string;
  gap_found: boolean;
  fix_worked: boolean | null;
  quality_kept: boolean;
  chosen_mitigation: Mitigation | null;
  chosen_label: string;
  max_abs_gap: number;
  mean_abs_gap_before: number;
  mean_abs_gap_after: number;
  mean_reduction: number | null;
  accuracy_baseline: number | null;
  accuracy_after: number | null;
  accuracy_drop: number | null;
  accuracy_drop_gate: number;
  sample_size: number;
  summary: string;
}

export interface Verdict {
  run_id: string;
  run_name: string;
  status: string;
  is_simulated: boolean;
  seed: number;
  repeats: number;
  models: VerdictModel[];
}

export interface ProgressModel {
  model: string;
  mitigation: Mitigation;
  status: string;
  completed: number;
  total: number;
  percent: number;
}

export interface Progress {
  run_id: string;
  status: string;
  completed: number;
  total: number;
  percent: number;
  variants: number;
  repeats: number;
  run_models: ProgressModel[];
  cost_usd: number;
  budget_cap_usd: number;
  updated_at: string;
}

export interface MitigationOption {
  value: Mitigation;
  label: string;
}

export interface Dashboard {
  run: RunDetail;
  verdict: Verdict;
  progress: Progress;
  audits: AuditRow[];
  accuracy: AccuracyRow[];
  shortlist: ShortlistRow[];
  mitigations: MitigationOption[];
}

export interface RunsResponse {
  items: RunSummary[];
  total: number;
  limit: number;
  offset: number;
}
