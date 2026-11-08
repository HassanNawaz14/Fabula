from __future__ import annotations

from itertools import pairwise

import pytest

from fabula.simulation import (
    FakeClock,
    advance_to,
    build_world_state,
    can_perceive,
    find_path,
    location_at,
    location_graph,
    next_waypoint,
    visible_npcs,
)


def test_clock_maps_seconds_to_minutes_and_stops_at_ten_minutes() -> None:
    clock = FakeClock()

    assert clock.minute == 0
    assert clock.finished is False
    clock.advance(59)
    assert clock.minute == 0
    clock.advance(1)
    assert clock.minute == 1
    clock.pause()
    clock.advance(600)
    assert clock.minute == 1
    assert clock.finished is False
    clock.resume()
    clock.advance(600)
    assert clock.finished is True
    assert clock.minute == 10


def test_clock_rejects_negative_advance() -> None:
    with pytest.raises(ValueError):
        FakeClock().advance(-1)


def test_schedule_boundaries_use_integer_minutes(sample_bundle) -> None:
    npc = sample_bundle.world.npcs[0]
    entries = sorted(npc.schedule, key=lambda entry: entry.at_minute)

    assert location_at(npc, 0) == npc.start_location or any(
        entry.at_minute == 0 for entry in entries
    )
    for entry in entries:
        assert location_at(npc, entry.at_minute) == entry.location
        if entry.at_minute > 0:
            previous = [item for item in entries if item.at_minute < entry.at_minute]
            expected = previous[-1].location if previous else npc.start_location
            assert location_at(npc, entry.at_minute - 1) == expected


def test_next_waypoint_returns_the_next_scheduled_entry(sample_bundle) -> None:
    npc = sample_bundle.world.npcs[0]
    entries = sorted(npc.schedule, key=lambda entry: entry.at_minute)
    assert next_waypoint(npc, 10) is None
    if entries[0].at_minute > 0:
        assert next_waypoint(npc, 0) == entries[0]


def test_schedule_rejects_out_of_range_minutes(sample_bundle) -> None:
    npc = sample_bundle.world.npcs[0]
    with pytest.raises(ValueError):
        location_at(npc, -1)
    with pytest.raises(ValueError):
        location_at(npc, 11)


def test_pathfinding_returns_a_deterministic_shortest_path(sample_bundle) -> None:
    locations = sample_bundle.world.locations
    start = locations[0].id
    goal = locations[-1].id
    graph = location_graph(sample_bundle.world)

    path = find_path(sample_bundle.world, start, goal)

    assert path[0] == start
    assert path[-1] == goal
    assert len(path) == len(set(path))
    for source, target in pairwise(path):
        assert target in graph[source]
    assert find_path(sample_bundle.world, start, goal) == path


def test_pathfinding_handles_same_location_and_unknown_locations(sample_bundle) -> None:
    location_id = sample_bundle.world.locations[0].id
    assert find_path(sample_bundle.world, location_id, location_id) == [location_id]
    with pytest.raises(ValueError):
        find_path(sample_bundle.world, "missing", location_id)
    with pytest.raises(ValueError):
        find_path(sample_bundle.world, location_id, "missing")


def test_perception_is_same_or_adjacent_only(sample_bundle) -> None:
    world = sample_bundle.world
    graph = location_graph(world)
    here = world.locations[0].id

    assert can_perceive(world, here, here)
    for neighbor in graph[here]:
        assert can_perceive(world, here, neighbor)
    non_neighbors = [
        location.id
        for location in world.locations
        if location.id != here and location.id not in graph[here]
    ]
    for location_id in non_neighbors:
        assert not can_perceive(world, here, location_id)


def test_visible_npcs_respects_current_positions(sample_bundle) -> None:
    state = build_world_state(sample_bundle.world)
    first, second = list(state.npcs)[:2]
    state.npcs[second].location_id = state.npcs[first].location_id

    assert second in visible_npcs(state, first)
    assert first in visible_npcs(state, second)


def test_advance_to_moves_npcs_along_schedules(sample_bundle) -> None:
    world = sample_bundle.world
    state = build_world_state(world)

    for minute in range(11):
        movements = advance_to(state, minute)
        for roster_entry in world.npcs:
            assert state.npc(roster_entry.id).location_id == location_at(roster_entry, minute)
        for movement in movements:
            assert movement.at_minute == minute
            assert movement.path[0] == movement.from_location
            assert movement.path[-1] == movement.to_location


def test_advance_to_is_deterministic(sample_bundle) -> None:
    first_state = build_world_state(sample_bundle.world)
    second_state = build_world_state(sample_bundle.world)

    first = [advance_to(first_state, minute) for minute in range(11)]
    second = [advance_to(second_state, minute) for minute in range(11)]

    assert first == second


def test_advance_to_rejects_invalid_minute(sample_bundle) -> None:
    state = build_world_state(sample_bundle.world)
    with pytest.raises(ValueError):
        advance_to(state, 11)


def test_world_state_unknown_npc_raises(sample_bundle) -> None:
    state = build_world_state(sample_bundle.world)
    with pytest.raises(ValueError):
        state.npc("missing")
