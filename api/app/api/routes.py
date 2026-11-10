from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app import __version__
from app.api.schemas import CreateRunRequest
from app.api.serializers import (
    accuracy_payload,
    accuracy_rows,
    audit_rows,
    dashboard_payload,
    export_csv,
    export_markdown,
    run_base_payload,
    run_detail_payload,
    score_payload,
    shortlist_payload,
    variant_payload,
)
from app.audit.engine import audit_payload, run_all_audits
from app.audit.verdict import verdict_for_run
from app.config import settings
from app.db import get_db
from app.llm.base import BudgetExceededError, ProviderConfigurationError
from app.llm.registry import default_models
from app.models import AuditResult, BaseCV, CVVariant, Run, RunModel, Score
from app.runner import create_run, execute_run, progress_for_run

router = APIRouter()

DEFAULT_PAIR_GROUPS = {
    "gender": ("woman", "man"),
    "name_origin": ("african", "anglo"),
    "age": ("senior", "mid_career"),
}


def _get_run(db: Session, run_id: str) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, object]:
    db.execute(text("SELECT 1"))
    run_count = db.scalar(select(func.count()).select_from(Run)) or 0
    simulated = (
        db.scalar(select(func.count()).select_from(Run).where(Run.is_simulated.is_(True))) or 0
    )
    return {
        "status": "ok",
        "version": __version__,
        "database": "sqlite" if settings.resolved_database_url.startswith("sqlite") else "postgres",
        "provider": settings.llm_provider,
        "runs": int(run_count),
        "simulated_runs": int(simulated),
    }


@router.get("/")
def root() -> dict[str, str]:
    return {
        "name": "FairScreen API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/runs")
def list_runs(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    variant_count = db.scalar(select(func.count()).select_from(CVVariant)) or 0
    total = db.scalar(select(func.count()).select_from(Run)) or 0
    runs = list(
        db.scalars(select(Run).order_by(Run.created_at.desc(), Run.id).limit(limit).offset(offset))
    )
    return {
        "items": [run_base_payload(db, run, variant_count=variant_count) for run in runs],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


@router.post("/runs", status_code=201)
def create_run_endpoint(
    payload: CreateRunRequest, db: Session = Depends(get_db)
) -> dict[str, object]:
    provider = payload.provider.lower()
    try:
        models = payload.models or default_models(provider)
        run = create_run(
            db,
            name=payload.name,
            provider=provider,
            models=models,
            mitigations=payload.mitigations,
            seed=payload.seed,
            repeats=payload.repeats,
            budget_cap_usd=payload.budget_cap_usd,
            shortlist_cutoff=payload.shortlist_cutoff,
            temperature=payload.temperature,
            bases_per_role=payload.bases_per_role,
            ensure_data=True,
        )
    except (ValueError, ProviderConfigurationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.execute:
        try:
            execute_run(db, run.id)
        except BudgetExceededError:
            db.refresh(run)
            return run_detail_payload(db, run)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Run execution failed: {exc}") from exc
        run_all_audits(db, run.id)
        db.refresh(run)
    return run_detail_payload(db, run)


@router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    return run_detail_payload(db, _get_run(db, run_id))


@router.post("/runs/{run_id}/execute")
def execute_run_endpoint(run_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    run = _get_run(db, run_id)
    if run.status == "completed":
        existing = (
            db.scalar(
                select(func.count()).select_from(AuditResult).where(AuditResult.run_id == run.id)
            )
            or 0
        )
        if not existing:
            run_all_audits(db, run.id)
        db.refresh(run)
        return run_detail_payload(db, run)
    try:
        execute_run(db, run.id)
    except BudgetExceededError:
        db.refresh(run)
        return run_detail_payload(db, run)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Run execution failed: {exc}") from exc
    run_all_audits(db, run.id)
    db.refresh(run)
    return run_detail_payload(db, run)


@router.get("/runs/{run_id}/progress")
def get_progress(run_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    return progress_for_run(db, _get_run(db, run_id))


@router.get("/runs/{run_id}/audits")
def get_audits(
    run_id: str,
    db: Session = Depends(get_db),
    model: str | None = Query(default=None),
    mitigation: str | None = Query(default=None),
) -> dict[str, object]:
    run = _get_run(db, run_id)
    rows = audit_rows(db, run.id, model, mitigation)
    return {
        "run_id": run.id,
        "is_simulated": run.is_simulated,
        "items": [audit_payload(row) for row in rows],
        "total": len(rows),
    }


@router.get("/runs/{run_id}/accuracy")
def get_accuracy(
    run_id: str,
    db: Session = Depends(get_db),
    model: str | None = Query(default=None),
    mitigation: str | None = Query(default=None),
) -> dict[str, object]:
    run = _get_run(db, run_id)
    rows = accuracy_rows(db, run.id, model, mitigation)
    return {
        "run_id": run.id,
        "is_simulated": run.is_simulated,
        "items": [accuracy_payload(row) for row in rows],
        "total": len(rows),
    }


@router.get("/runs/{run_id}/shortlist")
def get_shortlist(
    run_id: str,
    db: Session = Depends(get_db),
    model: str | None = Query(default=None),
    mitigation: str | None = Query(default=None),
) -> dict[str, object]:
    run = _get_run(db, run_id)
    rows = audit_rows(db, run.id, model, mitigation)
    return {
        "run_id": run.id,
        "is_simulated": run.is_simulated,
        "items": [shortlist_payload(row) for row in rows],
        "total": len(rows),
    }


@router.get("/runs/{run_id}/verdict")
def get_verdict(run_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    run = _get_run(db, run_id)
    return verdict_for_run(db, run.id)


@router.get("/runs/{run_id}/dashboard")
def get_dashboard(run_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    return dashboard_payload(db, _get_run(db, run_id))


@router.get("/runs/{run_id}/scores")
def get_scores(
    run_id: str,
    db: Session = Depends(get_db),
    model: str | None = Query(default=None),
    mitigation: str | None = Query(default=None),
    attribute: str | None = Query(default=None),
    group: str | None = Query(default=None),
    include_prompt: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    run = _get_run(db, run_id)
    filters = [Score.run_id == run.id]
    if model:
        filters.append(Score.model == model)
    if mitigation:
        filters.append(Score.mitigation == mitigation)
    if attribute:
        filters.append(CVVariant.attribute == attribute)
    if group:
        filters.append(CVVariant.group_name == group)
    total = (
        db.scalar(
            select(func.count())
            .select_from(Score)
            .join(CVVariant, Score.variant_id == CVVariant.id)
            .where(*filters)
        )
        or 0
    )
    rows = db.execute(
        select(Score, CVVariant, BaseCV)
        .join(CVVariant, Score.variant_id == CVVariant.id)
        .join(BaseCV, CVVariant.base_cv_id == BaseCV.id)
        .where(*filters)
        .order_by(Score.id)
        .limit(limit)
        .offset(offset)
    ).all()
    items: list[dict[str, object]] = []
    for score, variant, base in rows:
        item = score_payload(score)
        item.update(variant_payload(variant, base))
        if include_prompt:
            item["prompt_text"] = score.prompt_text
        items.append(item)
    return {
        "run_id": run.id,
        "items": items,
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


@router.get("/runs/{run_id}/pairs")
def get_pairs(
    run_id: str,
    db: Session = Depends(get_db),
    model: str | None = Query(default=None),
    mitigation: str = Query(default="none"),
    attribute: str = Query(default="gender"),
    group_a: str | None = Query(default=None),
    group_b: str | None = Query(default=None),
    role: str | None = Query(default=None),
    tier: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    run = _get_run(db, run_id)
    defaults = DEFAULT_PAIR_GROUPS.get(attribute)
    if defaults is None and (group_a is None or group_b is None):
        raise HTTPException(status_code=400, detail=f"No default groups for attribute: {attribute}")
    resolved_a = group_a or (defaults[0] if defaults else "")
    resolved_b = group_b or (defaults[1] if defaults else "")
    model_statement = select(RunModel).where(
        RunModel.run_id == run.id, RunModel.mitigation == mitigation
    )
    if model:
        model_statement = model_statement.where(RunModel.model_name == model)
    run_model = db.scalars(model_statement.order_by(RunModel.id)).first()
    if run_model is None:
        raise HTTPException(status_code=404, detail="Run model and mitigation not found")

    raw_rows: list[Any] = list(
        db.execute(
            select(
                CVVariant.base_cv_id,
                BaseCV.role,
                BaseCV.tier,
                CVVariant.group_name,
                CVVariant.label,
                CVVariant.id,
                CVVariant.text,
                func.avg(Score.score),
            )
            .select_from(Score)
            .join(CVVariant, Score.variant_id == CVVariant.id)
            .join(BaseCV, CVVariant.base_cv_id == BaseCV.id)
            .where(Score.run_model_id == run_model.id, CVVariant.attribute == attribute)
            .where(*([BaseCV.role == role] if role else []))
            .where(*([BaseCV.tier == tier] if tier else []))
            .group_by(
                CVVariant.base_cv_id,
                BaseCV.role,
                BaseCV.tier,
                CVVariant.group_name,
                CVVariant.label,
                CVVariant.id,
                CVVariant.text,
            )
        ).all()
    )
    lookup: dict[tuple[int, str], dict[str, Any]] = {}
    for (
        base_cv_id,
        row_role,
        row_tier,
        group_name,
        label,
        variant_id,
        cv_text,
        mean_score,
    ) in raw_rows:
        lookup[(base_cv_id, group_name)] = {
            "label": label,
            "variant_id": variant_id,
            "text": cv_text,
            "score": float(mean_score),
            "role": row_role,
            "tier": row_tier,
        }
    base_ids = sorted(
        {
            base_cv_id
            for (base_cv_id, group_name) in lookup
            if group_name in {resolved_a, resolved_b}
        }
    )
    paired = [
        base_cv_id
        for base_cv_id in base_ids
        if (base_cv_id, resolved_a) in lookup and (base_cv_id, resolved_b) in lookup
    ]
    total = len(paired)
    items: list[dict[str, object]] = []
    for base_cv_id in paired[offset : offset + limit]:
        left = lookup[(base_cv_id, resolved_a)]
        right = lookup[(base_cv_id, resolved_b)]
        items.append(
            {
                "base_cv_id": base_cv_id,
                "role": left["role"],
                "tier": left["tier"],
                "attribute": attribute,
                "group_a": resolved_a,
                "group_b": resolved_b,
                "label_a": left["label"],
                "label_b": right["label"],
                "variant_id_a": left["variant_id"],
                "variant_id_b": right["variant_id"],
                "score_a": left["score"],
                "score_b": right["score"],
                "gap": float(left["score"]) - float(right["score"]),
                "text_a": left["text"],
                "text_b": right["text"],
            }
        )
    return {
        "run_id": run.id,
        "is_simulated": run.is_simulated,
        "model": run_model.model_name,
        "mitigation": mitigation,
        "attribute": attribute,
        "group_a": resolved_a,
        "group_b": resolved_b,
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/runs/{run_id}/export/csv")
def export_csv_endpoint(run_id: str, db: Session = Depends(get_db)) -> Response:
    run = _get_run(db, run_id)
    content = export_csv(db, run)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="fairscreen_{run.id}_audit.csv"',
            "X-FairScreen-Simulated": str(run.is_simulated).lower(),
        },
    )


@router.get("/runs/{run_id}/export/markdown")
def export_markdown_endpoint(run_id: str, db: Session = Depends(get_db)) -> Response:
    run = _get_run(db, run_id)
    content = export_markdown(db, run)
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="fairscreen_{run.id}_report.md"',
            "X-FairScreen-Simulated": str(run.is_simulated).lower(),
        },
    )
