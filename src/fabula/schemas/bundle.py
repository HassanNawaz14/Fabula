from pydantic import Field, model_validator

from fabula.schemas.clues import CluesDocument
from fabula.schemas.npc import Identity, Memory
from fabula.schemas.truth import TruthDocument
from fabula.schemas.world import SCHEMA_VERSION, IdStr, SchemaVersion, StrictModel, WorldDocument


class NpcFiles(StrictModel):
    identity: Identity
    memory: Memory


class Bundle(StrictModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    world: WorldDocument
    truth: TruthDocument
    clues: CluesDocument
    npcs: dict[IdStr, NpcFiles] = Field(min_length=5, max_length=6)

    @model_validator(mode="after")
    def cross_references_resolve(self) -> "Bundle":
        location_ids = {loc.id for loc in self.world.locations}
        clue_ids = {clue.id for clue in self.clues.clues}
        npc_ids = {npc.id for npc in self.world.npcs}
        method_ids = {m.id for m in self.world.accusation_options.methods}
        motive_ids = {m.id for m in self.world.accusation_options.motives}

        if set(self.npcs) != npc_ids:
            raise ValueError("npc file keys must match the world npc roster")
        if self.world.mystery_type != self.truth.crime.type:
            raise ValueError("world mystery_type must match truth crime type")
        if self.truth.crime.location_id not in location_ids:
            raise ValueError("crime location must exist in world")

        for entry in self.truth.timeline:
            if entry.who not in npc_ids:
                raise ValueError(f"timeline references unknown npc {entry.who}")
            if entry.where not in location_ids:
                raise ValueError(f"timeline references unknown location {entry.where}")

        solution = self.truth.solution
        if solution.correct_culprit_id not in npc_ids:
            raise ValueError("solution culprit must be an npc in the world")
        if solution.correct_method_id not in method_ids:
            raise ValueError("solution method must match an accusation option")
        if solution.correct_motive_id not in motive_ids:
            raise ValueError("solution motive must match an accusation option")

        for herring in self.truth.red_herrings:
            if herring.npc not in npc_ids:
                raise ValueError(f"red herring references unknown npc {herring.npc}")

        for clue in self.clues.clues:
            if clue.location_id not in location_ids:
                raise ValueError(f"clue {clue.id} is placed at unknown location {clue.location_id}")
            if clue.revealed_by_npc is not None and clue.revealed_by_npc not in npc_ids:
                raise ValueError(
                    f"clue {clue.id} is revealed by unknown npc {clue.revealed_by_npc}"
                )
            if not set(clue.requires) <= clue_ids:
                raise ValueError(f"clue {clue.id} requires an unknown clue")

        for loc in self.world.locations:
            if not set(loc.clue_spots) <= clue_ids:
                raise ValueError(f"location {loc.id} references unknown clue spot")

        for npc_id, files in self.npcs.items():
            if files.identity.id != npc_id:
                raise ValueError(f"identity id {files.identity.id} does not match folder {npc_id}")
            if files.memory.npc_id != npc_id:
                raise ValueError(
                    f"memory npc_id {files.memory.npc_id} does not match folder {npc_id}"
                )
            if not set(files.identity.relationships) <= npc_ids:
                raise ValueError(f"npc {npc_id} has a relationship with an unknown npc")
            fact_ids = {f.id for f in files.memory.facts}
            for fact in files.memory.facts:
                if fact.where not in location_ids:
                    raise ValueError(
                        f"fact {fact.id} of {npc_id} references unknown location {fact.where}"
                    )
                if not set(fact.reveal_requires) <= clue_ids:
                    raise ValueError(f"fact {fact.id} of {npc_id} requires an unknown clue")
                if fact.cover_story_id is not None and (
                    files.memory.cover_story is None
                    or fact.cover_story_id != files.memory.cover_story.id
                ):
                    raise ValueError(f"fact {fact.id} of {npc_id} references unknown cover story")
            if (
                files.memory.cover_story is not None
                and not set(files.memory.cover_story.supporting_facts) <= fact_ids
            ):
                raise ValueError(f"cover story of {npc_id} references unknown facts")
        return self
