"""Deterministic who/how/why accusation checks against engine-only truth."""

from __future__ import annotations

from dataclasses import dataclass

from fabula.schemas import TruthDocument, WorldDocument
from fabula.simulation.clock import Clock


@dataclass(frozen=True)
class AccusationResult:
    correct: bool
    attempts_remaining: int
    terminal: bool
    timed_out: bool = False


@dataclass(frozen=True)
class AttemptRecord:
    who_id: str
    how_id: str
    why_id: str
    who_correct: bool
    how_correct: bool
    why_correct: bool
    minute: int


class AccusationService:
    def __init__(
        self,
        truth: TruthDocument,
        world: WorldDocument,
        *,
        max_attempts: int = 3,
        clock: Clock | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self._truth = truth
        self._npc_ids = {roster_entry.id for roster_entry in world.npcs}
        self._method_ids = {option.id for option in world.accusation_options.methods}
        self._motive_ids = {option.id for option in world.accusation_options.motives}
        self._max_attempts = max_attempts
        self._remaining = max_attempts
        self._terminal = False
        self._attempts: list[AttemptRecord] = []
        self._clock = clock

    @property
    def attempts_used(self) -> int:
        return len(self._attempts)

    def submit(self, who_id: str, how_id: str, why_id: str) -> AccusationResult:
        if self._terminal:
            raise RuntimeError("accusation is already resolved")
        if who_id not in self._npc_ids:
            raise ValueError(f"unknown culprit id {who_id!r}")
        if how_id not in self._method_ids:
            raise ValueError(f"unknown method id {how_id!r}")
        if why_id not in self._motive_ids:
            raise ValueError(f"unknown motive id {why_id!r}")

        solution = self._truth.solution
        who_correct = who_id == solution.correct_culprit_id
        how_correct = how_id == solution.correct_method_id
        why_correct = why_id == solution.correct_motive_id
        self._attempts.append(
            AttemptRecord(
                who_id=who_id,
                how_id=how_id,
                why_id=why_id,
                who_correct=who_correct,
                how_correct=how_correct,
                why_correct=why_correct,
                minute=self._minute(),
            )
        )
        self._remaining -= 1
        correct = who_correct and how_correct and why_correct
        self._terminal = correct or self._remaining == 0
        return AccusationResult(
            correct=correct,
            attempts_remaining=self._remaining,
            terminal=self._terminal,
        )

    def timeout(self) -> AccusationResult:
        if self._terminal:
            raise RuntimeError("accusation is already resolved")
        self._terminal = True
        return AccusationResult(
            correct=False,
            attempts_remaining=self._remaining,
            terminal=True,
            timed_out=True,
        )

    def attempt_log(self) -> tuple[AttemptRecord, ...]:
        """Internal per-component correctness for playtests and evaluation only."""
        return tuple(self._attempts)

    def _minute(self) -> int:
        return self._clock.minute if self._clock is not None else 0
