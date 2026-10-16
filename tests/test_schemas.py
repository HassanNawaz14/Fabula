import copy

import pytest
from pydantic import ValidationError

from fabula.schemas import (
    Bundle,
    CastDocument,
    GenerationSettings,
    NpcPromptInput,
    NpcReply,
    NpcStageOutput,
    TruthStageInput,
)

LOCATION_IDS = ["market", "library", "parking", "park"]
LOCATION_META = {
    "market": ("Saffron Market", "market", "A busy market square."),
    "library": ("Old Library", "library", "A quiet library."),
    "parking": ("Town Parking Lot", "parking", "An open parking lot with flickering lights."),
    "park": ("Town Park", "park", "A small green park."),
}
NPC_IDS = [f"npc_{i:02d}" for i in range(1, 7)]
METHOD_IDS = [f"m_method_{i}" for i in range(1, 5)]
MOTIVE_IDS = [f"m_motive_{i}" for i in range(1, 5)]


def build_locations(count: int) -> list[dict]:
    ids = LOCATION_IDS[:count]
    locations = []
    for index, loc_id in enumerate(ids):
        name, loc_type, description = LOCATION_META[loc_id]
        connections = []
        if index > 0:
            connections.append(ids[index - 1])
        if index < len(ids) - 1:
            connections.append(ids[index + 1])
        locations.append(
            {
                "id": loc_id,
                "name": name,
                "type": loc_type,
                "description": description,
                "position": {"x": index, "y": 0},
                "connections": connections,
                "clue_spots": [],
            }
        )
    return locations


def build_npcs(count: int, location_ids: list[str]) -> list[dict]:
    npcs = []
    for index in range(count):
        npc_id = NPC_IDS[index]
        start = location_ids[index % len(location_ids)]
        npcs.append(
            {
                "id": npc_id,
                "display_name": f"Character {index + 1}",
                "start_location": start,
                "schedule": [{"at_minute": index, "location": start}],
            }
        )
    return npcs


def build_clues(count: int, location_ids: list[str], npc_ids: list[str]) -> list[dict]:
    clues = []
    for index in range(count):
        clue_id = f"clue_{index + 1:02d}"
        last = index == count - 1
        clues.append(
            {
                "id": clue_id,
                "location_id": location_ids[index % len(location_ids)],
                "description": f"Clue number {index + 1}.",
                "discovery": "npc_reveal" if last else "examine",
                "revealed_by_npc": npc_ids[0] if last else None,
                "implies": [],
                "requires": [f"clue_{index:02d}"] if index > 0 else [],
            }
        )
    return clues


def assign_clue_spots(locations: list[dict], clues: list[dict]) -> None:
    for clue in clues:
        for location in locations:
            if location["id"] == clue["location_id"]:
                location["clue_spots"].append(clue["id"])


def build_npc_files(npc_id: str, index: int, location_id: str, is_culprit: bool) -> dict:
    fact_id = f"f_{npc_id[-2:]}_1"
    fact = {
        "id": fact_id,
        "who": npc_id,
        "what": f"{npc_id} took the locket near the {location_id} at minute 3."
        if is_culprit
        else f"{npc_id} saw something near the {location_id}.",
        "where": location_id,
        "when": "minute 3",
        "source": "did" if is_culprit else "witnessed",
        "secret": is_culprit,
        "disclosure": "lie" if is_culprit else "volunteer",
        "reveal_requires": [],
        "cover_story_id": "cs_01" if is_culprit else None,
    }
    memory = {
        "npc_id": npc_id,
        "facts": [fact],
        "cover_story": (
            {
                "id": "cs_01",
                "claim": f"{npc_id} was elsewhere the whole time.",
                "supporting_facts": [fact_id],
            }
            if is_culprit
            else None
        ),
    }
    identity = {
        "id": npc_id,
        "name": f"Character {index + 1}",
        "age": 20 + index,
        "role": "townsperson",
        "traits": ["observant"],
        "speech_style": "plain and direct",
        "backstory": "Lived in town for years.",
        "goals": ["get through the day"],
        "relationships": {"npc_01": "acquaintance"} if npc_id != "npc_01" else {},
        "attitude_to_player": "polite but guarded",
    }
    return {"identity": identity, "memory": memory}


def build_bundle_raw(npc_count: int = 5, location_count: int = 3, clue_count: int = 4) -> dict:
    locations = build_locations(location_count)
    location_ids = [loc["id"] for loc in locations]
    npc_ids = NPC_IDS[:npc_count]
    npcs = build_npcs(npc_count, location_ids)
    clues = build_clues(clue_count, location_ids, npc_ids)
    clues[0]["implies"] = ["f_03_1"]
    assign_clue_spots(locations, clues)
    culprit = "npc_03"
    world = {
        "schema_version": "1.0",
        "scenario_id": "scenario_test_1",
        "mystery_type": "theft",
        "tone": "cozy",
        "difficulty": "normal",
        "title": "The Missing Locket",
        "intro_text": "Something vanished from the market this morning.",
        "town_name": "Willowbrook",
        "locations": locations,
        "npcs": npcs,
        "accusation_options": {
            "methods": [
                {"id": method_id, "text": f"Method option {i}."}
                for i, method_id in enumerate(METHOD_IDS)
            ],
            "motives": [
                {"id": motive_id, "text": f"Motive option {i}."}
                for i, motive_id in enumerate(MOTIVE_IDS)
            ],
        },
    }
    truth = {
        "schema_version": "1.0",
        "crime": {
            "type": "theft",
            "target": "a silver locket",
            "time_window": {"start": 2, "end": 4},
            "location_id": location_ids[0],
        },
        "timeline": [
            {"t": 3, "who": culprit, "what": "Took the locket.", "where": location_ids[0]}
        ],
        "solution": {
            "correct_culprit_id": culprit,
            "correct_method_id": METHOD_IDS[0],
            "correct_motive_id": MOTIVE_IDS[0],
            "how": "Slipped the locket into a coat pocket.",
            "why": "Needed money for a debt.",
        },
        "red_herrings": [{"npc": "npc_02", "secret": "Owes a small debt."}],
    }
    npc_files = {
        npc_id: build_npc_files(
            npc_id, index, location_ids[index % len(location_ids)], npc_id == culprit
        )
        for index, npc_id in enumerate(npc_ids)
    }
    return {
        "schema_version": "1.0",
        "world": world,
        "truth": truth,
        "clues": {"schema_version": "1.0", "clues": clues},
        "npcs": npc_files,
    }


def validate(raw: dict) -> Bundle:
    return Bundle.model_validate(raw)


def test_minimal_bundle_validates_and_roundtrips() -> None:
    bundle = validate(build_bundle_raw())
    dumped = bundle.model_dump(mode="json")
    assert Bundle.model_validate(dumped).model_dump(mode="json") == dumped
    assert len(bundle.world.locations) == 3
    assert len(bundle.world.npcs) == 5
    assert len(bundle.clues.clues) == 4


def test_maximal_bundle_validates() -> None:
    bundle = validate(build_bundle_raw(npc_count=6, location_count=4, clue_count=6))
    assert len(bundle.world.npcs) == 6
    assert len(bundle.world.locations) == 4
    assert len(bundle.clues.clues) == 6


@pytest.mark.parametrize(
    ("npc_count", "location_count", "clue_count"),
    [(5, 2, 4), (4, 3, 4), (5, 3, 3), (5, 3, 7)],
)
def test_rejects_out_of_bounds_counts(npc_count: int, location_count: int, clue_count: int) -> None:
    raw = build_bundle_raw(npc_count=min(npc_count, 6), location_count=location_count, clue_count=4)
    if npc_count < 5:
        raw["world"]["npcs"] = raw["world"]["npcs"][:npc_count]
        raw["npcs"] = {key: raw["npcs"][key] for key in [npc["id"] for npc in raw["world"]["npcs"]]}
    if clue_count < 4:
        raw["clues"]["clues"] = raw["clues"]["clues"][:clue_count]
    if clue_count > 6:
        raw["clues"]["clues"] = raw["clues"]["clues"] + [
            copy.deepcopy(raw["clues"]["clues"][0]) for _ in range(clue_count - 4)
        ]
    with pytest.raises(ValidationError):
        validate(raw)


def test_rejects_too_many_locations() -> None:
    raw = build_bundle_raw(location_count=4)
    raw["world"]["locations"].append(copy.deepcopy(raw["world"]["locations"][0]))
    with pytest.raises(ValidationError):
        validate(raw)


def test_rejects_too_many_npcs() -> None:
    raw = build_bundle_raw(npc_count=6)
    last = copy.deepcopy(raw["world"]["npcs"][-1])
    last["id"] = "npc_07"
    raw["world"]["npcs"].append(last)
    with pytest.raises(ValidationError):
        validate(raw)


def test_rejects_unknown_location_type() -> None:
    raw = build_bundle_raw()
    raw["world"]["locations"][0]["type"] = "airport"
    with pytest.raises(ValidationError):
        validate(raw)


def test_rejects_schedule_minute_out_of_range() -> None:
    raw = build_bundle_raw()
    raw["world"]["npcs"][0]["schedule"][0]["at_minute"] = 11
    with pytest.raises(ValidationError):
        validate(raw)


def test_rejects_unknown_connection() -> None:
    raw = build_bundle_raw()
    raw["world"]["locations"][0]["connections"] = ["nowhere"]
    with pytest.raises(ValidationError):
        validate(raw)


def test_rejects_unknown_clue_location() -> None:
    raw = build_bundle_raw()
    raw["clues"]["clues"][0]["location_id"] = "nowhere"
    with pytest.raises(ValidationError):
        validate(raw)


def test_rejects_unknown_solution_culprit() -> None:
    raw = build_bundle_raw()
    raw["truth"]["solution"]["correct_culprit_id"] = "npc_99"
    with pytest.raises(ValidationError):
        validate(raw)


def test_rejects_method_not_in_options() -> None:
    raw = build_bundle_raw()
    raw["truth"]["solution"]["correct_method_id"] = "m_method_99"
    with pytest.raises(ValidationError):
        validate(raw)


def test_rejects_fact_belonging_to_another_npc() -> None:
    raw = build_bundle_raw()
    raw["npcs"]["npc_01"]["memory"]["facts"][0]["who"] = "npc_02"
    with pytest.raises(ValidationError):
        validate(raw)


def test_rejects_mismatched_identity_and_memory() -> None:
    raw = build_bundle_raw()
    raw["npcs"]["npc_01"]["memory"]["npc_id"] = "npc_02"
    with pytest.raises(ValidationError):
        validate(raw)


def test_rejects_duplicate_method_options() -> None:
    raw = build_bundle_raw()
    raw["world"]["accusation_options"]["methods"][1]["id"] = raw["world"]["accusation_options"][
        "methods"
    ][0]["id"]
    with pytest.raises(ValidationError):
        validate(raw)


def test_prompt_input_rejects_truth_field() -> None:
    raw = build_bundle_raw()
    files = raw["npcs"]["npc_01"]
    payload = {
        "identity": files["identity"],
        "memory": files["memory"],
        "chat_history": [],
        "player_input": "Did you see anything?",
        "truth": raw["truth"],
    }
    with pytest.raises(ValidationError):
        NpcPromptInput.model_validate(payload)


def test_prompt_input_accepts_own_files_only() -> None:
    raw = build_bundle_raw()
    files = raw["npcs"]["npc_01"]
    prompt = NpcPromptInput.model_validate(
        {
            "identity": files["identity"],
            "memory": files["memory"],
            "chat_history": [{"role": "player", "text": "Hello"}],
            "player_input": "Did you see anything?",
        }
    )
    assert prompt.memory.npc_id == "npc_01"


def test_rejects_unknown_mood() -> None:
    with pytest.raises(ValidationError):
        NpcReply.model_validate({"reply": "hello", "mood": "smug"})


def test_reply_defaults_to_neutral_mood() -> None:
    reply = NpcReply.model_validate({"reply": "hello"})
    assert reply.mood == "neutral"


def test_settings_accept_random_and_concrete_types() -> None:
    for mystery_type in ["random", "theft", "disappearance", "murder"]:
        settings = GenerationSettings.model_validate(
            {"mystery_type": mystery_type, "tone": "cozy", "difficulty": "easy"}
        )
        assert settings.mystery_type == mystery_type
    with pytest.raises(ValidationError):
        GenerationSettings.model_validate(
            {"mystery_type": "sabotage", "tone": "cozy", "difficulty": "easy"}
        )


def test_truth_stage_rejects_cast_that_does_not_match_world() -> None:
    raw = build_bundle_raw()
    cast_raw = {
        "schema_version": "1.0",
        "characters": [
            {
                "id": npc["id"],
                "display_name": npc["display_name"],
                "role": "townsperson",
                "traits": ["quiet"],
                "relationships": {},
                "attitude_to_player": "neutral",
            }
            for npc in raw["world"]["npcs"]
        ],
    }
    cast = CastDocument.model_validate(cast_raw)
    TruthStageInput.model_validate({"world": raw["world"], "cast": cast})
    cast_raw["characters"] = cast_raw["characters"][1:]
    with pytest.raises(ValidationError):
        TruthStageInput.model_validate({"world": raw["world"], "cast": cast_raw})


def test_npc_stage_output_requires_matching_ids() -> None:
    raw = build_bundle_raw()
    with pytest.raises(ValidationError):
        NpcStageOutput.model_validate(
            {
                "identity": raw["npcs"]["npc_01"]["identity"],
                "memory": raw["npcs"]["npc_02"]["memory"],
            }
        )
