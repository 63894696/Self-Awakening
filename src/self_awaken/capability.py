"""Capability sufficiency checks.

This module answers a cheaper and more useful question than "which exact
model is behind this endpoint": **does this endpoint deliver the capability
level my task actually needs?**

Rationale
---------
Black-box probing cannot prove model identity. Similar probes on different
flagship models score 0.86-0.93 against each other, so an absolute similarity
threshold will happily "certify" a substituted model. What black-box probing
*can* do reliably is bound capability: either the endpoint answers task-relevant
probes at the required level, or it does not.

So we report one of three verdicts per capability profile:

- ``sufficient``    -- the observed pass rate is above the threshold even at the
                       lower edge of its confidence interval.
- ``insufficient``  -- the observed pass rate stays below the threshold even at
                       the upper edge of its confidence interval.
- ``undetermined``  -- not enough evidence within the budget; run more probes.

Early stopping keeps the cost low: we stop as soon as the interval decides,
instead of always running the full probe bank.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .client_factory import create_client
from .schemas import Probe

# One-sided-ish 90% interval (z=1.645). We prefer a slightly looser interval than
# 95% because the cost of asking a user to run a few more probes is low, while the
# cost of a false "insufficient" verdict (paying for a second provider) is high.
Z = 1.645

# `pack` -> maximum number of probes to run.
PACK_SIZES = {"smoke": 12, "standard": 24, "deep": 1000}

# Capability profiles: which probe categories matter, and what pass rate counts
# as "good enough". Thresholds are calibrated so that current flagship models
# clear them (see docs/CAPABILITY.md); anything materially below is a real signal.
PROFILES: dict[str, dict[str, Any]] = {
    "code": {
        "label": "代码生成 / 理解 / 重构",
        "categories": ("code",),
        "threshold": 0.80,
    },
    "reasoning": {
        "label": "逻辑推理 / 歧义处理",
        "categories": ("logic", "reasoning"),
        "threshold": 0.75,
    },
    "instruction": {
        "label": "指令遵循 / 严格输出格式",
        "categories": ("instruction", "math"),
        "threshold": 0.80,
    },
    "math": {
        "label": "数值计算",
        "categories": ("math",),
        "threshold": 0.85,
    },
    "knowledge": {
        "label": "常识 / 领域知识",
        "categories": ("knowledge",),
        "threshold": 0.80,
    },
    "general": {
        "label": "通用任务（全类别加权）",
        "categories": ("code", "logic", "reasoning", "instruction", "math", "knowledge"),
        "threshold": 0.78,
    },
}

DEFAULT_PROFILE = "general"
DEFAULT_PACK = "smoke"


@dataclass(frozen=True)
class Verdict:
    verdict: str
    accuracy: float | None
    passed: int
    scored: int
    low: float
    high: float
    threshold: float
    reason: str


def wilson_interval(passed: int, scored: int, z: float = Z) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if scored <= 0:
        return 0.0, 1.0
    p = passed / scored
    denom = 1.0 + z * z / scored
    center = (p + z * z / (2 * scored)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / scored + z * z / (4.0 * scored * scored))) / denom
    return max(0.0, center - half), min(1.0, center + half)


def judge(passed: int, scored: int, threshold: float, min_probes: int = 0) -> Verdict:
    """Decide whether the evidence is already conclusive."""
    if scored <= 0:
        return Verdict("undetermined", None, passed, scored, 0.0, 1.0, threshold, "no_scored_probes")

    accuracy = passed / scored
    low, high = wilson_interval(passed, scored)

    if scored < min_probes:
        return Verdict("undetermined", accuracy, passed, scored, low, high, threshold, "need_more_probes")
    if low >= threshold:
        return Verdict("sufficient", accuracy, passed, scored, low, high, threshold, "ci_lower_above_threshold")
    if high < threshold:
        return Verdict("insufficient", accuracy, passed, scored, low, high, threshold, "ci_upper_below_threshold")
    return Verdict("undetermined", accuracy, passed, scored, low, high, threshold, "interval_straddles_threshold")


def select_probes(probes: Sequence[Probe], profile: str, pack: str) -> list[Probe]:
    """Pick probes for a profile, round-robin across categories for coverage."""
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}; choose from {', '.join(PROFILES)}")
    spec = PROFILES[profile]
    categories = [c for c in spec["categories"] if any(p.category == c for p in probes)]
    if not categories:
        raise ValueError(f"no probes match profile {profile!r}")

    by_category: dict[str, list[Probe]] = {c: [] for c in categories}
    for probe in probes:
        if probe.category in by_category:
            by_category[probe.category].append(probe)

    # Prefer probes that can be scored deterministically.
    for bucket in by_category.values():
        bucket.sort(key=lambda p: (p.expected is None, p.id))

    limit = PACK_SIZES.get(pack, PACK_SIZES[DEFAULT_PACK])
    ordered: list[Probe] = []
    index = 0
    while len(ordered) < limit:
        added = False
        for category in categories:
            bucket = by_category[category]
            if index < len(bucket):
                ordered.append(bucket[index])
                added = True
                if len(ordered) >= limit:
                    break
        if not added:
            break
        index += 1
    return ordered


def estimate_tokens(probes: Iterable[Probe], max_tokens: int) -> int:
    """Cheap upper-ish estimate of the tokens a run will consume.

    CJK text runs a bit over one token per character on common tokenizers, so we
    use 1.0 token/char for prompts (deliberately pessimistic) plus the output cap.
    """
    total = 0
    for probe in probes:
        total += max(1, len(probe.prompt)) + max_tokens
    return total


def check_capability(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    probes: Sequence[Probe],
    profile: str = DEFAULT_PROFILE,
    pack: str = DEFAULT_PACK,
    threshold: float | None = None,
    max_tokens: int = 192,
    temperature: float = 0.0,
    timeout: int = 90,
    api_type: str | None = None,
    token_budget: int | None = None,
    max_probes: int | None = None,
    min_probes: int = 10,
    on_progress: Any = None,
) -> dict[str, Any]:
    """Run the smallest probe sequence that decides the verdict."""
    from .fingerprint import _format_probe_error, summarize_results
    from .scoring import score_answer

    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}; choose from {', '.join(PROFILES)}")

    spec = PROFILES[profile]
    cut = float(threshold if threshold is not None else spec["threshold"])
    selected = select_probes(probes, profile, pack)
    if max_probes:
        selected = selected[:max_probes]

    estimate = estimate_tokens(selected, max_tokens)
    if token_budget is not None and estimate > token_budget:
        # Trim to what the budget can pay for, keeping coverage order.
        affordable = []
        running = 0
        for probe in selected:
            cost = max(1, len(probe.prompt)) + max_tokens
            if running + cost > token_budget:
                break
            affordable.append(probe)
            running += cost
        selected = affordable

    client = create_client(
        endpoint=endpoint,
        api_key=api_key,
        model=model,
        timeout=timeout,
        api_type=api_type,
    )

    results: list[dict[str, Any]] = []
    used_tokens = 0
    verdict = Verdict("undetermined", None, 0, 0, 0.0, 1.0, cut, "not_started")

    for probe in selected:
        answer = ""
        error = None
        latency = 0
        prompt_tokens = completion_tokens = None
        score: float | None = None
        choice: str | None = None
        try:
            completion = client.complete(probe.prompt, temperature=temperature, max_tokens=max_tokens)
            used_tokens += (completion.prompt_tokens or max(1, len(probe.prompt))) + (completion.completion_tokens or 0)
            # Reasoning models spend output tokens on hidden thinking. If the answer
            # was cut off by the cap, retry once with a larger budget instead of
            # scoring a truncated string as a wrong answer.
            if getattr(completion, "finish_reason", None) == "length" and max_tokens < 2048:
                retry_tokens = max(512, max_tokens * 4)
                completion = client.complete(probe.prompt, temperature=temperature, max_tokens=retry_tokens)
                used_tokens += (
                    (completion.prompt_tokens or max(1, len(probe.prompt)))
                    + (completion.completion_tokens or 0)
                )
            answer = completion.answer
            latency = completion.latency_ms
            prompt_tokens = completion.prompt_tokens
            completion_tokens = completion.completion_tokens
            if getattr(completion, "finish_reason", None) == "length":
                error = "truncated_output"
            else:
                score, choice = score_answer(probe.expected, answer)
        except Exception as exc:  # noqa: BLE001 - keep per-probe failures in the report.
            error = _format_probe_error(exc)

        used_tokens += (prompt_tokens or max(1, len(probe.prompt))) + (completion_tokens or 0)
        results.append(
            {
                "probe_id": probe.id,
                "category": probe.category,
                "prompt": probe.prompt,
                "answer": answer,
                "expected": probe.expected,
                "score": score,
                "choice": choice,
                "latency_ms": latency,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "error": error,
            }
        )

        scored = [r for r in results if r["score"] is not None]
        passed = sum(1 for r in scored if r["score"] >= 0.5)
        verdict = judge(passed, len(scored), cut, min_probes=min_probes)
        if on_progress:
            on_progress(len(results), verdict)

        if verdict.verdict != "undetermined":
            break
        if token_budget is not None and used_tokens >= token_budget:
            verdict = Verdict(
                "undetermined", verdict.accuracy, verdict.passed, verdict.scored,
                verdict.low, verdict.high, cut, "token_budget_exhausted",
            )
            break

    per_category: dict[str, dict[str, Any]] = {}
    for result in results:
        bucket = per_category.setdefault(result["category"], {"passed": 0, "scored": 0, "errors": 0})
        if result["error"]:
            bucket["errors"] += 1
        elif result["score"] is not None:
            bucket["scored"] += 1
            if result["score"] >= 0.5:
                bucket["passed"] += 1
    for bucket in per_category.values():
        bucket["accuracy"] = round(bucket["passed"] / bucket["scored"], 4) if bucket["scored"] else None

    return {
        "schema_version": 1,
        "kind": "capability",
        "endpoint": endpoint.rstrip("/"),
        "requested_model": model,
        "profile": profile,
        "profile_label": spec["label"],
        "pack": pack,
        "threshold": cut,
        "verdict": verdict.verdict,
        "reason": verdict.reason,
        "accuracy": round(verdict.accuracy, 4) if verdict.accuracy is not None else None,
        "passed": verdict.passed,
        "scored": verdict.scored,
        "confidence_interval": [round(verdict.low, 4), round(verdict.high, 4)],
        "probes_run": len(results),
        "probes_planned": len(selected),
        "estimated_tokens": estimate,
        "used_tokens": used_tokens,
        "token_budget": token_budget,
        "per_category": per_category,
        "summary": summarize_results(results),
        "results": results,
    }


def render_capability_report(report: dict[str, Any]) -> str:
    verdict = report["verdict"].upper()
    lines = [
        "# 能力达标判定（capability sufficiency）",
        "",
        f"- 接口：`{report['endpoint']}`",
        f"- 请求模型：`{report['requested_model']}`",
        f"- 能力档位：`{report['profile']}`（{report['profile_label']}）",
        f"- 判定：**{verdict}**",
        f"- 阈值：`{report['threshold']:.2f}`　通过率：`{_fmt(report['accuracy'])}`"
        f"（{report['passed']}/{report['scored']}）",
        f"- 90% 置信区间：`[{report['confidence_interval'][0]:.2f}, "
        f"{report['confidence_interval'][1]:.2f}]`",
        f"- 探针：运行 `{report['probes_run']}` / 计划 `{report['probes_planned']}`",
        f"- token 消耗：约 `{report['used_tokens']}`（预算上限 "
        f"`{report['token_budget'] or '未设置'}`，预估 `{report['estimated_tokens']}`）",
        "",
        "## 分类明细",
        "",
        "| 类别 | 通过/计分 | 正确率 | 错误 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for category, bucket in sorted(report["per_category"].items()):
        lines.append(
            f"| `{category}` | {bucket['passed']}/{bucket['scored']} | "
            f"{_fmt(bucket['accuracy'])} | {bucket['errors']} |"
        )

    lines += [
        "",
        "## 判定含义",
        "",
        "- `SUFFICIENT`：置信区间下界仍高于阈值，可以认为该接口满足此能力档位。",
        "- `INSUFFICIENT`：置信区间上界仍低于阈值，该接口达不到此能力档位。",
        "- `UNDETERMINED`：证据不足（探针不够或预算用尽），不代表不合格。",
    ]

    if report["verdict"] == "undetermined" and report["reason"] in {
        "need_more_probes",
        "interval_straddles_threshold",
    }:
        lines += [
            "",
            f"> 下一步：加大样本，例如 `--pack standard`（24 题）或 `--pack deep`。"
            f"当前用掉约 {report['used_tokens']} token，继续加测的成本仍很小。",
        ]
    if report["reason"] == "token_budget_exhausted":
        lines += ["", "> 预算用尽即停。调高 `--token-budget` 可继续判定。"]

    lines += [
        "",
        "> 本判定回答「够不够用」，不是「是不是某个具体模型」。黑盒方法无法证明模型身份，",
        "> 只能给出能力区间。",
    ]
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"
