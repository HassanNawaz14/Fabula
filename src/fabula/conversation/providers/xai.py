"""xAI Grok-class OpenAI-compatible REST adapter."""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx

from fabula.conversation.errors import ProviderError, ProviderTimeout
from fabula.conversation.provider import ProviderRequest, ProviderResponse

_URL = "https://api.x.ai/v1/chat/completions"


class XaiProvider:
    name = "xai"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout_seconds: float = 20.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("xAI API key must not be empty")
        self.model = model
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._client = client if client is not None else httpx.Client(timeout=timeout_seconds)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
        }

    def _payload(self, request: ProviderRequest, *, stream: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }
        if stream:
            payload["stream"] = True
        return payload

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        try:
            response = self._client.post(
                _URL,
                headers=self._headers(),
                json=self._payload(request),
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderTimeout("xAI request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"xAI request failed: {exc}") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError("xAI returned invalid JSON") from exc
        text = _extract_text(data)
        usage = data.get("usage") if isinstance(data, dict) else None
        return ProviderResponse(
            text=text,
            input_tokens=_usage(usage, "prompt_tokens"),
            output_tokens=_usage(usage, "completion_tokens"),
            model=self.model,
        )

    def stream(self, request: ProviderRequest) -> Iterator[str]:
        try:
            with self._client.stream(
                "POST",
                _URL,
                headers=self._headers(),
                json=self._payload(request, stream=True),
                timeout=self._timeout,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk = line.removeprefix("data:").strip()
                    if not chunk or chunk == "[DONE]":
                        continue
                    try:
                        data = json.loads(chunk)
                    except ValueError:
                        continue
                    text = _extract_delta(data)
                    if text:
                        yield text
        except httpx.TimeoutException as exc:
            raise ProviderTimeout("xAI stream timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"xAI stream failed: {exc}") from exc


def _extract_text(data: object) -> str:
    if not isinstance(data, dict):
        raise ProviderError("xAI response has an unexpected shape")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderError("xAI response contains no choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ProviderError("xAI response has an unexpected choice")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ProviderError("xAI response contains no message")
    content = message.get("content")
    if not isinstance(content, str) or not content:
        raise ProviderError("xAI response contains no text")
    return content


def _extract_delta(data: object) -> str:
    if not isinstance(data, dict):
        return ""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return ""
    delta = choices[0].get("delta")
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    return content if isinstance(content, str) else ""


def _usage(usage: object, key: str) -> int:
    if not isinstance(usage, dict):
        return 0
    value = usage.get(key, 0)
    return value if isinstance(value, int) else 0
