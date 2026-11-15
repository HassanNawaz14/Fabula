"""Procedural artwork for every town location type.

Each location type owns a small library of reusable scene parts (awnings,
counters, shelves, trees, carts, ...) that are composed into a full diorama.
A location instance picks one of several palettes/layout variants from its id,
so no two markets (or libraries, ...) look exactly alike on the map.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

import pygame

from fabula.schemas.enums import LocationType
from fabula.ui.assets.common import (
    Color,
    Frame,
    glow,
    hash_index,
    scatter,
    shade,
    shadow,
)

SceneDrawer = Callable[[Frame, int], None]


@dataclass(frozen=True)
class PlaceAsset:
    key: str
    label: str
    variants: int
    draw: SceneDrawer

    def variant_for(self, seed: str) -> int:
        return hash_index(seed, self.variants)


# ---------------------------------------------------------------------------
# Palette library
# ---------------------------------------------------------------------------

_AWNINGS: tuple[tuple[Color, Color], ...] = (
    ((186, 72, 66), (248, 236, 214)),
    ((58, 118, 132), (242, 235, 208)),
    ((206, 152, 52), (58, 50, 44)),
)

_WALLS: tuple[Color, ...] = ((214, 190, 156), (196, 186, 176), (206, 174, 144))
_ROOFS: tuple[Color, ...] = ((146, 66, 58), (72, 88, 104), (104, 74, 58))
_STONES: tuple[tuple[Color, Color], ...] = (
    ((216, 202, 178), (178, 162, 136)),
    ((200, 200, 206), (160, 160, 168)),
    ((208, 186, 160), (170, 146, 118)),
)
_CAFE_WALLS: tuple[Color, ...] = ((88, 132, 120), (156, 92, 102), (70, 96, 120))
_PARK_LAWNS: tuple[tuple[Color, Color], ...] = (
    ((92, 150, 78), (78, 132, 66)),
    ((156, 142, 66), (124, 116, 54)),
    ((126, 138, 90), (104, 118, 74)),
)
_PARK_CANOPIES: tuple[tuple[Color, Color], ...] = (
    ((70, 132, 68), (96, 164, 82)),
    ((176, 138, 54), (204, 168, 74)),
    ((132, 92, 104), (168, 126, 132)),
)
_ASPHALT: tuple[Color, ...] = ((88, 90, 96), (78, 84, 88), (96, 92, 88))
_LAWN: tuple[Color, ...] = ((104, 156, 82), (92, 144, 76), (116, 160, 86))
_WINDOW_GLOW: Color = (250, 214, 132)
_DOOR_WOOD: Color = (98, 68, 48)
_TRUNK: Color = (104, 76, 52)


# ---------------------------------------------------------------------------
# Reusable scene parts
# ---------------------------------------------------------------------------


def _bush(frame: Frame, x: float, y: float, size: float, color: Color) -> None:
    frame.circle(color, x, y, size)
    frame.circle(shade(color, 1.14), x - size * 0.42, y - size * 0.34, size * 0.56)
    frame.circle(shade(color, 0.86), x + size * 0.52, y - size * 0.12, size * 0.48)


def _tree(
    frame: Frame,
    x: float,
    ground_y: float,
    size: float,
    canopy: Color,
    highlight: Color,
) -> None:
    trunk_h = size * 0.9
    frame.rect(_TRUNK, x - 0.012, ground_y - trunk_h, 0.024, trunk_h, radius=0.004)
    frame.ellipse(shade(_TRUNK, 0.82), x - 0.045, ground_y - 0.012, 0.09, 0.024)
    frame.circle(shade(canopy, 0.82), x, ground_y - trunk_h - size * 0.24, size * 0.62)
    frame.circle(canopy, x - size * 0.46, ground_y - trunk_h - size * 0.02, size * 0.44)
    frame.circle(canopy, x + size * 0.48, ground_y - trunk_h - size * 0.08, size * 0.42)
    frame.circle(highlight, x - size * 0.12, ground_y - trunk_h - size * 0.52, size * 0.34)
    frame.circle(highlight, x + size * 0.34, ground_y - trunk_h + size * 0.06, size * 0.22)


def _lamp(frame: Frame, x: float, ground_y: float, height: float) -> None:
    frame.rect((58, 56, 62), x - 0.008, ground_y - height, 0.016, height, radius=0.003)
    frame.ellipse((48, 46, 52), x - 0.035, ground_y - 0.016, 0.07, 0.028)
    frame.rect((70, 68, 72), x - 0.03, ground_y - height - 0.055, 0.06, 0.05, radius=0.008)
    frame.rect(_WINDOW_GLOW, x - 0.02, ground_y - height - 0.046, 0.04, 0.032, radius=0.006)
    frame.polygon(
        (58, 56, 62),
        [
            (x - 0.04, ground_y - height - 0.055),
            (x + 0.04, ground_y - height - 0.055),
            (x, ground_y - height - 0.085),
        ],
    )


def _bench(frame: Frame, x: float, ground_y: float, width: float) -> None:
    wood = (136, 96, 62)
    frame.rect(shade(wood, 0.7), x - width / 2, ground_y - 0.03, 0.014, 0.03)
    frame.rect(shade(wood, 0.7), x + width / 2 - 0.014, ground_y - 0.03, 0.014, 0.03)
    frame.rect(wood, x - width / 2, ground_y - 0.058, width, 0.022, radius=0.006)
    frame.rect(shade(wood, 0.86), x - width / 2, ground_y - 0.105, width, 0.016, radius=0.005)
    frame.rect(shade(wood, 0.86), x - width / 2, ground_y - 0.082, width, 0.012, radius=0.004)


def _crate(frame: Frame, x: float, y: float, width: float, height: float) -> None:
    wood = (158, 112, 66)
    frame.rect(shade(wood, 0.78), x, y, width, height, radius=0.006)
    frame.rect(wood, x + 0.004, y + 0.004, width - 0.008, height - 0.008, radius=0.005)
    frame.line(
        shade(wood, 0.68), (x + 0.006, y + height / 2), (x + width - 0.006, y + height / 2), 0.008
    )
    frame.line(
        shade(wood, 0.68), (x + width / 2, y + 0.006), (x + width / 2, y + height - 0.006), 0.008
    )


def _barrel(frame: Frame, x: float, ground_y: float, width: float) -> None:
    height = width * 1.25
    body = (132, 92, 58)
    frame.rect(body, x - width / 2, ground_y - height, width, height, radius=width * 0.45)
    frame.rect(shade(body, 0.72), x - width / 2, ground_y - height * 0.74, width, height * 0.06)
    frame.rect(shade(body, 0.72), x - width / 2, ground_y - height * 0.28, width, height * 0.06)
    frame.ellipse(shade(body, 1.12), x - width / 2, ground_y - height, width, width * 0.5)


def _fruit_pile(frame: Frame, x: float, y: float, width: float, color: Color) -> None:
    for row, count in enumerate((3, 2)):
        for index in range(count):
            fx = x + width * (index + 0.5 + row * 0.5) / 3
            frame.circle(color, fx, y - row * 0.012, 0.009)
            frame.circle(shade(color, 1.2), fx - 0.002, y - row * 0.012 - 0.002, 0.004)


def _window(
    frame: Frame,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    arched: bool = False,
    lit: bool = True,
    frame_color: Color = (92, 78, 62),
) -> None:
    pane = _WINDOW_GLOW if lit else (92, 108, 124)
    frame.rect(frame_color, x - 0.008, y - 0.008, width + 0.016, height + 0.016, radius=0.008)
    frame.rect(pane, x, y, width, height, radius=0.006)
    if arched:
        frame.ellipse(pane, x, y - height * 0.24, width, height * 0.5)
        frame.rect(frame_color, x - 0.008, y - height * 0.28, width + 0.016, 0.012, radius=0.004)
    frame.line(frame_color, (x + width / 2, y), (x + width / 2, y + height), 0.006)
    frame.line(frame_color, (x, y + height / 2), (x + width, y + height / 2), 0.006)
    if lit:
        frame.rect((255, 238, 190), x + 0.006, y + 0.008, width * 0.32, height * 0.26, radius=0.004)


def _pickets(frame: Frame, x0: float, x1: float, y: float, height: float) -> None:
    wood = (188, 168, 132)
    frame.rect(wood, x0, y + height * 0.22, x1 - x0, 0.012)
    frame.rect(wood, x0, y + height * 0.62, x1 - x0, 0.012)
    count = max(2, round((x1 - x0) / 0.05))
    for index in range(count + 1):
        x = x0 + (x1 - x0) * index / count
        frame.rect(shade(wood, 0.92), x - 0.006, y, 0.012, height, radius=0.004)
        frame.polygon(shade(wood, 1.06), [(x - 0.006, y), (x + 0.006, y), (x, y - 0.018)])


def _cobbles(frame: Frame, fx: float, fy: float, fw: float, fh: float, seed: str) -> None:
    scatter(
        frame,
        seed,
        110,
        (fx, fy, fw, fh),
        ((178, 160, 136), (160, 142, 120), (196, 180, 158)),
        radius=(0.003, 0.008),
    )


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------


def _market_stall(
    frame: Frame,
    x: float,
    y: float,
    width: float,
    awning: Color,
    stripe: Color,
    produce: tuple[Color, ...],
) -> None:
    post = (108, 78, 54)
    frame.rect(post, x + 0.012, y + 0.05, 0.014, 0.27)
    frame.rect(post, x + width - 0.026, y + 0.05, 0.014, 0.27)

    # Counter and its cloth
    frame.rect((150, 112, 74), x, y + 0.21, width, 0.11, radius=0.008)
    frame.rect((196, 170, 136), x, y + 0.21, width, 0.026, radius=0.006)
    frame.rect((116, 84, 58), x + 0.004, y + 0.30, width - 0.008, 0.022)

    # Striped canopy
    segments = 7
    frame.rect(shade(awning, 0.7), x - 0.01, y + 0.075, width + 0.02, 0.045, radius=0.008)
    for index in range(segments):
        left = x + width * index / segments
        color = awning if index % 2 == 0 else stripe
        frame.polygon(
            color,
            [
                (left, y + 0.012),
                (left + width / segments, y + 0.012),
                (left + width / segments, y + 0.085),
                (left, y + 0.085),
            ],
        )
        frame.circle(color, left + width / (segments * 2), y + 0.09, width / (segments * 2))
    frame.line((88, 62, 46), (x - 0.01, y + 0.012), (x + width + 0.01, y + 0.012), 0.01)

    # Produce crates on the counter
    crate_w = width * 0.24
    for index, fruit in enumerate(produce):
        cx = x + 0.02 + index * (crate_w + 0.03)
        _crate(frame, cx, y + 0.145, crate_w, 0.07)
        _fruit_pile(frame, cx, y + 0.16, crate_w, fruit)

    # A sack leaning on the stall
    frame.ellipse((198, 176, 128), x + width - 0.075, y + 0.285, 0.07, 0.052)
    frame.ellipse((172, 150, 104), x + width - 0.07, y + 0.29, 0.06, 0.03)


def _draw_market(frame: Frame, variant: int) -> None:
    awning, stripe = _AWNINGS[variant % len(_AWNINGS)]
    shadow(frame, 0.03, 0.78, 0.94, 0.19, 76)

    frame.rect((188, 170, 144), 0.02, 0.57, 0.96, 0.41, radius=0.05)
    frame.rect((158, 141, 118), 0.02, 0.57, 0.96, 0.41, radius=0.05, width=0.005)
    _cobbles(frame, 0.04, 0.60, 0.92, 0.36, f"market:{variant}")

    # Back hedge line
    for index, x in enumerate((0.045, 0.21, 0.50, 0.79, 0.955)):
        _bush(frame, x, 0.555, 0.038, (62, 106, 66))
        if index % 2 == 0:
            _bush(frame, x + 0.06, 0.565, 0.026, (74, 120, 72))

    # Bunting across the square
    frame.line((96, 72, 52), (0.04, 0.075), (0.96, 0.10), 0.004)
    flags = ((196, 82, 74), (238, 214, 168), (78, 126, 138))
    for index in range(9):
        t = index / 8
        x = 0.04 + t * 0.92
        y = 0.076 + t * 0.024 + math.sin(t * math.pi) * 0.012
        frame.polygon(
            flags[(index + variant) % 3],
            [(x - 0.02, y), (x + 0.02, y), (x, y + 0.042)],
        )

    _market_stall(
        frame, 0.055, 0.34, 0.40, awning, stripe, ((222, 108, 58), (196, 64, 62), (104, 152, 72))
    )
    second_awning, second_stripe = _AWNINGS[(variant + 1) % len(_AWNINGS)]
    _market_stall(
        frame,
        0.545,
        0.39,
        0.385,
        second_awning,
        second_stripe,
        ((196, 148, 62), (118, 158, 88), (168, 110, 150)),
    )

    # Foreground props
    _barrel(frame, 0.10, 0.94, 0.06)
    _barrel(frame, 0.165, 0.95, 0.048)
    _crate(frame, 0.80, 0.845, 0.09, 0.075)
    _crate(frame, 0.865, 0.875, 0.07, 0.06)
    frame.ellipse((54, 46, 42), 0.30, 0.845, 0.10, 0.022)
    frame.ellipse((170, 140, 108), 0.302, 0.842, 0.096, 0.018)

    # Hanging lantern on a hook
    frame.line((70, 62, 52), (0.925, 0.20), (0.925, 0.30), 0.006)
    frame.rect((64, 58, 50), 0.905, 0.30, 0.04, 0.05, radius=0.006)
    frame.rect(_WINDOW_GLOW, 0.913, 0.311, 0.024, 0.03, radius=0.004)


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------


def _draw_library(frame: Frame, variant: int) -> None:
    stone, stone_dark = _STONES[variant % len(_STONES)]
    shadow(frame, 0.08, 0.86, 0.84, 0.12, 80)

    # Steps
    for index, (inset, height) in enumerate(((0.10, 0.035), (0.14, 0.032), (0.18, 0.028))):
        y = 0.775 + index * 0.028
        frame.rect(
            shade(stone, 0.92 - index * 0.03),
            0.10 + inset,
            y,
            0.80 - inset * 2,
            height,
            radius=0.006,
        )
        frame.rect(stone_dark, 0.10 + inset, y + height - 0.006, 0.80 - inset * 2, 0.006)

    # Facade
    frame.rect(stone, 0.14, 0.24, 0.72, 0.55, radius=0.012)
    frame.rect(stone_dark, 0.14, 0.24, 0.72, 0.55, radius=0.012, width=0.006)
    for row in range(1, 8):
        y = 0.24 + row * 0.065
        frame.line(shade(stone, 0.9), (0.145, y), (0.855, y), 0.003)

    # Pediment
    frame.polygon(stone, [(0.11, 0.245), (0.89, 0.245), (0.5, 0.075)])
    frame.polygon(shade(stone, 0.9), [(0.155, 0.235), (0.845, 0.235), (0.5, 0.105)])
    frame.polygon(shade(stone, 0.8), [(0.30, 0.215), (0.70, 0.215), (0.5, 0.145)], width=0.004)
    frame.circle(shade(stone, 0.78), 0.5, 0.195, 0.022)

    # Columns
    for x in (0.185, 0.315, 0.615, 0.745):
        frame.rect(shade(stone, 1.04), x, 0.30, 0.062, 0.46, radius=0.004)
        frame.rect(shade(stone, 0.88), x - 0.006, 0.30, 0.074, 0.022, radius=0.004)
        frame.rect(shade(stone, 0.88), x - 0.006, 0.742, 0.074, 0.024, radius=0.004)
        for groove in (0.016, 0.031, 0.046):
            frame.line(shade(stone, 0.92), (x + groove, 0.325), (x + groove, 0.738), 0.003)

    # Warm windows between columns
    _window(frame, 0.20, 0.40, 0.095, 0.19, arched=True)
    _window(frame, 0.345, 0.40, 0.095, 0.19, arched=True)
    _window(frame, 0.56, 0.40, 0.095, 0.19, arched=True)
    _window(frame, 0.705, 0.40, 0.095, 0.19, arched=True)

    # Arched entrance
    frame.ellipse(shade(stone, 1.12), 0.445, 0.435, 0.11, 0.16)
    frame.rect(shade(stone, 1.12), 0.445, 0.50, 0.11, 0.26)
    frame.ellipse(_DOOR_WOOD, 0.455, 0.455, 0.09, 0.13)
    frame.rect(_DOOR_WOOD, 0.455, 0.515, 0.09, 0.245)
    frame.line(shade(_DOOR_WOOD, 0.7), (0.5, 0.47), (0.5, 0.75), 0.005)
    frame.circle((212, 178, 94), 0.531, 0.63, 0.009)

    # Wall lanterns beside the door
    for x in (0.412, 0.588):
        frame.rect((64, 58, 52), x - 0.008, 0.535, 0.016, 0.045, radius=0.004)
        frame.rect(_WINDOW_GLOW, x - 0.006, 0.542, 0.012, 0.026, radius=0.003)
    frame.ellipse(_WINDOW_GLOW, 0.435, 0.765, 0.13, 0.02)

    # Ivy and a stack of books left on the steps
    for x, y, size in (
        (0.16, 0.44, 0.02),
        (0.175, 0.52, 0.026),
        (0.155, 0.60, 0.022),
        (0.78, 0.40, 0.018),
    ):
        _bush(frame, x, y, size, (62, 112, 66))
    frame.rect((146, 92, 76), 0.665, 0.735, 0.075, 0.016, radius=0.003)
    frame.rect((176, 122, 92), 0.672, 0.719, 0.075, 0.016, radius=0.003)
    frame.rect((96, 120, 138), 0.659, 0.703, 0.075, 0.016, radius=0.003)

    _lamp(frame, 0.075, 0.83, 0.24)
    _bush(frame, 0.935, 0.80, 0.035, (78, 128, 74))


# ---------------------------------------------------------------------------
# Cafe
# ---------------------------------------------------------------------------


def _cafe_table(frame: Frame, x: float, ground_y: float, umbrella: Color) -> None:
    frame.rect((110, 88, 66), x - 0.006, ground_y - 0.09, 0.012, 0.09)
    frame.ellipse((146, 114, 84), x - 0.07, ground_y - 0.10, 0.14, 0.03)
    frame.rect((128, 100, 74), x - 0.055, ground_y - 0.065, 0.11, 0.016, radius=0.006)
    frame.line((96, 80, 60), (x - 0.045, ground_y - 0.02), (x - 0.045, ground_y), 0.008)
    frame.line((96, 80, 60), (x + 0.045, ground_y - 0.02), (x + 0.045, ground_y), 0.008)
    # Chairs
    for direction in (-1, 1):
        cx = x + direction * 0.10
        frame.rect((118, 90, 64), cx - 0.022, ground_y - 0.045, 0.044, 0.012, radius=0.004)
        frame.rect((118, 90, 64), cx - 0.022, ground_y - 0.10, 0.012, 0.06, radius=0.004)
        frame.line((96, 80, 60), (cx - 0.018, ground_y - 0.033), (cx - 0.018, ground_y), 0.006)
        frame.line((96, 80, 60), (cx + 0.018, ground_y - 0.033), (cx + 0.018, ground_y), 0.006)
    # Parasol
    frame.line((104, 84, 62), (x, ground_y - 0.16), (x, ground_y - 0.095), 0.008)
    frame.polygon(
        umbrella,
        [(x - 0.13, ground_y - 0.165), (x + 0.13, ground_y - 0.165), (x, ground_y - 0.255)],
    )
    frame.polygon(
        shade(umbrella, 1.18),
        [(x - 0.06, ground_y - 0.168), (x + 0.06, ground_y - 0.168), (x, ground_y - 0.252)],
    )
    frame.circle(shade(umbrella, 0.8), x, ground_y - 0.26, 0.008)


def _draw_cafe(frame: Frame, variant: int) -> None:
    wall = _CAFE_WALLS[variant % len(_CAFE_WALLS)]
    awning, stripe = _AWNINGS[variant % len(_AWNINGS)]
    shadow(frame, 0.06, 0.86, 0.88, 0.12, 76)

    # Pavement
    frame.rect((168, 158, 146), 0.02, 0.73, 0.96, 0.24, radius=0.03)
    frame.rect((138, 130, 120), 0.02, 0.73, 0.96, 0.24, radius=0.03, width=0.004)
    for row in range(3):
        frame.line((150, 142, 132), (0.03, 0.78 + row * 0.06), (0.97, 0.78 + row * 0.06), 0.003)
    for index in range(9):
        x = 0.07 + index * 0.11
        frame.line((150, 142, 132), (x, 0.74), (x, 0.96), 0.003)

    # Facade
    frame.rect(wall, 0.09, 0.20, 0.82, 0.55, radius=0.012)
    frame.rect(shade(wall, 0.8), 0.09, 0.20, 0.82, 0.55, radius=0.012, width=0.006)
    frame.rect(shade(wall, 0.72), 0.075, 0.19, 0.85, 0.045, radius=0.01)
    frame.rect(shade(wall, 1.1), 0.10, 0.225, 0.80, 0.018)

    # Striped awning over the shop front
    for index in range(8):
        left = 0.14 + index * 0.09
        color = awning if index % 2 == 0 else stripe
        frame.polygon(
            color, [(left, 0.285), (left + 0.09, 0.285), (left + 0.09, 0.345), (left, 0.345)]
        )
        frame.circle(color, left + 0.045, 0.35, 0.022)
    frame.line((88, 62, 46), (0.13, 0.283), (0.87, 0.283), 0.008)

    # Large shop window with mullions
    _window(frame, 0.17, 0.40, 0.30, 0.20, lit=True)
    frame.line(shade(wall, 0.6), (0.32, 0.40), (0.32, 0.60), 0.006)
    # Door
    frame.rect(shade(wall, 0.64), 0.565, 0.395, 0.14, 0.265, radius=0.01)
    frame.rect(_DOOR_WOOD, 0.575, 0.41, 0.12, 0.25, radius=0.008)
    frame.rect(_WINDOW_GLOW, 0.592, 0.425, 0.086, 0.085, radius=0.006)
    frame.circle((212, 178, 94), 0.682, 0.55, 0.008)
    # Small window right
    _window(frame, 0.755, 0.42, 0.10, 0.15, lit=True)

    # Hanging sign with a cup
    frame.line((70, 62, 52), (0.80, 0.285), (0.80, 0.32), 0.006)
    frame.rect((70, 62, 52), 0.80, 0.32, 0.005, 0.07, 0.002)
    frame.rect((62, 54, 46), 0.815, 0.33, 0.10, 0.065, radius=0.008)
    frame.rect((238, 228, 204), 0.835, 0.343, 0.045, 0.03, radius=0.006)
    frame.ellipse((238, 228, 204), 0.835, 0.335, 0.045, 0.016)
    frame.circle((238, 228, 204), 0.886, 0.356, 0.012)
    frame.circle((62, 54, 46), 0.886, 0.356, 0.006)

    # Cafe tables on the pavement
    _cafe_table(frame, 0.24, 0.94, awning)
    _cafe_table(frame, 0.755, 0.955, _AWNINGS[(variant + 2) % 3][0])

    # Potted plants and a chalkboard
    for x in (0.115, 0.895):
        frame.polygon(
            (154, 104, 74),
            [(x - 0.026, 0.70), (x + 0.026, 0.70), (x + 0.018, 0.755), (x - 0.018, 0.755)],
        )
        _bush(frame, x, 0.672, 0.026, (72, 126, 70))
    frame.rect((72, 62, 54), 0.39, 0.70, 0.10, 0.13, radius=0.006)
    frame.rect((58, 50, 44), 0.397, 0.71, 0.086, 0.11, radius=0.004)
    frame.line((202, 192, 168), (0.41, 0.735), (0.47, 0.735), 0.003)
    frame.line((202, 192, 168), (0.41, 0.755), (0.455, 0.755), 0.003)
    frame.line((84, 74, 66), (0.42, 0.83), (0.435, 0.94), 0.006)
    frame.line((84, 74, 66), (0.46, 0.83), (0.445, 0.94), 0.006)

    # Cup on the right table, with a saucer
    frame.ellipse((240, 236, 224), 0.73, 0.875, 0.05, 0.012)
    frame.rect((238, 228, 210), 0.738, 0.845, 0.034, 0.032, radius=0.008)
    frame.circle((238, 228, 210), 0.774, 0.858, 0.012)
    frame.circle((110, 88, 66), 0.774, 0.858, 0.006)


# ---------------------------------------------------------------------------
# Park
# ---------------------------------------------------------------------------


def _draw_park(frame: Frame, variant: int) -> None:
    lawn, lawn_dark = _PARK_LAWNS[variant % len(_PARK_LAWNS)]
    canopy, canopy_light = _PARK_CANOPIES[variant % len(_PARK_CANOPIES)]
    shadow(frame, 0.02, 0.76, 0.96, 0.22, 66)

    frame.ellipse(lawn, 0.015, 0.52, 0.97, 0.46)
    frame.ellipse(lawn_dark, 0.03, 0.68, 0.94, 0.30)
    scatter(
        frame,
        f"park:{variant}",
        90,
        (0.05, 0.62, 0.90, 0.32),
        (shade(lawn, 1.12), shade(lawn_dark, 0.9), shade(lawn, 0.82)),
        radius=(0.002, 0.005),
    )

    # Winding path
    path = (
        (0.43, 1.01),
        (0.56, 1.01),
        (0.60, 0.86),
        (0.55, 0.76),
        (0.44, 0.70),
        (0.38, 0.62),
        (0.47, 0.56),
    )
    frame.polygon((206, 188, 150), path)
    frame.lines((176, 158, 122), path, 0.008)
    frame.lines(
        (224, 208, 172),
        [(0.47, 0.99), (0.56, 0.86), (0.50, 0.77), (0.42, 0.70), (0.42, 0.63)],
        0.004,
    )

    # Pond with reeds and ducks
    frame.ellipse((86, 146, 178), 0.055, 0.66, 0.31, 0.20)
    frame.ellipse((110, 170, 202), 0.075, 0.685, 0.27, 0.16)
    frame.ellipse((142, 196, 222), 0.105, 0.705, 0.20, 0.11)
    for index in range(3):
        x = 0.13 + index * 0.055
        frame.line((74, 124, 66), (x, 0.70), (x + 0.012, 0.61), 0.008)
        frame.ellipse((96, 150, 78), x + 0.006, 0.60, 0.02, 0.012)
    for x, y in ((0.17, 0.76), (0.215, 0.785)):
        frame.ellipse((236, 238, 230), x, y, 0.032, 0.018)
        frame.circle((236, 238, 230), x + 0.030, y - 0.006, 0.009)
        frame.polygon(
            (240, 172, 60), [(x + 0.038, y - 0.002), (x + 0.050, y + 0.002), (x + 0.038, y + 0.006)]
        )

    # Trees
    _tree(frame, 0.215, 0.66, 0.34, canopy, canopy_light)
    _tree(frame, 0.815, 0.60, 0.26, shade(canopy, 0.94), shade(canopy_light, 0.94))

    # Flower beds
    for index in range(10):
        x = 0.66 + (index % 5) * 0.045
        y = 0.76 + (index // 5) * 0.05
        color = ((224, 108, 122), (236, 196, 92), (166, 120, 204))[index % 3]
        frame.circle(color, x, y, 0.009)
        frame.line((84, 128, 72), (x, y + 0.009), (x, y + 0.022), 0.003)

    # Bench, lamp, stones
    _bench(frame, 0.60, 0.73, 0.16)
    _lamp(frame, 0.92, 0.79, 0.20)
    scatter(
        frame,
        f"park-stones:{variant}",
        14,
        (0.40, 0.80, 0.50, 0.14),
        ((170, 156, 132),),
        radius=(0.004, 0.009),
    )


# ---------------------------------------------------------------------------
# Parking / coach yard
# ---------------------------------------------------------------------------


def _cart(frame: Frame, x: float, ground_y: float, scale: float) -> None:
    wood = (140, 98, 60)
    frame.rect(
        shade(wood, 0.8), x - scale * 0.5, ground_y - scale * 0.95, scale, scale * 0.45, radius=0.01
    )
    frame.rect(
        wood, x - scale * 0.48, ground_y - scale * 0.93, scale * 0.96, scale * 0.22, radius=0.008
    )
    frame.line(
        shade(wood, 0.66),
        (x - scale * 0.45, ground_y - scale * 0.8),
        (x + scale * 0.45, ground_y - scale * 0.8),
        0.006,
    )
    for wheel_x in (x - scale * 0.34, x + scale * 0.34):
        frame.circle((62, 54, 46), wheel_x, ground_y - scale * 0.30, scale * 0.22)
        frame.circle((150, 124, 88), wheel_x, ground_y - scale * 0.30, scale * 0.15)
        frame.circle((62, 54, 46), wheel_x, ground_y - scale * 0.30, scale * 0.05)
        for angle in range(0, 360, 60):
            radians = math.radians(angle)
            frame.line(
                (96, 76, 54),
                (wheel_x, ground_y - scale * 0.30),
                (
                    wheel_x + math.cos(radians) * scale * 0.15,
                    ground_y - scale * 0.30 + math.sin(radians) * scale * 0.15,
                ),
                0.004,
            )
    # Shafts
    frame.line(
        (104, 78, 54),
        (x + scale * 0.48, ground_y - scale * 0.70),
        (x + scale * 0.85, ground_y - scale * 0.18),
        0.008,
    )
    frame.line(
        (104, 78, 54),
        (x + scale * 0.48, ground_y - scale * 0.62),
        (x + scale * 0.85, ground_y - scale * 0.10),
        0.008,
    )


def _draw_parking(frame: Frame, variant: int) -> None:
    asphalt = _ASPHALT[variant % len(_ASPHALT)]
    shadow(frame, 0.02, 0.78, 0.96, 0.20, 72)

    frame.rect(asphalt, 0.02, 0.50, 0.96, 0.48, radius=0.03)
    frame.rect(shade(asphalt, 0.8), 0.02, 0.50, 0.96, 0.48, radius=0.03, width=0.005)
    scatter(
        frame,
        f"parking:{variant}",
        120,
        (0.04, 0.54, 0.92, 0.40),
        (shade(asphalt, 0.85), shade(asphalt, 1.12), shade(asphalt, 0.94)),
        radius=(0.004, 0.012),
    )

    # Parking bay lines
    for index in range(5):
        x = 0.10 + index * 0.18
        frame.line((208, 208, 198), (x, 0.62), (x - 0.03, 0.88), 0.008)
    frame.line((208, 208, 198), (0.075, 0.62), (0.09, 0.88), 0.008)

    # Wooden fence at the back
    for index in range(9):
        x = 0.04 + index * 0.115
        frame.rect((152, 120, 82), x, 0.36, 0.018, 0.15, radius=0.003)
    frame.rect((168, 136, 94), 0.035, 0.39, 0.93, 0.016)
    frame.rect((168, 136, 94), 0.035, 0.45, 0.93, 0.016)

    # Carts parked in bays
    _cart(frame, 0.245, 0.87, 0.20)
    _cart(frame, 0.575, 0.835, 0.15)

    # Crates and barrels by the fence
    _crate(frame, 0.80, 0.72, 0.09, 0.075)
    _crate(frame, 0.885, 0.745, 0.07, 0.06)
    _barrel(frame, 0.93, 0.80, 0.05)

    # Oil stains and puddles
    for x, y, w in ((0.36, 0.80, 0.10), (0.50, 0.90, 0.06), (0.15, 0.92, 0.05)):
        frame.ellipse((60, 62, 68), x, y, w, w * 0.35)
    frame.ellipse((92, 108, 126), 0.76, 0.90, 0.10, 0.03)
    frame.ellipse((142, 162, 182), 0.775, 0.90, 0.06, 0.016)

    # Yard lamp
    _lamp(frame, 0.685, 0.72, 0.28)
    frame.rect((70, 62, 54), 0.845, 0.56, 0.085, 0.10, radius=0.008)
    frame.rect((208, 204, 190), 0.852, 0.57, 0.071, 0.08, radius=0.006)
    frame.circle((70, 62, 54), 0.887, 0.61, 0.018)
    frame.rect((70, 62, 54), 0.887, 0.61, 0.012, 0.036)
    frame.rect((70, 62, 54), 0.857, 0.636, 0.06, 0.012)
    frame.rect((70, 62, 54), 0.845, 0.72, 0.03, 0.10)


# ---------------------------------------------------------------------------
# Residence
# ---------------------------------------------------------------------------


def _draw_residence(frame: Frame, variant: int) -> None:
    wall = _WALLS[variant % len(_WALLS)]
    roof = _ROOFS[variant % len(_ROOFS)]
    lawn = _LAWN[variant % len(_LAWN)]
    shadow(frame, 0.07, 0.84, 0.86, 0.13, 78)

    # Garden ground
    frame.ellipse(lawn, 0.03, 0.70, 0.94, 0.27)
    scatter(
        frame,
        f"residence:{variant}",
        60,
        (0.06, 0.74, 0.88, 0.22),
        (shade(lawn, 1.1), shade(lawn, 0.88)),
        radius=(0.002, 0.005),
    )

    # House body
    frame.rect(wall, 0.17, 0.34, 0.66, 0.42, radius=0.008)
    frame.rect(shade(wall, 0.8), 0.17, 0.34, 0.66, 0.42, radius=0.008, width=0.005)

    # Roof with overhang and shingles
    frame.polygon(shade(roof, 0.82), [(0.09, 0.365), (0.91, 0.365), (0.5, 0.13)])
    frame.polygon(roof, [(0.13, 0.355), (0.87, 0.355), (0.5, 0.16)])
    for row in range(3):
        y = 0.19 + row * 0.052
        half = 0.13 + row * 0.09
        frame.line(shade(roof, 0.74), (0.5 - half, y), (0.5 + half, y), 0.003)
    for index in range(7):
        x = 0.28 + index * 0.073
        y_top = 0.30 - abs(x - 0.5) * 0.42
        frame.line(shade(roof, 0.86), (x, y_top), (x, 0.355), 0.003)

    # Chimney and pot
    frame.rect((122, 92, 78), 0.665, 0.145, 0.085, 0.17, radius=0.004)
    frame.rect(shade((122, 92, 78), 0.82), 0.665, 0.145, 0.085, 0.17, radius=0.004, width=0.004)
    for row in range(3):
        frame.line(
            shade((122, 92, 78), 0.76),
            (0.665, 0.175 + row * 0.045),
            (0.75, 0.175 + row * 0.045),
            0.003,
        )
    frame.rect((80, 64, 54), 0.652, 0.128, 0.111, 0.03, radius=0.004)

    # Windows with curtains and flower boxes
    for x in (0.245, 0.635):
        _window(frame, x, 0.43, 0.12, 0.15, lit=True)
        frame.rect((104, 74, 56), x - 0.006, 0.425, 0.012, 0.16)
        frame.rect((104, 74, 56), x + 0.114, 0.425, 0.012, 0.16)
        frame.rect((150, 96, 64), x - 0.012, 0.59, 0.144, 0.026, radius=0.004)
        for index in range(4):
            frame.circle(
                ((214, 96, 108), (228, 158, 84), (196, 120, 176))[index % 3],
                x + 0.012 + index * 0.033,
                0.587,
                0.01,
            )

    # Door, step and porch lantern
    frame.rect(shade(wall, 0.7), 0.435, 0.47, 0.14, 0.29, radius=0.008)
    frame.rect(_DOOR_WOOD, 0.445, 0.48, 0.12, 0.28, radius=0.006)
    frame.rect(shade(_DOOR_WOOD, 1.14), 0.455, 0.50, 0.10, 0.10, radius=0.006)
    frame.line(shade(_DOOR_WOOD, 0.7), (0.505, 0.49), (0.505, 0.75), 0.004)
    frame.circle((210, 176, 92), 0.545, 0.63, 0.008)
    frame.rect((176, 160, 138), 0.425, 0.745, 0.16, 0.025, radius=0.004)
    frame.rect((196, 178, 152), 0.405, 0.765, 0.20, 0.022, radius=0.004)
    frame.rect((70, 62, 54), 0.40, 0.545, 0.016, 0.04, radius=0.003)
    frame.rect(_WINDOW_GLOW, 0.403, 0.551, 0.011, 0.026, radius=0.003)

    # Garden path
    for index in range(4):
        y = 0.80 + index * 0.045
        width = 0.16 - index * 0.02
        frame.ellipse((198, 184, 158), 0.5 - width / 2 + index * 0.012, y, width, 0.03)

    # Picket fences and gate
    _pickets(frame, 0.04, 0.30, 0.79, 0.16)
    _pickets(frame, 0.70, 0.96, 0.79, 0.16)

    # Shrubs and mailbox
    _bush(frame, 0.22, 0.72, 0.04, (64, 116, 68))
    _bush(frame, 0.80, 0.73, 0.035, (74, 128, 74))
    frame.rect((96, 76, 62), 0.90, 0.62, 0.012, 0.15)
    frame.rect((84, 66, 56), 0.885, 0.585, 0.045, 0.04, radius=0.008)
    frame.rect((206, 196, 178), 0.889, 0.592, 0.037, 0.026, radius=0.004)
    frame.rect((206, 70, 64), 0.945, 0.592, 0.008, 0.036)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


PLACE_ASSETS: dict[LocationType, PlaceAsset] = {
    LocationType.MARKET: PlaceAsset("market", "Market", 3, _draw_market),
    LocationType.LIBRARY: PlaceAsset("library", "Library", 3, _draw_library),
    LocationType.CAFE: PlaceAsset("cafe", "Cafe", 3, _draw_cafe),
    LocationType.PARK: PlaceAsset("park", "Park", 3, _draw_park),
    LocationType.PARKING: PlaceAsset("parking", "Coach Yard", 3, _draw_parking),
    LocationType.RESIDENCE: PlaceAsset("residence", "Residence", 3, _draw_residence),
}

_GENERIC_ASSET = PlaceAsset("generic", "Building", 3, _draw_residence)


def get_place_asset(place_type: str) -> PlaceAsset:
    try:
        return PLACE_ASSETS[LocationType(place_type)]
    except ValueError:
        return _GENERIC_ASSET


def place_variant(place_type: str, seed: str) -> int:
    return get_place_asset(place_type).variant_for(f"{place_type}:{seed}")


@lru_cache(maxsize=96)
def _place_base(place_type: str, width: int, height: int, variant: int) -> pygame.Surface:
    asset = get_place_asset(place_type)
    surface = pygame.Surface((max(24, width), max(18, height)), pygame.SRCALPHA)
    asset.draw(Frame(surface, surface.get_rect()), variant % asset.variants)
    return surface


def render_place(
    place_type: str,
    size: tuple[int, int],
    variant: int = 0,
    tick: float = 0.0,
) -> pygame.Surface:
    """Return a fully composed scene, including its small ambient animation."""
    width, height = size
    base = _place_base(place_type, width, height, variant)
    frame = base.copy()
    _draw_ambient(frame, place_type, variant, tick)
    return frame


def _draw_ambient(surface: pygame.Surface, place_type: str, variant: int, tick: float) -> None:
    width, height = surface.get_size()
    asset = get_place_asset(place_type)
    if asset.key == "residence":
        _draw_smoke(surface, (0.705 * width, 0.118 * height), height, tick)
        glow(
            surface,
            (round(0.408 * width), round(0.565 * height)),
            round(height * 0.05),
            (255, 212, 140),
            46 + round(14 * math.sin(tick * 0.09)),
        )
    elif asset.key == "cafe":
        _draw_steam(surface, (0.755 * width, 0.83 * height), height, tick)
    elif asset.key == "market":
        flicker = 44 + round(16 * math.sin(tick * 0.12) + 6 * math.sin(tick * 0.31))
        glow(
            surface,
            (round(0.925 * width), round(0.335 * height)),
            round(height * 0.07),
            (255, 206, 120),
            flicker,
        )
    elif asset.key == "library":
        for x in (0.412, 0.588):
            glow(
                surface,
                (round(x * width), round(0.556 * height)),
                round(height * 0.055),
                (255, 214, 148),
                40,
            )
        glow(
            surface,
            (round(0.5 * width), round(0.75 * height)),
            round(height * 0.10),
            (255, 210, 140),
            22,
        )
    elif asset.key == "parking":
        flicker = 38 + round(16 * math.sin(tick * 0.16) + 8 * math.sin(tick * 0.43))
        glow(
            surface,
            (round(0.685 * width), round(0.445 * height)),
            round(height * 0.09),
            (255, 210, 130),
            flicker,
        )
    elif asset.key == "park":
        _draw_fireflies(surface, variant, tick)


def _draw_smoke(
    surface: pygame.Surface, origin: tuple[float, float], height: int, tick: float
) -> None:
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for index in range(4):
        phase = (tick * 0.008 + index * 0.24) % 1.0
        x = origin[0] + math.sin(phase * 5 + index) * height * 0.018
        y = origin[1] - phase * height * 0.20
        radius = max(2, round(height * (0.012 + phase * 0.024)))
        pygame.draw.circle(
            layer, (232, 232, 238, round(80 * (1 - phase))), (round(x), round(y)), radius
        )
    surface.blit(layer, (0, 0))


def _draw_steam(
    surface: pygame.Surface, origin: tuple[float, float], height: int, tick: float
) -> None:
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for index in range(3):
        phase = (tick * 0.014 + index * 0.33) % 1.0
        x = origin[0] + math.sin(phase * 6 + index * 1.7) * height * 0.012
        y = origin[1] - phase * height * 0.12
        radius = max(1, round(height * (0.006 + phase * 0.012)))
        pygame.draw.circle(
            layer, (245, 245, 248, round(70 * (1 - phase))), (round(x), round(y)), radius
        )
    surface.blit(layer, (0, 0))


def _draw_fireflies(surface: pygame.Surface, variant: int, tick: float) -> None:
    width, height = surface.get_size()
    colors = ((246, 226, 130), (222, 236, 140), (246, 206, 150))
    for index in range(5):
        phase = tick * 0.03 + index * 1.7 + variant
        x = (0.28 + 0.12 * math.sin(phase * 0.7 + index)) * width
        y = (0.58 + 0.08 * math.cos(phase * 0.9 + index * 1.3)) * height
        alpha = 40 + round(60 * (0.5 + 0.5 * math.sin(phase * 1.6)))
        glow(surface, (round(x), round(y)), max(2, round(height * 0.012)), colors[index % 3], alpha)


__all__ = [
    "PLACE_ASSETS",
    "PlaceAsset",
    "get_place_asset",
    "place_variant",
    "render_place",
]
