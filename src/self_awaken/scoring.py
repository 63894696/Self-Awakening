from __future__ import annotations

import hashlib
import re
import unicodedata


_UPPER_CHOICE_RE = re.compile(r"(?<![A-Za-z])([A-E])(?![A-Za-z])")
_EXPLICIT_CHOICE_RE = re.compile(
    r"(?:答案|选项|选择|我选|我选择)\s*(?:是|为|:|：)?\s*([A-Ea-e])"
)
_ONLY_CHOICE_RE = re.compile(r"^\s*([A-Ea-e])\s*(?:[.。)、)]\s*)?$")
# A line that is nothing but a bold/plain single letter: "**B**", "B", "B.".
_TRAILING_CHOICE_RE = re.compile(r"\*\*\s*([A-Ea-e])\s*\*\*|([A-E])\b\s*[.。]?\s*$")
# Conclusion markers that introduce the final answer.
_CONCLUSION_RE = re.compile(
    r"(?:因此|所以|综上|结论|最终答案|正确答案|answer|Answer|ANSWER)\s*(?:是|为|:|：)?\s*\**\s*([A-Ea-e])\b"
)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


_FENCE_RE = re.compile(r"^```[A-Za-z0-9_+.-]*\s*|\s*```$")


def canonicalize(value: str) -> str:
    """Normalize a free-form answer before exact comparison.

    Models wrap short answers in markdown, quotes, or backticks (```'ababab'```,
    `` `[0, 1, 2]` ``). Those are formatting choices, not capability failures, so
    they must not be scored as wrong answers.
    """
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    text = _FENCE_RE.sub("", text).strip()
    text = text.strip("`").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    text = text.strip("`").strip()
    text = re.sub(r"\s*([\[\](){}])\s*", r"\1", text)
    text = re.sub(r"\s*,\s*", ",", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def answer_digest(answer: str) -> str:
    return hashlib.sha256(normalize_text(answer).encode("utf-8")).hexdigest()[:16]


def extract_choice(answer: str) -> str | None:
    """Find the option a model chose.

    Order matters. A reasoning model often restates every option ("A. it floats —
    wrong, B. it is light — wrong, ...") and only states the real answer at the
    end. Matching the first letter it mentions therefore scores a correct answer
    as wrong, so we look at the conclusion first and fall back to the earliest
    mention only when no conclusion exists.
    """
    normalized = unicodedata.normalize("NFKC", answer)

    match = _ONLY_CHOICE_RE.search(normalized)
    if match:
        return match.group(1).upper()

    match = _CONCLUSION_RE.search(normalized)
    if match:
        return match.group(1).upper()

    # Last non-empty line is frequently the answer: "**B**" or "B".
    lines = [line for line in normalized.splitlines() if line.strip()]
    for line in reversed(lines[-3:]):
        match = _TRAILING_CHOICE_RE.search(line.strip())
        if match:
            return (match.group(1) or match.group(2)).upper()

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

    expected_norm = canonicalize(expected)
    choice = extract_choice(answer)

    if re.fullmatch(r"[a-e]", expected_norm):
        return (1.0 if choice == expected_norm.upper() else 0.0), choice

    answer_norm = canonicalize(answer)
    if answer_norm == expected_norm:
        return 1.0, choice

    # Numeric answers often come with the working shown. The conclusion is
    # usually the *last* number, not the first: "100-37=63, 63*2=126" must score
    # against 126, while taking numbers[0] would score it against 100.
    if re.fullmatch(r"-?\d+(?:\.\d+)?", expected_norm):
        numbers = re.findall(r"-?\d+(?:\.\d+)?", answer_norm)
        if not numbers:
            return 0.0, choice
        return (1.0 if numbers[-1] == expected_norm else 0.0), choice

    return 0.0, choice
