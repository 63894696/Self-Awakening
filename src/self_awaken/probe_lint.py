"""Probe bank linting.

A probe whose ``expected`` value is wrong is worse than no probe: it silently
marks a correct answer as a failure and can push a healthy endpoint to an
``insufficient`` verdict. This module catches the defect classes we have
actually produced in this repository:

- literal placeholder expected values (``<calc-failed>``, ``<needs-llm-eval>``)
- unevaluated Python expressions used as expected values (``int(5882 ** 0.5)``)
- unexpanded template slots in the prompt (``len('a'/'b'/'c')``)
- arithmetic prompts whose expected value does not match the expression
- duplicate probe ids or duplicate prompt text
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from .schemas import Probe

_PLACEHOLDER_RE = re.compile(r"^<[^>]*>$")
_EXPR_CALL_RE = re.compile(r"\b(str|int|len|round|abs|float|sum|sorted)\(")
# A template slot that never got filled: "A/B/C", "OK/YES/TRUE", "1/2/3/4".
_SLOT_RE = re.compile(r"(?:[A-Za-z\u4e00-\u9fff0-9]+/){2,}[A-Za-z\u4e00-\u9fff0-9]+")
_ARITH_CAPTURE_RE = re.compile(r"([0-9()\s.+\-*/]+)=\s*\?")
_DIGIT_SUM_RE = re.compile(r"各位数字之和为\s*(\d+)")


@dataclass(frozen=True)
class Issue:
    severity: str  # "error" | "warning"
    probe_id: str
    code: str
    message: str


def lint_probes(probes: Sequence[Probe]) -> list[Issue]:
    issues: list[Issue] = []
    seen_ids: set[str] = set()
    seen_prompts: dict[str, str] = {}

    for probe in probes:
        if probe.id in seen_ids:
            issues.append(Issue("error", probe.id, "duplicate_id", f"duplicate probe id {probe.id}"))
        seen_ids.add(probe.id)

        normalized_prompt = " ".join(probe.prompt.split())
        if normalized_prompt in seen_prompts:
            issues.append(
                Issue(
                    "warning",
                    probe.id,
                    "duplicate_prompt",
                    f"same prompt as {seen_prompts[normalized_prompt]}",
                )
            )
        else:
            seen_prompts[normalized_prompt] = probe.id

        issues.extend(_lint_expected(probe))
        issues.extend(_lint_prompt(probe))

    return issues


def _lint_expected(probe: Probe) -> list[Issue]:
    issues: list[Issue] = []
    expected = probe.expected

    if expected is None or not str(expected).strip():
        issues.append(Issue("error", probe.id, "missing_expected", "probe has no expected value"))
        return issues

    text = str(expected).strip()
    if _PLACEHOLDER_RE.match(text):
        issues.append(
            Issue("error", probe.id, "placeholder_expected", f"expected is a placeholder: {text}")
        )
    elif _EXPR_CALL_RE.search(text) and not _is_plain_number(text):
        issues.append(
            Issue(
                "error",
                probe.id,
                "unevaluated_expected",
                f"expected looks like an unevaluated expression: {text}",
            )
        )

    if "只选择" in probe.prompt or "只选" in probe.prompt:
        if not re.fullmatch(r"[A-Ea-e]", text):
            issues.append(
                Issue(
                    "error",
                    probe.id,
                    "choice_expected",
                    f"choice probe expects A-E, got {text!r}",
                )
            )

    match = _ARITH_CAPTURE_RE.search(probe.prompt)
    if match and _is_plain_number(text):
        declared = _eval_expression(match.group(1))
        if declared is not None and abs(declared - float(text)) > 1e-9:
            issues.append(
                Issue(
                    "error",
                    probe.id,
                    "arithmetic_mismatch",
                    f"prompt computes {declared:g}, expected says {text}",
                )
            )

    digit_sum = _DIGIT_SUM_RE.search(probe.prompt)
    if digit_sum and re.fullmatch(r"\d{2,}", text):
        total = sum(int(char) for char in text)
        if total != int(digit_sum.group(1)):
            issues.append(
                Issue(
                    "error",
                    probe.id,
                    "digit_sum_mismatch",
                    f"prompt says digit sum {digit_sum.group(1)}, but {text} sums to {total}",
                )
            )

    return issues


def _lint_prompt(probe: Probe) -> list[Issue]:
    issues: list[Issue] = []
    if "<" in probe.prompt and ">" in probe.prompt and re.search(r"<[a-z][a-z0-9_-]*>", probe.prompt):
        issues.append(
            Issue("error", probe.id, "placeholder_prompt", "prompt still contains a template placeholder")
        )
    slot = _SLOT_RE.search(probe.prompt)
    if slot:
        issues.append(
            Issue(
                "warning",
                probe.id,
                "unexpanded_slot",
                f"prompt may contain an unexpanded template slot: {slot.group(0)!r}",
            )
        )
    if "{ " in probe.prompt or re.search(r"\{[a-z_][a-z0-9_]*\}", probe.prompt):
        issues.append(
            Issue("error", probe.id, "unexpanded_field", "prompt still contains an unexpanded {field}")
        )
    return issues


def _is_plain_number(text: str) -> bool:
    return re.fullmatch(r"-?\d+(?:\.\d+)?", text.strip()) is not None


_ALLOWED_ARITH_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd,
)


def _eval_expression(expression: str) -> float | None:
    """Evaluate a pure-arithmetic expression found in a prompt."""
    expression = expression.strip()
    if not re.search(r"\d", expression) or not re.search(r"[+\-*/]", expression):
        return None
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_ARITH_NODES):
            return None
    try:
        value = eval(compile(tree, "<arith>", "eval"), {"__builtins__": {}}, {})  # noqa: S307
    except Exception:  # noqa: BLE001
        return None
    return float(value) if isinstance(value, (int, float)) else None


def safe_eval_expected(expression: str) -> str | None:
    """Evaluate a simple expected-value expression produced by our templates.

    Only arithmetic and a small whitelist of builtins are allowed; anything else
    returns ``None`` so callers drop the probe instead of shipping a bad value.
    """
    tree = ast.parse(expression, mode="eval")
    allowed_nodes = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Call, ast.Name,
        ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
        ast.Pow, ast.USub,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            return None
        if isinstance(node, ast.Name) and node.id not in {"str", "int", "len", "round", "abs", "float"}:
            return None
    try:
        value = eval(  # noqa: S307 - whitelisted AST above.
            compile(tree, "<expected>", "eval"),
            {"__builtins__": {"str": str, "int": int, "len": len, "round": round, "abs": abs, "float": float}},
            {},
        )
    except Exception:  # noqa: BLE001
        return None
    text = str(value).strip()
    return text or None


def summarize_issues(issues: Iterable[Issue]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0}
    for issue in issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
    return counts
