"""The three ways to begin a case: ready bundle, Kaggle GPU, or local model."""

from __future__ import annotations

from typing import Any

import pygame

from fabula.ui.menu_theme import (
    CREAM,
    GOLD,
    MUTED,
    MenuBackdrop,
    MenuButton,
    draw_panel,
    ui_font,
    wrap_text,
)

_OPTIONS = (
    (
        "Play a Ready Case",
        "Open a mystery that is already written. Starts instantly, fully offline.",
        "open_case_library",
    ),
    (
        "Generate on Kaggle",
        "Uses your Kaggle GPU account. Usually about 6–8 minutes.",
        "start_kaggle_generation",
    ),
    (
        "Generate Locally",
        "Runs the local model on this PC. Time varies — often 30+ minutes.",
        "start_local_generation",
    ),
)


class NewGameView:
    """Choose between ready cases, a Kaggle run, or local generation."""

    def __init__(self, width: int, height: int, app: Any = None) -> None:
        self.width = width
        self.height = height
        self.app = app
        self.scale = max(0.65, min(width / 1600, height / 900))
        self.tick = 0

        self.font_overline = self._font(16, bold=True)
        self.font_title = self._font(54, bold=True)
        self.font_subtitle = self._font(20)
        self.font_button = self._font(22)
        self.font_caption = self._font(15)
        self.font_footer = self._font(14)

        self.backdrop = MenuBackdrop(width, height)
        self._dim = pygame.Surface((width, height), pygame.SRCALPHA)
        self._dim.fill((4, 8, 12, 120))
        self._layout()

    def _font(self, size: float, *, bold: bool = False) -> pygame.font.Font:
        return ui_font(size * self.scale, bold=bold)

    def _layout(self) -> None:
        scale = self.scale
        pad = max(18, round(28 * scale))
        self.button_h = max(46, round(60 * scale))
        gap = max(12, round(18 * scale))
        header_h = (
            self.font_overline.get_height()
            + self.font_title.get_height()
            + self.font_subtitle.get_height()
            + max(16, round(24 * scale))
        )
        content_h = 3 * (self.button_h + self.font_caption.get_height() + max(4, round(7 * scale)))
        content_h += 2 * gap
        hint_h = self.font_footer.get_height() + max(20, round(28 * scale))
        panel_w = min(round(780 * scale), round(self.width * 0.86))
        panel_h = header_h + content_h + hint_h + pad * 2
        self.panel = pygame.Rect(
            self.width // 2 - panel_w // 2,
            self.height // 2 - panel_h // 2,
            panel_w,
            panel_h,
        )
        self.panel.x = max(12, self.panel.x)
        self.panel.y = max(12, self.panel.y)

        self.buttons: list[MenuButton] = []
        y = self.panel.y + pad + header_h
        inner_w = self.panel.width - pad * 2
        self.captions: list[tuple[str, tuple[int, int]]] = []
        for label, caption, action in _OPTIONS:
            rect = pygame.Rect(self.panel.x + pad, y, inner_w, self.button_h)
            self.buttons.append(
                MenuButton(
                    rect, label, lambda a=action: a, self.font_button, primary=not self.buttons
                )
            )
            self.captions.append(
                (caption, (rect.x + round(rect.width * 0.045) + 22, rect.bottom + 3))
            )
            y += self.button_h + self.font_caption.get_height() + max(4, round(7 * scale)) + gap

    def handle_event(self, event: pygame.event.Event) -> str | None:
        for button in self.buttons:
            result = button.handle_event(event)
            if result:
                return result
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back_to_menu"
            if event.key in (pygame.K_1, pygame.K_KP1):
                return _OPTIONS[0][2]
            if event.key in (pygame.K_2, pygame.K_KP2):
                return _OPTIONS[1][2]
            if event.key in (pygame.K_3, pygame.K_KP3):
                return _OPTIONS[2][2]
        return None

    def update(self) -> None:
        self.tick += 1
        for button in self.buttons:
            button.update()

    def draw(self, surface: pygame.Surface) -> None:
        self.backdrop.draw(surface, self.tick)
        surface.blit(self._dim, (0, 0))
        draw_panel(surface, self.panel)

        center = self.panel.centerx
        y = self.panel.y + max(18, round(28 * self.scale))
        overline = self.font_overline.render("CASE SELECTION", True, GOLD)
        surface.blit(overline, (center - overline.get_width() // 2, y))
        y += overline.get_height() + max(2, round(4 * self.scale))
        title = self.font_title.render("NEW GAME", True, CREAM)
        surface.blit(title, (center - title.get_width() // 2, y))
        y += title.get_height() + max(2, round(4 * self.scale))
        subtitle = self.font_subtitle.render("Choose how this mystery comes to life.", True, MUTED)
        surface.blit(subtitle, (center - subtitle.get_width() // 2, y))

        for button in self.buttons:
            button.draw(surface)

        for caption, (x, y) in self.captions:
            for index, line in enumerate(
                wrap_text(caption, self.font_caption, self.panel.width - 2 * 40)
            ):
                text = self.font_caption.render(line, True, (176, 178, 168))
                surface.blit(text, (x, y + index * self.font_caption.get_height()))

        hint = self.font_footer.render("1–3 to choose  ·  Esc to go back", True, (140, 144, 138))
        surface.blit(
            hint,
            (
                center - hint.get_width() // 2,
                self.panel.bottom - hint.get_height() - max(10, round(16 * self.scale)),
            ),
        )


__all__ = ["NewGameView"]
