"""Provider-neutral request and response types for live NPC conversation."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal, Protocol

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str


@dataclass(frozen=True)
class ProviderRequest:
    messages: tuple[Message, ...]
    model: str
    max_output_tokens: int = 300
    temperature: float = 0.7


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class ChatProvider(Protocol):
    name: str
    model: str

    def complete(self, request: ProviderRequest) -> ProviderResponse: ...

    def stream(self, request: ProviderRequest) -> Iterator[str]: ...
