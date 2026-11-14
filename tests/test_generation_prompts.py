from __future__ import annotations

import json
from pathlib import Path

import pytest

from fabula.generation import NPC_STAGE
from fabula.generation.mock_runner import cast_from_bundle
from fabula.generation.prompts import (
    CHATML_TEMPLATE,
    STAGE_SYSTEM_PROMPTS,
    STOP_TOKENS,
    build_stage_payload,
    build_stage_prompt,
)
from fabula.schemas import (
    CastStageInput,
    GenerationSettings,
    NpcStageInput,
    TruthStageInput,
)
from fabula.training_data import generate_skeleton

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "generation_prompts.json"
SETTINGS = GenerationSettings(mystery_type="theft", tone="cozy", difficulty="easy")


@pytest.fixture(scope="module")
def skeleton_bundle():
    return generate_skeleton("theft", 3, tone="cozy", difficulty="easy")


@pytest.fixture(scope="module")
def stage_inputs(skeleton_bundle):
    bundle = skeleton_bundle
    cast = cast_from_bundle(bundle)
    culprit_id = bundle.truth.solution.correct_culprit_id
    non_culprit_id = next(npc.id for npc in bundle.world.npcs if npc.id != culprit_id)
    return {
        "settings": SETTINGS,
        "world": CastStageInput(world=bundle.world),
        "truth": TruthStageInput(world=bundle.world, cast=cast),
        "culprit": NpcStageInput(
            world=bundle.world,
            cast=cast,
            truth=bundle.truth,
            clues=bundle.clues,
            npc_id=culprit_id,
        ),
        "non_culprit": NpcStageInput(
            world=bundle.world,
            cast=cast,
            truth=bundle.truth,
            clues=bundle.clues,
            npc_id=non_culprit_id,
        ),
        "cast": cast,
    }


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        (
            "settings->world",
            "You are the Fabula game generation engine. Given the scenario settings, "
            "generate the world document in valid JSON.",
        ),
        (
            "world->cast",
            "You are the Fabula game generation engine. Given the world document, "
            "generate the cast roster in valid JSON.",
        ),
        (
            "world+cast->truth+clues",
            "You are the Fabula game generation engine. Given the world and cast, "
            "generate the truth and clues documents in valid JSON.",
        ),
        (
            NPC_STAGE,
            "You are the Fabula game generation engine. Given the context and NPC ID, "
            "generate that NPC's identity and memory in valid JSON.",
        ),
    ],
)
def test_system_prompt_matches_training(stage, expected: str) -> None:
    assert STAGE_SYSTEM_PROMPTS[stage] == expected


def test_chatml_template_matches_training() -> None:
    assert CHATML_TEMPLATE == (
        "<|im_start|>system\n{system}<|im_end|>\n"
        "<|im_start|>user\n{user}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    assert STOP_TOKENS == ("<|im_end|>", "<|endoftext|>")


def test_payload_order_settings(stage_inputs) -> None:
    payload = build_stage_payload("settings->world", stage_inputs["settings"])
    assert list(payload) == ["mystery_type", "tone", "difficulty"]
    assert payload == {"mystery_type": "theft", "tone": "cozy", "difficulty": "easy"}


def test_payload_order_world(stage_inputs) -> None:
    payload = build_stage_payload("world->cast", stage_inputs["world"])
    assert list(payload) == ["world"]


def test_payload_order_truth(stage_inputs) -> None:
    payload = build_stage_payload("world+cast->truth+clues", stage_inputs["truth"])
    assert list(payload) == ["world", "cast"]


def test_npc_payload_omits_truth_for_non_culprit(stage_inputs) -> None:
    payload = build_stage_payload(NPC_STAGE, stage_inputs["non_culprit"])
    assert list(payload) == ["world", "cast", "clues", "npc_id"]
    assert "truth" not in payload


def test_npc_payload_appends_truth_last_for_culprit(stage_inputs) -> None:
    payload = build_stage_payload(NPC_STAGE, stage_inputs["culprit"])
    assert list(payload) == ["world", "cast", "clues", "npc_id", "truth"]


def test_prompt_is_deterministic(stage_inputs) -> None:
    first = build_stage_prompt(NPC_STAGE, stage_inputs["culprit"])
    second = build_stage_prompt(NPC_STAGE, stage_inputs["culprit"])
    assert first == second
    assert first.startswith("<|im_start|>system\n")
    assert first.endswith("<|im_start|>assistant\n")
    assert (
        CHATML_TEMPLATE.format(
            system=STAGE_SYSTEM_PROMPTS[NPC_STAGE],
            user=json.dumps(
                build_stage_payload(NPC_STAGE, stage_inputs["culprit"]), ensure_ascii=False
            ),
        )
        == first
    )


def test_non_ascii_is_preserved(stage_inputs) -> None:
    world = stage_inputs["world"].world.model_copy(update={"title": "Café Mystère"})
    prompt = build_stage_prompt("world->cast", CastStageInput(world=world))
    assert "Café Mystère" in prompt
    assert "\\u00e9" not in prompt


def test_golden_prompts_match_fixture(stage_inputs, skeleton_bundle) -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    culprit_id = skeleton_bundle.truth.solution.correct_culprit_id
    non_culprit_id = next(npc.id for npc in skeleton_bundle.world.npcs if npc.id != culprit_id)
    assert fixture["culprit_id"] == culprit_id
    assert fixture["non_culprit_id"] == non_culprit_id

    expected = fixture["prompts"]
    assert (
        build_stage_prompt("settings->world", stage_inputs["settings"])
        == expected["settings->world"]
    )
    assert build_stage_prompt("world->cast", stage_inputs["world"]) == expected["world->cast"]
    assert (
        build_stage_prompt("world+cast->truth+clues", stage_inputs["truth"])
        == expected["world+cast->truth+clues"]
    )
    assert build_stage_prompt(NPC_STAGE, stage_inputs["culprit"]) == expected["npc_culprit"]
    assert build_stage_prompt(NPC_STAGE, stage_inputs["non_culprit"]) == expected["npc_non_culprit"]
