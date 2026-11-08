from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import pytest

from fabula.simulation import BundleLoadError, load_bundle


def test_load_bundle_matches_source_files(loaded, sample_bundle) -> None:
    assert loaded.world == sample_bundle.world
    assert loaded.clues == sample_bundle.clues
    assert set(loaded.npcs) == set(sample_bundle.npcs)
    for npc_id, files in loaded.npcs.items():
        assert files.identity == sample_bundle.npcs[npc_id].identity
        assert files.memory == sample_bundle.npcs[npc_id].memory


def test_truth_is_only_reachable_through_accusation_handle(loaded, sample_bundle) -> None:
    assert loaded.accusation_truth() == sample_bundle.truth
    assert not hasattr(loaded, "truth")
    assert all(field.name != "truth" for field in dataclasses.fields(loaded))


def test_missing_file_is_rejected(bundle_dir: Path) -> None:
    (bundle_dir / "world.json").unlink()
    with pytest.raises(BundleLoadError):
        load_bundle(bundle_dir)


def test_missing_npc_file_is_rejected(bundle_dir: Path) -> None:
    first_npc = sorted((bundle_dir / "npcs").iterdir())[0]
    (first_npc / "memory.json").unlink()
    with pytest.raises(BundleLoadError):
        load_bundle(bundle_dir)


def test_unexpected_entry_in_npcs_is_rejected(bundle_dir: Path) -> None:
    (bundle_dir / "npcs" / "stray.txt").write_text("not a bundle file", encoding="utf-8")
    with pytest.raises(BundleLoadError):
        load_bundle(bundle_dir)


def test_symlinked_entry_is_rejected(bundle_dir: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = bundle_dir / "npcs" / "shadow"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is not permitted on this platform")
    with pytest.raises(BundleLoadError):
        load_bundle(bundle_dir)


def test_unknown_schema_version_is_rejected(bundle_dir: Path) -> None:
    path = bundle_dir / "world.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = "9.9"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BundleLoadError):
        load_bundle(bundle_dir)


def test_cross_stage_mismatch_is_rejected(bundle_dir: Path, sample_bundle) -> None:
    wrong_type = "murder" if sample_bundle.truth.crime.type.value != "murder" else "theft"
    path = bundle_dir / "truth.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["crime"]["type"] = wrong_type
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BundleLoadError):
        load_bundle(bundle_dir)


def test_loading_does_not_modify_the_bundle(bundle_dir: Path, digest) -> None:
    before = digest(bundle_dir)
    load_bundle(bundle_dir)
    assert digest(bundle_dir) == before


def test_simulation_package_has_no_ui_imports() -> None:
    import fabula.simulation  # noqa: F401

    assert "pygame" not in sys.modules
    assert "arcade" not in sys.modules
