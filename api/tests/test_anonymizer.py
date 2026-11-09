from __future__ import annotations

import re

import pytest

from app.cvs.anonymizer import ANONYMIZED_NAME, anonymize_cv
from app.cvs.generator import generate_dataset
from app.cvs.names import all_known_first_names, all_known_surnames

PRONOUN_RE = re.compile(
    r"\b(he|she|they|him|her|them|his|hers|their|theirs|himself|herself|themselves)\b",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(?:19[5-9]\d|20[0-3]\d)\b")
AGE_RE = re.compile(r"\b(?:aged?\s+\d{1,2}|\d{1,2}\s+years?\s+old)\b", re.IGNORECASE)


@pytest.fixture(scope="module")
def dataset():
    return generate_dataset(seed=2026, bases_per_role=33)


def test_every_variant_is_anonymized(dataset):
    first_names = all_known_first_names()
    surnames = all_known_surnames()
    for spec in dataset:
        for variant in spec.variants:
            original_name = variant.text.splitlines()[0]
            anonymized = anonymize_cv(variant.text)
            assert anonymized.splitlines()[0] == ANONYMIZED_NAME
            lowered = anonymized.lower()
            for token in original_name.lower().split():
                assert re.search(rf"\b{re.escape(token)}\b", lowered) is None
            for name in first_names:
                assert re.search(rf"\b{re.escape(name)}\b", lowered) is None
            for surname in surnames:
                assert re.search(rf"\b{re.escape(surname)}\b", lowered) is None
            assert PRONOUN_RE.search(anonymized) is None
            assert YEAR_RE.search(anonymized) is None
            assert AGE_RE.search(anonymized) is None
            assert not re.search(r"(?im)^\s*graduated\s*:", anonymized)
            assert not re.search(r"(?im)^\s*years?\s+of\s+experience\s*:\s*\d+", anonymized)
            assert "Professional summary" in anonymized
            assert "Core skills" in anonymized


def test_anonymized_variants_match_within_attribute(dataset):
    for spec in dataset:
        for attribute in ("gender", "name_origin", "age"):
            texts = {anonymize_cv(variant.text) for variant in spec.variants_for(attribute)}
            assert len(texts) == 1, f"{attribute} leaked through anonymization"


def test_pronouns_and_age_cues_are_removed():
    text = (
        "Alex Morgan\n"
        "Email: alex@example.com\n"
        "Age: 42\n"
        "Date of birth: 03/04/1982\n"
        "He led his team. She supported her colleague. They reviewed their work.\n"
        "Graduated: 2004\n"
        "Years of experience: 18\n"
    )
    anonymized = anonymize_cv(text)
    assert anonymized.splitlines()[0] == ANONYMIZED_NAME
    assert PRONOUN_RE.search(anonymized) is None
    assert YEAR_RE.search(anonymized) is None
    assert AGE_RE.search(anonymized) is None
    assert "2004" not in anonymized
    assert "18" not in anonymized


def test_keeps_role_relevant_content():
    text = (
        "Sophie Bennett\n"
        "Core skills\nPython, SQL, Docker\n"
        "Experience\nLed a migration, cutting latency by 30%.\n"
        "Graduated: 2015\n"
    )
    anonymized = anonymize_cv(text)
    assert "Python, SQL, Docker" in anonymized
    assert "cutting latency by 30%" in anonymized
