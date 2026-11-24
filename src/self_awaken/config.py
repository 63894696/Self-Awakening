"""Runtime configuration from environment variables."""

from __future__ import annotations

import os

API_TYPE = os.getenv("SELF_AWAKEN_API_TYPE", "openai").strip().lower()
MAX_RETRY = int(os.getenv("SELF_AWAKEN_MAX_RETRY", "5"))
BASE_DELAY = float(os.getenv("SELF_AWAKEN_BASE_DELAY", "0.5"))
AZURE_API_VERSION = os.getenv("SELF_AWAKEN_AZURE_API_VERSION", "2024-02-15-preview")
