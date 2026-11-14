"""Protocols shared by the staged generation orchestrator and model runners."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel

StageName = Literal[
    "settings->world",
    "world->cast",
    "world+cast->truth+clues",
    "world+cast+truth+clues+npc_id->identity+memory",
]

STAGES: tuple[StageName, ...] = (
    "settings->world",
    "world->cast",
    "world+cast->truth+clues",
    "world+cast+truth+clues+npc_id->identity+memory",
)


class ModelRunner(Protocol):
    """A text-in/text-out model boundary.

    E-02 binds this protocol to llama.cpp with constrained decoding; tests and
    the mock runner return precomputed stage JSON. The runner returns raw text
    and never validates it - the orchestrator owns parsing and validation.
    """

    def generate(
        self,
        stage: StageName,
        stage_input: BaseModel,
        output_model: type[BaseModel],
        seed: int,
    ) -> str: ...


class LocalBackend(Protocol):
    """A low-level local text-generation backend (for example llama.cpp)."""

    def generate(
        self,
        prompt: str,
        *,
        grammar: str | None,
        max_tokens: int,
        temperature: float,
        top_p: float,
        repeat_penalty: float,
        seed: int,
        stop: tuple[str, ...],
    ) -> str: ...

    def close(self) -> None: ...


class CancellationToken(Protocol):
    def is_cancelled(self) -> bool: ...


@dataclass
class CancellationFlag:
    """Simple thread-visible cancellation flag for UI and CLI callers."""

    _cancelled: bool = False

    def cancel(self) -> None:
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled


EventKind = Literal[
    "stage_started",
    "stage_attempt",
    "stage_succeeded",
    "bundle_published",
]


@dataclass(frozen=True)
class ProgressEvent:
    kind: EventKind
    stage: StageName | None = None
    attempt: int = 0
    detail: str = ""


ProgressCallback = Callable[[ProgressEvent], None]
