from dataclasses import dataclass
from typing import List, Any

@dataclass
class Probe:
    """Simple data container for a probe definition.

    Attributes correspond to the fields present in the JSONL probe files.
    """
    id: Any
    category: Any
    prompt: Any
    expected: Any
    tags: List[Any]

    @classmethod
    def from_dict(cls, data: dict) -> "Probe":
        """Create a :class:Probe from a raw dict.

        Missing `tags` defaults to an empty list.
        """
        return cls(
            id=data.get("id"),
            category=data.get("category"),
            prompt=data.get("prompt"),
            expected=data.get("expected"),
            tags=data.get("tags", []),
        )
