"""Deterministic blueprint samples for the neurosymbolic generation route.

Used when no fast model artifact is available, so the local route still
produces a validated case in seconds. The Kaggle distillation script imports
the same generator, keeping training data and runtime fallback identical.
"""

from __future__ import annotations

import random
from typing import Any

from fabula.generation.compiler import BlueprintCompiler
from fabula.generation.dsl import parse_dsl
from fabula.schemas.enums import Difficulty, MysteryType, Tone
from fabula.training_data.skeletons import disappearance, murder, theft

CONTENT_MAP = {
    MysteryType.THEFT: theft,
    MysteryType.DISAPPEARANCE: disappearance,
    MysteryType.MURDER: murder,
}


def generate_synthetic_blueprint_sample(seed: int) -> dict[str, Any]:
    """Generate a guaranteed-valid blueprint sample using the domain logic generator."""
    rng = random.Random(f"fabula-distillation:{seed}")
    mtype = rng.choice(list(MysteryType))
    tone = rng.choice(list(Tone))
    diff = rng.choice(list(Difficulty))

    content = CONTENT_MAP[mtype]
    crime_type = rng.choice(list(content.CRIME_LOCATION_PREF))
    scene_id = f"loc_{crime_type.value}"

    target = content.TARGETS[rng.randrange(len(content.TARGETS))]
    method = content.METHODS[rng.randrange(len(content.METHODS))]
    motive = content.MOTIVES[rng.randrange(len(content.MOTIVES))]
    crime_minute = rng.randint(2, 8)

    culprit_id = "npc_01"
    suspect_ids = ["npc_02", "npc_03", "npc_04", "npc_05"]

    locations = [scene_id, "loc_library", "loc_cafe", "loc_market"]

    timeline_lines = [
        f"- {crime_minute - 1} | {culprit_id} | {locations[1]} | prepares covert equipment",
        f"- {crime_minute} | {culprit_id} | {scene_id} | commits {mtype.value} using {method}",
        f"- {crime_minute} | {suspect_ids[0]} | {locations[2]} | working at counter",
        f"- {crime_minute + 1} | {suspect_ids[1]} | {locations[3]} | notices hurried footsteps",
    ]

    clue_lines = [
        f"- {mtype.value}_trace | {scene_id} | physical | links:{culprit_id} | proves:meth",
        f"- hidden_record | {locations[1]} | document | links:{culprit_id} | proves:mot",
        f"- stray_button | {locations[2]} | trace | red_herring:{suspect_ids[0]}",
        f"- witness_memo | {locations[3]} | document | links:{suspect_ids[1]} | proves:alibi",
    ]

    knowledge_lines = [
        f"- {suspect_ids[0]} | alibi:in_{locations[2]}_at_crime | sees:nobody_unusual",
        f"- {suspect_ids[1]} | alibi:in_{locations[3]}_at_crime | sees:{culprit_id}_running",
        f"- {suspect_ids[2]} | confirms:{suspect_ids[0]}_presence",
    ]

    dsl_text = f"""[CASE:{mtype.value}|{tone.value}|seed_{seed}]
PREMISE: A {mtype.value} of {target} disrupts the quiet routine of the town.
CAST: vict:{target} | culp:{culprit_id} | susp:{",".join(suspect_ids)}
CRIME: mot:{motive} | meth:{method} | scene:{scene_id} | time:{crime_minute}
TIMELINE:
{chr(10).join(timeline_lines)}
CLUES:
{chr(10).join(clue_lines)}
KNOWLEDGE:
{chr(10).join(knowledge_lines)}
"""

    bp = parse_dsl(dsl_text)
    compiler = BlueprintCompiler(bp, seed=seed)
    bundle = compiler.compile()
    assert compiler.verify_solvability(bundle) is True

    user_prompt = (
        f"GENERATE_CASE: type={mtype.value} tone={tone.value} difficulty={diff.value} seed={seed}"
    )

    return {
        "seed": seed,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Fabula's Master Mystery Architect. "
                    "Generate a valid Compact Blueprint DSL."
                ),
            },
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": dsl_text.strip()},
        ],
    }


__all__ = ["CONTENT_MAP", "generate_synthetic_blueprint_sample"]
