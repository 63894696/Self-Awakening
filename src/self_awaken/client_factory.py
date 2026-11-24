"""Factory for API clients based on provider configuration."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .client import OpenAICompatibleClient
from .config import API_TYPE, AZURE_API_VERSION, BASE_DELAY, MAX_RETRY


def create_client(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    timeout: int = 90,
    api_type: str | None = None,
    max_retry: int | None = None,
    base_delay: float | None = None,
    **kwargs: Any,
) -> OpenAICompatibleClient:
    """Return a client for the configured API provider."""
    provider = (api_type or API_TYPE).strip().lower()

    if provider == "openai":
        return OpenAICompatibleClient(
            endpoint=endpoint,
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_retry=max_retry if max_retry is not None else MAX_RETRY,
            base_delay=base_delay if base_delay is not None else BASE_DELAY,
        )

    if provider == "azure":
        return _create_azure_client(
            endpoint=endpoint,
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_retry=max_retry if max_retry is not None else MAX_RETRY,
            base_delay=base_delay if base_delay is not None else BASE_DELAY,
            api_version=kwargs.get("api_version", AZURE_API_VERSION),
        )

    if provider == "anthropic":
        raise NotImplementedError(
            "anthropic provider is not implemented; use openai-compatible proxy or openai provider"
        )

    raise ValueError(f"unsupported API type: {provider}")


def _create_azure_client(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    timeout: int,
    max_retry: int,
    base_delay: float,
    api_version: str,
) -> OpenAICompatibleClient:
    parsed = urlparse(endpoint.rstrip("/"))
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("api-version", api_version)
    azure_endpoint = urlunparse(parsed._replace(query=urlencode(query)))

    return OpenAICompatibleClient(
        endpoint=azure_endpoint,
        api_key=api_key,
        model=model,
        timeout=timeout,
        max_retry=max_retry,
        base_delay=base_delay,
        auth_header="api-key",
    )
