import json
from typing import Iterable
from .models import Probe

def load_probes(path: str) -> Iterable[Probe]:
    """
    Load probes from a JSONL file.

    Each line is expected to be a JSON object representing a probe.
    Yields Probe instances.
    """
    with open(path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                yield Probe.from_dict(data)
            except json.JSONDecodeError as e:
                raise ValueError(f'Invalid JSON on line {line_num}: {line}') from e
