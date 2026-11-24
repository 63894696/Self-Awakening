import time
from unittest.mock import Mock, patch

import pytest

from self_awaken.errors import RetryError
from self_awaken.retry import RetryHandler


class TestRetryHandler:
    def test_successful_call(self):
        mock_func = Mock(return_value="success")
        handler = RetryHandler(max_retry=3)
        result = handler.call(mock_func)

        assert result == "success"
        mock_func.assert_called_once()

    def test_retry_on_429(self):
        class RateLimitError(Exception):
            status_code = 429

        mock_func = Mock(side_effect=[RateLimitError(), RateLimitError(), "success"])
        handler = RetryHandler(max_retry=3, base_delay=0.1)

        with patch("time.sleep"):
            result = handler.call(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_on_connection_error(self):
        mock_func = Mock(side_effect=[ConnectionError("failed"), ConnectionError("failed"), "success"])
        handler = RetryHandler(max_retry=3, base_delay=0.1)

        with patch("time.sleep"):
            result = handler.call(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_exhausted_retries(self):
        mock_func = Mock(side_effect=ConnectionError("Persistent error"))
        handler = RetryHandler(max_retry=2, base_delay=0.1)

        with patch("time.sleep"):
            with pytest.raises(ConnectionError, match="Persistent error"):
                handler.call(mock_func)
        assert mock_func.call_count == 3

    def test_no_retry_on_unsupported_exception(self):
        mock_func = Mock(side_effect=ValueError("Invalid input"))
        handler = RetryHandler(max_retry=3)

        with pytest.raises(ValueError, match="Invalid input"):
            handler.call(mock_func)
        assert mock_func.call_count == 1

    def test_custom_exceptions(self):
        mock_func = Mock(side_effect=[ValueError("Retry this"), "success"])
        handler = RetryHandler(max_retry=2, retry_exceptions=[ValueError])

        with patch("time.sleep"):
            result = handler.call(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_error_type(self):
        mock_func = Mock(side_effect=[RetryError("rate limit", status_code=429), "ok"])
        handler = RetryHandler(max_retry=2, base_delay=0.01)

        with patch("time.sleep"):
            assert handler.call(mock_func) == "ok"
