# FairScreen Product Requirements Document

Status: reconstructed source of truth
Version: 1.0
Date: 2026-11-09

## Note on provenance

The master build prompt refers to `docs/PRD.md` as an existing file. The repository did not contain it when work started. This document reconstructs the PRD from the DataNova 2026 proposal deck (`DataNova_FairScreen_Proposal.pptx`) and the master build prompt. Where the two differed, this document follows the master build prompt and records the choice in `docs/DECISIONS.md`.

## 1. Product summary

FairScreen is a web tool that audits LLM-based CV screeners for bias. It generates synthetic matched CV pairs that differ in exactly one signal, scores them with two or three LLMs, computes statistically defensible score gaps, applies mitigations, re-runs the audit, checks that ranking quality did not collapse, and presents the evidence in a dashboard that a non-technical HR reviewer can read.

One sentence: measure it, fix it, prove it.

## 2. Problem

Teams increasingly use LLMs to score CVs and build shortlists. A name, a graduation year, or a name origin can move a score without anyone noticing. Most teams have no repeatable way to test whether equally qualified candidates receive equal treatment.

The question FairScreen answers: does the same qualified candidate get the same score, whoever they appear to be, for this model, this prompt, and this test set?

## 3. Users

- HR reviewer: needs a plain-language verdict, evidence, and exports.
- Responsible AI auditor: needs a repeatable test design and statistical detail.
- Builder or vendor: needs to see whether a mitigation fixes a gap without destroying ranking quality.

## 4. Scope

In scope:

- Synthetic CV generation for six roles and three quality tiers.
- Matched variants for gender-coded name, name origin, and age signal.
- Two or more real LLM adapters behind one provider interface.
- A deterministic mock provider for demo mode and tests.
- Baseline scoring, repeat runs, caching, budget caps, and resumable runs.
- Audit statistics: paired mean gaps, bootstrap confidence intervals, paired permutation tests, effect size, shortlist-rate ratio, repeat noise floor, Holm correction, ranking accuracy, and AUC.
- Mitigations: anonymization, skills-only prompt, and combined.
- Dashboard pages, CSV export, Markdown report, and a plain-language verdict.
- Light and dark themes, responsive layout, keyboard accessibility.

Out of scope:

- Real applicant data.
- Claims about a vendor or model in general.
- Automated hiring decisions.
- Attributes beyond gender-coded name, name origin, and age signal.
- Fine-tuning models or changing vendor internals.

## 5. Test design

### 5.1 Roles and base CVs

Six roles:

1. Software Engineer
2. Data Analyst
3. Marketing Manager
4. Registered Nurse
5. Customer Success Manager
6. Operations Coordinator

Each role has at least 30 base CVs, balanced across strong, average, and weak tiers. The implementation uses 33 per role, 11 per tier.

Every CV is synthetic. The generator uses deterministic seeds so the dataset can be reproduced.

### 5.2 Matched variants

Each base CV produces these variants:

- Gender-coded name: `woman` and `man`. The surname is held constant. Only the first name changes.
- Name origin: five origin groups (`anglo`, `african`, `east_asian`, `south_asian`, `middle_eastern`). Origin names are all male-coded to avoid confounding gender with origin. Only the full name changes.
- Age signal: `early_career`, `mid_career`, `senior`. Only graduation year and stated years of experience change. The name and all evidence stay constant.

A pair is valid only when its two rendered texts differ in the intended fields and nowhere else. An automated diff test enforces this.

### 5.3 Attributes and comparisons

Audited attributes and reference comparisons:

- Gender: woman minus man.
- Name origin: each non-Anglo group minus Anglo (four comparisons).
- Age: senior minus mid, senior minus early, mid minus early (three comparisons).

A positive gap means the first group scores higher. Negative values mean the first group scores lower.

### 5.4 Repeats

Each variant is scored three times by default. Repeats provide the noise floor and reduce transient variance.

## 6. Data model

The database is SQLite by default and Postgres-compatible through SQLAlchemy. Tables:

### base_cvs

- `id` integer primary key
- `role` string, indexed
- `tier` string, one of `strong`, `average`, `weak`, indexed
- `title` string
- `text` text, baseline rendered CV with a neutral name
- `seed` integer
- `created_at` datetime

### cv_variants

- `id` integer primary key
- `base_cv_id` foreign key to `base_cvs`
- `attribute` string, one of `gender`, `name_origin`, `age`
- `group_name` string
- `label` string, human-readable group label
- `text` text, full rendered CV
- `changed_fields` JSON list of field names
- `created_at` datetime
- unique constraint on (`base_cv_id`, `attribute`, `group_name`)
- indexes on (`attribute`, `group_name`)

### runs

- `id` string UUID primary key
- `name` string
- `provider` string, `mock`, `openai`, or `anthropic`
- `status` string, one of `pending`, `running`, `completed`, `failed`, `aborted`
- `seed` integer
- `repeats` integer
- `budget_cap_usd` float
- `cost_usd` float
- `is_simulated` boolean
- `prompt_version` string
- `settings` JSON
- `created_at`, `started_at`, `completed_at` datetimes
- `error` text

### run_models

- `id` integer primary key
- `run_id` foreign key to `runs`
- `model_name` string
- `provider` string
- `temperature` float
- `mitigation` string, one of `none`, `anonymization`, `skills_only`, `combined`
- `display_name` string
- `status` string
- `created_at` datetime
- unique constraint on (`run_id`, `model_name`, `mitigation`)

### scores

- `id` integer primary key
- `run_id` foreign key
- `run_model_id` foreign key
- `variant_id` foreign key
- `repeat` integer, zero-based
- `score` float from 0 to 10
- `reason` text
- `latency_ms` integer
- `prompt_text` text
- `model` string
- `temperature` float
- `mitigation` string
- `cached` boolean
- `cost_usd` float
- `created_at` datetime
- unique constraint on (`run_model_id`, `variant_id`, `repeat`)
- indexes on (`run_id`, `run_model_id`)

### llm_cache

- `id` integer primary key
- `cache_key` string unique
- `provider` string
- `model` string
- `prompt_version` string
- `variant_key` string, a hash of the exact CV text
- `repeat` integer
- `prompt_hash` string
- `score` float
- `reason` text
- `latency_ms` integer
- `cost_usd` float
- `created_at` datetime

### audit_results

- `id` integer primary key
- `run_id` foreign key
- `run_model_id` foreign key
- `model` string
- `mitigation` string
- `attribute` string
- `group_a` string
- `group_b` string
- `comparison_label` string
- `n_pairs` integer
- `mean_gap` float
- `ci_low` float
- `ci_high` float
- `p_value` float
- `p_adjusted` float
- `effect_size` float, Cohen's dz
- `noise_floor` float
- `shortlist_cutoff` float
- `rate_a` float
- `rate_b` float
- `shortlist_ratio` float nullable
- `significant` boolean, true when the 95 percent CI excludes zero
- `reduction_vs_baseline` float nullable
- `reduction_ci_low` float nullable
- `reduction_ci_high` float nullable
- `reduction_supported` boolean nullable
- `created_at` datetime
- unique constraint on (`run_model_id`, `attribute`, `group_a`, `group_b`)

### accuracy_results

- `id` integer primary key
- `run_id` foreign key
- `run_model_id` foreign key
- `model` string
- `mitigation` string
- `pairwise_accuracy` float
- `auc` float
- `n_items` integer
- `n_pairs` integer
- `created_at` datetime
- unique constraint on `run_model_id`

## 7. Statistics

All statistics live in `api/app/audit/` and never call an LLM.

- Mean gap: for each base CV, compute the mean repeated score for group A minus group B. Average across base CVs.
- Bootstrap 95 percent CI: 10,000 resamples of base CVs with replacement, seeded.
- Paired permutation test: 10,000 random sign flips, two-sided, seeded.
- Effect size: Cohen's dz, the mean paired difference divided by its standard deviation.
- Shortlist rate: fraction of group variants with mean score at or above the cutoff. Default cutoff is 7.0 out of 10.
- Shortlist-rate ratio: rate A divided by rate B. The four-fifths rule value 0.8 is a reference marker, not a legal conclusion.
- Noise floor: from repeat runs, 1.96 times the pooled within-variant repeat standard deviation. A gap smaller than this is inside normal repeat noise.
- Holm correction: applied across all comparisons for a mitigation, spanning attributes and models.
- Ranking accuracy: pairwise accuracy of scores against tier labels, with ties counting 0.5. AUC is the same quantity computed with the Mann-Whitney formula.
- Reduction: absolute baseline gap minus absolute mitigated gap, with a seeded bootstrap CI over base CVs.

## 8. Mitigations

- `none`: baseline prompt on the raw CV.
- `anonymization`: remove name, pronouns, graduation year, and age cues before scoring.
- `skills_only`: use a prompt that restricts scoring to role-relevant evidence.
- `combined`: anonymization plus the skills-only prompt.

The audit re-runs every mitigation for every model.

## 9. Demo mode

The system must run with no API keys.

`MockProvider` returns deterministic scores from CV text with:

- a quality signal derived from CV tier and evidence features,
- configurable planted bias per group,
- small seeded noise per repeat.

Three simulated models are provided with different planted bias strength and noise. One simulated model intentionally fails the accuracy gate under mitigation so the dashboard shows both pass and fail outcomes. Any run produced by the mock provider is labelled "Simulated data" in the UI and exports.

Real providers are optional at runtime. They are selected with environment variables. If a real provider is requested without a key, the run fails with a clear configuration error; demo mode is unaffected.

## 10. Provider interface

```python
class Provider:
    name: str
    def score(self, cv_text: str, prompt: str, settings: ScoreSettings) -> ProviderResult: ...
```

`ProviderResult`:

- `score`: float from 0 to 10
- `reason`: string
- `latency_ms`: integer
- `cost_usd`: float

Requirements:

- Strict JSON validation of the model response.
- Retries with exponential backoff on transport, JSON, or validation failures.
- Per (`model`, `prompt_version`, `variant`, `repeat`) cache.
- Configurable budget cap that aborts a run before cost overruns.
- Latency logging.

## 11. API surface

Base URL: `/`.

- `GET /health`
- `GET /runs`
- `POST /runs`
- `GET /runs/{run_id}`
- `POST /runs/{run_id}/execute`
- `GET /runs/{run_id}/progress`
- `GET /runs/{run_id}/audits`
- `GET /runs/{run_id}/accuracy`
- `GET /runs/{run_id}/shortlist`
- `GET /runs/{run_id}/verdict`
- `GET /runs/{run_id}/dashboard`
- `GET /runs/{run_id}/scores`
- `GET /runs/{run_id}/pairs`
- `GET /runs/{run_id}/export/csv`
- `GET /runs/{run_id}/export/markdown`

`POST /runs` accepts:

- `name`
- `provider`
- `models`
- `mitigations`
- `seed`
- `repeats`
- `budget_cap_usd`
- `shortlist_cutoff`
- `temperature`
- `bases_per_role` optional for smoke runs
- `execute` boolean, default true

## 12. Verdict thresholds

The verdict endpoint returns plain-language inputs per model:

- Gap found: at least one baseline comparison has a 95 percent CI excluding zero.
- Fix worked: every baseline comparison with a significant gap has a supported reduction versus the chosen mitigation, and that mitigation's CI includes zero for those comparisons.
- Quality kept: ranking accuracy after the chosen mitigation drops by 2 percentage points or less versus baseline.
- Chosen mitigation: `combined` when present, otherwise the mitigation with the smallest mean absolute gap.

The response includes `gap_found`, `fix_worked`, `quality_kept`, and a one-sentence summary per model. UI status chips always include a word, never color alone.

## 13. Dashboard spec

Pages:

1. Overview and Verdict: three status chips per model, plain-language sentences, simulator banner, exports.
2. Gap by group: dot-and-whisker chart centered on zero, confidence intervals, sample sizes.
3. Before vs after: paired bars of absolute gap before and after each mitigation.
4. Model comparison: grouped bars of gaps by model.
5. Shortlist ratio: horizontal bars with the 0.8 reference line.
6. Accuracy: two-bar comparison of baseline and mitigated pairwise accuracy, with the 2 point gate.
7. Method: test design, statistics, limits, ethics.
8. Runs: list of runs with status, provider, sample size, and simulated label.

Every chart:

- shows sample size,
- includes the caption "Results apply to this model, prompt and test set.",
- labels simulated results.

Global requirements:

- Deep teal primary, warm amber accent, coral warning color.
- Serif headings, clean sans body, generous spacing, editorial feel.
- Light and dark themes.
- Responsive to phone width, no horizontal page scroll.
- Keyboard accessible controls.
- Loading and error states for every fetch.
- CSV and Markdown download buttons.
- No em dashes in user-facing copy.

## 14. Non-functional requirements

- Python 3.11 target, tested on the available interpreter.
- FastAPI and SQLAlchemy backend.
- Next.js, TypeScript, Tailwind, and Recharts frontend.
- Tests with pytest. Unit tests for every statistic with known answers.
- Planted-bias test: 0.5 point bias is detected with a CI excluding zero.
- No-bias test: no gap beyond the repeat noise floor is flagged.
- Ruff and mypy or pyright for Python.
- ESLint and tsc for web.
- Reproducible one-command demo seed.
- Secrets only through environment variables.
- Synthetic data only.

## 15. Definition of Done

1. `make setup && make seed && make dev` brings up API and web with seeded demo, no API keys.
2. `make test` passes, including planted-bias and no-bias tests.
3. Dashboard shows all pages with seeded data: a gap found, a fix that reduces it, one model passing and one model failing the accuracy gate.
4. Pair-diff test proves every variant differs only in the intended signal.
5. Exports download correctly.
6. Real-provider code path verified with a recorded or stubbed HTTP response.
7. Lint and type checks pass.
8. README, METHOD.md, DECISIONS.md, and VERIFICATION.md are complete and accurate.
9. Screenshots of each dashboard page at desktop and phone width are saved in `docs/screenshots/`.

## 16. Build phases

- Phase 0: repository, configuration, database models, health endpoint.
- Phase 1: CV generator, names, anonymizer, preview script, pair-diff tests.
- Phase 2: provider interface, mock provider, real adapters, caching, budget, tests.
- Phase 3: runner, repeats, resume, progress, prompts, tests.
- Phase 4: audit engine, statistics, accuracy, verdict, tests.
- Phase 5: API endpoints, exports, API tests.
- Phase 6: demo seed, dashboard, screenshots, docs, verification.
