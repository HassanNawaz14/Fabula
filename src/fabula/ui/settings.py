from __future__ import annotations

from typing import Any

import pygame

from fabula.ui.components import Button, Panel
from fabula.ui.menu_theme import ui_font


class SettingsView:
    def __init__(self, width: int, height: int, app: Any) -> None:
        self.width = width
        self.height = height
        self.app = app
        self.scale = max(0.9, min(width / 1600, height / 900))
        self.font = ui_font(30 * self.scale)
        self.title_font = ui_font(42 * self.scale, bold=True)
        self.row_h = max(44, round(54 * self.scale))

        self.panel = Panel(pygame.Rect(width // 4, 90, width // 2, height - 180))
        self.back_button = Button(
            pygame.Rect(width // 2 - 130, height - 130, 260, 54),
            "Back to Menu",
            lambda: "back_to_menu",
            self.font,
        )

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if self.back_button.handle_event(event):
            return "back_to_menu"
        return None

    def update(self) -> None:
        self.back_button.update()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((20, 20, 30))
        self.panel.draw(surface)

        title = self.title_font.render("Settings", True, (255, 255, 255))
        surface.blit(title, (self.width // 2 - title.get_width() // 2, 110))

        y = 190
        for key, value in self.app.settings.items():
            text = f"{key.replace('_', ' ').capitalize()}: {value}"
            surf = self.font.render(text, True, (200, 200, 200))
            surface.blit(surf, (self.width // 4 + 40, y))
            y += self.row_h

        self.back_button.draw(surface)
