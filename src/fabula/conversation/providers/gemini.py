"""Google Gemini REST adapter."""

from __future__ import annotations

import json
from collections.abc import Iterator
from urllib.parse import quote

import httpx

from fabula.conversation.errors import ProviderError, ProviderTimeout
from fabula.conversation.provider import ProviderRequest, ProviderResponse

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout_seconds: float = 20.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key must not be empty")
        self.model = model
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._client = client if client is not None else httpx.Client(timeout=timeout_seconds)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _url(self, method: str) -> str:
        suffix = ":generateContent" if method == "generateContent" else f":{method}"
        return f"{_BASE_URL}/{quote(self.model, safe='')}{suffix}"

    def _payload(self, request: ProviderRequest) -> dict[str, object]:
        system_parts: list[str] = []
        contents: list[dict[str, object]] = []
        for message in request.messages:
            if message.role == "system":
                system_parts.append(message.content)
                continue
            contents.append(
                {
                    "role": "model" if message.role == "assistant" else "user",
                    "parts": [{"text": message.content}],
                }
            )
        payload: dict[str, object] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_output_tokens,
            },
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}
        return payload

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self._api_key, "content-type": "application/json"}

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        try:
            response = self._client.post(
                self._url("generateContent"),
                headers=self._headers(),
                json=self._payload(request),
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderTimeout("Gemini request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Gemini request failed: {exc}") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError("Gemini returned invalid JSON") from exc
        return ProviderResponse(
            text=_extract_text(data),
            input_tokens=_usage(data, "promptTokenCount"),
            output_tokens=_usage(data, "candidatesTokenCount"),
            model=self.model,
        )

    def stream(self, request: ProviderRequest) -> Iterator[str]:
        url = self._url("streamGenerateContent") + "?alt=sse"
        try:
            with self._client.stream(
                "POST",
                url,
                headers=self._headers(),
                json=self._payload(request),
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
                        yield _extract_text(json.loads(chunk))
                    except (ValueError, ProviderError):
                        continue
        except httpx.TimeoutException as exc:
            raise ProviderTimeout("Gemini stream timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Gemini stream failed: {exc}") from exc


def _extract_text(data: object) -> str:
    if not isinstance(data, dict):
        raise ProviderError("Gemini response has an unexpected shape")
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ProviderError("Gemini response contains no candidates")
    first = candidates[0]
    if not isinstance(first, dict):
        raise ProviderError("Gemini response has an unexpected candidate")
    content = first.get("content")
    if not isinstance(content, dict):
        raise ProviderError("Gemini response contains no content")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise ProviderError("Gemini response contains no parts")
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text:
        raise ProviderError("Gemini response contains no text")
    return text


def _usage(data: object, key: str) -> int:
    if not isinstance(data, dict):
        return 0
    usage = data.get("usageMetadata")
    if not isinstance(usage, dict):
        return 0
    value = usage.get(key, 0)
    return value if isinstance(value, int) else 0
