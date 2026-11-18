"""Kaggle Teacher Distillation Script for Fabula Compact Blueprints.

Generates 1,500 diverse mystery configurations, expands them via Teacher LLM
into Compact Blueprint DSL, verifies them through the symbolic compiler,
and partitions them into disjoint train/val/test splits for student SFT.
"""

from __future__ import annotations

import json
import os
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

PROMPT_TEMPLATE = """You are Fabula's Master Mystery Architect.
Generate a solvable mystery blueprint in the Compact Blueprint DSL format.

Constraints:
- Case Type: {mystery_type}
- Tone: {tone}
- Difficulty: {difficulty}
- Seed: {seed}

Output strictly in the Compact Blueprint DSL format:
[CASE:{mystery_type}|{tone}|seed_{seed}]
PREMISE: <one evocative sentence describing the crime>
CAST: vict:<name> | culp:<culprit_npc_id> | susp:<comma_separated_suspect_ids>
CRIME: mot:<motive> | meth:<method> | scene:<location_id> | time:<minute_1_to_9>
TIMELINE:
- <time> | <actor> | <location> | <action>
CLUES:
- <clue_id> | <location> | <type> | links:<actor> | proves:<mot_or_meth>
KNOWLEDGE:
- <npc_id> | <observation_or_alibi>
"""


def generate_synthetic_blueprint_sample(
    seed: int,
    mystery_type: MysteryType | str | None = None,
    tone: Tone | str | None = None,
    difficulty: Difficulty | str | None = None,
) -> dict[str, Any]:
    """Generate a guaranteed-valid blueprint sample using the domain logic generator."""
    rng = random.Random(f"fabula-distillation:{seed}")
    mtype = MysteryType(mystery_type) if mystery_type is not None else rng.choice(list(MysteryType))
    tone = Tone(tone) if tone is not None else rng.choice(list(Tone))
    diff = Difficulty(difficulty) if difficulty is not None else rng.choice(list(Difficulty))

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

    # Verify through compiler
    bp = parse_dsl(dsl_text)
    compiler = BlueprintCompiler(bp, seed=seed)
    bundle = compiler.compile()
    assert compiler.verify_solvability(bundle) is True

    user_prompt = (
        f"GENERATE_CASE: type={mtype.value} tone={tone.value} difficulty={diff.value} seed={seed}"
    )

    # Return ChatML format for Unsloth / Hugging Face SFT
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


def main():
    output_dir = os.environ.get("FABULA_DATA_DIR", "data/processed")
    os.makedirs(output_dir, exist_ok=True)

    print("Generating 1,500 validated teacher blueprint samples...")
    all_samples = []
    for seed in range(1500):
        sample = generate_synthetic_blueprint_sample(seed)
        all_samples.append(sample)
        if (seed + 1) % 300 == 0:
            print(f"  Generated and verified {seed + 1}/1500 samples.")

    # Disjoint seed splits: train (1200, 80%), val (150, 10%), test (150, 10%)
    train_samples = all_samples[:1200]
    val_samples = all_samples[1200:1350]
    test_samples = all_samples[1350:1500]

    splits = {
        "blueprint_train.jsonl": train_samples,
        "blueprint_val.jsonl": val_samples,
        "blueprint_test.jsonl": test_samples,
    }

    for fname, data in splits.items():
        out_path = os.path.join(output_dir, fname)
        with open(out_path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")
        print(f"Saved {len(data)} samples to {out_path}")

    print("Distillation dataset generation complete!")


if __name__ == "__main__":
    main()
