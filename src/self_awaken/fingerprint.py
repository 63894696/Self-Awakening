from __future__ import annotations

import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import OpenAICompatibleClient
from .client_factory import create_client
from .errors import EmptyResponseError
from .schemas import Probe, ProbeResult
from .scoring import answer_digest, score_answer


SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, data: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_probes(path: str | Path) -> list[Probe]:
    target = Path(path)
    if target.is_dir():
        files = sorted(target.glob("*.jsonl"))
        if not files:
            raise ValueError(f"no JSONL probe files found in directory: {target}")
        probes: list[Probe] = []
        for file_path in files:
            probes.extend(_load_probes_file(file_path))
        if not probes:
            raise ValueError(f"no probes found in directory: {target}")
        return probes
    return _load_probes_file(target)


def _load_probes_file(path: Path) -> list[Probe]:
    probes: list[Probe] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_no}: {exc}") from exc
            probes.append(Probe.from_dict(data))
    if not probes:
        raise ValueError(f"no probes found in {path}")
    return probes


def run_audit(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    probes: list[Probe],
    temperature: float = 0.0,
    max_tokens: int = 512,
    workers: int = 1,
    timeout: int = 90,
    api_type: str | None = None,
) -> dict[str, Any]:
    client = create_client(
        endpoint=endpoint,
        api_key=api_key,
        model=model,
        timeout=timeout,
        api_type=api_type,
    )
    results: list[ProbeResult] = []

    if workers <= 1:
        for probe in probes:
            results.append(_run_one(client, probe, temperature, max_tokens))
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_run_one, client, probe, temperature, max_tokens): probe.id
                for probe in probes
            }
            by_id: dict[str, ProbeResult] = {}
            for future in as_completed(futures):
                result = future.result()
                by_id[result.probe_id] = result
            results = [by_id[probe.id] for probe in probes]

    run = {
        "schema_version": SCHEMA_VERSION,
        "kind": "run",
        "created_at": utc_now(),
        "endpoint": _redact_endpoint(endpoint),
        "requested_model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "summary": summarize_results([result.to_dict() for result in results]),
        "results": [result.to_dict() for result in results],
    }
    return run


def make_baseline(run: dict[str, Any], name: str) -> dict[str, Any]:
    probes = {}
    for result in run.get("results", []):
        probe_id = result["probe_id"]
        probes[probe_id] = {
            "category": result.get("category"),
            "score": result.get("score"),
            "choice": result.get("choice"),
            "answer_digest": answer_digest(result.get("answer", "")),
            "completion_tokens": result.get("completion_tokens"),
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "baseline",
        "name": name,
        "created_at": utc_now(),
        "source": {
            "requested_model": run.get("requested_model"),
            "endpoint": run.get("endpoint"),
            "temperature": run.get("temperature"),
            "max_tokens": run.get("max_tokens"),
        },
        "summary": run.get("summary", {}),
        "probes": probes,
    }


def compare_run_to_baselines(run: dict[str, Any], baselines: list[dict[str, Any]]) -> dict[str, Any]:
    results = run.get("results", [])
    comparisons = [_compare_one(results, run.get("summary", {}), baseline) for baseline in baselines]
    comparisons.sort(key=lambda item: item["similarity"], reverse=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "comparison",
        "created_at": utc_now(),
        "run": {
            "requested_model": run.get("requested_model"),
            "endpoint": run.get("endpoint"),
            "summary": run.get("summary", {}),
        },
        "comparisons": comparisons,
    }


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [result["score"] for result in results if result.get("score") is not None]
    latencies = [result["latency_ms"] for result in results if result.get("latency_ms") is not None]
    completion_tokens = [
        result["completion_tokens"]
        for result in results
        if result.get("completion_tokens") is not None
    ]
    errors = [result for result in results if result.get("error")]
    return {
        "probe_count": len(results),
        "scored_count": len(scored),
        "accuracy": round(sum(scored) / len(scored), 4) if scored else None,
        "avg_latency_ms": round(statistics.mean(latencies), 2) if latencies else None,
        "avg_completion_tokens": round(statistics.mean(completion_tokens), 2) if completion_tokens else None,
        "error_count": len(errors),
    }


def _run_one(
    client: OpenAICompatibleClient,
    probe: Probe,
    temperature: float,
    max_tokens: int,
) -> ProbeResult:
    try:
        completion = client.complete(probe.prompt, temperature=temperature, max_tokens=max_tokens)
        score, choice = score_answer(probe.expected, completion.answer)
        return ProbeResult(
            probe_id=probe.id,
            category=probe.category,
            prompt=probe.prompt,
            answer=completion.answer,
            expected=probe.expected,
            score=score,
            choice=choice,
            latency_ms=completion.latency_ms,
            prompt_tokens=completion.prompt_tokens,
            completion_tokens=completion.completion_tokens,
            total_tokens=completion.total_tokens,
        )
    except Exception as exc:  # noqa: BLE001 - audit runs should preserve per-probe failures.
        return ProbeResult(
            probe_id=probe.id,
            category=probe.category,
            prompt=probe.prompt,
            answer="",
            expected=probe.expected,
            score=None,
            choice=None,
            latency_ms=0,
            error=_format_probe_error(exc),
        )


def _format_probe_error(exc: Exception) -> str:
    if isinstance(exc, EmptyResponseError):
        return f"empty_response: {exc}"
    return str(exc)


def _compare_one(
    results: list[dict[str, Any]],
    run_summary: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    baseline_probes = baseline.get("probes", {})
    evidence: list[dict[str, Any]] = []
    total_weight = 0.0
    total_score = 0.0

    for result in results:
        probe_id = result.get("probe_id")
        base = baseline_probes.get(probe_id)
        if not base:
            continue

        probe_weight = 0.0
        probe_score = 0.0
        digest = answer_digest(result.get("answer", ""))

        if result.get("choice") is not None and base.get("choice") is not None:
            probe_weight += 0.65
            if result["choice"] == base["choice"]:
                probe_score += 0.65

        if result.get("score") is not None and base.get("score") is not None:
            probe_weight += 0.25
            if result["score"] == base["score"]:
                probe_score += 0.25

        if base.get("answer_digest"):
            probe_weight += 0.10
            if digest == base["answer_digest"]:
                probe_score += 0.10

        if probe_weight:
            total_weight += probe_weight
            total_score += probe_score
            evidence.append(
                {
                    "probe_id": probe_id,
                    "score": round(probe_score / probe_weight, 4),
                    "choice_match": result.get("choice") == base.get("choice"),
                    "score_match": result.get("score") == base.get("score"),
                    "digest_match": digest == base.get("answer_digest"),
                }
            )

    behavioral_similarity = total_score / total_weight if total_weight else 0.0
    accuracy_similarity = _accuracy_similarity(run_summary, baseline.get("summary", {}))
    similarity = round((behavioral_similarity * 0.8) + (accuracy_similarity * 0.2), 4)
    return {
        "baseline": baseline.get("name", "unnamed baseline"),
        "similarity": similarity,
        "confidence": _confidence(similarity, len(evidence)),
        "matched_probe_count": len(evidence),
        "accuracy_similarity": round(accuracy_similarity, 4),
        "behavioral_similarity": round(behavioral_similarity, 4),
        "top_evidence": evidence[:8],
    }


def _accuracy_similarity(run_summary: dict[str, Any], baseline_summary: dict[str, Any]) -> float:
    run_accuracy = run_summary.get("accuracy")
    baseline_accuracy = baseline_summary.get("accuracy")
    if run_accuracy is None or baseline_accuracy is None:
        return 0.0
    delta = abs(float(run_accuracy) - float(baseline_accuracy))
    return max(0.0, 1.0 - (delta * 2.0))


def _confidence(similarity: float, matched_probe_count: int) -> str:
    if matched_probe_count < 5:
        return "low"
    if similarity >= 0.85:
        return "high"
    if similarity >= 0.65:
        return "medium"
    return "low"


def _redact_endpoint(endpoint: str) -> str:
    return endpoint.rstrip("/")

