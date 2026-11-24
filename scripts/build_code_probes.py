"""Regenerate ``data/probes/code.zh.jsonl``.

The core bank only had 9 ``code`` probes, which is not enough to reach a
statistical decision (12+ probes are needed before a 100% pass rate clears an
80% threshold at the 90% confidence level). This script adds deterministic
Python-semantics probes and — importantly — **derives every expected value by
executing Python**, so the expectations cannot drift from reality.

Run: ``python scripts/build_code_probes.py``
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probes" / "code.zh.jsonl"

# (probe id, what the question asks, Python expression that defines the answer)
ITEMS: list[tuple[str, str, str]] = [
    ("code-101", "7 // 2", "7 // 2"),
    ("code-102", "len('你好abc')", "len('你好abc')"),
    ("code-103", "[1, 2, 3][-1]", "[1, 2, 3][-1]"),
    ("code-104", "1 + 2 * 3 ** 2", "1 + 2 * 3 ** 2"),
    ("code-105", "3 / 2", "3 / 2"),
    ("code-106", "7 % 4", "7 % 4"),
    ("code-107", "len(set([1, 1, 2, 3, 3]))", "len(set([1, 1, 2, 3, 3]))"),
    ("code-108", "sum(range(2, 8, 3))", "sum(range(2, 8, 3))"),
    ("code-109", "int('3' * 2)", "int('3' * 2)"),
    ("code-110", "5 and 0 or 7", "5 and 0 or 7"),
    ("code-111", "{'a': 1}.get('b', 0)", "{'a': 1}.get('b', 0)"),
    ("code-112", "[x * 2 for x in range(3)][-1]", "[x * 2 for x in range(3)][-1]"),
    ("code-113", "2 ** 10", "2 ** 10"),
    ("code-114", "-7 // 2", "-7 // 2"),
    ("code-115", "len([1, [2, 3]][1])", "len([1, [2, 3]][1])"),
    ("code-117", "sorted([3, 1, 2])[0]", "sorted([3, 1, 2])[0]"),
    ("code-118", "'abc'.find('z')", "'abc'.find('z')"),
]
TEMPLATE = "只输出最终结果，不要解释。Python 表达式 `{expr}` 的值是什么？"


def main() -> int:
    lines: list[str] = []
    for probe_id, expr, py_expr in ITEMS:
        expected = str(eval(py_expr))  # noqa: S307 - fixed literal inputs.
        probe = {
            "id": probe_id,
            "category": "code",
            "prompt": TEMPLATE.format(expr=expr),
            "expected": expected,
            "tags": ["objective", "python", "derived"],
        }
        lines.append(json.dumps(probe, ensure_ascii=False))

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(lines)} probes to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
