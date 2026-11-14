"""Player session: clue discovery, journal, and per-NPC player statements."""

from __future__ import annotations

from fabula.schemas import Clue, DiscoveryMethod
from fabula.simulation.clock import Clock, FakeClock
from fabula.simulation.clues import ClueIndex
from fabula.simulation.journal import Journal, JournalEntry
from fabula.simulation.loader import LoadedBundle
from fabula.simulation.pathfinding import location_graph
from fabula.simulation.schedules import location_at


class Session:
    def __init__(self, loaded: LoadedBundle, clock: Clock | None = None) -> None:
        self.loaded = loaded
        self.clock = clock if clock is not None else FakeClock()
        self._clues = ClueIndex(loaded.clues)
        self._journal = Journal()
        self._statements: dict[str, list[str]] = {
            roster_entry.id: [] for roster_entry in loaded.world.npcs
        }
        self.player_location = loaded.world.locations[0].id
        self.npc_cycle_index = 0

    def move_player(self, location_id: str) -> None:
        graph = location_graph(self.loaded.world)
        if location_id not in graph:
            raise ValueError(f"unknown location {location_id!r}")
        if location_id != self.player_location and location_id not in graph[self.player_location]:
            raise ValueError(
                f"location {location_id!r} is not adjacent to "
                f"player location {self.player_location!r}"
            )
        self.player_location = location_id
        self.npc_cycle_index = 0

    def npcs_at(self, location_id: str) -> tuple[str, ...]:
        present = []
        for roster_entry in self.loaded.world.npcs:
            loc = location_at(roster_entry, self.clock.minute)
            if loc == location_id:
                present.append(roster_entry.id)
        return tuple(present)

    @property
    def discovered_ids(self) -> frozenset[str]:
        return frozenset(entry.clue_id for entry in self._journal.entries())

    @property
    def journal(self) -> tuple[JournalEntry, ...]:
        return self._journal.entries()

    def examine(self, location_id: str, clue_id: str) -> JournalEntry | None:
        clue = self._clues.get(clue_id)
        if clue.discovery is not DiscoveryMethod.EXAMINE:
            raise ValueError(f"clue {clue_id!r} cannot be discovered by examining")
        if clue.location_id != location_id:
            raise ValueError(f"clue {clue_id!r} is at {clue.location_id!r}, not {location_id!r}")
        return self._discover(clue, source=f"examine:{location_id}")

    def npc_reveal(self, npc_id: str, clue_id: str) -> JournalEntry | None:
        if npc_id not in self._statements:
            raise ValueError(f"unknown npc {npc_id!r}")
        clue = self._clues.get(clue_id)
        if clue.discovery is not DiscoveryMethod.NPC_REVEAL:
            raise ValueError(f"clue {clue_id!r} cannot be discovered by an NPC reveal")
        if clue.revealed_by_npc != npc_id:
            raise ValueError(f"clue {clue_id!r} is not revealed by npc {npc_id!r}")
        return self._discover(clue, source=f"npc_reveal:{npc_id}")

    def _discover(self, clue: Clue, source: str) -> JournalEntry | None:
        if self._journal.has(clue.id):
            return None
        missing = sorted(set(clue.requires) - self.discovered_ids)
        if missing:
            raise ValueError(f"clue {clue.id!r} requires undiscovered clues {missing}")
        entry = JournalEntry(
            clue_id=clue.id,
            description=clue.description,
            source=source,
            minute=self.clock.minute,
        )
        self._journal.record(entry)
        return entry

    def record_player_statement(self, npc_id: str, text: str) -> None:
        if npc_id not in self._statements:
            raise ValueError(f"unknown npc {npc_id!r}")
        if not text.strip():
            raise ValueError("player statement must not be empty")
        self._statements[npc_id].append(text)

    def statements_for(self, npc_id: str) -> tuple[str, ...]:
        if npc_id not in self._statements:
            raise ValueError(f"unknown npc {npc_id!r}")
        return tuple(self._statements[npc_id])
