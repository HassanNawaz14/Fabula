"""Prompt construction that mirrors the fine-tuning contract in training/scripts.

The fine-tuned model only ever saw these four system instructions, the payload
shapes below, and Qwen2.5 ChatML turns. Do not add schema text or extra
messages here without a real-model benchmark and an owner-facing note.
"""

from __future__ import annotations

import json

from pydantic import BaseModel

from fabula.generation.protocols import StageName
from fabula.schemas import (
    CastStageInput,
    GenerationSettings,
    NpcStageInput,
    TruthStageInput,
)

# Internal NPC stage name includes `truth` because NpcStageInput carries it.
# The training label was `world+cast+clues+npc_id->identity+memory`, and the
# model only receives truth in the culprit's payload.
STAGE_SYSTEM_PROMPTS: dict[StageName, str] = {
    "settings->world": (
        "You are the Fabula game generation engine. Given the scenario settings, "
        "generate the world document in valid JSON."
    ),
    "world->cast": (
        "You are the Fabula game generation engine. Given the world document, "
        "generate the cast roster in valid JSON."
    ),
    "world+cast->truth+clues": (
        "You are the Fabula game generation engine. Given the world and cast, "
        "generate the truth and clues documents in valid JSON."
    ),
    "world+cast+truth+clues+npc_id->identity+memory": (
        "You are the Fabula game generation engine. Given the context and NPC ID, "
        "generate that NPC's identity and memory in valid JSON."
    ),
}

CHATML_TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{user}<|im_end|>\n"
    "<|im_start|>assistant\n"
)

STOP_TOKENS: tuple[str, ...] = ("<|im_end|>", "<|endoftext|>")

NPC_STAGE: StageName = "world+cast+truth+clues+npc_id->identity+memory"


def _json_document(model: BaseModel) -> dict[str, object]:
    return model.model_dump(mode="json")


def build_stage_payload(stage: StageName, stage_input: BaseModel) -> dict[str, object]:
    """Build the exact user payload the model was trained on."""
    if stage == "settings->world":
        if not isinstance(stage_input, GenerationSettings):
            raise TypeError("settings->world expects GenerationSettings")
        return {
            "mystery_type": stage_input.mystery_type.value,
            "tone": stage_input.tone.value,
            "difficulty": stage_input.difficulty.value,
        }

    if stage == "world->cast":
        if not isinstance(stage_input, CastStageInput):
            raise TypeError("world->cast expects CastStageInput")
        return {"world": _json_document(stage_input.world)}

    if stage == "world+cast->truth+clues":
        if not isinstance(stage_input, TruthStageInput):
            raise TypeError("world+cast->truth+clues expects TruthStageInput")
        return {
            "world": _json_document(stage_input.world),
            "cast": _json_document(stage_input.cast),
        }

    if stage == NPC_STAGE:
        if not isinstance(stage_input, NpcStageInput):
            raise TypeError(f"{NPC_STAGE} expects NpcStageInput")
        payload: dict[str, object] = {
            "world": _json_document(stage_input.world),
            "cast": _json_document(stage_input.cast),
            "clues": _json_document(stage_input.clues),
            "npc_id": stage_input.npc_id,
        }
        if stage_input.truth.solution.correct_culprit_id == stage_input.npc_id:
            payload["truth"] = _json_document(stage_input.truth)
        return payload

    raise ValueError(f"unknown generation stage: {stage}")


def build_stage_prompt(stage: StageName, stage_input: BaseModel) -> str:
    """Build the ChatML prompt used at inference for one stage."""
    payload = build_stage_payload(stage, stage_input)
    user_content = json.dumps(payload, ensure_ascii=False)
    return CHATML_TEMPLATE.format(
        system=STAGE_SYSTEM_PROMPTS[stage],
        user=user_content,
    )
