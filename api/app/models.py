from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class BaseCV(Base):
    __tablename__ = "base_cvs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String(80), index=True)
    tier: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text)
    seed: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    variants: Mapped[list[CVVariant]] = relationship(
        back_populates="base_cv", cascade="all, delete-orphan"
    )


class CVVariant(Base):
    __tablename__ = "cv_variants"
    __table_args__ = (
        UniqueConstraint("base_cv_id", "attribute", "group_name", name="uq_variant_group"),
        Index("ix_variant_attribute_group", "attribute", "group_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    base_cv_id: Mapped[int] = mapped_column(ForeignKey("base_cvs.id"), index=True)
    attribute: Mapped[str] = mapped_column(String(32))
    group_name: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text)
    changed_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    base_cv: Mapped[BaseCV] = relationship(back_populates="variants")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(160))
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    seed: Mapped[int] = mapped_column(Integer, default=2026)
    repeats: Mapped[int] = mapped_column(Integer, default=3)
    budget_cap_usd: Mapped[float] = mapped_column(Float, default=5.0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    prompt_version: Mapped[str] = mapped_column(String(80), default="screening-v1")
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run_models: Mapped[list[RunModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    scores: Mapped[list[Score]] = relationship(back_populates="run", cascade="all, delete-orphan")
    audits: Mapped[list[AuditResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    accuracy: Mapped[list[AccuracyResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class RunModel(Base):
    __tablename__ = "run_models"
    __table_args__ = (
        UniqueConstraint("run_id", "model_name", "mitigation", name="uq_run_model_mitigation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    model_name: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(32))
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    mitigation: Mapped[str] = mapped_column(String(32), default="none")
    display_name: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[Run] = relationship(back_populates="run_models")
    scores: Mapped[list[Score]] = relationship(
        back_populates="run_model", cascade="all, delete-orphan"
    )
    audits: Mapped[list[AuditResult]] = relationship(
        back_populates="run_model", cascade="all, delete-orphan"
    )
    accuracy: Mapped[AccuracyResult | None] = relationship(
        back_populates="run_model", cascade="all, delete-orphan", uselist=False
    )


class LLMCache(Base):
    __tablename__ = "llm_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(80))
    variant_key: Mapped[str] = mapped_column(String(64))
    repeat: Mapped[int] = mapped_column(Integer)
    prompt_hash: Mapped[str] = mapped_column(String(64))
    score: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("run_model_id", "variant_id", "repeat", name="uq_score_repeat"),
        Index("ix_score_run_model", "run_id", "run_model_id"),
        CheckConstraint("score >= 0 AND score <= 10", name="ck_score_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    run_model_id: Mapped[int] = mapped_column(ForeignKey("run_models.id"), index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("cv_variants.id"), index=True)
    repeat: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    prompt_text: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(120))
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    mitigation: Mapped[str] = mapped_column(String(32))
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[Run] = relationship(back_populates="scores")
    run_model: Mapped[RunModel] = relationship(back_populates="scores")
    variant: Mapped[CVVariant] = relationship()


class AuditResult(Base):
    __tablename__ = "audit_results"
    __table_args__ = (
        UniqueConstraint(
            "run_model_id", "attribute", "group_a", "group_b", name="uq_audit_comparison"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    run_model_id: Mapped[int] = mapped_column(ForeignKey("run_models.id"), index=True)
    model: Mapped[str] = mapped_column(String(120))
    mitigation: Mapped[str] = mapped_column(String(32))
    attribute: Mapped[str] = mapped_column(String(32))
    group_a: Mapped[str] = mapped_column(String(40))
    group_b: Mapped[str] = mapped_column(String(40))
    comparison_label: Mapped[str] = mapped_column(String(120))
    n_pairs: Mapped[int] = mapped_column(Integer)
    mean_gap: Mapped[float] = mapped_column(Float)
    ci_low: Mapped[float] = mapped_column(Float)
    ci_high: Mapped[float] = mapped_column(Float)
    p_value: Mapped[float] = mapped_column(Float)
    p_adjusted: Mapped[float] = mapped_column(Float, default=1.0)
    effect_size: Mapped[float] = mapped_column(Float)
    noise_floor: Mapped[float] = mapped_column(Float, default=0.0)
    shortlist_cutoff: Mapped[float] = mapped_column(Float, default=7.0)
    rate_a: Mapped[float] = mapped_column(Float, default=0.0)
    rate_b: Mapped[float] = mapped_column(Float, default=0.0)
    shortlist_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    significant: Mapped[bool] = mapped_column(Boolean, default=False)
    reduction_vs_baseline: Mapped[float | None] = mapped_column(Float, nullable=True)
    reduction_ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    reduction_ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    reduction_supported: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[Run] = relationship(back_populates="audits")
    run_model: Mapped[RunModel] = relationship(back_populates="audits")


class AccuracyResult(Base):
    __tablename__ = "accuracy_results"
    __table_args__ = (UniqueConstraint("run_model_id", name="uq_accuracy_run_model"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    run_model_id: Mapped[int] = mapped_column(ForeignKey("run_models.id"), index=True)
    model: Mapped[str] = mapped_column(String(120))
    mitigation: Mapped[str] = mapped_column(String(32))
    pairwise_accuracy: Mapped[float] = mapped_column(Float)
    auc: Mapped[float] = mapped_column(Float)
    n_items: Mapped[int] = mapped_column(Integer)
    n_pairs: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[Run] = relationship(back_populates="accuracy")
    run_model: Mapped[RunModel] = relationship(back_populates="accuracy")
