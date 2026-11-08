"""Isolated prompt DTOs and safe per-NPC file loading."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from fabula.conversation.errors import NpcFileError
from fabula.schemas import ChatTurn, Identity, Memory, NpcFiles

_SAFE_NPC_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class PromptContext:
    """The only inputs a prompt builder may receive for one NPC."""

    identity: Identity
    memory: Memory
    chat_history: tuple[ChatTurn, ...] = field(default_factory=tuple)
    player_input: str = ""

    def __post_init__(self) -> None:
        if self.identity.id != self.memory.npc_id:
            raise ValueError("prompt identity and memory must belong to the same NPC")
        if not self.player_input.strip():
            raise ValueError("prompt player_input must not be empty")

    @classmethod
    def from_npc_files(
        cls,
        files: NpcFiles,
        chat_history: tuple[ChatTurn, ...] = (),
        player_input: str = "",
    ) -> PromptContext:
        return cls(
            identity=files.identity,
            memory=files.memory,
            chat_history=tuple(chat_history),
            player_input=player_input,
        )


def _checked_file(path: Path, parent: Path) -> Path:
    if path.is_symlink():
        raise NpcFileError(f"NPC file must not be a symlink: {path}")
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise NpcFileError(f"NPC file escapes its directory: {path}") from exc
    return path


def _read_model(path: Path, model_type: type[Identity] | type[Memory]):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise NpcFileError(f"cannot read NPC file {path}: {exc}") from exc
    try:
        return model_type.model_validate_json(text)
    except ValidationError as exc:
        raise NpcFileError(f"invalid NPC file {path}: {exc}") from exc


def load_npc_files(root: str | Path, npc_id: str) -> NpcFiles:
    """Load exactly one NPC's identity and memory, never the bundle or truth."""
    if not _SAFE_NPC_ID.fullmatch(npc_id):
        raise NpcFileError(f"unsafe NPC id {npc_id!r}")

    root_path = Path(root).resolve()
    npcs_dir = _checked_file(root_path / "npcs", root_path)
    npc_dir = _checked_file(npcs_dir / npc_id, npcs_dir)
    if not npc_dir.is_dir():
        raise NpcFileError(f"NPC directory does not exist: {npc_dir}")

    identity = _read_model(_checked_file(npc_dir / "identity.json", npc_dir), Identity)
    memory = _read_model(_checked_file(npc_dir / "memory.json", npc_dir), Memory)
    if identity.id != npc_id:
        raise NpcFileError(f"identity id {identity.id!r} does not match folder {npc_id!r}")
    if memory.npc_id != npc_id:
        raise NpcFileError(f"memory npc_id {memory.npc_id!r} does not match folder {npc_id!r}")
    return NpcFiles(identity=identity, memory=memory)
