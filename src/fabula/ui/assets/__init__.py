"""Procedural asset libraries used by the Fabula UI."""

from __future__ import annotations

from fabula.ui.assets.npcs import NPC_LOOKS, NpcLook, render_npc, resolve_look
from fabula.ui.assets.places import (
    PLACE_ASSETS,
    PlaceAsset,
    get_place_asset,
    place_variant,
    render_place,
)

__all__ = [
    "NPC_LOOKS",
    "PLACE_ASSETS",
    "NpcLook",
    "PlaceAsset",
    "get_place_asset",
    "place_variant",
    "render_npc",
    "render_place",
    "resolve_look",
]
