from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from fabula.schemas import Bundle
from fabula.simulation import LoadedBundle, load_bundle
from fabula.training_data import generate_skeleton


def write_bundle_files(bundle: Bundle, root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "world.json").write_text(
        bundle.world.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (root / "truth.json").write_text(
        bundle.truth.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (root / "clues.json").write_text(
        bundle.clues.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    for npc_id, files in bundle.npcs.items():
        npc_dir = root / "npcs" / npc_id
        npc_dir.mkdir(parents=True)
        (npc_dir / "identity.json").write_text(
            files.identity.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        (npc_dir / "memory.json").write_text(
            files.memory.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
    return root


def directory_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


@pytest.fixture
def sample_bundle() -> Bundle:
    return generate_skeleton("theft", 3, tone="cozy", difficulty="easy")


@pytest.fixture
def bundle_dir(tmp_path: Path, sample_bundle: Bundle) -> Path:
    return write_bundle_files(sample_bundle, tmp_path / "bundle")


@pytest.fixture
def loaded(bundle_dir: Path) -> LoadedBundle:
    return load_bundle(bundle_dir)


@pytest.fixture
def bundle_writer(tmp_path: Path):
    def _write(bundle: Bundle, name: str = "bundle") -> Path:
        return write_bundle_files(bundle, tmp_path / name)

    return _write


@pytest.fixture
def digest():
    return directory_digest
