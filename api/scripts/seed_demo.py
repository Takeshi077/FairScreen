from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))

from sqlalchemy import func, select  # noqa: E402

from app.audit.engine import run_all_audits  # noqa: E402
from app.audit.verdict import verdict_for_run  # noqa: E402
from app.cvs.generator import save_dataset  # noqa: E402
from app.db import Base, SessionLocal, engine, init_db  # noqa: E402
from app.llm.mock import simulated_model_names  # noqa: E402
from app.models import AccuracyResult, AuditResult, BaseCV, CVVariant, Score  # noqa: E402
from app.runner import DEFAULT_MITIGATIONS, create_run, execute_run  # noqa: E402


def main() -> None:
    print("Resetting demo database.")
    init_db()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        dataset = save_dataset(db, seed=2026, bases_per_role=33)
        print(f"Created {dataset['base_cvs']} base CVs and {dataset['variants']} variants.")

        run = create_run(
            db,
            name="Demo audit: three simulated screeners",
            provider="mock",
            models=simulated_model_names(),
            mitigations=DEFAULT_MITIGATIONS,
            seed=2026,
            repeats=3,
            budget_cap_usd=5.0,
            shortlist_cutoff=7.0,
            ensure_data=False,
        )
        print(f"Created run {run.id}. Scoring with simulated models.")
        execute_run(db, run.id)
        print("Computing audits, accuracy and verdict inputs.")
        run_all_audits(db, run.id)
        verdict = verdict_for_run(db, run.id)

        score_count = db.scalar(select(func.count()).select_from(Score)) or 0
        audit_count = db.scalar(select(func.count()).select_from(AuditResult)) or 0
        accuracy_count = db.scalar(select(func.count()).select_from(AccuracyResult)) or 0
        summary = {
            "run_id": run.id,
            "run_name": run.name,
            "base_cvs": db.scalar(select(func.count()).select_from(BaseCV)),
            "variants": db.scalar(select(func.count()).select_from(CVVariant)),
            "scores": score_count,
            "audits": audit_count,
            "accuracy_rows": accuracy_count,
            "models": [
                {
                    "model": model["model"],
                    "gap_found": model["gap_found"],
                    "fix_worked": model["fix_worked"],
                    "quality_kept": model["quality_kept"],
                    "chosen_mitigation": model["chosen_mitigation"],
                    "summary": model["summary"],
                }
                for model in cast(list[dict[str, Any]], verdict["models"])
            ],
        }
        print(json.dumps(summary, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
