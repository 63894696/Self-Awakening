from __future__ import annotations

import hashlib
import re
import unicodedata


_UPPER_CHOICE_RE = re.compile(r"(?<![A-Za-z])([A-E])(?![A-Za-z])")
_EXPLICIT_CHOICE_RE = re.compile(
    r"(?:答案|选项|选择|我选|我选择)\s*(?:是|为|:|：)?\s*([A-Ea-e])"
)
_ONLY_CHOICE_RE = re.compile(r"^\s*([A-Ea-e])\s*(?:[.。)、)]\s*)?$")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def answer_digest(answer: str) -> str:
    return hashlib.sha256(normalize_text(answer).encode("utf-8")).hexdigest()[:16]


def extract_choice(answer: str) -> str | None:
    normalized = unicodedata.normalize("NFKC", answer)
    match = _ONLY_CHOICE_RE.search(normalized)
    if match:
        return match.group(1).upper()
    match = _EXPLICIT_CHOICE_RE.search(normalized)
    if match:
        return match.group(1).upper()
    match = _UPPER_CHOICE_RE.search(normalized)
    if match:
        return match.group(1).upper()
    return None


def score_answer(expected: str | None, answer: str) -> tuple[float | None, str | None]:
    if expected is None:
        return None, extract_choice(answer)

    expected_norm = normalize_text(expected)
    choice = extract_choice(answer)

    if re.fullmatch(r"[a-e]", expected_norm):
        return (1.0 if choice == expected_norm.upper() else 0.0), choice

    answer_norm = normalize_text(answer)
    if answer_norm == expected_norm:
        return 1.0, choice

    # Numeric answers often appear with short explanations. Accept the first exact number.
    if re.fullmatch(r"-?\d+(\.\d+)?", expected_norm):
        numbers = re.findall(r"-?\d+(?:\.\d+)?", answer_norm)
        return (1.0 if numbers and numbers[0] == expected_norm else 0.0), choice

    return 0.0, choice
