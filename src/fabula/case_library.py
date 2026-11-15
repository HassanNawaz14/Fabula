"""Ready-to-play case bundles: discovery, validation, and installation."""

from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from fabula.schemas import WorldDocument
from fabula.simulation.loader import BundleLoadError, LoadedBundle, load_bundle

DEFAULT_LIBRARY_DIR = Path("bundles") / "library"


@dataclass(frozen=True)
class CaseSummary:
    """Just enough of a bundle to show it in the case picker."""

    case_id: str
    path: Path
    title: str
    town_name: str
    mystery_type: str
    tone: str
    difficulty: str
    intro_text: str = ""


def library_root(
    root: str | Path | None = None, *, environ: Mapping[str, str] | None = None
) -> Path:
    if root is not None:
        return Path(root)
    env = os.environ if environ is None else environ
    return Path(env.get("FABULA_LIBRARY_DIR", str(DEFAULT_LIBRARY_DIR)))


def _read_summary(case_dir: Path) -> CaseSummary | None:
    world_path = case_dir / "world.json"
    try:
        world = WorldDocument.model_validate_json(world_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError):
        return None
    return CaseSummary(
        case_id=case_dir.name,
        path=case_dir,
        title=world.title,
        town_name=world.town_name,
        mystery_type=world.mystery_type.value,
        tone=world.tone.value,
        difficulty=world.difficulty.value,
        intro_text=world.intro_text,
    )


def discover_cases(root: str | Path | None = None) -> list[CaseSummary]:
    """List valid-looking bundles, newest first, skipping broken folders."""
    base = library_root(root)
    if not base.is_dir():
        return []
    found: list[tuple[float, CaseSummary]] = []
    for case_dir in base.iterdir():
        if not case_dir.is_dir() or case_dir.name.startswith("."):
            continue
        summary = _read_summary(case_dir)
        if summary is None:
            continue
        try:
            modified = (case_dir / "world.json").stat().st_mtime
        except OSError:
            modified = 0.0
        found.append((modified, summary))
    found.sort(key=lambda item: (-item[0], item[1].case_id))
    return [summary for _modified, summary in found]


def validate_case(path: str | Path) -> LoadedBundle:
    """Fully validate a bundle directory before it is offered to a player."""
    return load_bundle(path)


def unique_case_id(prefix: str, root: str | Path | None = None) -> str:
    base = library_root(root)
    candidate = prefix
    index = 2
    while (base / candidate).exists():
        candidate = f"{prefix}_{index}"
        index += 1
    return candidate


def install_case(
    source: str | Path,
    case_id: str,
    *,
    root: str | Path | None = None,
) -> Path:
    """Validate a freshly downloaded bundle and copy it into the library."""
    source_path = Path(source)
    validate_case(source_path)
    base = library_root(root)
    base.mkdir(parents=True, exist_ok=True)
    target = base / unique_case_id(case_id, base)
    shutil.copytree(source_path, target)
    return target


__all__ = [
    "CaseSummary",
    "DEFAULT_LIBRARY_DIR",
    "BundleLoadError",
    "discover_cases",
    "install_case",
    "library_root",
    "unique_case_id",
    "validate_case",
]
