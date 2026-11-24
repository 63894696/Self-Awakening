import pytest

from self_awaken.client import OpenAICompatibleClient
from self_awaken.client_factory import create_client


def test_create_openai_client():
    client = create_client(
        endpoint="https://api.example.com/v1",
        api_key="key",
        model="gpt-test",
        api_type="openai",
    )
    assert isinstance(client, OpenAICompatibleClient)
    assert client.endpoint.endswith("/chat/completions")


def test_create_azure_client_uses_api_key_header():
    client = create_client(
        endpoint="https://example.openai.azure.com/openai/deployments/demo",
        api_key="azure-key",
        model="gpt-4",
        api_type="azure",
        api_version="2024-06-01",
    )
    assert client.auth_header == "api-key"
    assert "api-version=2024-06-01" in client.endpoint


def test_unsupported_provider():
    with pytest.raises(ValueError, match="unsupported API type"):
        create_client(
            endpoint="https://api.example.com",
            api_key="k",
            model="m",
            api_type="unknown",
        )


def test_anthropic_not_implemented():
    with pytest.raises(NotImplementedError):
        create_client(
            endpoint="https://api.anthropic.com",
            api_key="k",
            model="claude",
            api_type="anthropic",
        )
