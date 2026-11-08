"""Schedule lookups on the frozen integer-minute contract."""

from __future__ import annotations

from fabula.schemas import NpcRosterEntry, ScheduleEntry

MIN_MINUTE = 0
MAX_MINUTE = 10


def check_minute(minute: int) -> None:
    if not MIN_MINUTE <= minute <= MAX_MINUTE:
        raise ValueError(f"minute must be between {MIN_MINUTE} and {MAX_MINUTE}, got {minute}")


def location_at(npc: NpcRosterEntry, minute: int) -> str:
    check_minute(minute)
    current = npc.start_location
    for entry in sorted(npc.schedule, key=lambda item: item.at_minute):
        if entry.at_minute > minute:
            break
        current = entry.location
    return current


def next_waypoint(npc: NpcRosterEntry, minute: int) -> ScheduleEntry | None:
    check_minute(minute)
    for entry in sorted(npc.schedule, key=lambda item: item.at_minute):
        if entry.at_minute > minute:
            return entry
    return None
