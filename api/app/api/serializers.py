from __future__ import annotations

import csv
import io
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.engine import audit_payload
from app.audit.verdict import verdict_for_run
from app.models import AccuracyResult, AuditResult, BaseCV, CVVariant, Run, RunModel, Score
from app.runner import progress_for_run

MITIGATION_LABELS = {
    "none": "Baseline",
    "anonymization": "Anonymization",
    "skills_only": "Skills-only prompt",
    "combined": "Combined",
}


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def accuracy_payload(row: AccuracyResult) -> dict[str, Any]:
    return {
        "id": row.id,
        "model": row.model,
        "mitigation": row.mitigation,
        "mitigation_label": MITIGATION_LABELS.get(row.mitigation, row.mitigation),
        "pairwise_accuracy": row.pairwise_accuracy,
        "auc": row.auc,
        "n_items": row.n_items,
        "n_pairs": row.n_pairs,
    }


def run_base_payload(db: Session, run: Run, *, variant_count: int | None = None) -> dict[str, Any]:
    if variant_count is None:
        variant_count = db.scalar(select(func.count()).select_from(CVVariant)) or 0
    run_models = list(
        db.scalars(select(RunModel).where(RunModel.run_id == run.id).order_by(RunModel.id))
    )
    score_count = (
        db.scalar(select(func.count()).select_from(Score).where(Score.run_id == run.id)) or 0
    )
    model_count = len(run_models)
    total = variant_count * run.repeats * model_count
    return {
        "id": run.id,
        "name": run.name,
        "provider": run.provider,
        "status": run.status,
        "seed": run.seed,
        "repeats": run.repeats,
        "budget_cap_usd": run.budget_cap_usd,
        "cost_usd": round(run.cost_usd, 6),
        "is_simulated": run.is_simulated,
        "prompt_version": run.prompt_version,
        "created_at": _iso(run.created_at),
        "started_at": _iso(run.started_at),
        "completed_at": _iso(run.completed_at),
        "error": run.error,
        "variants": variant_count,
        "scores": int(score_count),
        "total_scores": int(total),
        "percent": round(100 * score_count / total, 2) if total else 0.0,
        "models": [
            {
                "model": row.model_name,
                "display_name": row.display_name,
                "mitigation": row.mitigation,
                "mitigation_label": MITIGATION_LABELS.get(row.mitigation, row.mitigation),
                "temperature": row.temperature,
                "status": row.status,
            }
            for row in run_models
        ],
        "settings": run.settings,
    }


def run_detail_payload(db: Session, run: Run) -> dict[str, Any]:
    payload = run_base_payload(db, run)
    audit_count = (
        db.scalar(select(func.count()).select_from(AuditResult).where(AuditResult.run_id == run.id))
        or 0
    )
    accuracy_count = (
        db.scalar(
            select(func.count()).select_from(AccuracyResult).where(AccuracyResult.run_id == run.id)
        )
        or 0
    )
    payload["audit_count"] = int(audit_count)
    payload["accuracy_count"] = int(accuracy_count)
    return payload


def audit_rows(
    db: Session,
    run_id: str,
    model: str | None,
    mitigation: str | None,
    role: str | None = None,
    tier: str | None = None,
) -> list[AuditResult]:
    statement = select(AuditResult).where(AuditResult.run_id == run_id)
    if model:
        statement = statement.where(AuditResult.model == model)
    if mitigation:
        statement = statement.where(AuditResult.mitigation == mitigation)
    # role/tier are reserved for future per-slice audit rows; currently ignored
    # because AuditResult aggregates across all roles and tiers.
    statement = statement.order_by(
        AuditResult.model, AuditResult.mitigation, AuditResult.attribute, AuditResult.group_a
    )
    return list(db.scalars(statement))


def accuracy_rows(
    db: Session, run_id: str, model: str | None, mitigation: str | None
) -> list[AccuracyResult]:
    statement = select(AccuracyResult).where(AccuracyResult.run_id == run_id)
    if model:
        statement = statement.where(AccuracyResult.model == model)
    if mitigation:
        statement = statement.where(AccuracyResult.mitigation == mitigation)
    statement = statement.order_by(AccuracyResult.model, AccuracyResult.mitigation)
    return list(db.scalars(statement))


def shortlist_payload(row: AuditResult) -> dict[str, Any]:
    return {
        "model": row.model,
        "mitigation": row.mitigation,
        "mitigation_label": MITIGATION_LABELS.get(row.mitigation, row.mitigation),
        "attribute": row.attribute,
        "comparison_label": row.comparison_label,
        "group_a": row.group_a,
        "group_b": row.group_b,
        "n_pairs": row.n_pairs,
        "shortlist_cutoff": row.shortlist_cutoff,
        "rate_a": row.rate_a,
        "rate_b": row.rate_b,
        "shortlist_ratio": row.shortlist_ratio,
        "significant": row.significant,
    }


def dashboard_payload(db: Session, run: Run) -> dict[str, Any]:
    audits = audit_rows(db, run.id, None, None)
    accuracy = accuracy_rows(db, run.id, None, None)
    return {
        "run": run_detail_payload(db, run),
        "verdict": verdict_for_run(db, run.id),
        "progress": progress_for_run(db, run),
        "audits": [audit_payload(row) for row in audits],
        "accuracy": [accuracy_payload(row) for row in accuracy],
        "shortlist": [shortlist_payload(row) for row in audits],
        "mitigations": [
            {
                "value": value,
                "label": MITIGATION_LABELS[value],
            }
            for value in ["none", "anonymization", "skills_only", "combined"]
        ],
    }


CSV_FIELDS = [
    "table",
    "simulated",
    "run_id",
    "run_name",
    "model",
    "mitigation",
    "attribute",
    "group_a",
    "group_b",
    "comparison_label",
    "n_pairs",
    "mean_gap",
    "ci_low",
    "ci_high",
    "p_value",
    "p_adjusted",
    "effect_size",
    "noise_floor",
    "shortlist_cutoff",
    "rate_a",
    "rate_b",
    "shortlist_ratio",
    "significant",
    "reduction_vs_baseline",
    "reduction_ci_low",
    "reduction_ci_high",
    "reduction_supported",
    "pairwise_accuracy",
    "auc",
    "n_items",
]


def export_csv(db: Session, run: Run) -> str:
    audits = audit_rows(db, run.id, None, None)
    accuracy = accuracy_rows(db, run.id, None, None)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in audits:
        writer.writerow(
            {
                "table": "audit",
                "simulated": str(run.is_simulated).lower(),
                "run_id": run.id,
                "run_name": run.name,
                "model": row.model,
                "mitigation": row.mitigation,
                "attribute": row.attribute,
                "group_a": row.group_a,
                "group_b": row.group_b,
                "comparison_label": row.comparison_label,
                "n_pairs": row.n_pairs,
                "mean_gap": row.mean_gap,
                "ci_low": row.ci_low,
                "ci_high": row.ci_high,
                "p_value": row.p_value,
                "p_adjusted": row.p_adjusted,
                "effect_size": row.effect_size,
                "noise_floor": row.noise_floor,
                "shortlist_cutoff": row.shortlist_cutoff,
                "rate_a": row.rate_a,
                "rate_b": row.rate_b,
                "shortlist_ratio": row.shortlist_ratio,
                "significant": str(row.significant).lower(),
                "reduction_vs_baseline": row.reduction_vs_baseline,
                "reduction_ci_low": row.reduction_ci_low,
                "reduction_ci_high": row.reduction_ci_high,
                "reduction_supported": (
                    "" if row.reduction_supported is None else str(row.reduction_supported).lower()
                ),
            }
        )
    for accuracy_row in accuracy:
        writer.writerow(
            {
                "table": "accuracy",
                "simulated": str(run.is_simulated).lower(),
                "run_id": run.id,
                "run_name": run.name,
                "model": accuracy_row.model,
                "mitigation": accuracy_row.mitigation,
                "n_pairs": accuracy_row.n_pairs,
                "pairwise_accuracy": accuracy_row.pairwise_accuracy,
                "auc": accuracy_row.auc,
                "n_items": accuracy_row.n_items,
            }
        )
    return buffer.getvalue()


def _fmt(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def _signed(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    return f"{value:+.{digits}f}"


def export_markdown(db: Session, run: Run) -> str:
    verdict = verdict_for_run(db, run.id)
    audits = audit_rows(db, run.id, None, None)
    accuracy = accuracy_rows(db, run.id, None, None)
    lines: list[str] = []
    lines.append(f"# FairScreen report: {run.name}")
    lines.append("")
    if run.is_simulated:
        lines.append(
            "**Simulated data.** These scores come from deterministic mock models, "
            "not from a live vendor model. They demonstrate the audit method."
        )
    else:
        lines.append(
            "**Scoped result.** These results apply only to this model, prompt, "
            "and synthetic test set."
        )
    lines.append("")
    lines.append("## Run")
    lines.append("")
    lines.append(f"- Run ID: `{run.id}`")
    lines.append(f"- Provider: `{run.provider}`")
    lines.append(f"- Status: `{run.status}`")
    lines.append(f"- Seed: {run.seed}")
    lines.append(f"- Repeats: {run.repeats}")
    lines.append(f"- Created: {_iso(run.created_at)}")
    lines.append(f"- Shortlist cutoff: {run.settings.get('shortlist_cutoff', 7.0)}")
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    verdict_models = cast(list[dict[str, Any]], verdict["models"])
    if not verdict_models:
        lines.append("No audit results are available for this run yet.")
    for model in verdict_models:
        lines.append(f"### {model['display_name']}")
        lines.append("")
        lines.append(f"- Gap found: {'Yes' if model['gap_found'] else 'No'}")
        fix_value = model["fix_worked"]
        fix_text = "Not applicable" if fix_value is None else ("Yes" if fix_value else "No")
        lines.append(f"- Fix worked: {fix_text}")
        lines.append(f"- Quality kept: {'Yes' if model['quality_kept'] else 'No'}")
        lines.append(f"- Chosen mitigation: {model['chosen_label']}")
        lines.append(f"- Sample size: {model['sample_size']} matched pairs per comparison")
        lines.append("")
        lines.append(str(model["summary"]))
        lines.append("")
    lines.append("## Audit table")
    lines.append("")
    lines.append(
        "| Model | Mitigation | Comparison | n | Mean gap | 95 percent CI | "
        "p adjusted | Effect size | Noise floor | Shortlist ratio | Significant |"
    )
    lines.append("| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |")
    for row in audits:
        ratio = "" if row.shortlist_ratio is None else f"{row.shortlist_ratio:.2f}"
        lines.append(
            f"| {row.model} | {MITIGATION_LABELS.get(row.mitigation, row.mitigation)} | "
            f"{row.comparison_label} | {row.n_pairs} | {_signed(row.mean_gap)} | "
            f"{_signed(row.ci_low)} to {_signed(row.ci_high)} | {_fmt(row.p_adjusted, 4)} | "
            f"{_fmt(row.effect_size, 2)} | {_fmt(row.noise_floor, 2)} | {ratio} | "
            f"{'Yes' if row.significant else 'No'} |"
        )
    lines.append("")
    lines.append("## Accuracy")
    lines.append("")
    lines.append("| Model | Mitigation | Pairwise accuracy | AUC | Items | Pairs |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
    for accuracy_row in accuracy:
        lines.append(
            f"| {accuracy_row.model} | "
            f"{MITIGATION_LABELS.get(accuracy_row.mitigation, accuracy_row.mitigation)} | "
            f"{_fmt(accuracy_row.pairwise_accuracy, 4)} | "
            f"{_fmt(accuracy_row.auc, 4)} | {accuracy_row.n_items} | "
            f"{accuracy_row.n_pairs} |"
        )
    lines.append("")
    lines.append("## Method and limits")
    lines.append("")
    lines.append(
        "Each base CV has matched variants that differ only in a gender-coded first name, "
        "a name-origin signal, or an age signal. Scores are repeated, and comparisons use "
        "paired mean gaps with seeded bootstrap confidence intervals, paired permutation "
        "tests, Holm correction, effect sizes, shortlist-rate ratios, and a repeat noise floor."
    )
    lines.append("")
    lines.append(
        "Ranking accuracy is pairwise accuracy against known quality tiers. The quality gate "
        "allows a drop of at most 2 percentage points versus baseline."
    )
    lines.append("")
    lines.append(
        "These results describe this model, prompt, and synthetic test set only. They are not "
        "a legal compliance finding and do not generalize to real applicants or to a vendor's "
        "model in general."
    )
    lines.append("")
    return "\n".join(lines)


def score_payload(row: Score) -> dict[str, Any]:
    return {
        "id": row.id,
        "variant_id": row.variant_id,
        "repeat": row.repeat,
        "score": row.score,
        "reason": row.reason,
        "latency_ms": row.latency_ms,
        "model": row.model,
        "temperature": row.temperature,
        "mitigation": row.mitigation,
        "mitigation_label": MITIGATION_LABELS.get(row.mitigation, row.mitigation),
        "cached": row.cached,
        "cost_usd": row.cost_usd,
        "created_at": _iso(row.created_at),
    }


def variant_payload(row: CVVariant, base: BaseCV) -> dict[str, Any]:
    return {
        "variant_id": row.id,
        "base_cv_id": base.id,
        "role": base.role,
        "tier": base.tier,
        "attribute": row.attribute,
        "group": row.group_name,
        "label": row.label,
        "changed_fields": row.changed_fields,
    }
