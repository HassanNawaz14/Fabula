"""Lookup and gating helpers for clues."""

from __future__ import annotations

from fabula.schemas import Clue, CluesDocument


class ClueIndex:
    def __init__(self, document: CluesDocument) -> None:
        self._clues = {clue.id: clue for clue in document.clues}

    def get(self, clue_id: str) -> Clue:
        try:
            return self._clues[clue_id]
        except KeyError as exc:
            raise ValueError(f"unknown clue {clue_id!r}") from exc

    def __len__(self) -> int:
        return len(self._clues)
