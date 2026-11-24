from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .capability import (
    DEFAULT_PACK,
    DEFAULT_PROFILE,
    PROFILES,
    check_capability,
    estimate_tokens,
    render_capability_report,
    select_probes,
)
from .fingerprint import (
    compare_run_to_baselines,
    load_json,
    load_probes,
    make_baseline,
    run_audit,
    write_json,
)
from .reporting import render_markdown_report, write_markdown

# Exit codes are part of the interface: agents can branch on them without parsing.
EXIT_SUFFICIENT = 0
EXIT_INSUFFICIENT = 1
EXIT_UNDETERMINED = 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="self-awaken",
        description="Black-box model transparency audit toolkit.",
    )
    subparsers = parser.add_subparsers(required=True)

    list_parser = subparsers.add_parser("list-probes", help="List probes in a JSONL probe file.")
    list_parser.add_argument("--probes", required=True)
    list_parser.set_defaults(func=cmd_list_probes)

    run_parser = subparsers.add_parser("run", help="Run probes against an OpenAI-compatible endpoint.")
    run_parser.add_argument("--endpoint", default=os.getenv("SELF_AWAKEN_ENDPOINT", "https://api.openai.com/v1"))
    run_parser.add_argument("--api-key", default=os.getenv("SELF_AWAKEN_API_KEY"))
    run_parser.add_argument("--model", required=True)
    run_parser.add_argument("--probes", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--temperature", type=float, default=0.0)
    run_parser.add_argument("--max-tokens", type=int, default=512)
    run_parser.add_argument("--workers", type=int, default=1)
    run_parser.add_argument("--timeout", type=int, default=90)
    run_parser.add_argument(
        "--provider",
        default=os.getenv("SELF_AWAKEN_API_TYPE", "openai"),
        help="API provider: openai, azure, anthropic (openai-compatible proxy uses openai).",
    )
    run_parser.set_defaults(func=cmd_run)

    baseline_parser = subparsers.add_parser("make-baseline", help="Create a baseline from a trusted run.")
    baseline_parser.add_argument("--run", required=True)
    baseline_parser.add_argument("--name", required=True)
    baseline_parser.add_argument("--out", required=True)
    baseline_parser.set_defaults(func=cmd_make_baseline)

    compare_parser = subparsers.add_parser("compare", help="Compare a run against one or more baselines.")
    compare_parser.add_argument("--run", required=True)
    compare_parser.add_argument("--baselines", nargs="+", required=True)
    compare_parser.add_argument("--out")
    compare_parser.add_argument("--json-out")
    compare_parser.set_defaults(func=cmd_compare)

    check_parser = subparsers.add_parser(
        "check",
        help="Cheaply decide whether an endpoint is good enough for a capability profile.",
    )
    check_parser.add_argument("--endpoint", default=os.getenv("SELF_AWAKEN_ENDPOINT", "https://api.openai.com/v1"))
    check_parser.add_argument("--api-key", default=os.getenv("SELF_AWAKEN_API_KEY"))
    check_parser.add_argument("--model", required=True)
    check_parser.add_argument("--probes", default="data/probes")
    check_parser.add_argument("--profile", default=DEFAULT_PROFILE, choices=sorted(PROFILES))
    check_parser.add_argument("--pack", default=DEFAULT_PACK, choices=["smoke", "standard", "deep"])
    check_parser.add_argument("--threshold", type=float, default=None)
    check_parser.add_argument("--max-tokens", type=int, default=192)
    check_parser.add_argument("--token-budget", type=int, default=40000)
    check_parser.add_argument("--max-probes", type=int, default=None)
    check_parser.add_argument("--min-probes", type=int, default=10)
    check_parser.add_argument("--temperature", type=float, default=0.0)
    check_parser.add_argument("--timeout", type=int, default=90)
    check_parser.add_argument(
        "--provider",
        default=os.getenv("SELF_AWAKEN_API_TYPE", "openai"),
    )
    check_parser.add_argument("--estimate-only", action="store_true", help="Print the cost estimate and exit.")
    check_parser.add_argument("--json", action="store_true", help="Print the full report as JSON.")
    check_parser.add_argument("--out", help="Also write the JSON report to this path.")
    check_parser.set_defaults(func=cmd_check)

    lint_parser = subparsers.add_parser("lint-probes", help="Check a probe bank for bad expected values.")
    lint_parser.add_argument("--probes", required=True)
    lint_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors.")
    lint_parser.set_defaults(func=cmd_lint_probes)

    return parser


def cmd_list_probes(args: argparse.Namespace) -> int:
    probes = load_probes(args.probes)
    for probe in probes:
        print(f"{probe.id}\t{probe.category}\t{','.join(probe.tags)}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if not args.api_key:
        raise SystemExit("missing API key: pass --api-key or set SELF_AWAKEN_API_KEY")

    probes = load_probes(args.probes)
    run = run_audit(
        endpoint=args.endpoint,
        api_key=args.api_key,
        model=args.model,
        probes=probes,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        workers=args.workers,
        timeout=args.timeout,
        api_type=args.provider,
    )
    write_json(args.out, run)
    print(f"wrote run: {Path(args.out)}")
    return 0


def cmd_make_baseline(args: argparse.Namespace) -> int:
    run = load_json(args.run)
    baseline = make_baseline(run, args.name)
    write_json(args.out, baseline)
    print(f"wrote baseline: {Path(args.out)}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    run = load_json(args.run)
    baselines = [load_json(path) for path in args.baselines]
    comparison = compare_run_to_baselines(run, baselines)

    if args.json_out:
        write_json(args.json_out, comparison)

    report = render_markdown_report(comparison)
    if args.out:
        write_markdown(args.out, report)
        print(f"wrote report: {Path(args.out)}")
    else:
        print(report)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    probes = load_probes(args.probes)
    selected = select_probes(probes, args.profile, args.pack)
    if args.max_probes:
        selected = selected[: args.max_probes]
    estimate = estimate_tokens(selected, args.max_tokens)

    if args.estimate_only:
        print(f"profile: {args.profile} ({PROFILES[args.profile]['label']})")
        print(f"pack: {args.pack}")
        print(f"probes: {len(selected)}")
        print(f"estimated_tokens: {estimate}")
        print("no request was made")
        return EXIT_SUFFICIENT

    if not args.api_key:
        raise SystemExit("missing API key: pass --api-key or set SELF_AWAKEN_API_KEY")

    def _progress(count: int, verdict) -> None:
        if sys.stderr.isatty():
            print(
                f"\r[{count}/{len(selected)}] {verdict.verdict} "
                f"accuracy={verdict.accuracy if verdict.accuracy is None else round(verdict.accuracy, 2)}",
                end="",
                file=sys.stderr,
                flush=True,
            )

    report = check_capability(
        endpoint=args.endpoint,
        api_key=args.api_key,
        model=args.model,
        probes=probes,
        profile=args.profile,
        pack=args.pack,
        threshold=args.threshold,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        timeout=args.timeout,
        api_type=args.provider,
        token_budget=args.token_budget,
        max_probes=args.max_probes,
        min_probes=args.min_probes,
        on_progress=_progress,
    )
    if sys.stderr.isatty():
        print("", file=sys.stderr)

    if args.out:
        write_json(args.out, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_capability_report(report))
        if args.out:
            print(f"wrote report: {Path(args.out)}")

    return {
        "sufficient": EXIT_SUFFICIENT,
        "insufficient": EXIT_INSUFFICIENT,
    }.get(report["verdict"], EXIT_UNDETERMINED)


def cmd_lint_probes(args: argparse.Namespace) -> int:
    from .probe_lint import lint_probes, summarize_issues

    probes = load_probes(args.probes)
    issues = lint_probes(probes)
    counts = summarize_issues(issues)

    for issue in issues:
        print(f"{issue.severity}\t{issue.probe_id}\t{issue.code}\t{issue.message}")

    print(f"\n{len(probes)} probes, {counts['error']} errors, {counts['warning']} warnings")
    if counts["error"]:
        return EXIT_INSUFFICIENT
    if args.strict and counts["warning"]:
        return EXIT_INSUFFICIENT
    return EXIT_SUFFICIENT


if __name__ == "__main__":
    raise SystemExit(main())

