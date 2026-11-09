from __future__ import annotations

import re
from collections import Counter

import pytest
from sqlalchemy import func, select

from app.cvs.content import ROLES, TIERS
from app.cvs.generator import generate_dataset, save_dataset
from app.cvs.names import AGE_GROUPS, GENDER_GROUPS, ORIGIN_GROUPS
from app.models import BaseCV, CVVariant


@pytest.fixture(scope="module")
def dataset():
    return generate_dataset(seed=2026, bases_per_role=33)


def test_roles_and_counts(dataset):
    assert len(ROLES) == 6
    assert len(dataset) == 6 * 33
    per_role = Counter(spec.role for spec in dataset)
    assert set(per_role) == set(ROLES)
    assert all(count == 33 for count in per_role.values())
    per_role_tier = Counter((spec.role, spec.tier) for spec in dataset)
    assert set(per_role_tier.values()) == {11}
    assert {tier for _, tier in per_role_tier} == set(TIERS)


def test_variant_shape(dataset):
    for spec in dataset:
        assert len(spec.variants) == 10
        gender = [v.group_name for v in spec.variants_for("gender")]
        origin = [v.group_name for v in spec.variants_for("name_origin")]
        age = [v.group_name for v in spec.variants_for("age")]
        assert gender == GENDER_GROUPS
        assert origin == ORIGIN_GROUPS
        assert age == AGE_GROUPS


def test_generation_is_deterministic():
    first = generate_dataset(seed=99, bases_per_role=6)
    second = generate_dataset(seed=99, bases_per_role=6)
    assert [(s.text, [v.text for v in s.variants]) for s in first] == [
        (s.text, [v.text for v in s.variants]) for s in second
    ]
    other = generate_dataset(seed=100, bases_per_role=6)
    assert first[0].text != other[0].text


def test_each_pair_differs_only_in_intended_fields(dataset):
    for spec in dataset:
        for attribute in ("gender", "name_origin"):
            variants = spec.variants_for(attribute)
            for left_index in range(len(variants)):
                for right_index in range(left_index + 1, len(variants)):
                    left = variants[left_index]
                    right = variants[right_index]
                    left_lines = left.text.splitlines()
                    right_lines = right.text.splitlines()
                    assert left_lines[0] != right_lines[0]
                    assert left_lines[1:] == right_lines[1:], (
                        f"Non-name content changed for {spec.role} {attribute}"
                    )
                    assert left.changed_fields == ["full_name"]
                    if attribute == "gender":
                        assert left_lines[0].split()[-1] == right_lines[0].split()[-1]

        age_variants = spec.variants_for("age")
        for left_index in range(len(age_variants)):
            for right_index in range(left_index + 1, len(age_variants)):
                left = age_variants[left_index]
                right = age_variants[right_index]
                left_lines = left.text.splitlines()
                right_lines = right.text.splitlines()
                assert len(left_lines) == len(right_lines)
                differing = [
                    index
                    for index, (l_line, r_line) in enumerate(
                        zip(left_lines, right_lines, strict=True)
                    )
                    if l_line != r_line
                ]
                assert len(differing) == 2
                assert "Years of experience" in left_lines[differing[0]]
                assert "Graduated" in left_lines[differing[1]]
                assert left.changed_fields == ["graduation_year", "years_of_experience"]


def test_pairs_are_realistic_length(dataset):
    for spec in dataset[:30]:
        assert 650 <= len(spec.text) <= 4500
        assert "Professional summary" in spec.text
        assert "Core skills" in spec.text
        assert "Experience" in spec.text
        assert "Education" in spec.text


def test_save_dataset_is_idempotent(clean_db, db):
    first = save_dataset(db, seed=2026, bases_per_role=3)
    assert first["created"] is True
    assert first["base_cvs"] == 18
    assert first["variants"] == 180
    second = save_dataset(db, seed=2026, bases_per_role=3)
    assert second["created"] is False
    assert second["base_cvs"] == 18
    assert db.scalar(select(func.count()).select_from(BaseCV)) == 18
    assert db.scalar(select(func.count()).select_from(CVVariant)) == 180
    gender_count = db.scalar(
        select(func.count()).select_from(CVVariant).where(CVVariant.attribute == "gender")
    )
    assert gender_count == 36


def test_age_lines_are_the_only_numeric_experience_fields(dataset):
    for variant in dataset[0].variants_for("age"):
        lines = variant.text.splitlines()
        year_lines = [line for line in lines if line.startswith("Years of experience:")]
        graduation_lines = [line for line in lines if line.startswith("Graduated:")]
        assert len(year_lines) == 1
        assert len(graduation_lines) == 1
        assert re.search(r"\d+", year_lines[0])
        assert re.search(r"\b(?:19|20)\d{2}\b", graduation_lines[0])
