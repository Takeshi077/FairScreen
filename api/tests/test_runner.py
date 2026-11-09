from __future__ import annotations

import re

import pytest
from sqlalchemy import func, select

from app.cvs.generator import save_dataset
from app.llm.base import BudgetExceededError, Provider, ProviderResult, ScoreSettings
from app.models import Score
from app.runner import create_run, execute_run, progress_for_run


class FakeProvider(Provider):
    name = "fake"

    def __init__(self, cost_per_call: float = 0.0) -> None:
        self.calls: list[tuple[str, str, ScoreSettings]] = []
        self.cost_per_call = cost_per_call

    def score(self, cv_text: str, prompt: str, settings: ScoreSettings) -> ProviderResult:
        self.calls.append((cv_text, prompt, settings))
        return ProviderResult(
            score=5.0 + (settings.repeat % 3) * 0.1,
            reason="fake",
            latency_ms=1,
            cost_usd=self.cost_per_call,
        )

    def estimate_cost(self, cv_text: str, prompt: str, settings: ScoreSettings) -> float:
        return self.cost_per_call


@pytest.fixture()
def seeded(clean_db, db):
    save_dataset(db, seed=7, bases_per_role=1, roles=["Software Engineer"])
    return db


def _make_run(db, **overrides):
    params = {
        "name": "runner test",
        "provider": "mock",
        "models": ["Mock-Screen-A"],
        "mitigations": ["none"],
        "seed": 7,
        "repeats": 2,
        "budget_cap_usd": 10.0,
        "ensure_data": False,
    }
    params.update(overrides)
    return create_run(db, **params)


def test_create_run_builds_run_models(seeded):
    run = _make_run(
        seeded,
        models=["Mock-Screen-A", "Mock-Screen-B"],
        mitigations=["none", "combined"],
    )
    assert run.status == "pending"
    assert run.is_simulated is True
    assert len(run.run_models) == 4
    assert {model.model_name for model in run.run_models} == {"Mock-Screen-A", "Mock-Screen-B"}
    assert {model.mitigation for model in run.run_models} == {"none", "combined"}


def test_create_run_rejects_unknown_mitigation(seeded):
    with pytest.raises(ValueError, match="Unknown mitigations"):
        _make_run(seeded, mitigations=["magic"])


def test_execute_run_completes_and_reports_progress(seeded):
    run = _make_run(seeded, mitigations=["none"], repeats=2)
    provider = FakeProvider()
    execute_run(seeded, run.id, provider_factory=lambda _model: provider)
    seeded.refresh(run)
    assert run.status == "completed"
    assert run.completed_at is not None
    assert len(provider.calls) == 10 * 2
    progress = progress_for_run(seeded, run)
    assert progress["percent"] == 100.0
    assert progress["completed"] == 20
    assert progress["total"] == 20
    assert progress["run_models"][0]["status"] == "completed"
    assert seeded.scalar(select(func.count()).select_from(Score)) == 20


def test_execute_records_prompt_model_temperature_and_mitigation(seeded):
    run = _make_run(seeded, mitigations=["skills_only"], repeats=1)
    provider = FakeProvider()
    execute_run(seeded, run.id, provider_factory=lambda _model: provider)
    score = seeded.scalars(select(Score)).first()
    assert score is not None
    assert "skills-only rubric" in score.prompt_text
    assert score.model == "Mock-Screen-A"
    assert score.temperature == 0.2
    assert score.mitigation == "skills_only"
    assert score.created_at is not None


def test_anonymization_uses_clean_text(seeded):
    run = _make_run(seeded, mitigations=["anonymization"], repeats=1)
    provider = FakeProvider()
    execute_run(seeded, run.id, provider_factory=lambda _model: provider)
    assert provider.calls
    for cv_text, _, _ in provider.calls:
        assert cv_text.splitlines()[0] == "Candidate"
        assert re.search(r"\b(?:Graduated|Years of experience)\b", cv_text) is None
        assert "Sophie" not in cv_text


def test_resume_skips_existing_scores(seeded):
    run = _make_run(seeded, mitigations=["none"], repeats=2)
    run_model = run.run_models[0]
    from app.models import CVVariant

    variant = seeded.scalars(select(CVVariant).order_by(CVVariant.id)).first()
    assert variant is not None
    seeded.add(
        Score(
            run_id=run.id,
            run_model_id=run_model.id,
            variant_id=variant.id,
            repeat=0,
            score=6.0,
            reason="pre-existing",
            latency_ms=1,
            prompt_text="pre-existing",
            model=run_model.model_name,
            temperature=run_model.temperature,
            mitigation=run_model.mitigation,
        )
    )
    seeded.commit()
    provider = FakeProvider()
    execute_run(seeded, run.id, provider_factory=lambda _model: provider)
    seeded.refresh(run)
    assert run.status == "completed"
    assert len(provider.calls) == 10 * 2 - 1
    assert seeded.scalar(select(func.count()).select_from(Score)) == 20


def test_cache_reuses_scores_across_runs(seeded):
    first = _make_run(seeded, mitigations=["none"], repeats=2)
    first_provider = FakeProvider()
    execute_run(seeded, first.id, provider_factory=lambda _model: first_provider)
    assert len(first_provider.calls) == 20

    second = _make_run(seeded, mitigations=["none"], repeats=2)
    second_provider = FakeProvider()
    execute_run(seeded, second.id, provider_factory=lambda _model: second_provider)
    seeded.refresh(second)
    assert second.status == "completed"
    assert len(second_provider.calls) == 0
    cached_scores = seeded.scalars(select(Score).where(Score.run_id == second.id)).all()
    assert len(cached_scores) == 20
    assert all(score.cached for score in cached_scores)


def test_budget_aborts_before_overrun(seeded):
    run = _make_run(seeded, mitigations=["none"], repeats=1, budget_cap_usd=1.0)
    provider = FakeProvider(cost_per_call=0.6)
    with pytest.raises(BudgetExceededError):
        execute_run(seeded, run.id, provider_factory=lambda _model: provider)
    seeded.refresh(run)
    assert run.status == "aborted"
    assert run.error is not None
    assert len(provider.calls) == 1
    assert seeded.scalar(select(func.count()).select_from(Score)) == 1
    assert run.cost_usd == pytest.approx(0.6)


def test_execute_completed_run_is_noop(seeded):
    run = _make_run(seeded, mitigations=["none"], repeats=1)
    provider = FakeProvider()
    execute_run(seeded, run.id, provider_factory=lambda _model: provider)
    first_calls = len(provider.calls)
    execute_run(seeded, run.id, provider_factory=lambda _model: provider)
    assert len(provider.calls) == first_calls
