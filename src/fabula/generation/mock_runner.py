"""Offline deterministic model runner used by tests, the CLI demo and E-02."""

from __future__ import annotations

from pydantic import BaseModel

from fabula.generation.protocols import StageName
from fabula.schemas import (
    Bundle,
    CastCharacter,
    CastDocument,
    NpcStageInput,
    NpcStageOutput,
    TruthStageOutput,
)
from fabula.training_data import generate_skeleton


def cast_from_bundle(bundle: Bundle) -> CastDocument:
    """Build the cast stage output implied by a validated skeleton bundle."""
    characters = []
    for roster_entry in bundle.world.npcs:
        identity = bundle.npcs[roster_entry.id].identity
        characters.append(
            CastCharacter(
                id=identity.id,
                display_name=identity.name,
                role=identity.role,
                traits=list(identity.traits),
                relationships=dict(identity.relationships),
                attitude_to_player=identity.attitude_to_player,
            )
        )
    return CastDocument(characters=characters)


class MockModelRunner:
    """Return valid stage JSON from a prebuilt bundle.

    `fail_stage_times` makes the next N calls for a stage return malformed
    text, which exercises the retry and exhaustion paths without a model.
    """

    def __init__(
        self,
        bundle: Bundle,
        fail_stage_times: dict[StageName, int] | None = None,
    ) -> None:
        self.bundle = bundle
        self.fail_stage_times = dict(fail_stage_times or {})
        self.calls: list[StageName] = []
        self.seeds: list[int] = []

    def generate(
        self,
        stage: StageName,
        stage_input: BaseModel,
        output_model: type[BaseModel],
        seed: int,
    ) -> str:
        self.calls.append(stage)
        self.seeds.append(seed)
        remaining = self.fail_stage_times.get(stage, 0)
        if remaining > 0:
            self.fail_stage_times[stage] = remaining - 1
            return "{ this is not valid stage JSON"

        payload = self._payload(stage, stage_input)
        return payload.model_dump_json()

    def _payload(self, stage: StageName, stage_input: BaseModel) -> BaseModel:
        if stage == "settings->world":
            return self.bundle.world
        if stage == "world->cast":
            return cast_from_bundle(self.bundle)
        if stage == "world+cast->truth+clues":
            return TruthStageOutput(truth=self.bundle.truth, clues=self.bundle.clues)
        if stage == "world+cast+truth+clues+npc_id->identity+memory":
            if not isinstance(stage_input, NpcStageInput):
                raise TypeError("npc stage input must be NpcStageInput")
            npc_files = self.bundle.npcs[stage_input.npc_id]
            return NpcStageOutput(identity=npc_files.identity, memory=npc_files.memory)
        raise ValueError(f"unknown generation stage: {stage}")


def skeleton_runner(
    fail_stage_times: dict[StageName, int] | None = None,
) -> MockModelRunner:
    """Convenience runner backed by a deterministic theft skeleton."""
    return MockModelRunner(generate_skeleton("theft", 0), fail_stage_times=fail_stage_times)
