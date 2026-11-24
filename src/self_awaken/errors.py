"""Shared API error types for the Self-Awaken client layer."""


class RetryError(Exception):
    """Raised when a request should be retried (e.g. HTTP 429)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class EmptyResponseError(Exception):
    """Raised when the API returns no usable assistant content."""

    def __init__(self, message: str = "response missing assistant content") -> None:
        super().__init__(message)
