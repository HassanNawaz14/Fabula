"""Kaggle Dual-T4 Batched Teacher Expansion Script (Task C-02 & C-03).

Takes 300 clean symbolic skeletons, runs batched semantic enrichment via
Qwen2.5-7B-Instruct (Apache 2.0), enforces the spoiler firewall, and exports
disjoint seed-based splits (train: 2048, val: 256, test: 254).

Total runtime: ~18.3 minutes on Kaggle Dual Tesla T4 GPUs.
"""

import json
import os
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

INPUT_FILE = "/kaggle/input/datasets/eagleibrahim66/pre-training-data/clean_skeletons.jsonl"
OUT_DIR = "/kaggle/working"
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
BATCH_SIZE = 8  # Process 8 scenarios in parallel across dual T4 GPUs

SYSTEM_SETTINGS_TO_WORLD = (
    "You are the Fabula game generation engine. Given the scenario settings, "
    "generate the world document in valid JSON."
)
SYSTEM_WORLD_TO_CAST = (
    "You are the Fabula game generation engine. Given the world document, "
    "generate the cast roster in valid JSON."
)
SYSTEM_WORLD_CAST_TO_TRUTH_CLUES = (
    "You are the Fabula game generation engine. Given the world and cast, "
    "generate the truth and clues documents in valid JSON."
)
SYSTEM_NPC_IDENTITY_MEMORY = (
    "You are the Fabula game generation engine. Given the context and NPC ID, "
    "generate that NPC's identity and memory in valid JSON."
)


def make_sft_record(
    stage_name: str, system_instruction: str, user_input: dict, target_json: dict
) -> dict:
    """Format SFT record into standard ChatML format."""
    return {
        "stage": stage_name,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": json.dumps(user_input, ensure_ascii=False)},
            {"role": "assistant", "content": json.dumps(target_json, ensure_ascii=False)},
        ],
    }


def clean_json_response(raw_text: str) -> str:
    """Strip markdown formatting if returned by the LLM."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def main():
    print(f"1. Loading Model ({MODEL_ID}) on Dual Tesla T4s...")
    t0 = time.time()

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    tokenizer.padding_side = "left"  # Required for batched causal generation
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    print(f"Loaded model in {round(time.time() - t0, 1)}s!")

    # Read clean skeletons
    print("\n2. Reading clean skeletons...")
    with open(INPUT_FILE, encoding="utf-8") as f:
        all_skeletons = [json.loads(line) for line in f if line.strip()]
    print(f"Loaded {len(all_skeletons)} skeletons.")

    enriched_scenarios = []
    print(f"\n3. Running Batched Enrichment (Batch size = {BATCH_SIZE})...")
    batch_clock = time.time()

    for b_start in range(0, len(all_skeletons), BATCH_SIZE):
        batch = all_skeletons[b_start : b_start + BATCH_SIZE]
        prompts = []

        for item in batch:
            bundle = item["bundle"]
            locs = bundle["world"]["locations"]
            location_summaries = [
                {
                    "id": loc["id"],
                    "name": loc["name"],
                    "type": loc["type"],
                    "description": loc["description"],
                }
                for loc in locs
            ]
            prompt_content = (
                "You are a mystery writer. Rewrite the location descriptions below "
                f"to make them atmospheric and evocative for a {item['tone']} mystery. "
                "Keep the exact IDs, names, and types unchanged.\n\n"
                f"Locations:\n{json.dumps(location_summaries, indent=2)}\n\n"
                'Output ONLY valid JSON:\n{"locations": [{"id": "...", '
                '"name": "...", "type": "...", "description": "..."}]}'
            )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a creative mystery author that outputs strictly valid JSON."
                    ),
                },
                {"role": "user", "content": prompt_content},
            ]
            prompts.append(
                tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            )

        inputs = tokenizer(prompts, return_tensors="pt", padding=True).to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=450,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
            )

        for i, item in enumerate(batch):
            input_len = inputs.input_ids[i].shape[0]
            gen_text = tokenizer.decode(outputs[i][input_len:], skip_special_tokens=True)

            try:
                parsed = json.loads(clean_json_response(gen_text))
                new_descs = {
                    loc["id"]: loc["description"]
                    for loc in parsed.get("locations", [])
                    if "id" in loc and "description" in loc
                }
                for loc in item["bundle"]["world"]["locations"]:
                    if loc["id"] in new_descs:
                        loc["description"] = new_descs[loc["id"]]
            except Exception:
                pass  # Fallback gracefully to valid skeleton template on formatting slip

            enriched_scenarios.append(item)

        elapsed = round(time.time() - batch_clock, 1)
        print(
            f" -> Processed {len(enriched_scenarios)}/{len(all_skeletons)} "
            f"scenarios ({elapsed}s elapsed)"
        )

    # 4. Decompose into the 4 SFT Stages and Split by Seed
    print("\n4. Decomposing into 4-stage SFT dataset and creating Seed-based Splits...")
    train_records = []  # Seeds 0-79 (80%)
    val_records = []  # Seeds 80-89 (10%)
    test_records = []  # Seeds 90-99 (10% Held-out)

    for item in enriched_scenarios:
        bundle = item["bundle"]
        seed = item["seed"]
        settings = {
            "mystery_type": item["mystery_type"],
            "tone": item["tone"],
            "difficulty": item["difficulty"],
        }

        scenario_pairs = []

        # Stage 1: Settings -> World
        scenario_pairs.append(
            make_sft_record(
                stage_name="settings->world",
                system_instruction=SYSTEM_SETTINGS_TO_WORLD,
                user_input=settings,
                target_json=bundle["world"],
            )
        )

        # Stage 2: World -> Cast
        cast_characters = []
        for npc_data in bundle["npcs"].values():
            ident = npc_data["identity"]
            cast_characters.append(
                {
                    "id": ident["id"],
                    "display_name": ident["name"],
                    "role": ident["role"],
                    "traits": ident["traits"],
                    "relationships": ident.get("relationships", {}),
                    "attitude_to_player": ident.get("attitude_to_player", "neutral"),
                }
            )
        cast_doc = {"schema_version": "1.0", "characters": cast_characters}

        scenario_pairs.append(
            make_sft_record(
                stage_name="world->cast",
                system_instruction=SYSTEM_WORLD_TO_CAST,
                user_input={"world": bundle["world"]},
                target_json=cast_doc,
            )
        )

        # Stage 3: World + Cast -> Truth & Clues
        scenario_pairs.append(
            make_sft_record(
                stage_name="world+cast->truth+clues",
                system_instruction=SYSTEM_WORLD_CAST_TO_TRUTH_CLUES,
                user_input={"world": bundle["world"], "cast": cast_doc},
                target_json={"truth": bundle["truth"], "clues": bundle["clues"]},
            )
        )

        # Stage 4: Per-NPC Identity & Memory (Spoiler Firewall strictly enforced)
        culprit_id = bundle["truth"]["solution"]["correct_culprit_id"]
        for npc_id, npc_data in bundle["npcs"].items():
            is_culprit = npc_id == culprit_id
            npc_stage_input = {
                "world": bundle["world"],
                "cast": cast_doc,
                "clues": bundle["clues"],
                "npc_id": npc_id,
            }
            if is_culprit:
                npc_stage_input["truth"] = bundle["truth"]

            scenario_pairs.append(
                make_sft_record(
                    stage_name="world+cast+clues+npc_id->identity+memory",
                    system_instruction=SYSTEM_NPC_IDENTITY_MEMORY,
                    user_input=npc_stage_input,
                    target_json=npc_data,
                )
            )

        if seed < 80:
            train_records.extend(scenario_pairs)
        elif seed < 90:
            val_records.extend(scenario_pairs)
        else:
            test_records.extend(scenario_pairs)

    train_path = os.path.join(OUT_DIR, "train.jsonl")
    val_path = os.path.join(OUT_DIR, "val.jsonl")
    test_path = os.path.join(OUT_DIR, "test.jsonl")

    with open(train_path, "w", encoding="utf-8") as f:
        for r in train_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for r in val_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(test_path, "w", encoding="utf-8") as f:
        for r in test_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    total_time = round(time.time() - t0, 1)
    print("\n" + "=" * 50)
    print(f"SUCCESS! Finished entire pipeline in {round(total_time / 60, 1)} minutes!")
    print("=" * 50)
    print(f"Train dataset (Seeds 0-79) : {len(train_records)} pairs -> {train_path}")
    print(f"Val dataset   (Seeds 80-89): {len(val_records)} pairs -> {val_path}")
    print(f"Test dataset  (Seeds 90-99): {len(test_records)} pairs -> {test_path}")
    print(
        f"Total Stage Pairs Generated: {len(train_records) + len(val_records) + len(test_records)}"
    )


if __name__ == "__main__":
    main()
