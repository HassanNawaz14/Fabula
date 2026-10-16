from pydantic import Field

from fabula.schemas.enums import MysteryType
from fabula.schemas.world import (
    SCHEMA_VERSION,
    IdStr,
    SchemaVersion,
    ShortStr,
    StrictModel,
    TextStr,
)


class TimeWindow(StrictModel):
    start: int = Field(ge=0, le=10)
    end: int = Field(ge=0, le=10)


class Crime(StrictModel):
    type: MysteryType
    target: ShortStr
    time_window: TimeWindow
    location_id: IdStr


class TimelineEntry(StrictModel):
    t: int = Field(ge=0, le=10)
    who: IdStr
    what: TextStr
    where: IdStr


class Solution(StrictModel):
    correct_culprit_id: IdStr
    correct_method_id: IdStr
    correct_motive_id: IdStr
    how: TextStr
    why: TextStr


class RedHerring(StrictModel):
    npc: IdStr
    secret: TextStr


class TruthDocument(StrictModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    crime: Crime
    timeline: list[TimelineEntry] = Field(min_length=1)
    solution: Solution
    red_herrings: list[RedHerring] = Field(default_factory=list)
