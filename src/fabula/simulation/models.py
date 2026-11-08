"""Runtime state models for the headless simulation core."""

from __future__ import annotations

from dataclasses import dataclass

from fabula.schemas import WorldDocument


@dataclass(frozen=True)
class NpcMovement:
    npc_id: str
    at_minute: int
    from_location: str
    to_location: str
    path: tuple[str, ...]


@dataclass
class NpcState:
    npc_id: str
    location_id: str
    path: tuple[str, ...] = ()


@dataclass
class WorldState:
    world: WorldDocument
    npcs: dict[str, NpcState]

    def npc(self, npc_id: str) -> NpcState:
        try:
            return self.npcs[npc_id]
        except KeyError as exc:
            raise ValueError(f"unknown npc {npc_id!r}") from exc
