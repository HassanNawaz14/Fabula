from __future__ import annotations

import pytest

from fabula.conversation import (
    ApiKeys,
    ConversationConfig,
    ConversationMode,
    create_conversation_service,
)
from fabula.schemas import DiscoveryMethod
from fabula.simulation import AccusationService, Session, load_bundle
from fabula.training_data import generate_skeleton


def _scripted_service(seed: int = 0):
    return create_conversation_service(
        ConversationConfig(mode=ConversationMode.SCRIPTED, scripted_seed=seed),
        keys=ApiKeys(),
    )


@pytest.mark.parametrize("mystery_type", ["theft", "disappearance", "murder"])
def test_scripted_clues_remain_collectible_and_playable(mystery_type, bundle_writer) -> None:
    bundle = generate_skeleton(mystery_type, 3, tone="cozy", difficulty="easy")
    loaded = load_bundle(bundle_writer(bundle, f"scripted-{mystery_type}"))
    session = Session(loaded)
    service = _scripted_service()

    for roster_entry in loaded.world.npcs:
        for _ in range(3):
            reply = service.reply(
                loaded.npcs[roster_entry.id],
                "What did you see? Can you help me?",
                discovered_clue_ids=session.discovered_ids,
                clues=loaded.clues.clues,
            )
            new_ids = [
                clue_id
                for clue_id in reply.revealed_clue_ids
                if clue_id not in session.discovered_ids
            ]
            for clue_id in new_ids:
                session.npc_reveal(roster_entry.id, clue_id)
            if not new_ids:
                break

    npc_reveal_ids = {
        clue.id for clue in loaded.clues.clues if clue.discovery is DiscoveryMethod.NPC_REVEAL
    }
    assert npc_reveal_ids <= session.discovered_ids

    solution = loaded.accusation_truth().solution
    result = AccusationService(loaded.accusation_truth(), loaded.world).submit(
        solution.correct_culprit_id,
        solution.correct_method_id,
        solution.correct_motive_id,
    )
    assert result.correct is True


def test_scripted_reply_reveals_public_clue_text(loaded) -> None:
    npc_id = next(
        clue.revealed_by_npc
        for clue in loaded.clues.clues
        if clue.discovery is DiscoveryMethod.NPC_REVEAL
    )
    clue = next(
        clue
        for clue in loaded.clues.clues
        if clue.revealed_by_npc == npc_id and clue.discovery is DiscoveryMethod.NPC_REVEAL
    )
    service = _scripted_service()

    reply = service.reply(
        loaded.npcs[npc_id],
        "What did you see?",
        clues=loaded.clues.clues,
    )

    assert reply.revealed_clue_ids == (clue.id,)
    assert clue.description in reply.text
    assert reply.scripted is True
    assert reply.provider is None


def test_scripted_replies_vary_and_keep_persona(loaded) -> None:
    service = _scripted_service()
    first = loaded.npcs["npc_01"]
    second = loaded.npcs["npc_02"]

    greetings = [service.reply(first, "Hello.") for _ in range(3)]
    other = service.reply(second, "Hello.")

    assert len({reply.text for reply in greetings}) > 1
    assert first.identity.name in greetings[0].text
    assert second.identity.name in other.text
    assert other.text not in {reply.text for reply in greetings}


def test_scripted_identity_and_backstory_stay_in_persona(loaded) -> None:
    service = _scripted_service()
    files = loaded.npcs["npc_01"]

    identity = service.reply(files, "Who are you?")
    story = service.reply(files, "Tell me about yourself.")

    assert files.identity.name in identity.text
    assert files.identity.backstory.split(".")[0] in story.text


def test_scripted_mode_never_leaks_memory_or_truth(sample_bundle) -> None:
    files = sample_bundle.npcs["npc_02"].model_copy(deep=True)
    hidden_fact = next(fact for fact in files.memory.facts if fact.secret)
    hidden_fact.what = "HIDDEN_SCRIPTED_CANARY_7c2a"
    service = _scripted_service()

    replies = [
        service.reply(files, "Hello."),
        service.reply(files, "Who are you?"),
        service.reply(files, "Something strange happened."),
        service.reply(files, "Goodbye."),
    ]
    text = "\n".join(reply.text for reply in replies)

    assert "HIDDEN_SCRIPTED_CANARY_7c2a" not in text
    assert sample_bundle.truth.solution.how not in text
    assert sample_bundle.npcs["npc_03"].memory.facts[0].what not in text


def test_scripted_clue_requires_are_respected(sample_bundle) -> None:
    files = sample_bundle.npcs["npc_05"]
    clue = next(
        clue
        for clue in sample_bundle.clues.clues
        if clue.revealed_by_npc == "npc_05" and clue.discovery is DiscoveryMethod.NPC_REVEAL
    ).model_copy(deep=True)
    clue.requires = ["clue_missing"]
    service = _scripted_service()

    without = service.reply(files, "What did you see?", clues=(clue,))
    with_gate = service.reply(
        files,
        "What did you see?",
        clues=(clue,),
        discovered_clue_ids=frozenset({"clue_missing"}),
    )

    assert without.revealed_clue_ids == ()
    assert with_gate.revealed_clue_ids == (clue.id,)
