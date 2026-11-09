from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cvs.content import (
    AVERAGE_VERBS,
    CITIES,
    COMPANIES,
    ROLE_CONTENT,
    ROLES,
    STRONG_VERBS,
    TIERS,
    UNIVERSITIES,
    WEAK_VERBS,
)
from app.cvs.names import (
    AGE_GROUPS,
    ATTRIBUTE_LABELS,
    GENDER_GROUPS,
    GENDER_NAMES,
    NEUTRAL_FIRST_NAMES,
    NEUTRAL_SURNAMES,
    ORIGIN_GROUPS,
    ORIGIN_NAMES,
)
from app.models import BaseCV, CVVariant

AGE_PROFILES: dict[str, tuple[int, int]] = {
    "early_career": (2021, 3),
    "mid_career": (2011, 13),
    "senior": (1999, 25),
}

BULLET_COUNTS = {"strong": 5, "average": 4, "weak": 3}
SKILL_COUNTS = {"strong": 14, "average": 10, "weak": 6}


@dataclass(frozen=True)
class VariantSpec:
    attribute: str
    group_name: str
    label: str
    text: str
    changed_fields: list[str]


@dataclass(frozen=True)
class BaseCVSpec:
    role: str
    tier: str
    title: str
    text: str
    seed: int
    variants: list[VariantSpec] = field(default_factory=list)

    def variants_for(self, attribute: str) -> list[VariantSpec]:
        return [variant for variant in self.variants if variant.attribute == attribute]


@dataclass
class GeneratedContent:
    title: str
    previous_title: str
    company: str
    previous_company: str
    skills: list[str]
    degree: str
    university: str
    cert: str
    city: str
    bullets: list[str]
    previous_bullet: str
    summary: str
    email: str
    handle: str
    phone: str


def _summary(role: str, tier: str, domain: str) -> str:
    if tier == "strong":
        return (
            f"Results-focused {role} with a record of delivering measurable improvements in "
            f"{domain}. Comfortable owning complex work from discovery through delivery."
        )
    if tier == "average":
        return (
            f"Experienced {role} with practical knowledge of {domain}. Works well in "
            f"collaborative teams and delivers reliable day to day support."
        )
    return (
        f"Early-career {role} building practical experience in {domain}. Keen to learn, "
        f"dependable, and ready to contribute."
    )


def _make_bullets(rng: random.Random, role: str, tier: str) -> tuple[list[str], str]:
    content = ROLE_CONTENT[role]
    count = BULLET_COUNTS[tier]
    objects = rng.sample(content["objects"], k=count)
    metrics = rng.sample(content["metrics"], k=count)
    if tier == "strong":
        verbs = rng.sample(STRONG_VERBS, k=count)
        bullets = [
            f"{verb} {obj}, {metric}."
            for verb, obj, metric in zip(verbs, objects, metrics, strict=True)
        ]
        previous = (
            f"{rng.choice(STRONG_VERBS)} {rng.choice(content['objects'])}, "
            f"{rng.choice(metrics)}."
        )
        return bullets, previous
    if tier == "average":
        verbs = rng.sample(AVERAGE_VERBS, k=count)
        bullets = []
        for index, (verb, obj) in enumerate(zip(verbs, objects, strict=True)):
            if index < 2:
                bullets.append(f"{verb} {obj}, {metrics[index]}.")
            else:
                bullets.append(f"{verb} {obj}.")
        previous = f"{rng.choice(AVERAGE_VERBS)} {rng.choice(content['objects'])}."
        return bullets, previous
    verbs = rng.sample(WEAK_VERBS, k=count)
    bullets = [f"{verb} {obj}." for verb, obj in zip(verbs, objects, strict=True)]
    previous = f"{rng.choice(WEAK_VERBS)} {rng.choice(content['objects'])}."
    return bullets, previous


def _make_content(
    rng: random.Random, role: str, tier: str, global_index: int, city: str
) -> GeneratedContent:
    content = ROLE_CONTENT[role]
    bullets, previous_bullet = _make_bullets(rng, role, tier)
    skills = rng.sample(content["skills"], k=SKILL_COUNTS[tier])
    number = global_index + 1
    return GeneratedContent(
        title=rng.choice(content["titles"]),
        previous_title=rng.choice(content["previous_titles"]),
        company=rng.choice(COMPANIES),
        previous_company=rng.choice(COMPANIES),
        skills=skills,
        degree=rng.choice(content["degrees"]),
        university=rng.choice(UNIVERSITIES),
        cert=rng.choice(content["certs"]),
        city=city,
        bullets=bullets,
        previous_bullet=previous_bullet,
        summary=_summary(role, tier, content["domain"]),
        email=f"candidate-{number:04d}@example.com",
        handle=f"candidate-{number:04d}",
        phone=f"+44 7700 9{number:05d}",
    )


def render_cv(
    name: str,
    content: GeneratedContent,
    graduation_year: int,
    years_experience: int,
) -> str:
    bullets = "\n".join(f"- {bullet}" for bullet in content.bullets)
    skills = ", ".join(content.skills)
    return (
        f"{name}\n"
        f"Email: {content.email}\n"
        f"Phone: {content.phone}\n"
        f"Location: {content.city}, UK\n"
        f"LinkedIn: linkedin.com/in/{content.handle}\n"
        "\n"
        "Professional summary\n"
        f"{content.summary}\n"
        "\n"
        "Core skills\n"
        f"{skills}\n"
        "\n"
        "Experience\n"
        f"{content.title} | {content.company}\n"
        f"Years of experience: {years_experience}\n"
        f"{bullets}\n"
        "\n"
        "Earlier role\n"
        f"{content.previous_title} | {content.previous_company}\n"
        f"- {content.previous_bullet}\n"
        "\n"
        "Education\n"
        f"{content.degree}\n"
        f"{content.university}\n"
        f"Graduated: {graduation_year}\n"
        "\n"
        "Additional\n"
        f"{content.cert}\n"
    )


def _age_values(group: str, offset: int) -> tuple[int, int]:
    graduation_year, years = AGE_PROFILES[group]
    return graduation_year + offset, years + offset


def generate_dataset(
    seed: int = 2026,
    bases_per_role: int = 33,
    roles: list[str] | None = None,
) -> list[BaseCVSpec]:
    selected_roles = roles or ROLES
    specs: list[BaseCVSpec] = []
    global_index = 0
    for role_index, role in enumerate(selected_roles):
        if role not in ROLE_CONTENT:
            raise ValueError(f"Unknown role: {role}")
        for index_in_role in range(bases_per_role):
            tier = TIERS[index_in_role % len(TIERS)]
            base_seed = seed * 100_000 + role_index * 1_000 + index_in_role
            rng = random.Random(base_seed)
            city = CITIES[(role_index * bases_per_role + index_in_role) % len(CITIES)]
            content = _make_content(rng, role, tier, global_index, city)
            surname = NEUTRAL_SURNAMES[
                (role_index * bases_per_role + index_in_role) % len(NEUTRAL_SURNAMES)
            ]
            neutral_first = NEUTRAL_FIRST_NAMES[
                (role_index * bases_per_role + index_in_role) % len(NEUTRAL_FIRST_NAMES)
            ]
            neutral_name = f"{neutral_first} {surname}"
            age_offset = rng.randrange(3)
            mid_year, mid_years = _age_values("mid_career", age_offset)
            base_text = render_cv(neutral_name, content, mid_year, mid_years)

            variants: list[VariantSpec] = []
            for group in GENDER_GROUPS:
                first = GENDER_NAMES[group][
                    (role_index * 7 + index_in_role * 3 + GENDER_GROUPS.index(group))
                    % len(GENDER_NAMES[group])
                ]
                name = f"{first} {surname}"
                variants.append(
                    VariantSpec(
                        attribute="gender",
                        group_name=group,
                        label=ATTRIBUTE_LABELS["gender"][group],
                        text=render_cv(name, content, mid_year, mid_years),
                        changed_fields=["full_name"],
                    )
                )
            for group in ORIGIN_GROUPS:
                first, origin_surname = ORIGIN_NAMES[group][
                    (role_index * 5 + index_in_role * 2 + ORIGIN_GROUPS.index(group))
                    % len(ORIGIN_NAMES[group])
                ]
                name = f"{first} {origin_surname}"
                variants.append(
                    VariantSpec(
                        attribute="name_origin",
                        group_name=group,
                        label=ATTRIBUTE_LABELS["name_origin"][group],
                        text=render_cv(name, content, mid_year, mid_years),
                        changed_fields=["full_name"],
                    )
                )
            for group in AGE_GROUPS:
                graduation_year, years = _age_values(group, age_offset)
                variants.append(
                    VariantSpec(
                        attribute="age",
                        group_name=group,
                        label=ATTRIBUTE_LABELS["age"][group],
                        text=render_cv(neutral_name, content, graduation_year, years),
                        changed_fields=["graduation_year", "years_of_experience"],
                    )
                )
            specs.append(
                BaseCVSpec(
                    role=role,
                    tier=tier,
                    title=content.title,
                    text=base_text,
                    seed=base_seed,
                    variants=variants,
                )
            )
            global_index += 1
    return specs


def save_dataset(
    db: Session,
    seed: int = 2026,
    bases_per_role: int = 33,
    roles: list[str] | None = None,
) -> dict[str, Any]:
    existing = db.scalar(select(func.count()).select_from(BaseCV)) or 0
    if existing:
        variant_count = db.scalar(select(func.count()).select_from(CVVariant)) or 0
        return {
            "created": False,
            "base_cvs": int(existing),
            "variants": int(variant_count),
        }

    specs = generate_dataset(seed=seed, bases_per_role=bases_per_role, roles=roles)
    variant_count = 0
    for spec in specs:
        base = BaseCV(
            role=spec.role,
            tier=spec.tier,
            title=spec.title,
            text=spec.text,
            seed=spec.seed,
        )
        db.add(base)
        db.flush()
        for variant in spec.variants:
            db.add(
                CVVariant(
                    base_cv_id=base.id,
                    attribute=variant.attribute,
                    group_name=variant.group_name,
                    label=variant.label,
                    text=variant.text,
                    changed_fields=variant.changed_fields,
                )
            )
            variant_count += 1
    db.commit()
    return {
        "created": True,
        "base_cvs": len(specs),
        "variants": variant_count,
        "roles": len(roles or ROLES),
    }
