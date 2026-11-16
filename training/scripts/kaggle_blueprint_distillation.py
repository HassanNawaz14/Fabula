"""Kaggle Teacher Distillation Script for Fabula Compact Blueprints.

Generates 1,500 diverse mystery configurations, expands them via Teacher LLM
into Compact Blueprint DSL, verifies them through the symbolic compiler,
and partitions them into disjoint train/val/test splits for student SFT.
"""

from __future__ import annotations

import json
import os

from fabula.generation.synthetic_blueprint import generate_synthetic_blueprint_sample

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
