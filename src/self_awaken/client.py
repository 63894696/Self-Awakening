"""OpenAI-compatible HTTP client with retry and empty-response handling."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .errors import EmptyResponseError, RetryError
from .retry import RetryHandler


@dataclass(frozen=True)
class ChatCompletion:
    answer: str
    latency_ms: int
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    raw_model: str | None = None


class OpenAICompatibleClient:
    """Thin wrapper around OpenAI-compatible /chat/completions endpoints."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        timeout: int = 90,
        max_retry: int = 5,
        base_delay: float = 0.5,
        auth_header: str = "Authorization",
    ) -> None:
        self.endpoint = _completion_url(endpoint)
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retry = max_retry
        self.base_delay = base_delay
        self.auth_header = auth_header
        self._request_start: float = 0.0

    def complete(self, prompt: str, temperature: float = 0.0, max_tokens: int = 512) -> ChatCompletion:
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        payload = json.dumps(body).encode("utf-8")
        headers = {
            self._authorization_header_name(): self._authorization_value(),
            "Content-Type": "application/json",
        }
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers=headers,
            method="POST",
        )

        handler = RetryHandler(max_retry=self.max_retry, base_delay=self.base_delay)
        max_content_attempts = 2
        last_content_error: EmptyResponseError | None = None

        for content_attempt in range(max_content_attempts):
            raw = handler.call(self._raw_post, request)
            latency_ms = int((time.perf_counter() - self._request_start) * 1000)
            data = json.loads(raw)
            try:
                answer = _extract_answer(data)
            except EmptyResponseError as exc:
                last_content_error = exc
                if content_attempt < max_content_attempts - 1:
                    continue
                raise

            usage = data.get("usage", {}) if isinstance(data, dict) else {}
            return ChatCompletion(
                answer=answer,
                latency_ms=latency_ms,
                prompt_tokens=_optional_int(usage.get("prompt_tokens")),
                completion_tokens=_optional_int(usage.get("completion_tokens")),
                total_tokens=_optional_int(usage.get("total_tokens")),
                raw_model=str(data.get("model")) if isinstance(data, dict) and data.get("model") else None,
            )

        if last_content_error:
            raise last_content_error
        raise EmptyResponseError("response missing assistant content")

    call_api = complete

    def _authorization_header_name(self) -> str:
        if self.auth_header.lower() == "api-key":
            return "api-key"
        return "Authorization"

    def _authorization_value(self) -> str:
        if self.auth_header.lower() == "api-key":
            return self.api_key
        return f"Bearer {self.api_key}"

    def _raw_post(self, request: urllib.request.Request) -> str:
        self._request_start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise RetryError("Rate limit reached (429)", status_code=429) from exc
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"request failed: {exc.reason}") from exc

        if not raw or not raw.strip():
            err = EmptyResponseError("Empty response received from API")
            raise RetryError(str(err), status_code=None) from err

        return raw


def _completion_url(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/chat/completions"):
        return endpoint
    return f"{endpoint}/chat/completions"


def _extract_answer(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not choices:
        raise RuntimeError("response missing choices")

    first = choices[0]
    if not isinstance(first, dict):
        raise EmptyResponseError("response missing assistant content")

    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if content is not None:
            text = str(content)
            if text.strip():
                return text
            raise EmptyResponseError("response missing assistant content")

    text_field = first.get("text")
    if text_field is not None:
        text = str(text_field)
        if text.strip():
            return text
        raise EmptyResponseError("response missing assistant content")

    raise EmptyResponseError("response missing assistant content")


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
