"""Phase 2 - Features: build an encoded, scaled feature table from the cleaned dataset."""

import json
from pathlib import Path

import pandas as pd

from fabula.schemas import Bundle

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "data" / "processed" / "clean_skeletons.jsonl"
PROCESSED_DIR = ROOT / "data" / "processed"

NUMERIC_COLUMNS = [
    "n_locations",
    "n_npcs",
    "n_clues",
    "n_facts",
    "n_secret_facts",
    "n_volunteer",
    "n_if_asked",
    "n_hide",
    "n_lie",
    "n_red_herrings",
    "has_cover_story",
    "window_minutes",
    "n_timeline_events",
    "n_examine_clues",
    "n_reveal_clues",
    "avg_facts_per_npc",
]


def features_from_row(row: dict) -> dict:
    bundle = Bundle.model_validate(row["bundle"])
    facts = [fact for files in bundle.npcs.values() for fact in files.memory.facts]
    window = bundle.truth.crime.time_window
    return {
        "mystery_type": bundle.world.mystery_type.value,
        "tone": bundle.world.tone.value,
        "difficulty": bundle.world.difficulty.value,
        "n_locations": len(bundle.world.locations),
        "n_npcs": len(bundle.world.npcs),
        "n_clues": len(bundle.clues.clues),
        "n_facts": len(facts),
        "n_secret_facts": sum(1 for fact in facts if fact.secret),
        "n_volunteer": sum(1 for fact in facts if fact.disclosure.value == "volunteer"),
        "n_if_asked": sum(1 for fact in facts if fact.disclosure.value == "if_asked"),
        "n_hide": sum(1 for fact in facts if fact.disclosure.value == "hide"),
        "n_lie": sum(1 for fact in facts if fact.disclosure.value == "lie"),
        "n_red_herrings": len(bundle.truth.red_herrings),
        "has_cover_story": int(any(files.memory.cover_story for files in bundle.npcs.values())),
        "window_minutes": window.end - window.start,
        "n_timeline_events": len(bundle.truth.timeline),
        "n_examine_clues": sum(
            1 for clue in bundle.clues.clues if clue.discovery.value == "examine"
        ),
        "n_reveal_clues": sum(
            1 for clue in bundle.clues.clues if clue.discovery.value == "npc_reveal"
        ),
        "avg_facts_per_npc": round(len(facts) / len(bundle.npcs), 3),
    }


def main() -> None:
    raw_text = CLEAN.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
    frame = pd.DataFrame(features_from_row(row) for row in rows)
    encoded = pd.get_dummies(frame, columns=["mystery_type", "tone", "difficulty"], dtype=int)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    encoded.to_csv(PROCESSED_DIR / "features.csv", index=False)

    scaled = encoded.copy()
    for column in NUMERIC_COLUMNS:
        span = scaled[column].max() - scaled[column].min()
        scaled[column] = (scaled[column] - scaled[column].min()) / span if span else 0.0
    scaled.to_csv(PROCESSED_DIR / "features_scaled.csv", index=False)
    print(
        f"features: {len(frame)} rows, {len(encoded.columns)} columns "
        "-> features.csv + features_scaled.csv"
    )


if __name__ == "__main__":
    main()
