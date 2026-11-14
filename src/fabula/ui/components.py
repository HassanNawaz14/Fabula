from __future__ import annotations

import pygame
from typing import Callable, Any

class Component:
    def __init__(self, rect: pygame.Rect):
        self.rect = rect
    
    def handle_event(self, event: pygame.event.Event) -> Any:
        pass
    
    def update(self) -> None:
        pass
    
    def draw(self, surface: pygame.Surface) -> None:
        pass

class Panel(Component):
    def __init__(self, rect: pygame.Rect, color: tuple[int, int, int] = (40, 40, 60), border: int = 2):
        super().__init__(rect)
        self.color = color
        self.border = border
        
    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, (100, 100, 150), self.rect, self.border)

class Button(Component):
    def __init__(self, rect: pygame.Rect, text: str, callback: Callable[[], Any], font: pygame.font.Font):
        super().__init__(rect)
        self.text = text
        self.callback = callback
        self.font = font
        self.hovered = False
        
    def handle_event(self, event: pygame.event.Event) -> Any:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                return self.callback()
        return None
    
    def draw(self, surface: pygame.Surface) -> None:
        color = (150, 150, 200) if self.hovered else (100, 100, 150)
        pygame.draw.rect(surface, color, self.rect)
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
