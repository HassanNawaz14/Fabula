"""Phase 2 - Collection: generate the skeleton dataset and write the evidence log."""

import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

from fabula import __version__
from fabula.training_data.build_skeleton_dataset import write_dataset

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "raw"
REPORTS_DIR = ROOT / "data" / "reports"


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC).isoformat(timespec="seconds")
    clock = time.perf_counter()
    manifest = write_dataset(OUT_DIR, seeds_per_type=100)
    duration = round(time.perf_counter() - clock, 3)

    log = {
        "step": "collection",
        "method": "synthetic symbolic generation (no scraping, no downloaded datasets - HG-17)",
        "command": "python data/scripts/collect.py",
        "started_at": started,
        "duration_seconds": duration,
        "python": platform.python_version(),
        "generator_version": __version__,
        "output": str(OUT_DIR / "skeletons.jsonl"),
        "total_rows": manifest["total_rows"],
        "rejected_rows": manifest["rejected_rows"],
        "counts_by_type": manifest["counts_by_type"],
        "counts_by_tone": manifest["counts_by_tone"],
        "counts_by_difficulty": manifest["counts_by_difficulty"],
        "jsonl_sha256": manifest["jsonl_sha256"],
    }
    (REPORTS_DIR / "collection_log.json").write_text(
        json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (REPORTS_DIR / "dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"collected {manifest['total_rows']} skeletons "
        f"({manifest['rejected_rows']} rejected) in {duration}s"
    )


if __name__ == "__main__":
    main()
