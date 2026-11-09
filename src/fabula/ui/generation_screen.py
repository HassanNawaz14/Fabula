from __future__ import annotations

import pygame


class GenerationScreen:
    """Loading and progress screen before starting the simulation."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.status_message = "Preparing Game Bundle..."
        self.progress = 0.0
        self.error: str | None = None
        self.is_ready = False

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and self.is_ready:
                return "start_game"
        return None

    def update(self) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((20, 20, 30))
        try:
            font_title = pygame.font.Font(None, 48)
            font_body = pygame.font.Font(None, 24)
        except Exception:
            font_title = None
            font_body = None

        if font_title:
            title_surf = font_title.render("FABULA — Mystery Generation", True, (240, 240, 255))
            surface.blit(title_surf, (self.width // 2 - title_surf.get_width() // 2, 100))

        if self.error:
            if font_body:
                err_surf = font_body.render(f"Error: {self.error}", True, (255, 100, 100))
                surface.blit(err_surf, (self.width // 2 - err_surf.get_width() // 2, 220))
        else:
            if font_body:
                status_surf = font_body.render(self.status_message, True, (200, 200, 220))
                surface.blit(status_surf, (self.width // 2 - status_surf.get_width() // 2, 220))

                if self.is_ready:
                    prompt_surf = font_body.render(
                        "Press ENTER to Begin Investigation", True, (100, 255, 150)
                    )
                    surface.blit(prompt_surf, (self.width // 2 - prompt_surf.get_width() // 2, 300))
