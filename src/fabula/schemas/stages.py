from typing import Literal

from pydantic import Field, model_validator

from fabula.schemas.clues import CluesDocument
from fabula.schemas.enums import Difficulty, SettingsMysteryType, Tone
from fabula.schemas.npc import Identity, Memory
from fabula.schemas.truth import TruthDocument
from fabula.schemas.world import (
    SCHEMA_VERSION,
    IdStr,
    NameStr,
    SchemaVersion,
    ShortStr,
    StrictModel,
    WorldDocument,
)


class GenerationSettings(StrictModel):
    mystery_type: SettingsMysteryType
    tone: Tone
    difficulty: Difficulty


WorldStageInput = GenerationSettings
WorldStageOutput = WorldDocument


class CastCharacter(StrictModel):
    id: IdStr
    display_name: NameStr
    role: ShortStr
    traits: list[ShortStr] = Field(min_length=1, max_length=8)
    relationships: dict[IdStr, ShortStr] = Field(default_factory=dict)
    attitude_to_player: ShortStr


class CastDocument(StrictModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    characters: list[CastCharacter] = Field(min_length=5, max_length=6)

    @model_validator(mode="after")
    def unique_character_ids(self) -> "CastDocument":
        ids = [c.id for c in self.characters]
        if len(ids) != len(set(ids)):
            raise ValueError("cast character ids must be unique")
        return self


class CastStageInput(StrictModel):
    world: WorldDocument


CastStageOutput = CastDocument


class TruthStageInput(StrictModel):
    world: WorldDocument
    cast: CastDocument

    @model_validator(mode="after")
    def cast_matches_world(self) -> "TruthStageInput":
        world_ids = {npc.id for npc in self.world.npcs}
        cast_ids = {c.id for c in self.cast.characters}
        if cast_ids != world_ids:
            raise ValueError("cast characters must match the world npc roster")
        return self


class TruthStageOutput(StrictModel):
    truth: TruthDocument
    clues: CluesDocument


class NpcStageInput(StrictModel):
    world: WorldDocument
    cast: CastDocument
    truth: TruthDocument
    clues: CluesDocument
    npc_id: IdStr

    @model_validator(mode="after")
    def npc_id_in_world(self) -> "NpcStageInput":
        if self.npc_id not in {npc.id for npc in self.world.npcs}:
            raise ValueError(f"npc_id {self.npc_id} is not in the world roster")
        return self


class NpcStageOutput(StrictModel):
    identity: Identity
    memory: Memory

    @model_validator(mode="after")
    def files_belong_together(self) -> "NpcStageOutput":
        if self.identity.id != self.memory.npc_id:
            raise ValueError("identity id and memory npc_id must match")
        return self


class StageSequence(StrictModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    stages: Literal[
        "settings->world",
        "world->cast",
        "world+cast->truth+clues",
        "world+cast+truth+clues+npc_id->identity+memory",
    ]
