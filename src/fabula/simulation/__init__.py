"""Headless simulation core: bundle loading, time, movement, clues and accusation."""

from fabula.simulation.accusation import AccusationResult, AccusationService, AttemptRecord
from fabula.simulation.clock import Clock, FakeClock
from fabula.simulation.clues import ClueIndex
from fabula.simulation.journal import Journal, JournalEntry
from fabula.simulation.loader import BundleLoadError, LoadedBundle, load_bundle
from fabula.simulation.models import NpcMovement, NpcState, WorldState
from fabula.simulation.pathfinding import find_path, location_graph
from fabula.simulation.perception import can_perceive, visible_npcs
from fabula.simulation.schedules import location_at, next_waypoint
from fabula.simulation.session import Session
from fabula.simulation.world import advance_to, build_world_state

__all__ = [
    "AccusationResult",
    "AccusationService",
    "AttemptRecord",
    "BundleLoadError",
    "Clock",
    "ClueIndex",
    "FakeClock",
    "Journal",
    "JournalEntry",
    "LoadedBundle",
    "NpcMovement",
    "NpcState",
    "Session",
    "WorldState",
    "advance_to",
    "build_world_state",
    "can_perceive",
    "find_path",
    "load_bundle",
    "location_at",
    "location_graph",
    "next_waypoint",
    "visible_npcs",
]
