from __future__ import annotations

from pydantic import BaseModel, Field


class CreateRunRequest(BaseModel):
    name: str = Field(default="FairScreen demo run", min_length=1, max_length=160)
    provider: str = Field(default="mock", min_length=1, max_length=32)
    models: list[str] | None = None
    mitigations: list[str] | None = None
    seed: int | None = Field(default=None, ge=0)
    repeats: int = Field(default=3, ge=1, le=10)
    budget_cap_usd: float = Field(default=5.0, gt=0.0)
    shortlist_cutoff: float = Field(default=7.0, ge=0.0, le=10.0)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    bases_per_role: int = Field(default=33, ge=1, le=200)
    execute: bool = True
