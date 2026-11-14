from __future__ import annotations

import json

import httpx
import pytest

from fabula.conversation import (
    Message,
    ProviderError,
    ProviderRequest,
    ProviderResponse,
    ProviderTimeout,
)
from fabula.conversation.config import ApiKeys, ConversationConfig, config_from_env, load_api_keys
from fabula.conversation.errors import ConversationSetupError
from fabula.conversation.mock import MockProvider
from fabula.conversation.providers import GeminiProvider, XaiProvider
from fabula.conversation.service import create_conversation_service


def _request() -> ProviderRequest:
    return ProviderRequest(
        messages=(),
        model="test-model",
        max_output_tokens=64,
        temperature=0.2,
    )


def _client(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler)


def test_mock_provider_replays_responses_and_chunks_streams() -> None:
    provider = MockProvider(
        [
            ProviderResponse(text="abcdefghijklmnopqrstuvwxyz", input_tokens=2, output_tokens=3),
            ProviderResponse(text="abcdefghijklmnopqrstuvwxyz", input_tokens=2, output_tokens=3),
        ]
    )

    response = provider.complete(_request())
    chunks = list(provider.stream(_request()))

    assert response.text == "abcdefghijklmnopqrstuvwxyz"
    assert "".join(chunks) == "abcdefghijklmnopqrstuvwxyz"
    assert provider.calls == 2


def test_mock_provider_can_raise_a_scripted_error() -> None:
    provider = MockProvider([ProviderTimeout("offline timeout")])
    with pytest.raises(ProviderTimeout):
        provider.complete(_request())


def test_gemini_complete_maps_messages_and_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/models/gemini-test:generateContent")
        assert request.headers["x-goog-api-key"] == "gemini-secret"
        payload = json.loads(request.content)
        assert payload["systemInstruction"]["parts"][0]["text"] == "rules"
        assert payload["contents"][0]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "hello"}]}}],
                "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 4},
            },
        )

    client = _client(httpx.MockTransport(handler))
    provider = GeminiProvider("gemini-secret", "gemini-test", client=client)
    request = ProviderRequest(
        messages=(Message(role="system", content="rules"), Message(role="user", content="hi")),
        model="gemini-test",
    )
    response = provider.complete(request)

    assert response.text == "hello"
    assert response.input_tokens == 11
    assert response.output_tokens == 4
    assert response.total_tokens == 15
    client.close()


def test_gemini_timeout_and_http_error_are_typed() -> None:
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    timeout_client = _client(httpx.MockTransport(timeout_handler))
    with pytest.raises(ProviderTimeout):
        GeminiProvider("key", "model", client=timeout_client).complete(_request())
    timeout_client.close()

    error_client = _client(httpx.MockTransport(lambda request: httpx.Response(500, text="nope")))
    with pytest.raises(ProviderError):
        GeminiProvider("key", "model", client=error_client).complete(_request())
    error_client.close()


def test_gemini_stream_yields_deltas() -> None:
    body = "\n".join(
        [
            'data: {"candidates":[{"content":{"parts":[{"text":"Hel"}]}}]}',
            'data: {"candidates":[{"content":{"parts":[{"text":"lo"}]}}]}',
        ]
    )
    client = _client(
        httpx.MockTransport(
            lambda request: httpx.Response(
                200, text=body, headers={"content-type": "text/event-stream"}
            )
        )
    )
    provider = GeminiProvider("key", "model", client=client)

    assert "".join(provider.stream(_request())) == "Hello"
    client.close()


def test_xai_complete_and_stream() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer xai-secret"
        payload = json.loads(request.content)
        if payload.get("stream"):
            return httpx.Response(
                200,
                text=(
                    'data: {"choices":[{"delta":{"content":"Hi"}}]}\n'
                    'data: {"choices":[{"delta":{"content":" there"}}]}\n'
                    "data: [DONE]\n"
                ),
                headers={"content-type": "text/event-stream"},
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 9, "completion_tokens": 3},
            },
        )

    client = _client(httpx.MockTransport(handler))
    provider = XaiProvider("xai-secret", "grok-test", client=client)

    response = provider.complete(_request())
    chunks = list(provider.stream(_request()))

    assert response.text == "hello"
    assert response.total_tokens == 12
    assert "".join(chunks) == "Hi there"
    client.close()


def test_load_api_keys_from_environment() -> None:
    keys = load_api_keys({"GEMINI_API_KEY": "g", "XAI_API_KEY": "x"})
    assert keys == ApiKeys(gemini="g", xai="x")


def test_config_from_env_reads_mode_models_and_toggles() -> None:
    config = config_from_env(
        {
            "FABULA_CONVERSATION_MODE": "scripted",
            "FABULA_GEMINI_MODEL": "gemini-test",
            "FABULA_LEAK_FILTER": "1",
        }
    )
    assert config.mode.value == "scripted"
    assert config.gemini_model == "gemini-test"
    assert config.leak_filter is True
    assert config.gated_reveal is False


def test_explicit_live_mode_without_keys_fails_clearly() -> None:
    with pytest.raises(ConversationSetupError):
        create_conversation_service(ConversationConfig(mode="live"), keys=ApiKeys())


def test_auto_mode_with_a_key_resolves_to_live() -> None:
    service = create_conversation_service(
        ConversationConfig(mode="auto", keys=ApiKeys(gemini="test-key"))
    )

    assert service.mode.value == "live"
    assert service.status.provider == "gemini"
    service.close()


def test_invalid_mode_environment_value_fails_clearly() -> None:
    with pytest.raises(ValueError, match="auto, live, or scripted"):
        config_from_env({"FABULA_CONVERSATION_MODE": "sometimes"})
