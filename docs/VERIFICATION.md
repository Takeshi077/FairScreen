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

Pending.

## Phase 4

Pending.

## Phase 5

Pending.

## Phase 6

Pending.
