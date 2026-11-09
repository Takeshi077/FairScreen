from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, field

from app.cvs.content import STRONG_VERBS, WEAK_VERBS
from app.cvs.names import GENDER_NAMES, ORIGIN_NAMES
from app.llm.base import Provider, ProviderResult, ScoreSettings

GROUP_BIAS: dict[str, dict[str, float]] = {
    "gender": {"woman": -0.50, "man": 0.0},
    "name_origin": {
        "anglo": 0.0,
        "african": -0.46,
        "east_asian": -0.26,
        "south_asian": -0.36,
        "middle_eastern": -0.41,
    },
    "age": {"early_career": -0.16, "mid_career": 0.0, "senior": -0.45},
}

_ORIGIN_LOOKUP = {
    (first.lower(), surname.lower()): group
    for group, names in ORIGIN_NAMES.items()
    for first, surname in names
}
_GENDER_LOOKUP = {first.lower(): group for group, names in GENDER_NAMES.items() for first in names}
_AGE_RE = re.compile(r"(?im)^\s*years?\s+of\s+experience\s*:\s*(\d+)\s*$")
_BULLET_RE = re.compile(r"^-\s+(.*)$")


@dataclass(frozen=True)
class MockProfile:
    name: str
    bias_scale: float = 1.0
    noise: float = 0.15
    mitigation_noise: float = 0.0
    group_bias: dict[str, dict[str, float]] = field(default_factory=lambda: GROUP_BIAS)
    latency_base_ms: int = 8
    latency_spread_ms: int = 20


SIMULATED_PROFILES: dict[str, MockProfile] = {
    "Mock-Screen-A": MockProfile(
        name="Mock-Screen-A",
        bias_scale=1.0,
        noise=0.14,
        mitigation_noise=0.0,
        latency_base_ms=9,
    ),
    "Mock-Screen-B": MockProfile(
        name="Mock-Screen-B",
        bias_scale=0.72,
        noise=0.25,
        mitigation_noise=0.0,
        latency_base_ms=11,
    ),
    "Mock-Screen-C": MockProfile(
        name="Mock-Screen-C",
        bias_scale=1.15,
        noise=0.12,
        mitigation_noise=2.05,
        latency_base_ms=14,
    ),
}


def simulated_model_names() -> list[str]:
    return list(SIMULATED_PROFILES)


def _stable_int(*parts: object) -> int:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _detect_gender(cv_text: str) -> str | None:
    first_line = cv_text.splitlines()[0] if cv_text.splitlines() else ""
    first_token = first_line.split()[0].lower() if first_line.split() else ""
    return _GENDER_LOOKUP.get(first_token)


def _detect_origin(cv_text: str) -> str | None:
    first_line = cv_text.splitlines()[0] if cv_text.splitlines() else ""
    tokens = first_line.split()
    if len(tokens) < 2:
        return None
    return _ORIGIN_LOOKUP.get((tokens[0].lower(), tokens[1].lower()))


def _detect_age(cv_text: str) -> str | None:
    match = _AGE_RE.search(cv_text)
    if not match:
        return None
    years = int(match.group(1))
    if years >= 20:
        return "senior"
    if years >= 8:
        return "mid_career"
    return "early_career"


def _skill_count(cv_text: str) -> int:
    lines = cv_text.splitlines()
    for index, line in enumerate(lines):
        if line.strip().lower() == "core skills":
            for candidate in lines[index + 1 :]:
                if candidate.strip():
                    return len([item for item in candidate.split(",") if item.strip()])
    return 0


def _content_key(cv_text: str) -> str:
    lines = cv_text.splitlines()
    kept = [
        line
        for index, line in enumerate(lines)
        if index > 0
        and not line.startswith("Years of experience:")
        and not line.startswith("Graduated:")
    ]
    return "\n".join(kept)


def _quality_signal(cv_text: str) -> float:
    bullets = [match.group(1) for line in cv_text.splitlines() if (match := _BULLET_RE.match(line))]
    metric_count = sum(1 for bullet in bullets if re.search(r"\d", bullet))
    strong_count = sum(
        1
        for bullet in bullets
        if any(bullet.lower().startswith(verb.lower() + " ") for verb in STRONG_VERBS)
    )
    weak_count = sum(
        1
        for bullet in bullets
        if any(bullet.lower().startswith(verb.lower() + " ") for verb in WEAK_VERBS)
    )
    skills = _skill_count(cv_text)
    quality = 4.30 + 0.42 * metric_count + 0.32 * strong_count - 0.32 * weak_count + 0.035 * skills
    jitter = ((_stable_int(_content_key(cv_text)) % 10_000) / 10_000 - 0.5) * 0.24
    return min(9.75, max(0.20, quality + jitter))


def _detected_group_bias(cv_text: str, profile: MockProfile) -> float:
    bias = 0.0
    detected = {
        "gender": _detect_gender(cv_text),
        "name_origin": _detect_origin(cv_text),
        "age": _detect_age(cv_text),
    }
    for attribute, group in detected.items():
        if group is None:
            continue
        bias += profile.group_bias.get(attribute, {}).get(group, 0.0)
    return bias * profile.bias_scale


def _mitigation_multiplier(mitigation: str) -> float:
    if mitigation in {"anonymization", "combined"}:
        return 0.0
    if mitigation == "skills_only":
        return 0.26
    return 1.0


class MockProvider(Provider):
    name = "mock"

    def __init__(self, model_name: str, profile: MockProfile | None = None) -> None:
        self.model_name = model_name
        self.profile = profile or SIMULATED_PROFILES.get(model_name, MockProfile(name=model_name))

    def score(self, cv_text: str, prompt: str, settings: ScoreSettings) -> ProviderResult:
        quality = _quality_signal(cv_text)
        bias = _detected_group_bias(cv_text, self.profile) * _mitigation_multiplier(
            settings.mitigation
        )
        noise_sd = self.profile.noise
        if settings.mitigation != "none":
            noise_sd += self.profile.mitigation_noise
        seed = _stable_int(
            self.model_name,
            settings.repeat,
            settings.temperature,
            settings.prompt_version,
            settings.mitigation,
            hashlib.sha256(cv_text.encode("utf-8")).hexdigest(),
            hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        )
        rng = random.Random(seed)
        noise = rng.gauss(0.0, noise_sd) if noise_sd > 0 else 0.0
        score = round(min(9.95, max(0.05, quality + bias + noise)), 3)
        latency = self.profile.latency_base_ms + (
            _stable_int(seed) % (self.profile.latency_spread_ms + 1)
        )
        if settings.mitigation == "none":
            reason = "Simulated assessment based on evidence strength and stated experience."
        else:
            reason = "Simulated assessment of role evidence after mitigation."
        return ProviderResult(
            score=score,
            reason=reason,
            latency_ms=latency,
            cost_usd=0.0,
            raw={
                "simulated": True,
                "quality": round(quality, 3),
                "bias": round(bias, 3),
                "noise_sd": round(noise_sd, 3),
            },
        )

    def estimate_cost(self, cv_text: str, prompt: str, settings: ScoreSettings) -> float:
        return 0.0
