from typing import Annotated

from pydantic import Field, model_validator

from fabula.schemas.enums import DiscoveryMethod
from fabula.schemas.world import SCHEMA_VERSION, IdStr, SchemaVersion, StrictModel, TextStr


class Clue(StrictModel):
    id: IdStr
    location_id: IdStr
    description: TextStr
    discovery: DiscoveryMethod
    revealed_by_npc: IdStr | None = None
    implies: list[IdStr] = Field(default_factory=list)
    requires: list[IdStr] = Field(default_factory=list)


class CluesDocument(StrictModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    clues: Annotated[list[Clue], Field(min_length=4, max_length=6)]

    @model_validator(mode="after")
    def unique_clue_ids(self) -> "CluesDocument":
        ids = [c.id for c in self.clues]
        if len(ids) != len(set(ids)):
            raise ValueError("clue ids must be unique")
        return self
