# FairScreen decisions log

This file records choices made where the PRD was missing, silent, or ambiguous.

## D001: Reconstructed PRD

The repository did not contain `docs/PRD.md` at the start of work. The only product source was `DataNova_FairScreen_Proposal.pptx` plus the master build prompt. I reconstructed `docs/PRD.md` from both, treating the master prompt as authoritative where they differ. This is the largest deviation from the instruction to "make sure PRD is already in the repo".

## D002: Python interpreter

The spec asks for Python 3.11. The available interpreter is Python 3.14.5. Code targets 3.11 syntax and avoids 3.14-only features. Dependency versions are pinned to versions that install on both. Verification is performed on 3.14.5. Mypy uses `python_version = "3.14"` because the installed NumPy type stubs use syntax that mypy rejects under a 3.11 target.

## D003: Origin names hold gender constant

To avoid confounding gender with name origin, all origin-test names are male-coded first names with origin-specific full names. Gender tests hold the surname constant and vary only the first name.

## D004: Age signal fields

Age variants change exactly two rendered fields: graduation year and stated years of experience. CV employment bullets contain no dates, so no extra fields need to change. This keeps the pair-diff contract strict.

## D005: Noise floor definition

The repeat noise floor is 1.96 times the pooled within-variant repeat standard deviation of individual scores. This is a practical noise band for a single score, not a confidence interval for the mean gap. Mean-gap uncertainty is reported separately by the bootstrap CI.

## D006: Verdict "fix worked" rule

A fix is considered worked only when every baseline comparison with a significant gap has a statistically supported reduction under the chosen mitigation and the mitigation's 95 percent CI includes zero for that comparison. The chosen mitigation is `combined` when present, otherwise the mitigation with the smallest mean absolute gap. This is stricter than "any gap shrank" and prevents a cosmetic reduction from being reported as a fix.

## D007: Origin comparisons use Anglo as reference

Origin audits compare each of the four non-Anglo groups to the Anglo group. This gives four interpretable comparisons instead of ten pairwise combinations and matches the dashboard grouping.

## D008: One demo run contains all models

The seed script creates one completed run containing three simulated models and four mitigations. This keeps the dashboard's model comparison and before/after views on the same run and avoids cross-run joins.

## D009: Simulated accuracy failure is intentional

Simulated model C applies extra score noise under mitigation conditions. This is a deliberate demo behavior so the dashboard shows one model passing and one failing the 2 point accuracy gate, as required by the Definition of Done. It is clearly labelled simulated data.

## D010: Mock cost and budget

Mock calls cost zero. The budget guard is still implemented and tested with a fake priced provider. Real adapters use configurable per-million-token prices from environment variables.

## D011: No external font download at build time

The editorial look uses local serif and sans font stacks instead of Google Fonts. This keeps builds and screenshots offline-friendly and avoids network failures.

## D012: Windows verification

The host is Windows and GNU make was not installed. A Makefile is provided for the required commands. If make remains unavailable after setup attempts, equivalent PowerShell commands are recorded in `docs/VERIFICATION.md` and a `scripts/dev.ps1` helper is used for the live demo.

## D013: Statistical correction scope

Holm correction is applied across all comparisons for a given mitigation, pooling attributes and models. This is a conservative family definition and matches the requirement to correct across attributes and models.

## D014: Real-provider verification without keys

No API keys were supplied. The real adapter code paths are verified with stubbed HTTP responses through `httpx.MockTransport`, and this is stated as stubbed verification in `docs/VERIFICATION.md`. No real-model results are invented.

## D015: CSV scope

`/runs/{id}/export/csv` exports the audit and accuracy tables, which are the reportable results, not the raw 70,000 score rows. Raw scores remain available through the scores endpoint. The Markdown report includes method, verdict, audit table, accuracy table, and limits.
