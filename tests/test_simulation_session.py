from __future__ import annotations

from pathlib import Path

import pytest

from fabula.schemas import DiscoveryMethod
from fabula.simulation import Session, load_bundle


def _examine_clue(loaded):
    return next(clue for clue in loaded.clues.clues if clue.discovery is DiscoveryMethod.EXAMINE)


def _reveal_clue(loaded):
    return next(
        clue
        for clue in loaded.clues.clues
        if clue.discovery is DiscoveryMethod.NPC_REVEAL and clue.revealed_by_npc is not None
    )


def test_examine_discovers_a_clue_once(loaded) -> None:
    clue = _examine_clue(loaded)
    session = Session(loaded)
    session.clock.advance(120)

    entry = session.examine(clue.location_id, clue.id)

    assert entry is not None
    assert entry.minute == 2
    assert entry.source == f"examine:{clue.location_id}"
    assert session.discovered_ids == {clue.id}
    assert len(session.journal) == 1
    assert session.examine(clue.location_id, clue.id) is None
    assert len(session.journal) == 1


def test_examine_rejects_wrong_location(loaded) -> None:
    clue = _examine_clue(loaded)
    other_location = next(
        location.id for location in loaded.world.locations if location.id != clue.location_id
    )
    with pytest.raises(ValueError):
        Session(loaded).examine(other_location, clue.id)


def test_examine_rejects_an_npc_reveal_clue(loaded) -> None:
    clue = _reveal_clue(loaded)
    with pytest.raises(ValueError):
        Session(loaded).examine(clue.location_id, clue.id)


def test_npc_reveal_requires_the_right_npc(loaded) -> None:
    clue = _reveal_clue(loaded)
    other_npc = next(
        roster_entry.id
        for roster_entry in loaded.world.npcs
        if roster_entry.id != clue.revealed_by_npc
    )
    with pytest.raises(ValueError):
        Session(loaded).npc_reveal(other_npc, clue.id)

    entry = Session(loaded).npc_reveal(clue.revealed_by_npc, clue.id)
    assert entry is not None
    assert entry.source == f"npc_reveal:{clue.revealed_by_npc}"


def test_clue_requires_gate_blocks_until_prerequisites_are_found(
    sample_bundle, bundle_writer
) -> None:
    bundle = sample_bundle.model_copy(deep=True)
    examine_clues = [
        clue for clue in bundle.clues.clues if clue.discovery is DiscoveryMethod.EXAMINE
    ]
    first, second = examine_clues[0], examine_clues[1]
    second.requires = [first.id]
    loaded = load_bundle(bundle_writer(bundle, "gated"))
    session = Session(loaded)

    with pytest.raises(ValueError):
        session.examine(second.location_id, second.id)

    assert session.examine(first.location_id, first.id) is not None
    assert session.examine(second.location_id, second.id) is not None


def test_unknown_clue_raises(loaded) -> None:
    with pytest.raises(ValueError):
        Session(loaded).examine(loaded.world.locations[0].id, "missing")


def test_player_statements_are_scoped_to_one_npc(loaded) -> None:
    session = Session(loaded)
    first, second = [roster_entry.id for roster_entry in loaded.world.npcs[:2]]

    session.record_player_statement(first, "I saw you near the market.")

    assert session.statements_for(first) == ("I saw you near the market.",)
    assert session.statements_for(second) == ()
    with pytest.raises(ValueError):
        session.record_player_statement(first, "   ")
    with pytest.raises(ValueError):
        session.record_player_statement("missing", "hello")


def test_session_does_not_mutate_bundle_files(loaded, bundle_dir: Path, digest) -> None:
    before = digest(bundle_dir)
    clue = _examine_clue(loaded)
    session = Session(loaded)

    session.examine(clue.location_id, clue.id)
    session.record_player_statement(loaded.world.npcs[0].id, "hello")

    assert digest(bundle_dir) == before
