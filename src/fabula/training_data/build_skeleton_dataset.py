import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from fabula import __version__
from fabula.schemas import Difficulty, MysteryType, Tone, validate_bundle
from fabula.training_data import generate_skeleton

GENERATOR_ID = "fabula-skeletons-v1"
TONES = list(Tone)
DIFFICULTIES = list(Difficulty)


def build_rows(seeds_per_type: int) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    rejected: list[dict] = []
    line = 0
    for mystery_type in MysteryType:
        for seed in range(seeds_per_type):
            tone = TONES[seed % len(TONES)]
            difficulty = DIFFICULTIES[(seed // len(TONES)) % len(DIFFICULTIES)]
            line += 1
            try:
                bundle = generate_skeleton(mystery_type, seed, tone=tone, difficulty=difficulty)
                issues = validate_bundle(bundle)
                if issues:
                    raise ValueError("; ".join(f"{i.code.value}: {i.message}" for i in issues))
                rows.append(
                    {
                        "mystery_type": mystery_type.value,
                        "seed": seed,
                        "tone": tone.value,
                        "difficulty": difficulty.value,
                        "provenance": {
                            "generator": GENERATOR_ID,
                            "generator_version": __version__,
                            "schema_version": bundle.schema_version,
                            "validated": True,
                        },
                        "bundle": bundle.model_dump(mode="json"),
                    }
                )
            except Exception as exc:
                rejected.append(
                    {
                        "line": line,
                        "mystery_type": mystery_type.value,
                        "seed": seed,
                        "error": str(exc),
                    }
                )
    return rows, rejected


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_dataset(out_dir: Path, seeds_per_type: int) -> dict:
    rows, rejected = build_rows(seeds_per_type)
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "skeletons.jsonl"
    tmp_path = out_dir / "skeletons.jsonl.tmp"
    with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    tmp_path.replace(jsonl_path)

    manifest = {
        "generator": GENERATOR_ID,
        "generator_version": __version__,
        "seeds_per_type": seeds_per_type,
        "total_rows": len(rows),
        "rejected_rows": len(rejected),
        "rejected": rejected,
        "counts_by_type": dict(Counter(row["mystery_type"] for row in rows)),
        "counts_by_tone": dict(Counter(row["tone"] for row in rows)),
        "counts_by_difficulty": dict(Counter(row["difficulty"] for row in rows)),
        "jsonl": jsonl_path.name,
        "jsonl_sha256": _sha256(jsonl_path),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    manifest_path = out_dir / "skeleton_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the balanced Fabula skeleton dataset.")
    parser.add_argument("--seeds-per-type", type=int, default=100)
    parser.add_argument("--out-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()
    manifest = write_dataset(args.out_dir, args.seeds_per_type)
    print(
        f"wrote {manifest['total_rows']} rows "
        f"({manifest['rejected_rows']} rejected) -> {args.out_dir / manifest['jsonl']}"
    )


if __name__ == "__main__":
    main()
