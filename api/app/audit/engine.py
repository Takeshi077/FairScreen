from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.audit.stats import (
    bootstrap_ci,
    bootstrap_reduction,
    cohen_dz,
    holm_adjust,
    mean_gap,
    paired_permutation_test,
    pairwise_accuracy,
    repeat_noise_floor,
    shortlist_ratio,
    stable_seed,
)
from app.config import get_settings
from app.models import AccuracyResult, AuditResult, BaseCV, CVVariant, Run, RunModel, Score

TIER_VALUES = {"weak": 1, "average": 2, "strong": 3}


@dataclass(frozen=True)
class Comparison:
    attribute: str
    group_a: str
    group_b: str
    label: str


COMPARISONS: list[Comparison] = [
    Comparison("gender", "woman", "man", "Woman vs man"),
    Comparison("name_origin", "african", "anglo", "African vs Anglo"),
    Comparison("name_origin", "east_asian", "anglo", "East Asian vs Anglo"),
    Comparison("name_origin", "south_asian", "anglo", "South Asian vs Anglo"),
    Comparison("name_origin", "middle_eastern", "anglo", "Middle Eastern vs Anglo"),
    Comparison("age", "senior", "mid_career", "Senior vs mid career"),
    Comparison("age", "senior", "early_career", "Senior vs early career"),
    Comparison("age", "mid_career", "early_career", "Mid career vs early career"),
]


@dataclass
class AuditComputation:
    comparison: Comparison
    base_ids: list[int]
    diffs: np.ndarray
    n_pairs: int
    mean_gap: float
    ci_low: float
    ci_high: float
    p_value: float
    p_adjusted: float
    effect_size: float
    noise_floor: float
    rate_a: float
    rate_b: float
    ratio: float | None

    @property
    def significant(self) -> bool:
        return self.n_pairs >= 2 and (self.ci_low > 0.0 or self.ci_high < 0.0)


def _load_run_model_scores(
    db: Session, run_model_id: int
) -> dict[tuple[int, str, str], dict[int, float]]:
    rows = db.execute(
        select(
            CVVariant.base_cv_id,
            CVVariant.attribute,
            CVVariant.group_name,
            Score.repeat,
            Score.score,
        )
        .join(CVVariant, Score.variant_id == CVVariant.id)
        .where(Score.run_model_id == run_model_id)
    ).all()
    raw: dict[tuple[int, str, str], dict[int, float]] = defaultdict(dict)
    for base_cv_id, attribute, group_name, repeat, score in rows:
        raw[(base_cv_id, attribute, group_name)][int(repeat)] = float(score)
    return raw


def _compute_comparison(
    comparison: Comparison,
    raw: dict[tuple[int, str, str], dict[int, float]],
    *,
    cutoff: float,
    run_seed: int,
    model: str,
    mitigation: str,
    n_bootstrap: int,
    n_permutation: int,
) -> AuditComputation | None:
    bases_a = {
        base_id
        for (base_id, attribute, group) in raw
        if attribute == comparison.attribute and group == comparison.group_a
    }
    bases_b = {
        base_id
        for (base_id, attribute, group) in raw
        if attribute == comparison.attribute and group == comparison.group_b
    }
    bases = sorted(bases_a & bases_b)
    if len(bases) < 2:
        return None

    diffs: list[float] = []
    means_a: list[float] = []
    means_b: list[float] = []
    repeat_values: list[list[float]] = []
    used_bases: list[int] = []
    for base_id in bases:
        values_a = raw[(base_id, comparison.attribute, comparison.group_a)]
        values_b = raw[(base_id, comparison.attribute, comparison.group_b)]
        common = sorted(set(values_a) & set(values_b))
        if not common:
            continue
        mean_a = float(np.mean([values_a[repeat] for repeat in common]))
        mean_b = float(np.mean([values_b[repeat] for repeat in common]))
        diffs.append(mean_a - mean_b)
        means_a.append(mean_a)
        means_b.append(mean_b)
        repeat_values.append([values_a[repeat] for repeat in common])
        repeat_values.append([values_b[repeat] for repeat in common])
        used_bases.append(base_id)
    if len(diffs) < 2:
        return None

    seed = stable_seed(
        run_seed,
        model,
        mitigation,
        comparison.attribute,
        comparison.group_a,
        comparison.group_b,
    )
    diff_array = np.asarray(diffs, dtype=float)
    ci_low, ci_high = bootstrap_ci(diff_array, n_resamples=n_bootstrap, seed=seed)
    p_value = paired_permutation_test(diff_array, n_resamples=n_permutation, seed=seed + 1)
    rate_a = float(np.mean([1.0 if value >= cutoff else 0.0 for value in means_a]))
    rate_b = float(np.mean([1.0 if value >= cutoff else 0.0 for value in means_b]))
    return AuditComputation(
        comparison=comparison,
        base_ids=used_bases,
        diffs=diff_array,
        n_pairs=len(diffs),
        mean_gap=mean_gap(diff_array),
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
        p_adjusted=1.0,
        effect_size=cohen_dz(diff_array),
        noise_floor=repeat_noise_floor(repeat_values),
        rate_a=rate_a,
        rate_b=rate_b,
        ratio=shortlist_ratio(rate_a, rate_b),
    )


def _accuracy_for_run_model(db: Session, run_model: RunModel) -> AccuracyResult | None:
    rows = db.execute(
        select(CVVariant.id, BaseCV.tier, func.avg(Score.score))
        .select_from(Score)
        .join(CVVariant, Score.variant_id == CVVariant.id)
        .join(BaseCV, CVVariant.base_cv_id == BaseCV.id)
        .where(Score.run_model_id == run_model.id)
        .group_by(CVVariant.id, BaseCV.tier)
    ).all()
    if not rows:
        return None
    scores = [float(row[2]) for row in rows]
    tiers = [TIER_VALUES[str(row[1])] for row in rows]
    accuracy, auc, n_pairs = pairwise_accuracy(scores, tiers)
    return AccuracyResult(
        run_id=run_model.run_id,
        run_model_id=run_model.id,
        model=run_model.model_name,
        mitigation=run_model.mitigation,
        pairwise_accuracy=accuracy,
        auc=auc,
        n_items=len(rows),
        n_pairs=n_pairs,
    )


def run_all_audits(
    db: Session,
    run_id: str,
    *,
    n_bootstrap: int | None = None,
    n_permutation: int | None = None,
) -> list[AuditResult]:
    config = get_settings()
    bootstrap_count = n_bootstrap or config.fairscreen_bootstrap
    permutation_count = n_permutation or config.fairscreen_permutation
    run = db.get(Run, run_id)
    if run is None:
        raise ValueError(f"Run not found: {run_id}")
    run_models = list(
        db.scalars(select(RunModel).where(RunModel.run_id == run.id).order_by(RunModel.id))
    )
    if not run_models:
        return []

    db.execute(delete(AuditResult).where(AuditResult.run_id == run.id))
    db.execute(delete(AccuracyResult).where(AccuracyResult.run_id == run.id))
    db.commit()

    cutoff = float(run.settings.get("shortlist_cutoff", config.fairscreen_shortlist_cutoff))
    computations: dict[tuple[str, str, str, str, str], AuditComputation] = {}
    by_mitigation: dict[str, list[tuple[RunModel, AuditComputation]]] = defaultdict(list)
    raw_by_model: dict[int, dict[tuple[int, str, str], dict[int, float]]] = {}

    for run_model in run_models:
        raw = raw_by_model.setdefault(run_model.id, _load_run_model_scores(db, run_model.id))
        for comparison in COMPARISONS:
            computation = _compute_comparison(
                comparison,
                raw,
                cutoff=cutoff,
                run_seed=run.seed,
                model=run_model.model_name,
                mitigation=run_model.mitigation,
                n_bootstrap=bootstrap_count,
                n_permutation=permutation_count,
            )
            if computation is None:
                continue
            computations[
                (
                    run_model.model_name,
                    run_model.mitigation,
                    comparison.attribute,
                    comparison.group_a,
                    comparison.group_b,
                )
            ] = computation
            by_mitigation[run_model.mitigation].append((run_model, computation))

    for items in by_mitigation.values():
        adjusted = holm_adjust([computation.p_value for _, computation in items])
        for (_, computation), p_adjusted in zip(items, adjusted, strict=True):
            computation.p_adjusted = p_adjusted

    rows: list[AuditResult] = []
    row_lookup: dict[tuple[str, str, str, str, str], AuditResult] = {}
    for mitigation, items in by_mitigation.items():
        for run_model, computation in items:
            row = AuditResult(
                run_id=run.id,
                run_model_id=run_model.id,
                model=run_model.model_name,
                mitigation=mitigation,
                attribute=computation.comparison.attribute,
                group_a=computation.comparison.group_a,
                group_b=computation.comparison.group_b,
                comparison_label=computation.comparison.label,
                n_pairs=computation.n_pairs,
                mean_gap=computation.mean_gap,
                ci_low=computation.ci_low,
                ci_high=computation.ci_high,
                p_value=computation.p_value,
                p_adjusted=computation.p_adjusted,
                effect_size=computation.effect_size,
                noise_floor=computation.noise_floor,
                shortlist_cutoff=cutoff,
                rate_a=computation.rate_a,
                rate_b=computation.rate_b,
                shortlist_ratio=computation.ratio,
                significant=computation.significant,
            )
            db.add(row)
            rows.append(row)
            row_lookup[
                (
                    run_model.model_name,
                    mitigation,
                    computation.comparison.attribute,
                    computation.comparison.group_a,
                    computation.comparison.group_b,
                )
            ] = row

    for key, row in row_lookup.items():
        model, mitigation, attribute, group_a, group_b = key
        if mitigation == "none":
            continue
        baseline = computations.get((model, "none", attribute, group_a, group_b))
        current = computations.get(key)
        if baseline is None or current is None or baseline.diffs.size != current.diffs.size:
            continue
        reduction, ci_low, ci_high = bootstrap_reduction(
            baseline.diffs,
            current.diffs,
            n_resamples=bootstrap_count,
            seed=stable_seed(run.seed, model, attribute, group_a, group_b, "reduction"),
        )
        row.reduction_vs_baseline = reduction
        row.reduction_ci_low = ci_low
        row.reduction_ci_high = ci_high
        row.reduction_supported = bool(reduction > 0 and ci_low > 0)

    db.flush()
    for run_model in run_models:
        accuracy = _accuracy_for_run_model(db, run_model)
        if accuracy is not None:
            db.add(accuracy)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def audit_payload(row: AuditResult) -> dict[str, object]:
    return {
        "id": row.id,
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
        "significant": row.significant,
        "reduction_vs_baseline": row.reduction_vs_baseline,
        "reduction_ci_low": row.reduction_ci_low,
        "reduction_ci_high": row.reduction_ci_high,
        "reduction_supported": row.reduction_supported,
    }
