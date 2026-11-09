from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.base import ProviderResult
from app.models import LLMCache


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_cache_parts(
    provider: str,
    model: str,
    prompt_version: str,
    cv_text: str,
    prompt: str,
    repeat: int,
    temperature: float,
) -> tuple[str, str, str]:
    variant_key = _sha256(cv_text)
    prompt_hash = _sha256(prompt)
    cache_key = _sha256(
        "|".join(
            [
                provider,
                model,
                prompt_version,
                variant_key,
                prompt_hash,
                str(repeat),
                f"{temperature:.4f}",
            ]
        )
    )
    return cache_key, variant_key, prompt_hash


def get_cached(db: Session, cache_key: str) -> LLMCache | None:
    return db.scalar(select(LLMCache).where(LLMCache.cache_key == cache_key))


def store_cached(
    db: Session,
    *,
    cache_key: str,
    variant_key: str,
    prompt_hash: str,
    provider: str,
    model: str,
    prompt_version: str,
    repeat: int,
    result: ProviderResult,
) -> LLMCache:
    entry = LLMCache(
        cache_key=cache_key,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        variant_key=variant_key,
        repeat=repeat,
        prompt_hash=prompt_hash,
        score=result.score,
        reason=result.reason,
        latency_ms=result.latency_ms,
        cost_usd=result.cost_usd,
    )
    db.add(entry)
    return entry
