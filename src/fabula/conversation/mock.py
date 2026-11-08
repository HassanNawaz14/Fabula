"""Deterministic offline provider for tests and scripted demos."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from fabula.conversation.provider import ProviderRequest, ProviderResponse

_DEFAULT_REPLY = '{"reply": "I see.", "mood": "neutral"}'
_CHUNK_SIZE = 16


class MockProvider:
    def __init__(
        self,
        responses: Sequence[ProviderResponse | Exception] | None = None,
        *,
        name: str = "mock",
        model: str = "mock-1",
        default_reply: str = _DEFAULT_REPLY,
    ) -> None:
        self.name = name
        self.model = model
        self.requests: list[ProviderRequest] = []
        self.calls = 0
        self._responses = list(responses or [])
        self._default_reply = default_reply

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        self.calls += 1
        if self._responses:
            item = self._responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return ProviderResponse(
            text=self._default_reply,
            input_tokens=10,
            output_tokens=5,
            model=self.model,
        )

    def stream(self, request: ProviderRequest) -> Iterator[str]:
        response = self.complete(request)
        for start in range(0, len(response.text), _CHUNK_SIZE):
            yield response.text[start : start + _CHUNK_SIZE]
