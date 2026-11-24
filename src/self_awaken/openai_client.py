"""Backward-compatible aliases for the merged OpenAI client."""

from __future__ import annotations

from .client import ChatCompletion, OpenAICompatibleClient, _completion_url, _extract_answer
from .errors import EmptyResponseError, RetryError

OpenAIClient = OpenAICompatibleClient

__all__ = [
    "ChatCompletion",
    "EmptyResponseError",
    "OpenAIClient",
    "OpenAICompatibleClient",
    "RetryError",
    "_completion_url",
    "_extract_answer",
]
