from __future__ import annotations

import argparse
import os
from pathlib import Path

from .fingerprint import (
    compare_run_to_baselines,
    load_json,
    load_probes,
    make_baseline,
    run_audit,
    write_json,
)
from .reporting import render_markdown_report, write_markdown


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


if __name__ == "__main__":
    raise SystemExit(main())

