from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Probe:
    id: str
    category: str
    prompt: str
    expected: str | None = None
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Probe":
        required = ["id", "category", "prompt"]
        missing = [key for key in required if not data.get(key)]
        if missing:
            raise ValueError(f"probe missing required fields: {', '.join(missing)}")

        tags = data.get("tags", [])
        if not isinstance(tags, list):
            raise ValueError(f"probe {data['id']} tags must be a list")

        return cls(
            id=str(data["id"]),
            category=str(data["category"]),
            prompt=str(data["prompt"]),
            expected=str(data["expected"]) if data.get("expected") is not None else None,
            tags=[str(tag) for tag in tags],
            notes=str(data.get("notes", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "prompt": self.prompt,
            "expected": self.expected,
            "tags": self.tags,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    category: str
    prompt: str
    answer: str
    expected: str | None
    score: float | None
    choice: str | None
    latency_ms: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "category": self.category,
            "prompt": self.prompt,
            "answer": self.answer,
            "expected": self.expected,
            "score": self.score,
            "choice": self.choice,
            "latency_ms": self.latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "error": self.error,
        }

