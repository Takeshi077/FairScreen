# Verification log

This file is appended as each phase is completed. Command output is pasted verbatim where practical. Dates are local.

## Environment

- OS: Windows 11, PowerShell 5.1
- Python: 3.14.5
- Node: 24.16.0
- npm: 11.13.0
- Git: 2.53.0
- GNU make: not initially installed

## Phase 0

Commands:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest api/tests/test_api_smoke.py -q
.\.venv\Scripts\python.exe -m ruff check api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir api --port 8010
Invoke-RestMethod http://127.0.0.1:8010/health
```

Results:

```text
pytest: 2 passed, 1 third-party deprecation warning
ruff: All checks passed!
health: {"status":"ok","version":"1.0.0","database":"sqlite","provider":"mock","runs":0,"simulated_runs":0}
```

GNU make was installed with winget (`ezwinports.make` 4.4.1). Each new shell may need the winget package bin directory added to PATH. The Makefile uses the repository `.venv`.

## Phase 1

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest api/tests/test_generator.py api/tests/test_anonymizer.py -q
.\.venv\Scripts\python.exe -m ruff check api
.\.venv\Scripts\python.exe api/scripts/preview_pairs.py --pairs 2 --bases-per-role 6
```

Results:

```text
pytest: 11 passed
ruff: All checks passed!
preview: printed matched pairs across roles and attributes with only the intended lines marked as changes.
```

Dataset facts verified by tests:

- 6 roles, 33 base CVs per role, 11 per tier, 198 base CVs total.
- 10 variants per base: 2 gender, 5 origin, 3 age. 1,980 variants total.
- Gender and origin pairs differ only in the full name line.
- Age pairs differ only in the years-of-experience line and graduation-year line.
- Anonymizing every variant removes names, pronouns, four-digit years, graduation years, and age cues.
- Anonymized variants within one base and attribute are identical, so identity signal cannot leak.

## Phase 2

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest api/tests/test_providers.py -q
.\.venv\Scripts\python.exe -m ruff check api
.\.venv\Scripts\python.exe -m mypy
```

Results:

```text
pytest: 25 passed
ruff: All checks passed!
mypy: Success: no issues found in 23 source files
```

Provider evidence:

- Mock scores are deterministic for the same model, prompt, repeat and settings.
- Repeat runs produce different seeded noise.
- Tier means are ordered strong > average > weak by wide margins.
- A planted 0.5 point gender bias produces exactly a 0.5 point matched gap when noise is disabled.
- Skills-only reduces the planted gap; anonymization removes it.
- OpenAI-compatible and Anthropic-compatible adapters were exercised through `httpx.MockTransport` with stubbed HTTP responses. This is stubbed verification, not a live API call.
- Malformed JSON and HTTP 500 responses retry with backoff and then fail with a clear provider error.
- Strict JSON validation rejects out-of-range scores, booleans, string scores, NaN, missing keys and empty reasons.
- Cache key includes provider, model, prompt version, CV hash, prompt hash, repeat and temperature.
- Budget guard raises before a call would exceed the cap.

## Phase 3

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest api/tests/test_runner.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check api
.\.venv\Scripts\python.exe -m mypy
```

Results:

```text
test_runner: 9 passed
full suite: 47 passed
ruff: All checks passed!
mypy: Success: no issues found in 24 source files
```

Runner evidence:

- Runs build one row per model and mitigation combination.
- A completed run of 10 variants x 2 repeats produced 20 scores and progress of 100 percent.
- Prompt text, model, temperature, mitigation, reason, latency and timestamp are stored on each score.
- Anonymization runs receive text whose first line is `Candidate` and with no graduation or years-of-experience lines.
- Resume skips pre-existing scores and only scores the missing rows.
- A second run with the same model, prompt, variant, repeat and temperature made zero provider calls and reused all 20 cached scores.
- A priced fake provider with a $1.00 cap aborted after one $0.60 call, before the second call would have exceeded the cap. The run status was `aborted`, cost was $0.60, and only one score existed.

## Phase 4

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest api/tests/test_audit_stats.py api/tests/test_audit_engine.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check api
.\.venv\Scripts\python.exe -m mypy
```

Results:

```text
audit tests: 17 passed
full suite: 64 passed
ruff: All checks passed!
mypy: Success: no issues found in 27 source files
```

Audit evidence:

- Known-answer tests cover mean gap, bootstrap CI, paired permutation p-values, Cohen's dz, Holm adjustment, shortlist ratio, repeat noise floor, pairwise ranking accuracy, and bootstrap reduction.
- A synthetic dataset with a planted 0.5 point woman-versus-man gap across 40 matched pairs produced a mean gap near -0.50, a 95 percent CI entirely below zero, a significant audit flag, an adjusted p-value below 0.01, and a large negative effect size.
- A zero-bias synthetic dataset did not produce a significant flag, its CI included zero, and its mean gap stayed inside the repeat noise floor.
- A synthetic baseline with a 0.5 point gap and a combined mitigation with no gap produced a supported reduction with a CI above zero. The verdict marked the gap found, the fix worked, and quality kept.
- Holm adjustment is applied across all comparisons for a mitigation, pooling attributes and models.
- Verdict logic follows D006: every significant baseline comparison must have a supported reduction and a mitigation CI that includes zero.

## Phase 5

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest api/tests/test_api.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check api
.\.venv\Scripts\python.exe -m mypy
```

Results:

```text
API tests: 9 passed
full suite: 73 passed
ruff: All checks passed!
mypy: Success: no issues found in 29 source files
```

API evidence:

- `POST /runs` creates and optionally executes a run. A small smoke run made 60 CV variants, 120 scores across two mitigations, and audit plus accuracy rows.
- `GET /runs` and `GET /runs/{id}` return status, provider, settings, counts, model rows and simulated labels.
- `GET /runs/{id}/progress` reaches 100 percent for a completed run.
- `GET /runs/{id}/dashboard` returns run metadata, verdict, progress, audits, accuracy, shortlist rows and mitigation labels in one response.
- `GET /runs/{id}/audits`, `/accuracy`, `/shortlist`, `/scores` and `/pairs` return filtered, paginated data. `pairs` returns matched texts and mean scores for the two selected groups.
- `GET /runs/{id}/export/csv` returns an attachment with a header row, both audit and accuracy tables, the run id, and a simulated-data response header.
- `GET /runs/{id}/export/markdown` returns a report with run details, verdict, audit table, accuracy table, method and limits, and a simulated-data notice.
- Unknown run ids return 404 on every run endpoint. Unknown mitigations return 400.
- `execute=false` leaves a run pending, and `POST /runs/{id}/execute` completes it and computes audits.

## Phase 6

Pending.
