"""Retry policy and attempt loop for a single generation stage."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from fabula.generation.errors import GenerationCancelled, StageExhaustedError, StageValidationError
from fabula.generation.protocols import StageName

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")


@dataclass(frozen=True)
class RetryOutcome(Generic[T]):
    value: T
    attempts: int


def call_with_retries(
    stage: StageName,
    policy: RetryPolicy,
    attempt: Callable[[int], T],
    *,
    is_cancelled: Callable[[], bool],
    on_attempt: Callable[[StageName, int], None] | None = None,
) -> RetryOutcome[T]:
    """Run one stage, retrying only validation failures.

    Cancellation is checked before every attempt and is never retried.
    """
    last_error: StageValidationError | None = None
    for number in range(1, policy.max_attempts + 1):
        if is_cancelled():
            raise GenerationCancelled(stage)
        if on_attempt is not None:
            on_attempt(stage, number)
        try:
            return RetryOutcome(value=attempt(number), attempts=number)
        except StageValidationError as exc:
            last_error = exc
    raise StageExhaustedError(
        stage=stage,
        attempts=policy.max_attempts,
        last_error=last_error,
    )
