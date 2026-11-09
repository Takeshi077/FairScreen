from __future__ import annotations

import re

from app.cvs.names import all_known_first_names, all_known_surnames

ANONYMIZED_NAME = "Candidate"

_PRONOUN_MAP = {
    "he": "the candidate",
    "she": "the candidate",
    "they": "the candidate",
    "him": "the candidate",
    "her": "the candidate",
    "them": "the candidate",
    "his": "the candidate's",
    "hers": "the candidate's",
    "their": "the candidate's",
    "theirs": "the candidate's",
    "himself": "the candidate",
    "herself": "the candidate",
    "themselves": "the candidate",
}

_PRONOUN_RE = re.compile(
    r"\b(" + "|".join(sorted(_PRONOUN_MAP, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
_GRADUATION_RE = re.compile(r"(?im)^\s*graduated\s*:\s*\d{4}\s*$")
_YEARS_EXPERIENCE_RE = re.compile(r"(?im)^\s*years?\s+of\s+experience\s*:\s*\d+\s*(?:years?)?\s*$")
_AGE_LINE_RE = re.compile(r"(?im)^\s*(?:age|aged|date\s+of\s+birth|dob)\s*:?.*$")
_AGE_CUE_RE = re.compile(
    r"\b(?:aged?\s+\d{1,2}|\d{1,2}\s+years?\s+old|date\s+of\s+birth)\b",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(?:19[5-9]\d|20[0-3]\d)\b")


def _build_name_re() -> re.Pattern[str]:
    names = sorted(all_known_first_names() | all_known_surnames(), key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(name) for name in names) + r")\b", re.IGNORECASE)


_NAME_RE = _build_name_re()


def anonymize_cv(text: str) -> str:
    lines = text.splitlines()
    if lines:
        lines[0] = ANONYMIZED_NAME
    cleaned = "\n".join(lines)

    cleaned = _GRADUATION_RE.sub("", cleaned)
    cleaned = _YEARS_EXPERIENCE_RE.sub("Experience: relevant professional experience", cleaned)
    cleaned = _AGE_LINE_RE.sub("", cleaned)
    cleaned = _NAME_RE.sub(ANONYMIZED_NAME, cleaned)
    cleaned = _PRONOUN_RE.sub(lambda match: _PRONOUN_MAP[match.group(0).lower()], cleaned)
    cleaned = _AGE_CUE_RE.sub("age removed", cleaned)
    cleaned = _YEAR_RE.sub("year removed", cleaned)

    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + "\n"
