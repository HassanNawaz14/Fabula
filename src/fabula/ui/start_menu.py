from __future__ import annotations
from typing import Any
import pygame
from fabula.ui.components import Button, Panel

class StartMenuView:
    def __init__(self, width: int, height: int, app: Any) -> None:
        self.width = width
        self.height = height
        self.app = app
        
        self.font_title = pygame.font.Font(None, 60)
        self.font_button = pygame.font.Font(None, 30)
        
        button_w, button_h = 300, 50
        x = width // 2 - button_w // 2
        
        self.buttons = [
            Button(pygame.Rect(x, 150, button_w, button_h), "Play Dummy Game", lambda: "start_dummy", self.font_button),
            Button(pygame.Rect(x, 220, button_w, button_h), "Generate New Game (LLM)", lambda: "go_generation", self.font_button),
            Button(pygame.Rect(x, 290, button_w, button_h), f"Mode: {app.settings['conversation_mode']}", self._toggle_mode, self.font_button),
            Button(pygame.Rect(x, 360, button_w, button_h), "Settings", lambda: "go_settings", self.font_button),
            Button(pygame.Rect(x, 430, button_w, button_h), "Quit", lambda: "quit_game", self.font_button),
        ]

    def _toggle_mode(self) -> None:
        if self.app.settings["conversation_mode"] == "auto":
            self.app.settings["conversation_mode"] = "scripted"
        else:
            self.app.settings["conversation_mode"] = "auto"
        # Update button text
        self.buttons[2].text = f"Mode: {self.app.settings['conversation_mode']}"

    def handle_event(self, event: pygame.event.Event) -> str | None:
        for btn in self.buttons:
            res = btn.handle_event(event)
            if res: return res
        return None

    def update(self) -> None:
        for btn in self.buttons: btn.update()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((20, 20, 30))
        title = self.font_title.render("FABULA", True, (255, 100, 100))
        surface.blit(title, (self.width // 2 - title.get_width() // 2, 50))
        
        for btn in self.buttons:
            btn.draw(surface)
