"""Idempotent discovery journal."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JournalEntry:
    clue_id: str
    description: str
    source: str
    minute: int


class Journal:
    def __init__(self) -> None:
        self._entries: dict[str, JournalEntry] = {}

    def has(self, clue_id: str) -> bool:
        return clue_id in self._entries

    def record(self, entry: JournalEntry) -> bool:
        if entry.clue_id in self._entries:
            return False
        self._entries[entry.clue_id] = entry
        return True

    def entries(self) -> tuple[JournalEntry, ...]:
        return tuple(self._entries.values())
