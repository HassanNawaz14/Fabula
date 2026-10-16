import random

from fabula.schemas import Bundle, Difficulty, LocationType, MysteryType, Tone
from fabula.schemas.world import Location, NpcRosterEntry, Position, ScheduleEntry
from fabula.training_data.skeletons import common, disappearance, murder, theft

CONTENT = {
    MysteryType.THEFT: theft,
    MysteryType.DISAPPEARANCE: disappearance,
    MysteryType.MURDER: murder,
}


def _pick_location_types(rng: random.Random, content) -> tuple[LocationType, list[LocationType]]:
    preferred = list(content.CRIME_LOCATION_PREF)
    crime_type = preferred[rng.randrange(len(preferred))]
    filler_pool = [loc for loc in LocationType if loc != crime_type]
    count = rng.choice([3, 4])
    filler = rng.sample(filler_pool, k=count - 1)
    types = [crime_type] + filler
    rng.shuffle(types)
    return crime_type, types


def _build_locations(rng: random.Random, loc_types: list[LocationType]) -> list[Location]:
    locations = []
    for index, loc_type in enumerate(loc_types):
        names, descriptions = common.LOCATION_PROFILES[loc_type]
        connections = []
        if index > 0:
            connections.append(f"loc_{loc_types[index - 1].value}")
        if index < len(loc_types) - 1:
            connections.append(f"loc_{loc_types[index + 1].value}")
        locations.append(
            Location(
                id=f"loc_{loc_type.value}",
                name=names[rng.randrange(len(names))],
                type=loc_type,
                description=descriptions[rng.randrange(len(descriptions))],
                position=Position(x=index, y=0),
                connections=connections,
            )
        )
    if len(locations) >= 4 and rng.random() < 0.5:
        a, b = locations[0], locations[-1]
        a.connections.append(b.id)
        b.connections.append(a.id)
    return locations


def _build_schedules(
    rng: random.Random, npc_ids: list[str], location_ids: list[str]
) -> dict[str, list[ScheduleEntry]]:
    schedules = {}
    for npc_id in npc_ids:
        minutes = sorted(rng.sample(range(0, 11), k=rng.choice([2, 3])))
        schedules[npc_id] = [
            ScheduleEntry(at_minute=minute, location=location_ids[rng.randrange(len(location_ids))])
            for minute in minutes
        ]
    return schedules


def generate_skeleton(
    mystery_type: MysteryType | str,
    seed: int,
    tone: Tone | str | None = None,
    difficulty: Difficulty | str | None = None,
) -> Bundle:
    mt = MysteryType(mystery_type)
    rng = random.Random(f"fabula-skeletons-v1:{mt.value}:{seed}")
    content = CONTENT[mt]

    tone_value = Tone(tone) if tone is not None else list(Tone)[rng.randrange(len(list(Tone)))]
    difficulty_value = (
        Difficulty(difficulty)
        if difficulty is not None
        else list(Difficulty)[rng.randrange(len(list(Difficulty)))]
    )

    town = common.TOWN_NAMES[rng.randrange(len(common.TOWN_NAMES))]
    crime_type, loc_types = _pick_location_types(rng, content)
    locations = _build_locations(rng, loc_types)
    location_ids = [loc.id for loc in locations]
    crime_location = next(loc for loc in locations if loc.type == crime_type)

    npc_count = rng.choice([5, 6])
    npc_ids = [f"npc_{index:02d}" for index in range(1, npc_count + 1)]
    names = rng.sample(common.FIRST_NAMES, k=npc_count)
    culprit_id = npc_ids[rng.randrange(npc_count)]
    herring_id = rng.choice([nid for nid in npc_ids if nid != culprit_id])
    witness_id = rng.choice([nid for nid in npc_ids if nid not in {culprit_id, herring_id}])

    schedules = _build_schedules(rng, npc_ids, location_ids)
    roster = []
    identities = {}
    for index, npc_id in enumerate(npc_ids):
        start_location = schedules[npc_id][0].location
        roster.append(
            NpcRosterEntry(
                id=npc_id,
                display_name=names[index],
                start_location=start_location,
                schedule=schedules[npc_id],
            )
        )
        other_ids = [nid for nid in npc_ids if nid != npc_id]
        identities[npc_id] = {
            "id": npc_id,
            "name": names[index],
            "age": rng.randint(19, 68),
            "role": common.ROLES[rng.randrange(len(common.ROLES))],
            "traits": rng.sample(common.TRAITS, k=2),
            "speech_style": common.SPEECH_STYLES[rng.randrange(len(common.SPEECH_STYLES))],
            "backstory": common.BACKSTORIES[rng.randrange(len(common.BACKSTORIES))].format(
                town=town
            ),
            "goals": rng.sample(common.GOALS, k=2),
            "relationships": {
                other_ids[rng.randrange(len(other_ids))]: common.RELATIONSHIPS[
                    rng.randrange(len(common.RELATIONSHIPS))
                ]
            },
            "attitude_to_player": common.ATTITUDES[rng.randrange(len(common.ATTITUDES))],
        }

    target = content.TARGETS[rng.randrange(len(content.TARGETS))]
    method = content.METHODS[rng.randrange(len(content.METHODS))]
    motive = content.MOTIVES[rng.randrange(len(content.MOTIVES))]
    window_start = rng.randint(1, 4)
    window_end = min(10, window_start + rng.randint(2, 5))
    crime_minute = rng.randint(window_start, window_end)
    alibi_location = rng.choice([loc_id for loc_id in location_ids if loc_id != crime_location.id])
    alibi_minute = rng.randint(0, 10)
    herring_minute = rng.randint(0, 10)
    herring_location = schedules[herring_id][-1].location
    culprit_name = identities[culprit_id]["name"]
    witness_name = identities[witness_id]["name"]

    culprit_facts = [
        {
            "id": f"{culprit_id}_crime",
            "who": culprit_id,
            "what": f"I {method} at the {crime_location.id} at minute {crime_minute}.",
            "where": crime_location.id,
            "when": f"minute {crime_minute}",
            "source": "did",
            "secret": True,
            "disclosure": "lie",
            "reveal_requires": [],
            "cover_story_id": f"{culprit_id}_cover",
        },
        {
            "id": f"{culprit_id}_trace",
            "who": culprit_id,
            "what": common.TRACE_LINES[rng.randrange(len(common.TRACE_LINES))].format(
                place=crime_location.id
            ),
            "where": crime_location.id,
            "when": f"minute {crime_minute}",
            "source": "did",
            "secret": True,
            "disclosure": "hide",
            "reveal_requires": [],
            "cover_story_id": None,
        },
        {
            "id": f"{culprit_id}_alibi",
            "who": culprit_id,
            "what": common.ALIBI_LINES[rng.randrange(len(common.ALIBI_LINES))].format(
                place=alibi_location
            ),
            "where": alibi_location,
            "when": f"minute {alibi_minute}",
            "source": "heard",
            "secret": False,
            "disclosure": "if_asked",
            "reveal_requires": [],
            "cover_story_id": None,
        },
    ]
    culprit_memory = {
        "npc_id": culprit_id,
        "facts": culprit_facts,
        "cover_story": {
            "id": f"{culprit_id}_cover",
            "claim": (
                f"I was at the {alibi_location} the whole time, never near the {crime_location.id}."
            ),
            "supporting_facts": [f"{culprit_id}_alibi"],
        },
    }
    witness_memory = {
        "npc_id": witness_id,
        "facts": [
            {
                "id": f"{witness_id}_saw",
                "who": witness_id,
                "what": common.WITNESS_LINES[rng.randrange(len(common.WITNESS_LINES))].format(
                    place=crime_location.id
                ),
                "where": crime_location.id,
                "when": f"minute {crime_minute}",
                "source": "witnessed",
                "secret": False,
                "disclosure": "if_asked",
                "reveal_requires": [],
                "cover_story_id": None,
            }
        ],
        "cover_story": None,
    }
    herring_fact_id = f"{herring_id}_secret"
    herring_memory = {
        "npc_id": herring_id,
        "facts": [
            {
                "id": herring_fact_id,
                "who": herring_id,
                "what": (
                    f"I {common.HERRING_ACTS[rng.randrange(len(common.HERRING_ACTS))]} "
                    "and hope no one finds out."
                ),
                "where": herring_location,
                "when": f"minute {herring_minute}",
                "source": "did",
                "secret": True,
                "disclosure": "hide",
                "reveal_requires": [],
                "cover_story_id": None,
            }
        ],
        "cover_story": None,
    }
    other_memories = {}
    gossip_pairs: list[tuple[str, str]] = []
    for npc_id in npc_ids:
        if npc_id in {culprit_id, witness_id, herring_id}:
            continue
        fact_id = f"{npc_id}_gossip"
        gossip_pairs.append((npc_id, fact_id))
        other_memories[npc_id] = {
            "npc_id": npc_id,
            "facts": [
                {
                    "id": fact_id,
                    "who": npc_id,
                    "what": common.RUMOUR_LINES[rng.randrange(len(common.RUMOUR_LINES))].format(
                        target=target
                    ),
                    "where": schedules[npc_id][0].location,
                    "when": f"minute {rng.randint(0, 10)}",
                    "source": "heard",
                    "secret": False,
                    "disclosure": "volunteer",
                    "reveal_requires": [],
                    "cover_story_id": None,
                }
            ],
            "cover_story": None,
        }

    clue_defs = [
        {
            "id": "clue_01",
            "location_id": crime_location.id,
            "description": (
                f"Something is out of place at the {crime_location.id} — signs of a rushed exit."
            ),
            "discovery": "examine",
            "revealed_by_npc": None,
            "implies": [f"{culprit_id}_trace"],
            "requires": [],
        },
        {
            "id": "clue_02",
            "location_id": schedules[witness_id][0].location,
            "description": f"{witness_name} saw someone hurry away from the {crime_location.id}.",
            "discovery": "npc_reveal",
            "revealed_by_npc": witness_id,
            "implies": [f"{witness_id}_saw"],
            "requires": [],
        },
        {
            "id": "clue_03",
            "location_id": herring_location,
            "description": (
                "Something hidden nearby suggests someone in town is keeping a secret of their own."
            ),
            "discovery": "examine",
            "revealed_by_npc": None,
            "implies": [herring_fact_id],
            "requires": [],
        },
        {
            "id": "clue_04",
            "location_id": alibi_location,
            "description": (
                f"{culprit_name}'s claimed alibi at the {alibi_location} can be checked."
            ),
            "discovery": "npc_reveal",
            "revealed_by_npc": culprit_id,
            "implies": [f"{culprit_id}_alibi"],
            "requires": [],
        },
    ]
    extra_clues = []
    for index, (owner_id, fact_id) in enumerate(gossip_pairs):
        extra_clues.append(
            {
                "id": f"clue_{5 + index:02d}",
                "location_id": schedules[owner_id][0].location,
                "description": "A loose rumour that may or may not matter.",
                "discovery": "examine",
                "revealed_by_npc": None,
                "implies": [fact_id],
                "requires": [],
            }
        )
    n_clues = min(rng.randint(4, 6), 4 + len(extra_clues))
    clues = clue_defs + extra_clues[: n_clues - 4]

    clue_spots: dict[str, list[str]] = {}
    for clue in clues:
        clue_spots.setdefault(clue["location_id"], []).append(clue["id"])
    for location in locations:
        location.clue_spots = clue_spots.get(location.id, [])

    method_ids = [f"m_method_{index}" for index in range(1, 5)]
    motive_ids = [f"m_motive_{index}" for index in range(1, 5)]
    method_pool = [
        content.METHODS[i] for i in range(len(content.METHODS)) if content.METHODS[i] != method
    ]
    motive_pool = [
        content.MOTIVES[i] for i in range(len(content.MOTIVES)) if content.MOTIVES[i] != motive
    ]
    method_distractors = rng.sample(method_pool, k=3)
    motive_distractors = rng.sample(motive_pool, k=3)
    correct_method_slot = rng.randrange(4)
    correct_motive_slot = rng.randrange(4)
    method_texts = list(method_distractors)
    motive_texts = list(motive_distractors)
    method_texts.insert(correct_method_slot, method)
    motive_texts.insert(correct_motive_slot, motive)

    timeline = [
        {
            "t": crime_minute,
            "who": culprit_id,
            "what": f"Was busy near the {crime_location.id} and left in a hurry.",
            "where": crime_location.id,
        },
        {
            "t": crime_minute,
            "who": witness_id,
            "what": "Walked past and noticed something wrong.",
            "where": crime_location.id,
        },
        {
            "t": herring_minute,
            "who": herring_id,
            "what": "Was seen near their usual spot, acting nervous.",
            "where": herring_location,
        },
    ]

    memories = {culprit_id: culprit_memory, witness_id: witness_memory, herring_id: herring_memory}
    memories.update(other_memories)
    npc_files = {
        npc_id: {"identity": identities[npc_id], "memory": memories[npc_id]} for npc_id in npc_ids
    }

    title = content.TITLE_FMT.format(target=target, crime_place=crime_location.name)
    intro = content.INTRO_FMT.format(target=target, crime_place=crime_location.name, town=town)

    raw = {
        "schema_version": "1.0",
        "world": {
            "schema_version": "1.0",
            "scenario_id": f"{mt.value}_{seed}",
            "mystery_type": mt.value,
            "tone": tone_value.value,
            "difficulty": difficulty_value.value,
            "title": title[:120],
            "intro_text": intro,
            "town_name": town,
            "locations": [location.model_dump(mode="json") for location in locations],
            "npcs": [entry.model_dump(mode="json") for entry in roster],
            "accusation_options": {
                "methods": [
                    {"id": method_ids[index], "text": f"Method {index + 1}: {method_texts[index]}."}
                    for index in range(4)
                ],
                "motives": [
                    {"id": motive_ids[index], "text": f"Motive {index + 1}: {motive_texts[index]}."}
                    for index in range(4)
                ],
            },
        },
        "truth": {
            "schema_version": "1.0",
            "crime": {
                "type": mt.value,
                "target": target,
                "time_window": {"start": window_start, "end": window_end},
                "location_id": crime_location.id,
            },
            "timeline": timeline,
            "solution": {
                "correct_culprit_id": culprit_id,
                "correct_method_id": method_ids[correct_method_slot],
                "correct_motive_id": motive_ids[correct_motive_slot],
                "how": content.how_text(
                    culprit_name, method, target, crime_location.id, crime_minute
                ),
                "why": content.why_text(motive),
            },
            "red_herrings": [{"npc": herring_id, "secret": herring_memory["facts"][0]["what"]}],
        },
        "clues": {"schema_version": "1.0", "clues": clues},
        "npcs": npc_files,
    }
    return Bundle.model_validate(raw)
