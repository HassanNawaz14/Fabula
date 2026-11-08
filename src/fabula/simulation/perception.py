"""Perception rules: an NPC sees only its own and adjacent locations."""

from __future__ import annotations

from fabula.schemas import WorldDocument
from fabula.simulation.models import WorldState
from fabula.simulation.pathfinding import location_graph


def can_perceive(world: WorldDocument, observer_location: str, target_location: str) -> bool:
    graph = location_graph(world)
    if observer_location not in graph:
        raise ValueError(f"unknown observer location {observer_location!r}")
    if target_location not in graph:
        raise ValueError(f"unknown target location {target_location!r}")
    return target_location == observer_location or target_location in graph[observer_location]


def visible_npcs(state: WorldState, npc_id: str) -> tuple[str, ...]:
    observer = state.npc(npc_id)
    return tuple(
        sorted(
            other.npc_id
            for other in state.npcs.values()
            if other.npc_id != npc_id
            and can_perceive(state.world, observer.location_id, other.location_id)
        )
    )
