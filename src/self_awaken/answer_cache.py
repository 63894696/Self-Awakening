"""Answer cache: never pay twice for the same probe against the same endpoint.

A capability check is cheap, but it is also repeated: the same endpoint is
re-checked after a provider update, in CI, or by several agents. Every repeat
currently re-bills the prompts. The cache makes a repeated check free for probes
that were already answered with the same effective request.

Design constraints:

- **Key covers everything that changes the answer**: endpoint, model, prompt,
  temperature. A different model or endpoint must never hit the same entry, or a
  cached answer could mask a substitution.
- **Append-only JSONL.** A crash mid-run must not corrupt earlier entries; on
  load, the last record for a key wins.
- **Never cache errors.** A rate limit or timeout is a transient condition, not
  an answer.
- **Cache hits cost zero tokens** and are reported separately, so the token
  figure in a report always means "tokens actually spent".
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CACHE_VERSION = 1


def default_cache_path() -> Path:
    """Platform cache location, never inside the working repository."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
    else:
        base = os.environ.get("XDG_CACHE_HOME")
        root = Path(base) if base else Path.home() / ".cache"
    return root / "self-awaken" / "answers.jsonl"


def cache_key(*, endpoint: str, model: str, prompt: str, temperature: float) -> str:
    material = json.dumps(
        {
            "v": CACHE_VERSION,
            "endpoint": endpoint.rstrip("/").lower(),
            "model": model.strip(),
            "prompt": prompt,
            "temperature": round(float(temperature), 4),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CachedAnswer:
    answer: str
    latency_ms: int
    prompt_tokens: int | None
    completion_tokens: int | None
    finish_reason: str | None
    raw_model: str | None
    created_at: float

    def as_completion(self) -> Any:
        """Return an object shaped like ``ChatCompletion`` for the caller."""
        from .client import ChatCompletion

        return ChatCompletion(
            answer=self.answer,
            latency_ms=0,  # No network round trip this time.
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            raw_model=self.raw_model,
            finish_reason=self.finish_reason,
        )


class AnswerCache:
    """Append-only cache of successful answers."""

    def __init__(self, path: str | Path | None = None, *, enabled: bool = True) -> None:
        self.path = Path(path) if path else default_cache_path()
        self.enabled = enabled
        self._entries: dict[str, CachedAnswer] = {}
        self.hits = 0
        self.misses = 0
        self.stores = 0
        if self.enabled:
            self._load()

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, key: str) -> CachedAnswer | None:
        if not self.enabled:
            return None
        entry = self._entries.get(key)
        if entry is None:
            self.misses += 1
            return None
        self.hits += 1
        return entry

    def put(self, key: str, completion: Any) -> None:
        if not self.enabled:
            return
        answer = getattr(completion, "answer", None)
        if not answer or not str(answer).strip():
            return
        if getattr(completion, "finish_reason", None) == "length":
            # A truncated answer must not be replayed as if it were final.
            return
        entry = CachedAnswer(
            answer=str(answer),
            latency_ms=int(getattr(completion, "latency_ms", 0) or 0),
            prompt_tokens=getattr(completion, "prompt_tokens", None),
            completion_tokens=getattr(completion, "completion_tokens", None),
            finish_reason=getattr(completion, "finish_reason", None),
            raw_model=getattr(completion, "raw_model", None),
            created_at=time.time(),
        )
        self._entries[key] = entry
        self.stores += 1
        self._append(key, entry)

    def stats(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "stored": self.stores, "entries": len(self._entries)}

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue  # A torn line from an interrupted run.
                    key = record.get("key")
                    payload = record.get("value") or {}
                    if not key or not isinstance(payload, dict):
                        continue
                    try:
                        self._entries[str(key)] = CachedAnswer(
                            answer=str(payload["answer"]),
                            latency_ms=int(payload.get("latency_ms") or 0),
                            prompt_tokens=payload.get("prompt_tokens"),
                            completion_tokens=payload.get("completion_tokens"),
                            finish_reason=payload.get("finish_reason"),
                            raw_model=payload.get("raw_model"),
                            created_at=float(payload.get("created_at") or 0),
                        )
                    except (KeyError, TypeError, ValueError):
                        continue
        except OSError as exc:  # A read-only or locked cache must not break the run.
            print(f"warning: answer cache unreadable ({exc}); continuing without it", file=sys.stderr)
            self.enabled = False

    def _append(self, key: str, entry: CachedAnswer) -> None:
        record = {
            "key": key,
            "value": {
                "answer": entry.answer,
                "latency_ms": entry.latency_ms,
                "prompt_tokens": entry.prompt_tokens,
                "completion_tokens": entry.completion_tokens,
                "finish_reason": entry.finish_reason,
                "raw_model": entry.raw_model,
                "created_at": entry.created_at,
            },
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            print(f"warning: could not write answer cache ({exc})", file=sys.stderr)
