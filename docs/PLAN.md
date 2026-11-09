# FairScreen Build Plan

Date: 2026-11-09
Source of truth: `docs/PRD.md`

## 1. Repository tree

```text
FairScreen/
  .env.example
  .gitignore
  Makefile
  README.md
  docker-compose.yml
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  api/
    app/
      __init__.py
      config.py
      db.py
      models.py
      schemas.py
      prompts.py
      runner.py
      exports.py
      main.py
      audit/
        __init__.py
        stats.py
        engine.py
        verdict.py
      cvs/
        __init__.py
        names.py
        content.py
        generator.py
        anonymizer.py
      llm/
        __init__.py
        base.py
        cache.py
        mock.py
        openai_provider.py
        anthropic_provider.py
        registry.py
      api/
        __init__.py
        routes.py
    scripts/
      preview_pairs.py
      seed_demo.py
    tests/
      conftest.py
      test_generator.py
      test_anonymizer.py
      test_providers.py
      test_runner.py
      test_stats.py
      test_audit.py
      test_verdict.py
      test_api.py
      test_exports.py
  web/
    package.json
    next.config.mjs
    postcss.config.mjs
    tailwind.config.ts
    tsconfig.json
    .eslintrc.json
    app/
      layout.tsx
      globals.css
      providers.tsx
      page.tsx
      gap/page.tsx
      before-after/page.tsx
      models/page.tsx
      shortlist/page.tsx
      accuracy/page.tsx
      method/page.tsx
      runs/page.tsx
      components/
        AppShell.tsx
        ChartFrame.tsx
        StatusChip.tsx
        SimulatedBanner.tsx
        RunGate.tsx
        charts/...
      lib/
        api.ts
        types.ts
        format.ts
    scripts/
      screenshots.mjs
  docs/
    PRD.md
    PLAN.md
    DECISIONS.md
    METHOD.md
    VERIFICATION.md
    screenshots/
  data/
    .gitkeep
```

`data/` is generated and gitignored except for `.gitkeep`. Screenshots are committed.

## 2. Module responsibilities

- `api/app/config.py`: environment settings, paths, provider selection, pricing.
- `api/app/db.py`: SQLAlchemy engine, session factory, `create_all`.
- `api/app/models.py`: all tables from PRD section 6.
- `api/app/schemas.py`: Pydantic request and response models.
- `api/app/prompts.py`: baseline and skills-only prompts with versions.
- `api/app/cvs/names.py`: gender, origin, and neutral name pools.
- `api/app/cvs/content.py`: role-specific skills, bullets, companies, education.
- `api/app/cvs/generator.py`: deterministic base CVs and matched variants.
- `api/app/cvs/anonymizer.py`: identity and age signal removal.
- `api/app/llm/base.py`: provider protocol, result, validation, errors.
- `api/app/llm/mock.py`: deterministic simulated provider with planted bias.
- `api/app/llm/openai_provider.py`: OpenAI-compatible chat adapter.
- `api/app/llm/anthropic_provider.py`: Anthropic messages adapter.
- `api/app/llm/cache.py`: database-backed score cache.
- `api/app/llm/registry.py`: provider selection from settings.
- `api/app/runner.py`: resumable run execution, progress, repeats, budget.
- `api/app/audit/stats.py`: bootstrap, permutation, Holm, effect size, accuracy, ratios.
- `api/app/audit/engine.py`: compare groups, store audits, reductions, accuracy.
- `api/app/audit/verdict.py`: plain-language verdict inputs.
- `api/app/exports.py`: CSV and Markdown reports.
- `api/app/api/routes.py`: FastAPI routes from PRD section 11.
- `api/app/main.py`: app factory, CORS, startup database setup.
- `api/scripts/preview_pairs.py`: random side-by-side pair diffs.
- `api/scripts/seed_demo.py`: full seeded demo run.

## 3. Build order and verification tests

### Phase 0: foundation

Build:

- Git repository, `.gitignore`, `.env.example`, Python dependencies, package layout.
- Settings, database session, all SQLAlchemy models.
- FastAPI app with `GET /health`.

Prove:

- `python -c` imports app and creates tables.
- `pytest tests/test_api.py::test_health` passes.
- `curl /health` returns status and database info.

### Phase 1: synthetic data

Build:

- Six roles, 33 base CVs per role, 11 per tier.
- Gender, origin, and age variants.
- Anonymizer.
- `scripts/preview_pairs.py`.

Prove:

- `test_generator.py`: counts, tier balance, deterministic output.
- `test_generator.py`: every pair differs only in intended fields.
- `test_anonymizer.py`: no names, pronouns, graduation years, or age cues remain.
- `python api/scripts/preview_pairs.py --pairs 3` prints readable diffs.

### Phase 2: providers

Build:

- Provider protocol and strict result validation.
- Mock provider with tier quality signal, planted group bias, repeat noise.
- OpenAI-compatible and Anthropic-compatible adapters with retry and backoff.
- Database cache and budget guard support.

Prove:

- `test_providers.py`: mock is deterministic, tier ordered, bias configurable.
- `test_providers.py`: stubbed HTTP response parses correctly for both real adapters.
- `test_providers.py`: malformed JSON retries and then fails.
- `test_runner.py`: cache key reuse and budget abort.

### Phase 3: runner

Build:

- Run and run-model creation.
- Repeats, resume, progress calculation, prompt text storage.
- Mitigation text transformation.

Prove:

- `test_runner.py`: resumable run skips existing scores.
- `test_runner.py`: progress reaches 100 percent.
- `test_runner.py`: budget cap aborts before overrun.
- `test_runner.py`: anonymized scores use anonymized text and prompt version recorded.

### Phase 4: audit engine

Build:

- Bootstrap, permutation, effect size, noise floor, shortlist ratio, Holm.
- Accuracy and AUC.
- Reductions versus baseline.
- Verdict thresholds.

Prove:

- `test_stats.py`: known-answer tests for every statistic.
- `test_audit.py`: planted 0.5 bias detected, CI excludes zero.
- `test_audit.py`: zero bias not flagged beyond noise floor.
- `test_verdict.py`: pass and fail accuracy gate outcomes.
- At least 80 percent coverage of `app/audit`.

### Phase 5: API and exports

Build:

- All PRD endpoints, dashboard aggregate, exports.
- API tests with an isolated temporary SQLite database.

Prove:

- `test_api.py`: health, runs, execute, progress, audits, accuracy, verdict, dashboard.
- `test_exports.py`: CSV headers and row counts, Markdown sections.
- `curl` examples recorded in `docs/VERIFICATION.md`.

### Phase 6: demo, dashboard, docs

Build:

- `scripts/seed_demo.py` with three mock models, four mitigations, planted bias.
- Next.js app with eight pages, Recharts charts, themes, accessibility, exports.
- README, METHOD, DECISIONS, VERIFICATION.
- Screenshots at desktop and phone widths.

Prove:

- `make setup`, `make seed`, `make test`, `make dev` (or documented Windows equivalents).
- API and web run, dashboard pages load with seeded data.
- One model passes accuracy, one fails.
- Screenshots saved for every page at both widths.
- Ruff, mypy, eslint, tsc all pass.

## 4. Commit sequence

One commit after each phase:

- `phase-0: scaffold api, settings, database models`
- `phase-1: synthetic cv generator and anonymizer`
- `phase-2: llm providers, mock bias model, cache and budget`
- `phase-3: resumable scoring runner`
- `phase-4: audit statistics, accuracy and verdict`
- `phase-5: api endpoints and exports`
- `phase-6: demo seed, dashboard and documentation`
