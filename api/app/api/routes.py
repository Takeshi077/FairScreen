from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app import __version__
from app.config import settings
from app.db import get_db
from app.models import Run

router = APIRouter()


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
