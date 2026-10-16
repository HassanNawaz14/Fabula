from typing import Annotated

from pydantic import Field, model_validator

from fabula.schemas.enums import Disclosure, FactSource, Mood
from fabula.schemas.world import (
    SCHEMA_VERSION,
    IdStr,
    NameStr,
    SchemaVersion,
    ShortStr,
    StrictModel,
    TextStr,
)


class Identity(StrictModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    id: IdStr
    name: NameStr
    age: int = Field(ge=0, le=120)
    role: ShortStr
    traits: Annotated[list[ShortStr], Field(min_length=1, max_length=8)]
    speech_style: TextStr
    backstory: TextStr
    goals: list[ShortStr] = Field(default_factory=list)
    relationships: dict[IdStr, ShortStr] = Field(default_factory=dict)
    attitude_to_player: TextStr


class Fact(StrictModel):
    id: IdStr
    who: IdStr
    what: TextStr
    where: IdStr
    when: ShortStr
    source: FactSource
    secret: bool
    disclosure: Disclosure
    reveal_requires: list[IdStr] = Field(default_factory=list)
    cover_story_id: IdStr | None = None


class CoverStory(StrictModel):
    id: IdStr
    claim: TextStr
    supporting_facts: list[IdStr] = Field(default_factory=list)


class Memory(StrictModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    npc_id: IdStr
    facts: list[Fact] = Field(min_length=1)
    cover_story: CoverStory | None = None

    @model_validator(mode="after")
    def fact_ids_unique_and_self(self) -> "Memory":
        fact_ids = [f.id for f in self.facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("fact ids must be unique")
        if any(f.who != self.npc_id for f in self.facts):
            raise ValueError("every fact must belong to this npc")
        return self


class NpcReply(StrictModel):
    reply: TextStr
    mood: Mood = Mood.NEUTRAL
