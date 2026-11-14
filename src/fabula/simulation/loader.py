"""Typed, validated loading of a read-only game bundle."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from pydantic import BaseModel, ValidationError

from fabula.schemas import (
    Bundle,
    CluesDocument,
    Identity,
    Memory,
    NpcFiles,
    TruthDocument,
    WorldDocument,
    validate_bundle,
)


class BundleLoadError(ValueError):
    """The bundle is missing, malformed, or semantically invalid."""


@dataclass(frozen=True)
class LoadedBundle:
    root: Path
    world: WorldDocument
    clues: CluesDocument
    npcs: Mapping[str, NpcFiles]
    _truth: TruthDocument = field(repr=False, compare=False)

    def accusation_truth(self) -> TruthDocument:
        """Engine-only truth handle; only the accusation service should call this."""
        return self._truth


def _read_model(path: Path, model_type: type[BaseModel]) -> BaseModel:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BundleLoadError(f"cannot read bundle file {path}: {exc}") from exc
    try:
        return model_type.model_validate_json(text)
    except ValidationError as exc:
        raise BundleLoadError(f"invalid bundle file {path}: {exc}") from exc


def _checked_path(path: Path, parent: Path) -> Path:
    if path.is_symlink():
        raise BundleLoadError(f"bundle entry must not be a symlink: {path}")
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise BundleLoadError(f"bundle entry escapes its directory: {path}") from exc
    return path


def load_bundle(root: str | Path) -> LoadedBundle:
    root_path = Path(root)
    if not root_path.is_dir():
        raise BundleLoadError(f"bundle directory does not exist: {root_path}")

    world_path = _checked_path(root_path / "world.json", root_path)
    truth_path = _checked_path(root_path / "truth.json", root_path)
    clues_path = _checked_path(root_path / "clues.json", root_path)
    world = _read_model(world_path, WorldDocument)
    truth = _read_model(truth_path, TruthDocument)
    clues = _read_model(clues_path, CluesDocument)

    npcs_dir = _checked_path(root_path / "npcs", root_path)
    if not npcs_dir.is_dir():
        raise BundleLoadError(f"bundle is missing the npcs/ directory: {npcs_dir}")

    npcs: dict[str, NpcFiles] = {}
    for npc_dir in sorted(npcs_dir.iterdir()):
        if not npc_dir.is_dir():
            raise BundleLoadError(f"unexpected file inside npcs/: {npc_dir.name}")
        _checked_path(npc_dir, npcs_dir)
        identity = _read_model(_checked_path(npc_dir / "identity.json", npc_dir), Identity)
        memory = _read_model(_checked_path(npc_dir / "memory.json", npc_dir), Memory)
        npcs[npc_dir.name] = NpcFiles(identity=identity, memory=memory)

    try:
        bundle = Bundle(world=world, truth=truth, clues=clues, npcs=npcs)
    except (ValidationError, ValueError) as exc:
        raise BundleLoadError(f"bundle cross-references are invalid: {exc}") from exc

    issues = validate_bundle(bundle)
    if issues:
        detail = "; ".join(f"{issue.code}: {issue.message}" for issue in issues)
        raise BundleLoadError(f"bundle failed semantic validation: {detail}")

    return LoadedBundle(
        root=root_path.resolve(),
        world=bundle.world,
        clues=bundle.clues,
        npcs=MappingProxyType(dict(bundle.npcs)),
        _truth=bundle.truth,
    )
