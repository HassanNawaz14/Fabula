from __future__ import annotations
from typing import Any
import pygame
from fabula.ui.components import Button, Panel

class SettingsView:
    def __init__(self, width: int, height: int, app: Any) -> None:
        self.width = width
        self.height = height
        self.app = app
        self.font = pygame.font.Font(None, 30)
        
        self.panel = Panel(pygame.Rect(width // 4, 100, width // 2, height - 200))
        self.back_button = Button(pygame.Rect(width // 2 - 100, height - 150, 200, 40), "Back to Menu", lambda: "back_to_menu", self.font)
        
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if self.back_button.handle_event(event):
            return "back_to_menu"
        return None

    def update(self) -> None:
        self.back_button.update()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((20, 20, 30))
        self.panel.draw(surface)
        
        title = self.font.render("Settings", True, (255, 255, 255))
        surface.blit(title, (self.width // 2 - title.get_width() // 2, 120))
        
        y = 180
        for key, value in self.app.settings.items():
            text = f"{key.replace('_', ' ').capitalize()}: {value}"
            surf = self.font.render(text, True, (200, 200, 200))
            surface.blit(surf, (self.width // 4 + 40, y))
            y += 40
            
        self.back_button.draw(surface)
