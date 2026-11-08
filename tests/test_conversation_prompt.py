from __future__ import annotations

from pathlib import Path

import pytest

from fabula.conversation import NpcFileError, PromptContext, build_messages, load_npc_files
from fabula.schemas import ChatTurn


def _prompt_text(messages) -> str:
    return "\n".join(message.content for message in messages)


def test_load_npc_files_reads_only_the_selected_npc(bundle_dir: Path, sample_bundle) -> None:
    files = load_npc_files(bundle_dir, "npc_01")

    assert files.identity == sample_bundle.npcs["npc_01"].identity
    assert files.memory == sample_bundle.npcs["npc_01"].memory


def test_load_npc_files_rejects_traversal_and_unknown_ids(bundle_dir: Path) -> None:
    with pytest.raises(NpcFileError):
        load_npc_files(bundle_dir, "../npc_01")
    with pytest.raises(NpcFileError):
        load_npc_files(bundle_dir, "npc_01/../../world")
    with pytest.raises(NpcFileError):
        load_npc_files(bundle_dir, "missing_npc")


def test_load_npc_files_rejects_identity_id_mismatch(sample_bundle, bundle_writer) -> None:
    bundle = sample_bundle.model_copy(deep=True)
    bundle.npcs["npc_01"].identity.id = "npc_99"
    root = bundle_writer(bundle, "identity-mismatch")

    with pytest.raises(NpcFileError):
        load_npc_files(root, "npc_01")


def test_load_npc_files_rejects_symlinked_npc_directory(
    sample_bundle, bundle_dir, tmp_path
) -> None:
    outside = tmp_path / "outside_npc"
    outside.mkdir()
    identity = sample_bundle.npcs["npc_01"].identity.model_copy(deep=True)
    identity.id = "npc_99"
    memory = sample_bundle.npcs["npc_01"].memory.model_copy(deep=True)
    memory.npc_id = "npc_99"
    (outside / "identity.json").write_text(identity.model_dump_json(), encoding="utf-8")
    (outside / "memory.json").write_text(memory.model_dump_json(), encoding="utf-8")

    link = bundle_dir / "npcs" / "npc_99"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is not permitted on this platform")

    with pytest.raises(NpcFileError):
        load_npc_files(bundle_dir, "npc_99")


def test_prompt_contains_only_own_identity_and_memory(sample_bundle) -> None:
    bundle = sample_bundle.model_copy(deep=True)
    bundle.truth.solution.how = "TRUTH_CANARY_9f3d"
    bundle.npcs["npc_02"].memory.facts[0].what = "OTHER_NPC_CANARY_6b1c"
    files = bundle.npcs["npc_01"]
    context = PromptContext.from_npc_files(files, player_input="Hello there.")
    messages = build_messages(context)
    text = _prompt_text(messages)

    assert files.identity.name in text
    assert files.memory.facts[0].what in text
    assert "TRUTH_CANARY_9f3d" not in text
    assert "OTHER_NPC_CANARY_6b1c" not in text
    assert messages[0].role == "system"
    assert messages[-1].role == "user"


def test_prompt_maps_history_roles_and_appends_player_input(sample_bundle) -> None:
    files = sample_bundle.npcs["npc_01"]
    history = (
        ChatTurn(role="player", text="First question."),
        ChatTurn(role="npc", text="First answer."),
    )
    context = PromptContext.from_npc_files(files, chat_history=history, player_input="Second?")
    messages = build_messages(context)

    assert [message.role for message in messages] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert messages[1].content == "First question."
    assert messages[2].content == "First answer."
    assert messages[3].content == "Second?"


def test_prompt_is_deterministic(sample_bundle) -> None:
    context = PromptContext.from_npc_files(sample_bundle.npcs["npc_01"], player_input="Hello.")
    assert build_messages(context) == build_messages(context)


def test_gated_reveal_excludes_facts_until_required_clue(sample_bundle, bundle_writer) -> None:
    bundle = sample_bundle.model_copy(deep=True)
    fact = bundle.npcs["npc_01"].memory.facts[0]
    fact.reveal_requires = ["clue_01"]
    fact.what = "GATED_FACT_CANARY_42"
    root = bundle_writer(bundle, "gated-prompt")
    files = load_npc_files(root, "npc_01")
    context = PromptContext.from_npc_files(files, player_input="Tell me what you know.")

    baseline = _prompt_text(build_messages(context))
    gated_without_clue = _prompt_text(
        build_messages(context, gated_reveal=True, discovered_clue_ids=frozenset())
    )
    gated_with_clue = _prompt_text(
        build_messages(
            context,
            gated_reveal=True,
            discovered_clue_ids=frozenset({"clue_01"}),
        )
    )

    assert "GATED_FACT_CANARY_42" in baseline
    assert "GATED_FACT_CANARY_42" not in gated_without_clue
    assert "GATED_FACT_CANARY_42" in gated_with_clue


def test_prompt_context_rejects_mismatched_identity_and_memory(sample_bundle) -> None:
    files = sample_bundle.npcs["npc_01"]
    with pytest.raises(ValueError):
        PromptContext(
            identity=files.identity,
            memory=sample_bundle.npcs["npc_02"].memory,
            player_input="Hello.",
        )
    with pytest.raises(ValueError):
        PromptContext.from_npc_files(files, player_input="   ")
