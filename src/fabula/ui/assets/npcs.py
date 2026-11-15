"""Procedural avatar artwork for every NPC role.

A role is described by a small ``NpcLook`` recipe (outfit colours plus a hat,
hair style, accessory, and optional apron/glasses/scarf). The renderer composes
those parts into a full character; a per-NPC seed varies skin, hair colour, and
small palette shifts so two vendors still look like different people.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import pygame

from fabula.ui.assets.common import (
    Color,
    Frame,
    glow,
    hash_index,
    shade,
    shadow,
)

SkinPalette = tuple[Color, ...]

_SKIN_TONES: SkinPalette = (
    (248, 214, 180),
    (232, 190, 150),
    (206, 156, 116),
    (170, 118, 82),
    (128, 88, 62),
    (98, 66, 48),
)

_HAIR_COLORS: tuple[Color, ...] = (
    (52, 40, 32),
    (96, 64, 40),
    (32, 32, 36),
    (146, 106, 60),
    (178, 168, 156),
    (110, 52, 40),
)


@dataclass(frozen=True)
class NpcLook:
    key: str
    label: str
    clothing: Color
    accent: Color
    hat: str = "none"
    hair: str = "short"
    accessory: str = "none"
    apron: Color | None = None
    glasses: bool = False
    scarf: bool = False


NPC_LOOKS: dict[str, NpcLook] = {
    "market_vendor": NpcLook(
        "market_vendor",
        "Market vendor",
        clothing=(126, 150, 96),
        accent=(196, 156, 76),
        hat="cap",
        accessory="basket",
        apron=(198, 168, 120),
    ),
    "librarian": NpcLook(
        "librarian",
        "Librarian",
        clothing=(108, 86, 130),
        accent=(214, 184, 112),
        hair="bun",
        accessory="book",
        glasses=True,
        scarf=True,
    ),
    "coach_driver": NpcLook(
        "coach_driver",
        "Coach driver",
        clothing=(122, 92, 64),
        accent=(176, 132, 70),
        hat="cap",
        accessory="crop",
        scarf=True,
    ),
    "baker": NpcLook(
        "baker",
        "Baker",
        clothing=(232, 226, 212),
        accent=(188, 128, 78),
        hat="chef",
        hair="short",
        accessory="bread",
        apron=(238, 232, 218),
    ),
    "carpenter": NpcLook(
        "carpenter",
        "Carpenter",
        clothing=(156, 118, 76),
        accent=(96, 76, 54),
        hat="cap",
        accessory="hammer",
        apron=(112, 86, 58),
    ),
    "herbalist": NpcLook(
        "herbalist",
        "Herbalist",
        clothing=(84, 122, 78),
        accent=(214, 168, 92),
        hat="hood",
        hair="long",
        accessory="flowers",
        scarf=True,
    ),
    "night_watchman": NpcLook(
        "night_watchman",
        "Night watchman",
        clothing=(58, 66, 96),
        accent=(208, 176, 96),
        hat="brim",
        hair="short",
        accessory="lantern",
        scarf=True,
    ),
    "tea_house_keeper": NpcLook(
        "tea_house_keeper",
        "Tea-house keeper",
        clothing=(74, 132, 126),
        accent=(216, 170, 104),
        hair="bun",
        accessory="teapot",
        apron=(232, 220, 196),
    ),
    "stable_hand": NpcLook(
        "stable_hand",
        "Stable hand",
        clothing=(138, 104, 68),
        accent=(198, 172, 92),
        hat="straw",
        hair="short",
        accessory="pitchfork",
        apron=(150, 118, 82),
    ),
    "schoolteacher": NpcLook(
        "schoolteacher",
        "Schoolteacher",
        clothing=(70, 84, 118),
        accent=(220, 190, 120),
        hair="bun",
        accessory="book",
        glasses=True,
        scarf=True,
    ),
    "fishmonger": NpcLook(
        "fishmonger",
        "Fishmonger",
        clothing=(86, 112, 128),
        accent=(204, 176, 112),
        hat="bandana",
        accessory="fish",
        apron=(200, 210, 208),
    ),
    "clocksmith": NpcLook(
        "clocksmith",
        "Clocksmith",
        clothing=(104, 84, 96),
        accent=(208, 172, 88),
        hat="cap",
        hair="short",
        accessory="clock",
        apron=(88, 72, 62),
        glasses=True,
    ),
    "detective": NpcLook(
        "detective",
        "Detective",
        clothing=(92, 82, 78),
        accent=(198, 158, 82),
        hat="fedora",
        hair="short",
        accessory="magnifier",
    ),
    "villager": NpcLook(
        "villager",
        "Villager",
        clothing=(124, 124, 116),
        accent=(178, 152, 104),
        hair="short",
        accessory="none",
    ),
}

_ROLE_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("vendor", "market_vendor"),
    ("market", "market_vendor"),
    ("librarian", "librarian"),
    ("library", "librarian"),
    ("coach", "coach_driver"),
    ("driver", "coach_driver"),
    ("baker", "baker"),
    ("bakery", "baker"),
    ("carpenter", "carpenter"),
    ("herbalist", "herbalist"),
    ("watch", "night_watchman"),
    ("guard", "night_watchman"),
    ("police", "night_watchman"),
    ("tea", "tea_house_keeper"),
    ("stable", "stable_hand"),
    ("teacher", "schoolteacher"),
    ("school", "schoolteacher"),
    ("fish", "fishmonger"),
    ("clock", "clocksmith"),
    ("detective", "detective"),
    ("inspector", "detective"),
    ("investigator", "detective"),
)


def resolve_look(role: str) -> NpcLook:
    """Map a free-form role string onto the closest avatar recipe."""
    text = role.strip().lower()
    best_key: str | None = None
    best_length = -1
    for keyword, key in _ROLE_KEYWORDS:
        if keyword in text and len(keyword) > best_length:
            best_key = key
            best_length = len(keyword)
    return NPC_LOOKS.get(best_key, NPC_LOOKS["villager"])


def _draw_shoes(frame: Frame) -> None:
    frame.ellipse((52, 44, 40), 0.33, 0.885, 0.16, 0.055)
    frame.ellipse((52, 44, 40), 0.53, 0.885, 0.16, 0.055)


def _draw_legs(frame: Frame, clothing: Color) -> None:
    trousers = shade(clothing, 0.62)
    frame.rect(trousers, 0.355, 0.645, 0.125, 0.245, radius=0.025)
    frame.rect(trousers, 0.52, 0.645, 0.125, 0.245, radius=0.025)
    frame.rect(shade(trousers, 0.82), 0.355, 0.645, 0.055, 0.245, radius=0.025)
    frame.rect(shade(trousers, 0.82), 0.52, 0.645, 0.055, 0.245, radius=0.025)
    _draw_shoes(frame)


def _draw_body(frame: Frame, look: NpcLook, skin: Color) -> None:
    outfit = look.clothing
    # Tapered coat with soft shoulders.
    frame.rect(outfit, 0.285, 0.30, 0.43, 0.37, radius=0.07)
    frame.ellipse(shade(outfit, 0.98), 0.25, 0.29, 0.50, 0.09)
    frame.polygon(shade(outfit, 1.1), [(0.405, 0.30), (0.50, 0.345), (0.595, 0.30), (0.50, 0.36)])
    frame.rect(shade(outfit, 0.72), 0.27, 0.652, 0.46, 0.032, radius=0.012)
    frame.rect(look.accent, 0.31, 0.545, 0.38, 0.045, radius=0.012)
    frame.rect(shade(look.accent, 0.7), 0.47, 0.535, 0.06, 0.065, radius=0.008)
    frame.circle(shade(outfit, 0.7), 0.50, 0.425, 0.012)
    frame.circle(shade(outfit, 0.7), 0.50, 0.485, 0.012)

    if look.apron is not None:
        frame.rect(look.apron, 0.295, 0.435, 0.41, 0.255, radius=0.025)
        frame.rect(shade(look.apron, 0.88), 0.295, 0.435, 0.41, 0.255, radius=0.025, width=0.004)
        frame.rect(shade(look.apron, 1.04), 0.405, 0.345, 0.19, 0.10, radius=0.018)
        frame.rect(shade(look.apron, 0.88), 0.405, 0.345, 0.19, 0.10, radius=0.018, width=0.004)
        frame.line(shade(look.apron, 0.86), (0.405, 0.36), (0.325, 0.345), 0.012)
        frame.line(shade(look.apron, 0.86), (0.595, 0.36), (0.675, 0.345), 0.012)

    # Sleeves angled slightly outward, with cuffs and hands.
    frame.polygon(
        shade(outfit, 0.9),
        [(0.17, 0.35), (0.285, 0.315), (0.30, 0.585), (0.205, 0.625)],
    )
    frame.polygon(
        shade(outfit, 0.9),
        [(0.83, 0.35), (0.715, 0.315), (0.70, 0.585), (0.795, 0.625)],
    )
    frame.rect(shade(outfit, 0.82), 0.198, 0.565, 0.09, 0.032, radius=0.008)
    frame.rect(shade(outfit, 0.82), 0.712, 0.565, 0.09, 0.032, radius=0.008)
    frame.circle(skin, 0.215, 0.625, 0.045)
    frame.circle(skin, 0.785, 0.625, 0.045)


def _draw_head(frame: Frame, look: NpcLook, skin: Color, hair: Color) -> None:
    frame.rect(skin, 0.45, 0.26, 0.10, 0.06, radius=0.015)
    frame.circle(shade(skin, 0.9), 0.30, 0.175, 0.042)
    frame.circle(shade(skin, 0.9), 0.70, 0.175, 0.042)
    frame.circle(skin, 0.50, 0.17, 0.19)
    frame.circle(shade(skin, 1.08), 0.43, 0.14, 0.09)

    _draw_hair(frame, look.hair, hair)

    # Eyes, brows, nose, mouth
    frame.circle((52, 44, 42), 0.435, 0.175, 0.019)
    frame.circle((52, 44, 42), 0.565, 0.175, 0.019)
    frame.circle((250, 250, 248), 0.428, 0.170, 0.006)
    frame.circle((250, 250, 248), 0.558, 0.170, 0.006)
    frame.line(shade(hair, 0.9), (0.395, 0.145), (0.465, 0.140), 0.008)
    frame.line(shade(hair, 0.9), (0.535, 0.140), (0.605, 0.145), 0.008)
    frame.line(shade(skin, 0.78), (0.50, 0.185), (0.485, 0.207), 0.006)
    frame.line((136, 76, 72), (0.455, 0.232), (0.545, 0.232), 0.007)
    frame.line(shade(skin, 0.85), (0.47, 0.245), (0.53, 0.245), 0.004)

    if look.glasses:
        pygame.draw.circle(
            frame.surface,
            (56, 48, 44),
            frame.pt(0.435, 0.175),
            frame.unit(0.052),
            frame.unit(0.008),
        )
        pygame.draw.circle(
            frame.surface,
            (56, 48, 44),
            frame.pt(0.565, 0.175),
            frame.unit(0.052),
            frame.unit(0.008),
        )
        frame.line((56, 48, 44), (0.485, 0.172), (0.515, 0.172), 0.006)

    if look.scarf:
        frame.ellipse(look.accent, 0.34, 0.255, 0.32, 0.065)
        frame.polygon(
            shade(look.accent, 0.88), [(0.55, 0.275), (0.63, 0.275), (0.60, 0.40), (0.545, 0.37)]
        )

    _draw_hat(frame, look.hat, skin, hair)
    _draw_accessory(frame, look.accessory)


def _draw_hair(frame: Frame, style: str, color: Color) -> None:
    if style == "bald":
        return
    if style == "curly":
        for cx, cy, radius in (
            (0.36, 0.075, 0.055),
            (0.44, 0.045, 0.062),
            (0.54, 0.042, 0.062),
            (0.63, 0.07, 0.055),
            (0.34, 0.145, 0.04),
            (0.67, 0.135, 0.04),
        ):
            frame.circle(color, cx, cy, radius)
        return

    frame.polygon(
        shade(color, 0.92),
        [
            (0.315, 0.175),
            (0.325, 0.095),
            (0.42, 0.035),
            (0.58, 0.035),
            (0.675, 0.095),
            (0.685, 0.175),
            (0.62, 0.105),
            (0.50, 0.078),
            (0.38, 0.105),
        ],
    )
    frame.rect(color, 0.31, 0.135, 0.045, 0.11, radius=0.02)
    frame.rect(color, 0.645, 0.135, 0.045, 0.11, radius=0.02)
    frame.ellipse(shade(color, 1.12), 0.39, 0.055, 0.22, 0.055)

    if style == "long":
        frame.rect(color, 0.285, 0.16, 0.07, 0.26, radius=0.03)
        frame.rect(color, 0.645, 0.16, 0.07, 0.26, radius=0.03)
    elif style == "bun":
        frame.circle(color, 0.50, 0.055, 0.058)
        frame.circle(shade(color, 1.1), 0.48, 0.045, 0.028)


def _draw_hat(frame: Frame, style: str, skin: Color, hair: Color) -> None:
    if style == "cap":
        frame.ellipse(shade(hair, 0.8), 0.29, 0.075, 0.42, 0.06)
        frame.rect((66, 60, 58), 0.36, 0.02, 0.28, 0.09, radius=0.035)
        frame.rect((84, 74, 68), 0.36, 0.085, 0.28, 0.022, radius=0.01)
    elif style == "chef":
        frame.rect((244, 242, 236), 0.335, 0.088, 0.33, 0.05, radius=0.012)
        frame.circle((250, 248, 242), 0.40, 0.07, 0.072)
        frame.circle((250, 248, 242), 0.50, 0.052, 0.078)
        frame.circle((250, 248, 242), 0.60, 0.07, 0.072)
        frame.circle((236, 234, 228), 0.50, 0.095, 0.05)
    elif style == "brim":
        frame.ellipse((58, 52, 48), 0.21, 0.095, 0.58, 0.075)
        frame.rect((58, 52, 48), 0.36, 0.015, 0.28, 0.10, radius=0.035)
        frame.rect((118, 92, 60), 0.36, 0.085, 0.28, 0.024, radius=0.01)
    elif style == "straw":
        frame.ellipse((212, 184, 118), 0.23, 0.095, 0.54, 0.08)
        frame.rect((222, 194, 128), 0.365, 0.02, 0.27, 0.10, radius=0.045)
        frame.rect((140, 104, 62), 0.365, 0.085, 0.27, 0.026, radius=0.008)
        frame.line((188, 156, 100), (0.37, 0.045), (0.63, 0.045), 0.004)
    elif style == "hood":
        frame.polygon(
            shade((84, 122, 78), 0.82),
            [
                (0.285, 0.225),
                (0.30, 0.095),
                (0.43, 0.025),
                (0.57, 0.025),
                (0.70, 0.095),
                (0.715, 0.225),
                (0.645, 0.135),
                (0.50, 0.095),
                (0.355, 0.135),
            ],
        )
        frame.line(shade((84, 122, 78), 0.7), (0.30, 0.09), (0.30, 0.23), 0.01)
        frame.line(shade((84, 122, 78), 0.7), (0.70, 0.09), (0.70, 0.23), 0.01)
    elif style == "bandana":
        frame.polygon(
            (196, 76, 70),
            [
                (0.315, 0.135),
                (0.35, 0.045),
                (0.50, 0.005),
                (0.65, 0.045),
                (0.685, 0.135),
                (0.60, 0.09),
                (0.50, 0.078),
                (0.40, 0.09),
            ],
        )
        frame.polygon((196, 76, 70), [(0.665, 0.095), (0.73, 0.16), (0.70, 0.075)])
        frame.line((160, 58, 54), (0.35, 0.06), (0.65, 0.06), 0.005)
    elif style == "fedora":
        frame.ellipse((46, 38, 34), 0.19, 0.100, 0.62, 0.070)
        frame.polygon(
            (66, 56, 48),
            [
                (0.375, 0.098),
                (0.395, 0.022),
                (0.445, 0.002),
                (0.555, 0.002),
                (0.605, 0.022),
                (0.625, 0.098),
            ],
        )
        frame.rect((184, 144, 80), 0.385, 0.070, 0.23, 0.026, radius=0.008)
        frame.line((44, 36, 32), (0.44, 0.014), (0.56, 0.014), 0.006)


def _draw_accessory(frame: Frame, accessory: str) -> None:
    if accessory == "none":
        return
    if accessory == "book":
        frame.polygon((150, 92, 62), [(0.64, 0.50), (0.85, 0.56), (0.79, 0.72), (0.60, 0.66)])
        frame.polygon(
            (242, 234, 210), [(0.65, 0.505), (0.755, 0.535), (0.705, 0.655), (0.61, 0.625)]
        )
        frame.polygon(
            (236, 226, 198), [(0.755, 0.535), (0.845, 0.565), (0.787, 0.71), (0.705, 0.655)]
        )
        frame.line((176, 160, 138), (0.70, 0.55), (0.73, 0.64), 0.004)
    elif accessory == "bread":
        frame.ellipse((136, 88, 50), 0.645, 0.515, 0.26, 0.125)
        frame.ellipse((214, 162, 96), 0.66, 0.525, 0.23, 0.105)
        frame.ellipse((238, 196, 134), 0.685, 0.535, 0.18, 0.075)
        for offset in (0.0, 0.045, 0.09):
            frame.line((132, 82, 44), (0.68 + offset, 0.57), (0.71 + offset, 0.548), 0.009)
    elif accessory == "basket":
        frame.rect((146, 102, 58), 0.64, 0.565, 0.24, 0.13, radius=0.02)
        frame.rect((176, 132, 78), 0.64, 0.565, 0.24, 0.035, radius=0.01)
        for cx, color in ((0.69, (214, 92, 62)), (0.755, (204, 156, 60)), (0.815, (118, 154, 74))):
            frame.circle(color, cx, 0.552, 0.032)
        frame.line((176, 132, 78), (0.67, 0.63), (0.85, 0.63), 0.004)
    elif accessory == "lantern":
        frame.line((68, 62, 52), (0.80, 0.47), (0.80, 0.53), 0.008)
        frame.rect((64, 58, 50), 0.735, 0.53, 0.13, 0.14, radius=0.02)
        frame.rect((250, 208, 118), 0.755, 0.552, 0.09, 0.09, radius=0.012)
        frame.rect((64, 58, 50), 0.725, 0.665, 0.15, 0.02, radius=0.006)
    elif accessory == "hammer":
        frame.line((122, 88, 56), (0.80, 0.50), (0.78, 0.71), 0.014)
        frame.rect((92, 92, 98), 0.715, 0.47, 0.16, 0.055, radius=0.012)
    elif accessory == "flowers":
        for dx, color in (
            (-0.035, (226, 104, 122)),
            (0.01, (240, 200, 92)),
            (0.05, (170, 128, 210)),
        ):
            frame.line((84, 128, 72), (0.80, 0.62), (0.80 + dx, 0.48), 0.006)
            frame.circle(color, 0.80 + dx, 0.47, 0.03)
            frame.circle((246, 238, 196), 0.80 + dx, 0.47, 0.012)
    elif accessory == "teapot":
        frame.circle((226, 226, 218), 0.815, 0.60, 0.075)
        frame.rect((226, 226, 218), 0.78, 0.505, 0.07, 0.03, radius=0.01)
        frame.line((226, 226, 218), (0.87, 0.585), (0.92, 0.55), 0.012)
        pygame.draw.circle(
            frame.surface,
            (226, 226, 218),
            frame.pt(0.885, 0.615),
            frame.unit(0.035),
            frame.unit(0.01),
        )
        frame.circle((160, 118, 88), 0.815, 0.595, 0.02)
    elif accessory == "fish":
        frame.ellipse((176, 192, 200), 0.66, 0.55, 0.24, 0.10)
        frame.polygon((176, 192, 200), [(0.88, 0.56), (0.95, 0.52), (0.93, 0.62)])
        frame.circle((52, 44, 42), 0.705, 0.575, 0.012)
        frame.line((140, 158, 168), (0.72, 0.58), (0.82, 0.605), 0.004)
    elif accessory == "clock":
        frame.circle((214, 180, 92), 0.82, 0.60, 0.075)
        frame.circle((244, 228, 188), 0.82, 0.60, 0.055)
        frame.line((64, 54, 46), (0.82, 0.60), (0.82, 0.565), 0.006)
        frame.line((64, 54, 46), (0.82, 0.60), (0.845, 0.615), 0.006)
        frame.rect((214, 180, 92), 0.805, 0.515, 0.03, 0.02, radius=0.006)
    elif accessory == "pitchfork":
        frame.line((134, 96, 58), (0.84, 0.42), (0.80, 0.78), 0.012)
        frame.line((134, 96, 58), (0.795, 0.42), (0.885, 0.42), 0.01)
        for dx in (-0.04, 0.0, 0.04):
            frame.line((176, 176, 168), (0.84 + dx, 0.42), (0.84 + dx, 0.36), 0.008)
    elif accessory == "crop":
        frame.line((96, 72, 52), (0.82, 0.50), (0.72, 0.74), 0.01)
        frame.ellipse((96, 72, 52), 0.66, 0.72, 0.08, 0.05)
        frame.ellipse((150, 112, 78), 0.675, 0.727, 0.05, 0.03)
    elif accessory == "magnifier":
        frame.line((74, 54, 36), (0.79, 0.63), (0.868, 0.552), 0.016)
        frame.line((152, 112, 64), (0.795, 0.624), (0.864, 0.556), 0.008)
        frame.circle((194, 216, 218), 0.905, 0.505, 0.062)
        pygame.draw.circle(
            frame.surface,
            (212, 172, 94),
            frame.pt(0.905, 0.505),
            frame.unit(0.062),
            frame.unit(0.012),
        )
        frame.line((250, 250, 244), (0.878, 0.472), (0.898, 0.448), 0.007)


def _avatar_base(look_key: str, variant: int, width: int, height: int) -> pygame.Surface:
    look = NPC_LOOKS[look_key]
    skin = _SKIN_TONES[variant % len(_SKIN_TONES)]
    hair = _HAIR_COLORS[(variant * 3 + hash_index(look_key, 5)) % len(_HAIR_COLORS)]
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    frame = Frame(surface, surface.get_rect())
    shadow(frame, 0.16, 0.90, 0.68, 0.075, 90)
    _draw_legs(frame, look.clothing)
    _draw_body(frame, look, skin)
    _draw_head(frame, look, skin, hair)
    return surface


@lru_cache(maxsize=256)
def _cached_avatar(look_key: str, variant: int, width: int, height: int) -> pygame.Surface:
    return _avatar_base(look_key, variant, width, height)


def render_npc(
    role: str,
    seed: str,
    height: int,
    tick: float = 0.0,
) -> pygame.Surface:
    """Render an avatar for ``role``; ``seed`` makes each person distinct."""
    look = resolve_look(role)
    height = max(24, height)
    width = max(16, round(height * 0.62))
    variant = hash_index(seed, 24)
    avatar = _cached_avatar(look.key, variant, width, height).copy()
    if tick:
        _draw_avatar_ambient(avatar, look, tick)
    return avatar


def _draw_avatar_ambient(avatar: pygame.Surface, look: NpcLook, tick: float) -> None:
    if look.accessory != "lantern":
        return
    width, height = avatar.get_size()
    glow(
        avatar,
        (round(0.80 * width), round(0.60 * height)),
        round(height * 0.045),
        (255, 214, 130),
        50 + round(18 * math.sin(tick * 0.18)),
    )


__all__ = ["NPC_LOOKS", "NpcLook", "render_npc", "resolve_look"]
