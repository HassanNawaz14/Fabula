"""Illustrated backdrop and themed controls shared by the front-end screens."""

from __future__ import annotations

import math
from collections.abc import Callable
from functools import lru_cache
from typing import Any

import pygame

from fabula.ui.assets.common import Color, mix, shade

GOLD: Color = (246, 206, 116)
CREAM: Color = (252, 244, 224)
MUTED: Color = (196, 196, 186)
INK: Color = (18, 22, 26)

FONT_SCALE = 1.3


def ui_font(size: float, *, bold: bool = False) -> pygame.font.Font:
    """Build a UI font, applying the global readability multiplier."""
    font = pygame.font.Font(None, max(10, round(size * FONT_SCALE)))
    font.set_bold(bold)
    return font


def menu_button_width(text: str, font: pygame.font.Font, *, scale: float = 1.0) -> int:
    """Minimum width for a themed button so its label and chevron never clip."""
    return font.size(text)[0] + max(76, round(92 * scale))


def wrap_text(text: str, font: pygame.font.Font, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if current and font.size(trial)[0] > width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines or [""]


def humanize(text: str, replacements: dict[str, str]) -> str:
    """Swap internal ids (e.g. ``loc_library``) for their display names."""
    for key in sorted(replacements, key=len, reverse=True):
        text = text.replace(key, replacements[key])
    return text


def render_spaced(text: str, font: pygame.font.Font, color: Color, spacing: int) -> pygame.Surface:
    glyphs = [font.render(character, True, color) for character in text]
    width = sum(glyph.get_width() for glyph in glyphs) + spacing * max(0, len(glyphs) - 1)
    height = max(glyph.get_height() for glyph in glyphs)
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    x = 0
    for glyph in glyphs:
        surface.blit(glyph, (x, 0))
        x += glyph.get_width() + spacing
    return surface


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    fill: tuple[int, int, int, int] = (10, 14, 18, 228),
    border: Color = (146, 124, 84),
    radius: int = 14,
    shadow: bool = True,
) -> None:
    """Draw a framed card, with a soft drop shadow for depth."""
    if shadow:
        cast = rect.move(0, max(4, radius // 2))
        layer = pygame.Surface(cast.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (0, 0, 0, 110), layer.get_rect(), border_radius=radius)
        surface.blit(layer, cast.topleft)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=radius)
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, border, rect, 2, border_radius=radius)


def draw_centered_header(
    surface: pygame.Surface,
    width: int,
    top: int,
    overline: pygame.Surface,
    title: pygame.Surface,
    subtitle: pygame.Surface,
    *,
    scale: float = 1.0,
) -> None:
    """Blit an overline / title / subtitle stack, centred with flanking rules."""
    center = width // 2
    over_y = top
    surface.blit(overline, (center - overline.get_width() // 2, over_y))
    rule_y = over_y + overline.get_height() // 2
    rule_len = max(18, round(48 * scale))
    gap = max(8, round(14 * scale))
    left_end = center - overline.get_width() // 2 - gap
    right_start = center + (overline.get_width() + 1) // 2 + gap
    pygame.draw.line(surface, (112, 92, 58), (left_end - rule_len, rule_y), (left_end, rule_y), 1)
    pygame.draw.line(
        surface,
        (112, 92, 58),
        (right_start, rule_y),
        (right_start + rule_len, rule_y),
        1,
    )

    title_y = over_y + overline.get_height() + max(2, round(5 * scale))
    surface.blit(title, (center - title.get_width() // 2, title_y))
    subtitle_y = title_y + title.get_height() + max(2, round(4 * scale))
    surface.blit(subtitle, (center - subtitle.get_width() // 2, subtitle_y))


def _draw_sky(surface: pygame.Surface, width: int, height: int, horizon: int) -> None:
    top = (12, 16, 32)
    middle = (36, 38, 70)
    low = (92, 74, 88)
    for y in range(horizon):
        t = y / max(1, horizon - 1)
        if t < 0.55:
            color = mix(top, middle, t / 0.55)
        else:
            color = mix(middle, low, (t - 0.55) / 0.45)
        pygame.draw.line(surface, color, (0, y), (width, y))


def _draw_stars(surface: pygame.Surface, width: int, horizon: int) -> None:
    for index in range(150):
        x = (index * 7919 + 173) % width
        y = (index * 3571 + 41) % max(1, round(horizon * 0.93))
        radius = 1 + (index * 13) % 2
        brightness = 130 + (index * 47) % 110
        color = (brightness, brightness, min(255, brightness + 22))
        pygame.draw.circle(surface, color, (x, y), radius)


def _draw_moon(surface: pygame.Surface, width: int, height: int) -> None:
    radius = max(14, round(min(width, height) * 0.042))
    center = (round(width * 0.80), round(height * 0.19))
    halo = pygame.Surface((width, height), pygame.SRCALPHA)
    for ring in range(8, 0, -1):
        pygame.draw.circle(halo, (242, 232, 202, 9), center, radius + ring * radius // 2)
    surface.blit(halo, (0, 0))
    pygame.draw.circle(surface, (250, 242, 214), center, radius)
    pygame.draw.circle(
        surface,
        (232, 220, 188),
        (center[0] - radius // 3, center[1] - radius // 4),
        max(2, radius // 5),
    )
    pygame.draw.circle(
        surface,
        (228, 216, 184),
        (center[0] + radius // 4, center[1] + radius // 3),
        max(2, radius // 7),
    )


def _draw_hills(surface: pygame.Surface, width: int, height: int, horizon: int) -> None:
    for layer, color in enumerate(((22, 30, 42), (28, 38, 46))):
        points = [(0, horizon)]
        step = max(18, width // 16)
        for x in range(0, width + step, step):
            wave = math.sin(x * 0.0021 + layer * 1.7)
            points.append((x, horizon - round((0.012 + 0.024 * abs(wave)) * height) - layer * 6))
        points.extend([(width, horizon + 30), (0, horizon + 30)])
        pygame.draw.polygon(surface, color, points)


def _draw_town(
    surface: pygame.Surface, width: int, height: int, horizon: int, scale: float
) -> None:
    base_y = horizon + round(height * 0.018)
    x = round(width * 0.36)
    end_x = width - round(width * 0.035)
    index = 0
    while x < end_x:
        building_w = round((34 + (index * 29) % 54) * scale)
        building_h = round((44 + (index * 37) % 88) * scale)
        color = shade((30, 34, 44), 0.9 + 0.045 * (index % 3))
        body = pygame.Rect(x, base_y - building_h, building_w, building_h)
        pygame.draw.rect(surface, color, body)
        roof = [
            (body.left - round(4 * scale), body.top),
            (body.right + round(4 * scale), body.top),
            (body.centerx, body.top - round(building_h * 0.34)),
        ]
        pygame.draw.polygon(surface, shade(color, 1.14), roof)
        if index % 3 == 0:
            chimney = pygame.Rect(
                body.left + round(building_w * 0.66),
                body.top - round(building_h * 0.48),
                max(4, round(8 * scale)),
                round(building_h * 0.22),
            )
            pygame.draw.rect(surface, shade(color, 0.86), chimney)
        windows = 2 if building_w > 42 * scale else 1
        rows = 2 if building_h > 60 * scale else 1
        window_w = max(3, round(7 * scale))
        window_h = max(4, round(10 * scale))
        for row in range(rows):
            for col in range(windows):
                lit = (index * 7 + row * 3 + col) % 3 != 0
                window_color = (236, 194, 122) if lit else (46, 50, 60)
                wx = body.left + round(building_w * (col + 1) / (windows + 1)) - window_w // 2
                wy = body.top + round(building_h * (row + 1) / (rows + 1)) - window_h // 2
                pygame.draw.rect(
                    surface, window_color, (wx, wy, window_w, window_h), border_radius=1
                )
        x += building_w + round(10 * scale)
        index += 1

    tower_w = max(12, round(30 * scale))
    tower_h = max(40, round(150 * scale))
    tower_x = round(width * 0.55)
    tower_top = base_y - tower_h
    pygame.draw.rect(surface, (26, 30, 40), (tower_x, tower_top, tower_w, tower_h))
    spire = [
        (tower_x - round(7 * scale), tower_top),
        (tower_x + tower_w + round(7 * scale), tower_top),
        (tower_x + tower_w // 2, tower_top - round(46 * scale)),
    ]
    pygame.draw.polygon(surface, (24, 28, 38), spire)
    clock_radius = max(4, round(9 * scale))
    clock_center = (tower_x + tower_w // 2, tower_top + round(20 * scale))
    pygame.draw.circle(surface, (240, 218, 168), clock_center, clock_radius)
    pygame.draw.line(
        surface,
        (92, 74, 48),
        clock_center,
        (clock_center[0], clock_center[1] - clock_radius + 2),
        2,
    )
    pygame.draw.line(
        surface,
        (92, 74, 48),
        clock_center,
        (clock_center[0] + clock_radius - 2, clock_center[1] + 1),
        2,
    )


def _draw_figure(surface: pygame.Surface, x: int, feet_y: int, height: int, color: Color) -> None:
    head_radius = max(3, round(height * 0.10))
    body = [
        (x - round(height * 0.13), feet_y),
        (x + round(height * 0.13), feet_y),
        (x + round(height * 0.11), feet_y - round(height * 0.56)),
        (x - round(height * 0.11), feet_y - round(height * 0.56)),
    ]
    pygame.draw.polygon(surface, color, body)
    pygame.draw.circle(surface, color, (x, feet_y - round(height * 0.66)), head_radius)
    pygame.draw.rect(
        surface,
        color,
        (
            x - round(head_radius * 1.5),
            feet_y - round(height * 0.72),
            round(head_radius * 3.0),
            max(2, round(head_radius * 0.5)),
        ),
    )
    pygame.draw.rect(
        surface,
        color,
        (
            x - round(head_radius * 0.9),
            feet_y - round(height * 0.86),
            round(head_radius * 1.8),
            round(head_radius * 0.9),
        ),
    )
    pygame.draw.line(
        surface,
        color,
        (x - round(height * 0.05), feet_y),
        (x - round(height * 0.06), feet_y + round(height * 0.12)),
        max(2, round(height * 0.04)),
    )
    pygame.draw.line(
        surface,
        color,
        (x + round(height * 0.05), feet_y),
        (x + round(height * 0.06), feet_y + round(height * 0.12)),
        max(2, round(height * 0.04)),
    )


def _draw_tree(surface: pygame.Surface, x: int, base_y: int, size: int, color: Color) -> None:
    pygame.draw.rect(
        surface,
        shade(color, 0.82),
        (x - max(2, size // 18), base_y - size // 2, max(4, size // 9), size // 2),
    )
    for offset, radius in ((-0.20, 0.34), (0.20, 0.30), (0.0, 0.42)):
        pygame.draw.circle(
            surface,
            shade(color, 1.0 + offset * 0.2),
            (x + round(size * offset), base_y - round(size * 0.55)),
            round(size * radius),
        )


def _draw_ground(
    surface: pygame.Surface, width: int, height: int, horizon: int, scale: float
) -> None:
    ground_top = (26, 44, 36)
    ground_bottom = (10, 20, 20)
    for y in range(horizon, height):
        t = (y - horizon) / max(1, height - horizon - 1)
        pygame.draw.line(surface, mix(ground_top, ground_bottom, t), (0, y), (width, y))

    path = [
        (round(width * 0.58), height),
        (round(width * 0.69), height),
        (round(width * 0.75), horizon + round(height * 0.02)),
        (round(width * 0.70), horizon + round(height * 0.02)),
    ]
    pygame.draw.polygon(surface, (58, 54, 46), path)
    pygame.draw.polygon(surface, (92, 84, 70), path, 2)
    for index in range(10):
        t = (index + 1) / 12
        y = height - round((height - horizon) * t)
        center_x = round(width * (0.635 + 0.05 * t))
        pygame.draw.ellipse(
            surface,
            (82, 76, 64),
            (center_x - round(14 * scale), y - round(3 * scale), round(28 * scale), 4),
        )

    for side, x, size in (
        (0, round(width * 0.08), round(90 * scale)),
        (1, round(width * 0.93), round(120 * scale)),
        (2, round(width * 0.25), round(70 * scale)),
    ):
        _draw_tree(surface, x, horizon + round(height * (0.05 + side * 0.01)), size, (24, 40, 34))

    glow = pygame.Surface((width, height), pygame.SRCALPHA)
    lamp_y = horizon - round(height * 0.01)
    for index, x in enumerate((round(width * 0.53), round(width * 0.82))):
        post_h = round(95 * scale)
        base_x = x + index * round(8 * scale)
        for ring in range(6, 0, -1):
            pygame.draw.circle(
                glow,
                (255, 198, 120, 12),
                (base_x, lamp_y - post_h),
                round((post_h * 0.10) * (ring + 1)),
            )
        pygame.draw.rect(
            surface,
            (18, 22, 26),
            (base_x - 2, lamp_y - post_h, 4, post_h),
        )
        pygame.draw.rect(
            surface,
            (18, 22, 26),
            (base_x - round(10 * scale), lamp_y - post_h - 2, round(20 * scale), 5),
        )
        pygame.draw.circle(surface, (250, 214, 142), (base_x, lamp_y - post_h + 2), 4)
    surface.blit(glow, (0, 0))

    _draw_figure(
        surface,
        round(width * 0.65),
        round(height * 0.93),
        round(height * 0.13),
        (14, 18, 24),
    )
    _draw_figure(
        surface, round(width * 0.72), round(height * 0.97), round(height * 0.10), (18, 22, 28)
    )

    for index in range(90):
        x = (index * 2657 + 89) % width
        y = horizon + (index * 1453 + 301) % max(1, height - horizon)
        color = (46, 74, 54) if index % 2 else (32, 58, 44)
        pygame.draw.line(surface, color, (x, y), (x + 2, y - 5), 2)


@lru_cache(maxsize=8)
def render_menu_background(width: int, height: int) -> pygame.Surface:
    surface = pygame.Surface((width, height))
    scale = max(0.65, min(width / 1600, height / 900))
    horizon = round(height * 0.62)
    _draw_sky(surface, width, height, horizon)
    _draw_stars(surface, width, horizon)
    _draw_moon(surface, width, height)
    _draw_hills(surface, width, height, horizon)
    _draw_town(surface, width, height, horizon, scale)
    _draw_ground(surface, width, height, horizon, scale)
    return surface


class MenuBackdrop:
    """Static night-town artwork with a light animated atmosphere."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.base = render_menu_background(width, height)
        self._overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        self._motes = [
            (
                (index * 0.1373) % 1.0,
                0.34 + (index * 0.211) % 0.58,
                0.18 + (index % 5) * 0.07,
                1 + index % 2,
                index * 0.7,
            )
            for index in range(28)
        ]

    def draw(self, surface: pygame.Surface, tick: float) -> None:
        surface.blit(self.base, (0, 0))
        overlay = self._overlay
        overlay.fill((0, 0, 0, 0))
        for index in range(24):
            x = (index * 7919 + 173) % self.width
            y = (index * 3571 + 41) % max(1, round(self.height * 0.55))
            alpha = round(45 + 45 * math.sin(tick * 0.05 + index))
            pygame.draw.circle(overlay, (255, 248, 220, max(0, alpha)), (x, y), 2)
        for fraction_x, fraction_y, speed, size, phase in self._motes:
            x = (fraction_x * self.width + tick * speed) % self.width
            y = fraction_y * self.height + math.sin(tick * 0.03 + phase) * 9
            pygame.draw.circle(overlay, (246, 222, 158, 38), (round(x), round(y)), size)
        for index in range(2):
            drift = (tick * 0.00035 * (1 + index * 0.6) + index * 0.5) % 1.2 - 0.1
            fog = pygame.Rect(
                round(drift * self.width - self.width * 0.25),
                round(self.height * 0.60 + index * self.height * 0.035),
                round(self.width * 0.55),
                round(self.height * 0.05),
            )
            pygame.draw.ellipse(overlay, (196, 204, 214, 10), fog)
        surface.blit(overlay, (0, 0))


class MenuButton:
    """Dark parchment-style button with a bright primary variant."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        callback: Callable[[], Any],
        font: pygame.font.Font,
        *,
        primary: bool = False,
    ) -> None:
        self.rect = rect
        self.text = text
        self.callback = callback
        self.font = font
        self.primary = primary
        self.hovered = False

    def handle_event(self, event: pygame.event.Event) -> Any:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered:
            return self.callback()
        return None

    def update(self) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        panel = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        if self.primary:
            fill = (255, 224, 148, 255) if self.hovered else (238, 198, 110, 255)
            border = (255, 238, 188)
            text_color = (38, 30, 18)
        else:
            fill = (52, 44, 30, 238) if self.hovered else (16, 20, 24, 214)
            border = GOLD if self.hovered else (146, 124, 84)
            text_color = GOLD if self.hovered else CREAM
        pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=11)
        surface.blit(panel, self.rect.topleft)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=11)

        accent_x = self.rect.x + round(self.rect.width * 0.045)
        accent = pygame.Rect(accent_x, self.rect.centery - 8, 4, 16)
        pygame.draw.rect(
            surface,
            (92, 70, 38) if self.primary else (GOLD if self.hovered else (112, 96, 66)),
            accent,
            border_radius=2,
        )
        text_surface = self.font.render(self.text, True, text_color)
        surface.blit(
            text_surface,
            (
                accent_x + 22,
                self.rect.centery - text_surface.get_height() // 2,
            ),
        )
        chevron_x = self.rect.right - round(self.rect.width * 0.06)
        pygame.draw.lines(
            surface,
            text_color,
            False,
            [
                (chevron_x - 4, self.rect.centery - 5),
                (chevron_x + 2, self.rect.centery),
                (chevron_x - 4, self.rect.centery + 5),
            ],
            2,
        )
