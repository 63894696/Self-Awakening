"""Make the repository root importable for tests run via the `pytest` entry point.

`pip install -e .` installs the `self_awaken` package, but the optional
`web_report` Flask app lives at the repository root and is not packaged.
Running `python -m pytest` already puts the current directory on sys.path;
running the `pytest` binary does not, so we add it here explicitly.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
