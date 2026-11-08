"""World-state construction and scheduled movement."""

from __future__ import annotations

from fabula.schemas import WorldDocument
from fabula.simulation.models import NpcMovement, NpcState, WorldState
from fabula.simulation.pathfinding import find_path
from fabula.simulation.schedules import location_at


def build_world_state(world: WorldDocument) -> WorldState:
    npcs = {
        roster_entry.id: NpcState(
            npc_id=roster_entry.id,
            location_id=roster_entry.start_location,
        )
        for roster_entry in world.npcs
    }
    return WorldState(world=world, npcs=npcs)


def advance_to(state: WorldState, minute: int) -> tuple[NpcMovement, ...]:
    movements: list[NpcMovement] = []
    for roster_entry in state.world.npcs:
        target = location_at(roster_entry, minute)
        current = state.npcs[roster_entry.id].location_id
        if target == current:
            continue
        path = tuple(find_path(state.world, current, target))
        state.npcs[roster_entry.id].location_id = target
        state.npcs[roster_entry.id].path = path
        movements.append(
            NpcMovement(
                npc_id=roster_entry.id,
                at_minute=minute,
                from_location=current,
                to_location=target,
                path=path,
            )
        )
    return tuple(movements)
