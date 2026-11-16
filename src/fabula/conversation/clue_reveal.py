"""Clue eligibility shared by the scripted and live conversation paths."""

from __future__ import annotations

from collections.abc import Sequence

from fabula.schemas import Clue, DiscoveryMethod


def eligible_reveal_clues(
    npc_id: str,
    clues: Sequence[Clue],
    discovered_clue_ids: frozenset[str],
) -> tuple[Clue, ...]:
    """Clues this NPC may reveal now: theirs, still hidden, prerequisites met."""
    return tuple(
        clue
        for clue in clues
        if clue.discovery is DiscoveryMethod.NPC_REVEAL
        and clue.revealed_by_npc == npc_id
        and clue.id not in discovered_clue_ids
        and set(clue.requires) <= discovered_clue_ids
    )
