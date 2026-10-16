import json
from pathlib import Path

from fabula.schemas import Bundle
from fabula.training_data.build_skeleton_dataset import build_rows, write_dataset


def test_build_rows_is_balanced_and_complete() -> None:
    rows, rejected = build_rows(seeds_per_type=3)
    assert rejected == []
    assert len(rows) == 9
    for row in rows:
        Bundle.model_validate(row["bundle"])
        assert row["provenance"]["validated"] is True


def test_write_dataset_is_reproducible(tmp_path: Path) -> None:
    first = write_dataset(tmp_path / "a", seeds_per_type=2)
    second = write_dataset(tmp_path / "b", seeds_per_type=2)
    assert (tmp_path / "a" / "skeletons.jsonl").read_bytes() == (
        tmp_path / "b" / "skeletons.jsonl"
    ).read_bytes()
    assert first["jsonl_sha256"] == second["jsonl_sha256"]
    assert first["total_rows"] == 6
    assert first["counts_by_type"] == {"theft": 2, "disappearance": 2, "murder": 2}


def test_manifest_counts_reconcile(tmp_path: Path) -> None:
    manifest = write_dataset(tmp_path, seeds_per_type=4)
    lines = (tmp_path / "skeletons.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == manifest["total_rows"] == sum(manifest["counts_by_type"].values())
    recorded = json.loads((tmp_path / "skeleton_manifest.json").read_text(encoding="utf-8"))
    assert recorded["jsonl_sha256"] == manifest["jsonl_sha256"]
