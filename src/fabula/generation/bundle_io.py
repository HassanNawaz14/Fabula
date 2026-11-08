"""Canonical bundle file layout and atomic on-disk publication."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from fabula.generation.errors import BundlePublishError
from fabula.schemas import Bundle

_UNSAFE_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe_component(value: str, where: str) -> str:
    if value in {"", ".", ".."} or _UNSAFE_PATH_CHARS.search(value) is not None:
        raise BundlePublishError(f"unsafe {where} id for a bundle path: {value!r}")
    return value


def _dump(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"


def bundle_files(bundle: Bundle) -> dict[str, str]:
    """Return the full bundle as relative POSIX-style paths mapped to UTF-8 text."""
    files = {
        "world.json": _dump(bundle.world),
        "truth.json": _dump(bundle.truth),
        "clues.json": _dump(bundle.clues),
    }
    for npc_id, npc_files in bundle.npcs.items():
        safe_id = _safe_component(npc_id, "npc")
        files[f"npcs/{safe_id}/identity.json"] = _dump(npc_files.identity)
        files[f"npcs/{safe_id}/memory.json"] = _dump(npc_files.memory)
    return files


def write_bundle_files(bundle: Bundle, root: Path) -> None:
    """Write every bundle file under an existing root directory."""
    for relative_path, text in bundle_files(bundle).items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def publish_bundle(bundle: Bundle, output_dir: Path) -> Path:
    """Publish a validated bundle atomically, replacing any previous bundle.

    Files are written to a sibling temporary directory first. The swap keeps
    the previous bundle intact when writing or validation fails, and the
    temporary directory is always removed.
    """
    target = output_dir.resolve()
    parent = target.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BundlePublishError(f"cannot create bundle parent {parent}: {exc}") from exc

    temp_dir = parent / f".{target.name}.tmp-{uuid4().hex}"
    backup_dir = parent / f".{target.name}.bak-{uuid4().hex}"
    try:
        temp_dir.mkdir()
        write_bundle_files(bundle, temp_dir)
        if target.exists():
            target.rename(backup_dir)
        try:
            temp_dir.rename(target)
        except OSError:
            if backup_dir.exists() and not target.exists():
                backup_dir.rename(target)
            raise
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
    except BundlePublishError:
        raise
    except OSError as exc:
        raise BundlePublishError(f"cannot publish bundle to {target}: {exc}") from exc
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        if backup_dir.exists() and target.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
    return target
