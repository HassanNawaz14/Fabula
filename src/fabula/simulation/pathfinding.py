"""Deterministic shortest-path search over the location graph."""

from __future__ import annotations

import heapq
from itertools import count

from fabula.schemas import WorldDocument


def location_graph(world: WorldDocument) -> dict[str, tuple[str, ...]]:
    adjacency: dict[str, set[str]] = {location.id: set() for location in world.locations}
    for location in world.locations:
        for neighbor in location.connections:
            if neighbor not in adjacency:
                raise ValueError(f"location {location.id} connects to unknown location {neighbor}")
            adjacency[location.id].add(neighbor)
            adjacency[neighbor].add(location.id)
    return {location_id: tuple(sorted(neighbors)) for location_id, neighbors in adjacency.items()}


def find_path(world: WorldDocument, start: str, goal: str) -> list[str]:
    adjacency = location_graph(world)
    if start not in adjacency:
        raise ValueError(f"unknown start location {start!r}")
    if goal not in adjacency:
        raise ValueError(f"unknown goal location {goal!r}")
    if start == goal:
        return [start]

    insertion_order = count()
    frontier: list[tuple[int, int, str]] = [(0, next(insertion_order), start)]
    costs: dict[str, int] = {start: 0}
    came_from: dict[str, str] = {}
    settled: set[str] = set()

    while frontier:
        cost, _, current = heapq.heappop(frontier)
        if current in settled:
            continue
        settled.add(current)
        if current == goal:
            break
        for neighbor in adjacency[current]:
            candidate_cost = cost + 1
            if neighbor not in costs or candidate_cost < costs[neighbor]:
                costs[neighbor] = candidate_cost
                came_from[neighbor] = current
                heapq.heappush(frontier, (candidate_cost, next(insertion_order), neighbor))

    if goal not in costs:
        raise ValueError(f"no path from {start!r} to {goal!r}")

    path = [goal]
    while path[-1] != start:
        path.append(came_from[path[-1]])
    path.reverse()
    return path
