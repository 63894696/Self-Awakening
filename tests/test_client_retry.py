"""Unit tests for OpenAICompatibleClient retry and empty-response handling."""

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from self_awaken.client import ChatCompletion, OpenAICompatibleClient, _extract_answer
from self_awaken.errors import EmptyResponseError, RetryError


@pytest.fixture
def client():
    return OpenAICompatibleClient(
        endpoint="https://api.openai.com/v1",
        api_key="test-api-key",
        model="gpt-4o-mini",
        timeout=30,
        max_retry=5,
        base_delay=0.01,
    )


@pytest.fixture
def success_response():
    return {
        "id": "chatcmpl-test",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Test response from model."},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 9, "total_tokens": 21},
    }


def test_retry_on_429_then_success(client, success_response):
    http_error_429 = urllib.error.HTTPError(
        url="https://api.openai.com/v1/chat/completions",
        code=429,
        msg="Too Many Requests",
        hdrs=MagicMock(),
        fp=None,
    )
    raw_responses = [http_error_429, http_error_429, json.dumps(success_response)]
    call_count = [0]

    def mock_raw_post(self, request):
        idx = call_count[0]
        call_count[0] += 1
        response = raw_responses[idx]
        if isinstance(response, urllib.error.HTTPError):
            raise response
        return response

    with patch.object(OpenAICompatibleClient, "_raw_post", mock_raw_post):
        result = client.complete("What is 2+2?")

    assert call_count[0] == 3
    assert result.answer == "Test response from model."


def test_raises_retry_error_on_429_after_retries(client):
    http_error_429 = urllib.error.HTTPError(
        url="https://api.openai.com/v1/chat/completions",
        code=429,
        msg="Too Many Requests",
        hdrs=MagicMock(),
        fp=None,
    )

    def mock_raw_post(self, request):
        raise http_error_429

    with patch.object(OpenAICompatibleClient, "_raw_post", mock_raw_post):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            client.complete("Fail immediately")

    assert exc_info.value.code == 429


def test_retry_on_empty_body_then_success(client, success_response):
    call_count = [0]

    def mock_raw_post(self, request):
        idx = call_count[0]
        call_count[0] += 1
        if idx < 2:
            raise RetryError("Empty response received from API", status_code=None)
        return json.dumps(success_response)

    with patch.object(OpenAICompatibleClient, "_raw_post", mock_raw_post):
        result = client.complete("Trigger empty first")

    assert call_count[0] == 3
    assert result.answer == "Test response from model."


def test_raises_retry_error_on_empty_body_after_retries(client):
    def mock_raw_post(self, request):
        raise RetryError("Empty response received from API", status_code=None)

    with patch.object(OpenAICompatibleClient, "_raw_post", mock_raw_post):
        with pytest.raises(RetryError) as exc_info:
            client.complete("Always empty")

    assert "Empty response" in str(exc_info.value)


def test_retry_on_empty_content_then_success(client, success_response):
    empty_content = {
        "choices": [{"message": {"role": "assistant", "content": ""}}],
        "usage": {},
    }
    call_count = [0]

    def mock_raw_post(self, request):
        call_count[0] += 1
        if call_count[0] == 1:
            return json.dumps(empty_content)
        return json.dumps(success_response)

    with patch.object(OpenAICompatibleClient, "_raw_post", mock_raw_post):
        result = client.complete("Need content retry")

    assert call_count[0] == 2
    assert result.answer == "Test response from model."


def test_successful_call_returns_chat_completion(client, success_response):
    def mock_raw_post(self, request):
        return json.dumps(success_response)

    with patch.object(OpenAICompatibleClient, "_raw_post", mock_raw_post):
        result = client.complete("Hello")

    assert isinstance(result, ChatCompletion)
    assert result.answer == "Test response from model."


def test_extract_answer_raises_on_empty_content():
    with pytest.raises(EmptyResponseError):
        _extract_answer({"choices": [{"message": {"content": ""}}]})
