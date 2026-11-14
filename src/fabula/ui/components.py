import pygame
from typing import Callable, Any

class Panel:
    def __init__(self, rect: pygame.Rect, color: tuple[int, int, int] = (30, 30, 40), alpha: int = 200):
        self.rect = rect
        self.color = color
        self.alpha = alpha
        self.surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        self.surface.fill((*color, alpha))
        
    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.surface, self.rect)
        pygame.draw.rect(surface, (100, 100, 120), self.rect, 2, border_radius=8)

class Button:
    def __init__(self, rect: pygame.Rect, text: str, callback: Callable[[], Any], font: pygame.font.Font):
        self.rect = rect
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
    
    def update(self) -> None:
        pass
        
    def draw(self, surface: pygame.Surface) -> None:
        color = (100, 100, 150) if self.hovered else (50, 50, 80)
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        pygame.draw.rect(surface, (200, 200, 255), self.rect, 2, border_radius=5)
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

