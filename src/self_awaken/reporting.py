from __future__ import annotations

from pathlib import Path
from typing import Any


def render_markdown_report(comparison: dict[str, Any]) -> str:
    run = comparison.get("run", {})
    summary = run.get("summary", {})
    lines = [
        "# Self-Awakening 审计报告",
        "",
        f"- 请求模型：`{run.get('requested_model', 'unknown')}`",
        f"- 接口：`{run.get('endpoint', 'unknown')}`",
        f"- 探针数量：`{summary.get('probe_count', 0)}`",
        f"- 客观题正确率：`{summary.get('accuracy')}`",
        f"- 平均延迟 ms：`{summary.get('avg_latency_ms')}`",
        "",
        "## 基线相似度",
        "",
        "| 排名 | 基线 | 相似度 | 置信 | 命中探针 |",
        "| --- | --- | ---: | --- | ---: |",
    ]

    for index, item in enumerate(comparison.get("comparisons", []), start=1):
        lines.append(
            f"| {index} | {item['baseline']} | {item['similarity']} | "
            f"{item['confidence']} | {item['matched_probe_count']} |"
        )

    lines.extend(["", "## 证据摘录", ""])
    for item in comparison.get("comparisons", [])[:3]:
        lines.append(f"### {item['baseline']}")
        lines.append("")
        if not item.get("top_evidence"):
            lines.append("没有足够的探针交集。")
            lines.append("")
            continue
        lines.append("| 探针 | 局部分数 | 选项一致 | 得分一致 | 哈希一致 |")
        lines.append("| --- | ---: | --- | --- | --- |")
        for evidence in item["top_evidence"]:
            lines.append(
                f"| `{evidence['probe_id']}` | {evidence['score']} | "
                f"{_yes_no(evidence['choice_match'])} | "
                f"{_yes_no(evidence['score_match'])} | "
                f"{_yes_no(evidence['digest_match'])} |"
            )
        lines.append("")

    lines.extend(
        [
            "## 解读边界",
            "",
            "本报告是黑盒相似度审计，不是模型身份的绝对证明。动态路由、系统提示词、温度参数、供应商版本更新、缓存策略和题库泄漏都会影响结果。",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"

