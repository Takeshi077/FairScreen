from __future__ import annotations

import numpy as np
import pytest
from sqlalchemy import select

from app.audit.engine import run_all_audits
from app.audit.verdict import verdict_for_run
from app.cvs.generator import save_dataset
from app.models import AuditResult, BaseCV, CVVariant, Score
from app.runner import create_run

TIER_SCORES = {"weak": 5.0, "average": 6.5, "strong": 8.0}


@pytest.fixture()
def seeded(clean_db, db):
    save_dataset(db, seed=11, bases_per_role=40, roles=["Software Engineer"])
    return db


def _make_run(db, mitigations: list[str]):
    return create_run(
        db,
        name="audit test",
        provider="mock",
        models=["Mock-Screen-A"],
        mitigations=mitigations,
        seed=11,
        repeats=3,
        budget_cap_usd=10.0,
        ensure_data=False,
    )


def _insert_scores(
    db,
    run,
    mitigation: str,
    woman_bias: float,
    noise: float,
    noise_seed: int,
) -> None:
    run_model = next(model for model in run.run_models if model.mitigation == mitigation)
    rows = db.execute(
        select(CVVariant.id, CVVariant.base_cv_id, CVVariant.group_name, BaseCV.tier)
        .join(BaseCV, CVVariant.base_cv_id == BaseCV.id)
        .where(CVVariant.attribute == "gender")
        .order_by(CVVariant.id)
    ).all()
    rng = np.random.default_rng(noise_seed)
    for variant_id, _, group, tier in rows:
        bias = woman_bias if group == "woman" else 0.0
        for repeat in range(run.repeats):
            value = TIER_SCORES[tier] + bias + float(rng.normal(0.0, noise))
            db.add(
                Score(
                    run_id=run.id,
                    run_model_id=run_model.id,
                    variant_id=variant_id,
                    repeat=repeat,
                    score=min(10.0, max(0.0, value)),
                    reason="synthetic test score",
                    latency_ms=1,
                    prompt_text="prompt",
                    model=run_model.model_name,
                    temperature=run_model.temperature,
                    mitigation=mitigation,
                )
            )
    db.commit()


def _gender_audit(db, run_id: str, mitigation: str) -> AuditResult:
    audit = db.scalars(
        select(AuditResult).where(
            AuditResult.run_id == run_id,
            AuditResult.mitigation == mitigation,
            AuditResult.attribute == "gender",
        )
    ).first()
    assert audit is not None
    return audit


def test_audit_detects_planted_gender_gap(seeded):
    run = _make_run(seeded, ["none"])
    _insert_scores(seeded, run, "none", woman_bias=-0.5, noise=0.12, noise_seed=101)
    run_all_audits(seeded, run.id, n_bootstrap=400, n_permutation=400)

    audit = _gender_audit(seeded, run.id, "none")
    assert audit.n_pairs == 40
    assert audit.mean_gap == pytest.approx(-0.5, abs=0.08)
    assert audit.ci_high < 0.0
    assert audit.significant is True
    assert audit.p_adjusted < 0.01
    assert audit.effect_size < -1.0
    assert audit.noise_floor > 0.0


def test_audit_does_not_flag_zero_bias_beyond_noise_floor(seeded):
    run = _make_run(seeded, ["none"])
    _insert_scores(seeded, run, "none", woman_bias=0.0, noise=0.12, noise_seed=202)
    run_all_audits(seeded, run.id, n_bootstrap=400, n_permutation=400)

    audit = _gender_audit(seeded, run.id, "none")
    assert audit.significant is False
    assert audit.ci_low <= 0.0 <= audit.ci_high
    assert abs(audit.mean_gap) <= audit.noise_floor


def test_audit_computes_supported_reduction(seeded):
    run = _make_run(seeded, ["none", "combined"])
    _insert_scores(seeded, run, "none", woman_bias=-0.5, noise=0.12, noise_seed=301)
    _insert_scores(seeded, run, "combined", woman_bias=0.0, noise=0.12, noise_seed=302)
    run_all_audits(seeded, run.id, n_bootstrap=400, n_permutation=400)

    baseline = _gender_audit(seeded, run.id, "none")
    combined = _gender_audit(seeded, run.id, "combined")
    assert baseline.significant is True
    assert combined.reduction_vs_baseline == pytest.approx(0.5, abs=0.1)
    assert combined.reduction_ci_low > 0.0
    assert combined.reduction_supported is True
    assert combined.ci_low <= 0.0 <= combined.ci_high

    verdict = verdict_for_run(seeded, run.id)
    model = verdict["models"][0]
    assert model["gap_found"] is True
    assert model["fix_worked"] is True
    assert model["quality_kept"] is True
    assert model["chosen_mitigation"] == "combined"
    assert "Combined" in str(model["summary"])
