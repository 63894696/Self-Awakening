"""Automatic retry with exponential backoff on rate limits and connection errors."""

from __future__ import annotations

import logging
import random
import time
import urllib.error
from typing import Any, Callable, List, Optional, Type

from .errors import RetryError


class RetryHandler:
    """Retry a callable on transient failures with exponential backoff."""

    def __init__(
        self,
        max_retry: int = 5,
        base_delay: float = 0.5,
        retry_exceptions: Optional[List[Type[Exception]]] = None,
    ) -> None:
        self.max_retry = max_retry
        self.base_delay = base_delay
        self.retry_exceptions = retry_exceptions or [
            ConnectionError,
            TimeoutError,
            OSError,
            urllib.error.HTTPError,
            RetryError,
        ]
        self.logger = logging.getLogger(__name__)

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        last_exception: Exception | None = None

        for attempt in range(self.max_retry + 1):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                if not self._should_retry(exc):
                    raise

                last_exception = exc
                if attempt < self.max_retry:
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(
                        "Attempt %s failed: %s. Retrying in %.2fs",
                        attempt + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    self.logger.error("All %s attempts failed. Last error: %s", self.max_retry, exc)
                    break

        if last_exception:
            raise last_exception
        raise RuntimeError("All retries exhausted without raising")

    def _should_retry(self, exception: Exception) -> bool:
        for retry_exception in self.retry_exceptions:
            if isinstance(exception, retry_exception):
                return True
        if getattr(exception, "status_code", None) == 429:
            return True
        if getattr(exception, "code", None) == 429:
            return True
        return False

    def _calculate_delay(self, attempt: int) -> float:
        delay = self.base_delay * (2**attempt)
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter
