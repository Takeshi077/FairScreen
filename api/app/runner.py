from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.cvs.anonymizer import anonymize_cv
from app.cvs.generator import save_dataset
from app.llm.base import Budget, BudgetExceededError, Provider, ProviderResult, ScoreSettings
from app.llm.cache import get_cached, make_cache_parts, store_cached
from app.llm.registry import build_provider, default_models
from app.models import CVVariant, Run, RunModel, Score, utcnow
from app.prompts import SCREENING_PROMPT_VERSION, prompt_for_mitigation

DEFAULT_MITIGATIONS = ["none", "anonymization", "skills_only", "combined"]
MITIGATION_LABELS = {
    "none": "Baseline",
    "anonymization": "Anonymization",
    "skills_only": "Skills-only prompt",
    "combined": "Combined",
}
ANONYMIZING_MITIGATIONS = {"anonymization", "combined"}
COMMIT_EVERY = 250


def create_run(
    db: Session,
    *,
    name: str,
    provider: str | None = None,
    models: list[str] | None = None,
    mitigations: list[str] | None = None,
    seed: int | None = None,
    repeats: int | None = None,
    budget_cap_usd: float | None = None,
    shortlist_cutoff: float | None = None,
    temperature: float | None = None,
    bases_per_role: int = 33,
    ensure_data: bool = True,
) -> Run:
    config = get_settings()
    effective_provider = (provider or config.llm_provider).lower()
    effective_models = list(dict.fromkeys(models or default_models(effective_provider)))
    effective_mitigations = list(dict.fromkeys(mitigations or DEFAULT_MITIGATIONS))
    unknown = [item for item in effective_mitigations if item not in DEFAULT_MITIGATIONS]
    if unknown:
        raise ValueError(f"Unknown mitigations: {', '.join(unknown)}")
    if not effective_models:
        raise ValueError("At least one model is required")

    build_provider(effective_provider, effective_models[0]).close()

    if ensure_data:
        existing = db.scalar(select(func.count()).select_from(CVVariant)) or 0
        if not existing:
            save_dataset(db, seed=seed or config.fairscreen_seed, bases_per_role=bases_per_role)

    run = Run(
        name=name,
        provider=effective_provider,
        status="pending",
        seed=seed if seed is not None else config.fairscreen_seed,
        repeats=repeats if repeats is not None else config.fairscreen_repeats,
        budget_cap_usd=(
            budget_cap_usd if budget_cap_usd is not None else config.fairscreen_budget_usd
        ),
        cost_usd=0.0,
        is_simulated=effective_provider == "mock",
        prompt_version=SCREENING_PROMPT_VERSION,
        settings={
            "models": effective_models,
            "mitigations": effective_mitigations,
            "shortlist_cutoff": (
                shortlist_cutoff
                if shortlist_cutoff is not None
                else config.fairscreen_shortlist_cutoff
            ),
            "temperature": temperature if temperature is not None else config.llm_temperature,
            "bases_per_role": bases_per_role,
        },
    )
    run.settings["shortlist_cutoff"] = float(run.settings["shortlist_cutoff"])
    run.settings["temperature"] = float(run.settings["temperature"])
    db.add(run)
    db.flush()
    for model in effective_models:
        for mitigation in effective_mitigations:
            db.add(
                RunModel(
                    run_id=run.id,
                    model_name=model,
                    provider=effective_provider,
                    temperature=float(run.settings["temperature"]),
                    mitigation=mitigation,
                    display_name=f"{model} / {MITIGATION_LABELS[mitigation]}",
                    status="pending",
                )
            )
    db.commit()
    db.refresh(run)
    return run


def _variant_text(variant: CVVariant, mitigation: str) -> str:
    if mitigation in ANONYMIZING_MITIGATIONS:
        return anonymize_cv(variant.text)
    return variant.text


def _record_score(
    db: Session,
    run: Run,
    run_model: RunModel,
    variant: CVVariant,
    repeat: int,
    prompt: str,
    result: ProviderResult,
    cached: bool,
) -> None:
    db.add(
        Score(
            run_id=run.id,
            run_model_id=run_model.id,
            variant_id=variant.id,
            repeat=repeat,
            score=result.score,
            reason=result.reason,
            latency_ms=result.latency_ms,
            prompt_text=prompt,
            model=run_model.model_name,
            temperature=run_model.temperature,
            mitigation=run_model.mitigation,
            cached=cached,
            cost_usd=0.0 if cached else result.cost_usd,
        )
    )


def execute_run(
    db: Session,
    run_id: str,
    *,
    provider_factory: Callable[[str], Provider] | None = None,
    use_cache: bool | None = None,
) -> Run:
    config = get_settings()
    run = db.get(Run, run_id)
    if run is None:
        raise ValueError(f"Run not found: {run_id}")
    if run.status == "completed":
        return run

    variants = list(db.scalars(select(CVVariant).order_by(CVVariant.id)))
    if not variants:
        raise ValueError("No CV variants exist. Seed the dataset first.")
    run_models = list(
        db.scalars(select(RunModel).where(RunModel.run_id == run.id).order_by(RunModel.id))
    )
    if not run_models:
        raise ValueError(f"Run {run.id} has no models")

    run.status = "running"
    run.started_at = run.started_at or utcnow()
    run.completed_at = None
    run.error = None
    for run_model in run_models:
        if run_model.status != "completed":
            run_model.status = "running"
    db.commit()

    factory = provider_factory or (lambda model: build_provider(run.provider, model))
    providers: dict[str, Provider] = {}
    budget = Budget(cap_usd=run.budget_cap_usd, spent_usd=run.cost_usd)
    cache_enabled = config.fairscreen_cache_enabled if use_cache is None else use_cache
    memory_cache: dict[str, ProviderResult] = {}
    pending = 0

    try:
        for run_model in run_models:
            provider = providers.get(run_model.model_name)
            if provider is None:
                provider = factory(run_model.model_name)
                providers[run_model.model_name] = provider
            prompt_version, prompt = prompt_for_mitigation(run_model.mitigation)
            text_cache: dict[int, str] = {}
            existing = {
                (variant_id, repeat)
                for variant_id, repeat in db.execute(
                    select(Score.variant_id, Score.repeat).where(Score.run_model_id == run_model.id)
                )
            }
            for variant in variants:
                text = text_cache.get(variant.id)
                if text is None:
                    text = _variant_text(variant, run_model.mitigation)
                    text_cache[variant.id] = text
                for repeat in range(run.repeats):
                    if (variant.id, repeat) in existing:
                        continue
                    settings = ScoreSettings(
                        model=run_model.model_name,
                        temperature=run_model.temperature,
                        provider=run.provider,
                        prompt_version=prompt_version,
                        mitigation=run_model.mitigation,
                        repeat=repeat,
                    )
                    key, variant_key, prompt_hash = make_cache_parts(
                        run.provider,
                        run_model.model_name,
                        prompt_version,
                        text,
                        prompt,
                        repeat,
                        run_model.temperature,
                    )
                    result = memory_cache.get(key)
                    cached = result is not None
                    if result is None and cache_enabled:
                        entry = get_cached(db, key)
                        if entry is not None:
                            result = ProviderResult(
                                score=entry.score,
                                reason=entry.reason,
                                latency_ms=entry.latency_ms,
                                cost_usd=0.0,
                            )
                            memory_cache[key] = result
                            cached = True
                    if result is None:
                        estimate = provider.estimate_cost(text, prompt, settings)
                        budget.ensure_can_spend(estimate)
                        result = provider.score(text, prompt, settings)
                        budget.charge(result.cost_usd)
                        memory_cache[key] = result
                        if cache_enabled:
                            store_cached(
                                db,
                                cache_key=key,
                                variant_key=variant_key,
                                prompt_hash=prompt_hash,
                                provider=run.provider,
                                model=run_model.model_name,
                                prompt_version=prompt_version,
                                repeat=repeat,
                                result=result,
                            )
                    _record_score(db, run, run_model, variant, repeat, prompt, result, cached)
                    pending += 1
                    if pending >= COMMIT_EVERY:
                        run.cost_usd = budget.spent_usd
                        db.commit()
                        pending = 0
            run_model.status = "completed"
            run.cost_usd = budget.spent_usd
            db.commit()
        run.status = "completed"
        run.completed_at = utcnow()
        run.cost_usd = budget.spent_usd
        run.error = None
        db.commit()
    except BudgetExceededError as exc:
        run.status = "aborted"
        run.error = str(exc)
        run.cost_usd = budget.spent_usd
        for run_model in run_models:
            if run_model.status != "completed":
                run_model.status = "aborted"
        db.commit()
        raise
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)[:2000]
        run.cost_usd = budget.spent_usd
        for run_model in run_models:
            if run_model.status != "completed":
                run_model.status = "failed"
        db.commit()
        raise
    finally:
        for provider in providers.values():
            provider.close()
    return run


def progress_for_run(db: Session, run: Run) -> dict[str, Any]:
    variant_count = db.scalar(select(func.count()).select_from(CVVariant)) or 0
    run_models = list(
        db.scalars(select(RunModel).where(RunModel.run_id == run.id).order_by(RunModel.id))
    )
    total = variant_count * run.repeats * len(run_models)
    completed = (
        db.scalar(select(func.count()).select_from(Score).where(Score.run_id == run.id)) or 0
    )
    per_model: list[dict[str, Any]] = []
    for run_model in run_models:
        model_count = (
            db.scalar(
                select(func.count()).select_from(Score).where(Score.run_model_id == run_model.id)
            )
            or 0
        )
        model_total = variant_count * run.repeats
        per_model.append(
            {
                "model": run_model.model_name,
                "mitigation": run_model.mitigation,
                "status": run_model.status,
                "completed": int(model_count),
                "total": model_total,
                "percent": round(100 * model_count / model_total, 2) if model_total else 0.0,
            }
        )
    return {
        "run_id": run.id,
        "status": run.status,
        "completed": int(completed),
        "total": int(total),
        "percent": round(100 * completed / total, 2) if total else 0.0,
        "variants": int(variant_count),
        "repeats": run.repeats,
        "run_models": per_model,
        "cost_usd": round(run.cost_usd, 6),
        "budget_cap_usd": run.budget_cap_usd,
        "updated_at": datetime.now(UTC).isoformat(),
    }
