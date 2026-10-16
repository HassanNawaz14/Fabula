"""Phase 2 - Cleaning: re-validate every row, drop duplicates, write cleaned data + report."""

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from fabula.schemas import Bundle, validate_bundle

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "skeletons.jsonl"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "data" / "reports"


def row_hash(bundle_dump: dict) -> str:
    canonical = json.dumps(bundle_dump, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_text = RAW.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in raw_text.splitlines() if line.strip()]

    kept: list[dict] = []
    invalid: list[dict] = []
    seen: set[str] = set()
    duplicates = 0

    for index, row in enumerate(rows, start=1):
        try:
            bundle = Bundle.model_validate(row["bundle"])
        except ValidationError as exc:
            invalid.append({"line": index, "stage": "schema", "error": str(exc)[:300]})
            continue
        issues = validate_bundle(bundle)
        if issues:
            invalid.append(
                {
                    "line": index,
                    "stage": "validators",
                    "error": "; ".join(f"{i.code.value}: {i.message}" for i in issues),
                }
            )
            continue
        digest = row_hash(row["bundle"])
        if digest in seen:
            duplicates += 1
            continue
        seen.add(digest)
        kept.append(row)

    out_path = PROCESSED_DIR / "clean_skeletons.jsonl"
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in kept:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    report = {
        "step": "cleaning",
        "input": str(RAW),
        "output": str(out_path),
        "rows_in": len(rows),
        "invalid_removed": len(invalid),
        "duplicates_removed": duplicates,
        "rows_out": len(kept),
        "missing_values": (
            "none possible: schemas require every field and forbid extras (extra='forbid')"
        ),
        "outliers": "bounded by schema (3-4 locations, 5-6 NPCs, 4-6 clues, minutes 0-10)",
        "invalid_details": invalid,
    }
    (REPORTS_DIR / "cleaning_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"cleaned: {len(rows)} in -> {len(kept)} out (invalid {len(invalid)}, dupes {duplicates})"
    )


if __name__ == "__main__":
    main()
