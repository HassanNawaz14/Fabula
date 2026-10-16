from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fabula.schemas.enums import Difficulty, LocationType, MysteryType, Tone

SchemaVersion = Literal["1.0"]
SCHEMA_VERSION: SchemaVersion = "1.0"

IdStr = Annotated[str, Field(min_length=1, max_length=64)]
NameStr = Annotated[str, Field(min_length=1, max_length=120)]
TextStr = Annotated[str, Field(min_length=1, max_length=4000)]
ShortStr = Annotated[str, Field(min_length=1, max_length=400)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Position(StrictModel):
    x: int = Field(ge=0, le=99)
    y: int = Field(ge=0, le=99)


class Location(StrictModel):
    id: IdStr
    name: NameStr
    type: LocationType
    description: TextStr
    position: Position
    connections: list[IdStr] = Field(min_length=1)
    clue_spots: list[IdStr] = Field(default_factory=list)


class ScheduleEntry(StrictModel):
    at_minute: int = Field(ge=0, le=10)
    location: IdStr


class NpcRosterEntry(StrictModel):
    id: IdStr
    display_name: NameStr
    start_location: IdStr
    schedule: list[ScheduleEntry] = Field(min_length=1)


class MethodOption(StrictModel):
    id: IdStr
    text: ShortStr


class MotiveOption(StrictModel):
    id: IdStr
    text: ShortStr


class AccusationOptions(StrictModel):
    methods: list[MethodOption] = Field(min_length=4, max_length=4)
    motives: list[MotiveOption] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def unique_option_ids(self) -> "AccusationOptions":
        method_ids = [m.id for m in self.methods]
        motive_ids = [m.id for m in self.motives]
        if len(method_ids) != len(set(method_ids)):
            raise ValueError("method option ids must be unique")
        if len(motive_ids) != len(set(motive_ids)):
            raise ValueError("motive option ids must be unique")
        if set(method_ids) & set(motive_ids):
            raise ValueError("method and motive option ids must not overlap")
        return self


class WorldDocument(StrictModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    scenario_id: IdStr
    mystery_type: MysteryType
    tone: Tone
    difficulty: Difficulty
    title: NameStr
    intro_text: TextStr
    town_name: NameStr
    locations: Annotated[list[Location], Field(min_length=3, max_length=4)]
    npcs: Annotated[list[NpcRosterEntry], Field(min_length=5, max_length=6)]
    accusation_options: AccusationOptions

    @model_validator(mode="after")
    def unique_ids_and_valid_refs(self) -> "WorldDocument":
        location_ids = [loc.id for loc in self.locations]
        npc_ids = [npc.id for npc in self.npcs]
        if len(location_ids) != len(set(location_ids)):
            raise ValueError("location ids must be unique")
        if len(npc_ids) != len(set(npc_ids)):
            raise ValueError("npc ids must be unique")
        known_locations = set(location_ids)
        for loc in self.locations:
            for ref in loc.connections:
                if ref not in known_locations:
                    raise ValueError(f"location {loc.id} connects to unknown location {ref}")
                if ref == loc.id:
                    raise ValueError(f"location {loc.id} cannot connect to itself")
        for npc in self.npcs:
            if npc.start_location not in known_locations:
                raise ValueError(f"npc {npc.id} starts at unknown location {npc.start_location}")
            for entry in npc.schedule:
                if entry.location not in known_locations:
                    raise ValueError(
                        f"npc {npc.id} schedule references unknown location {entry.location}"
                    )
        return self
