from __future__ import annotations

import json
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(RuntimeError):
    """Base error for provider failures."""


class ProviderConfigurationError(ProviderError):
    """Raised when a provider is requested without required configuration."""


class ProviderResponseError(ProviderError):
    """Raised when a provider response is malformed or fails validation."""


class BudgetExceededError(ProviderError):
    """Raised before a provider call that would exceed the run budget."""


@dataclass(frozen=True)
class ScoreSettings:
    model: str
    temperature: float = 0.2
    provider: str = "mock"
    prompt_version: str = "screening-v1"
    mitigation: str = "none"
    repeat: int = 0


@dataclass(frozen=True)
class ProviderResult:
    score: float
    reason: str
    latency_ms: int
    cost_usd: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


class Provider(ABC):
    name: str = "provider"

    @abstractmethod
    def score(self, cv_text: str, prompt: str, settings: ScoreSettings) -> ProviderResult:
        raise NotImplementedError

    def estimate_cost(self, cv_text: str, prompt: str, settings: ScoreSettings) -> float:
        return 0.0

    def close(self) -> None:
        return None


def parse_score_response(text: str) -> tuple[float, str]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ProviderResponseError(f"Response is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProviderResponseError("Response JSON must be an object")
    if "score" not in payload or "reason" not in payload:
        raise ProviderResponseError("Response JSON must contain score and reason")
    score = payload["score"]
    reason = payload["reason"]
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ProviderResponseError("score must be a number")
    numeric = float(score)
    if not math.isfinite(numeric) or numeric < 0 or numeric > 10:
        raise ProviderResponseError("score must be finite and between 0 and 10")
    if not isinstance(reason, str) or not reason.strip():
        raise ProviderResponseError("reason must be a non-empty string")
    return numeric, reason.strip()[:1000]


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


@dataclass
class Budget:
    cap_usd: float
    spent_usd: float = 0.0

    @property
    def remaining(self) -> float:
        return max(0.0, self.cap_usd - self.spent_usd)

    def ensure_can_spend(self, estimate_usd: float) -> None:
        if self.spent_usd + estimate_usd > self.cap_usd + 1e-9:
            raise BudgetExceededError(
                f"Budget cap of ${self.cap_usd:.4f} would be exceeded. "
                f"Spent ${self.spent_usd:.4f}, next call estimated at ${estimate_usd:.4f}."
            )

    def charge(self, actual_usd: float) -> None:
        self.spent_usd += max(0.0, actual_usd)
