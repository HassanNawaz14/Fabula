"""Shared drawing helpers for the procedural asset libraries."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

import pygame

Color = tuple[int, int, int]
Point = tuple[float, float]


def hash_index(seed: str, modulo: int) -> int:
    """Stable pseudo-random index so art never changes between launches."""
    if modulo <= 1:
        return 0
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % modulo


def shade(color: Color, factor: float) -> Color:
    return tuple(max(0, min(255, round(channel * factor))) for channel in color)  # type: ignore[return-value]


def mix(first: Color, second: Color, weight: float) -> Color:
    return tuple(  # type: ignore[return-value]
        round(a + (b - a) * weight) for a, b in zip(first, second, strict=True)
    )


class Frame:
    """A drawing surface addressed with normalised coordinates.

    All helpers take fractions of the frame's rect so the same artwork scales
    from a 200 px thumbnail to a 600 px fullscreen diorama.
    """

    def __init__(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        self.surface = surface
        self.area = rect

    def pt(self, fx: float, fy: float) -> tuple[int, int]:
        return (
            self.area.x + round(fx * self.area.width),
            self.area.y + round(fy * self.area.height),
        )

    def box(self, fx: float, fy: float, fw: float, fh: float) -> pygame.Rect:
        return pygame.Rect(
            self.area.x + round(fx * self.area.width),
            self.area.y + round(fy * self.area.height),
            round(fw * self.area.width),
            round(fh * self.area.height),
        )

    def unit(self, fraction: float) -> int:
        return max(1, round(fraction * min(self.area.width, self.area.height)))

    def rect(  # noqa: PLR0913
        self,
        color: Color,
        fx: float,
        fy: float,
        fw: float,
        fh: float,
        radius: float = 0.0,
        width: float = 0.0,
    ) -> None:
        pygame.draw.rect(
            self.surface,
            color,
            self.box(fx, fy, fw, fh),
            max(0, round(width * min(self.area.width, self.area.height))),
            border_radius=self.unit(radius),
        )

    def ellipse(self, color: Color, fx: float, fy: float, fw: float, fh: float) -> None:
        pygame.draw.ellipse(self.surface, color, self.box(fx, fy, fw, fh))

    def circle(self, color: Color, fx: float, fy: float, radius: float) -> None:
        pygame.draw.circle(self.surface, color, self.pt(fx, fy), self.unit(radius))

    def polygon(self, color: Color, points: Sequence[Point], width: float = 0.0) -> None:
        pygame.draw.polygon(
            self.surface,
            color,
            [self.pt(fx, fy) for fx, fy in points],
            max(0, round(width * min(self.area.width, self.area.height))),
        )

    def line(self, color: Color, start: Point, end: Point, width: float = 0.012) -> None:
        pygame.draw.line(
            self.surface,
            color,
            self.pt(*start),
            self.pt(*end),
            self.unit(width),
        )

    def lines(self, color: Color, points: Sequence[Point], width: float = 0.012) -> None:
        pygame.draw.lines(
            self.surface,
            color,
            False,
            [self.pt(fx, fy) for fx, fy in points],
            self.unit(width),
        )


def shadow(frame: Frame, fx: float, fy: float, fw: float, fh: float, alpha: int = 70) -> None:
    """Soft ground shadow beneath a building or avatar."""
    layer = pygame.Surface(frame.area.size, pygame.SRCALPHA)
    local = frame.box(fx, fy, fw, fh).move(-frame.area.x, -frame.area.y)
    pygame.draw.ellipse(layer, (0, 0, 0, alpha), local)
    frame.surface.blit(layer, frame.area.topleft)


def glow(
    surface: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    color: Color,
    alpha: int,
) -> None:
    """Cheap two-layer light bloom used for lamps, lanterns, and fireflies."""
    if radius <= 0 or alpha <= 0:
        return
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.circle(layer, (*color, alpha // 3), center, radius)
    pygame.draw.circle(layer, (*color, alpha), center, max(1, radius // 2))
    surface.blit(layer, (0, 0))


def scatter(
    frame: Frame,
    seed: str,
    count: int,
    area: tuple[float, float, float, float],
    colors: Sequence[Color],
    radius: tuple[float, float] = (0.004, 0.009),
) -> None:
    """Deterministic speckles: cobbles, grass tufts, pebbles, flowers."""
    fx, fy, fw, fh = area
    for index in range(count):
        x = fx + hash_index(f"{seed}:{index}:x", 1000) / 1000 * fw
        y = fy + hash_index(f"{seed}:{index}:y", 1000) / 1000 * fh
        size = radius[0] + hash_index(f"{seed}:{index}:s", 1000) / 1000 * (radius[1] - radius[0])
        color = colors[hash_index(f"{seed}:{index}:c", len(colors))]
        frame.circle(color, x, y, size)
