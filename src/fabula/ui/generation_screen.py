from __future__ import annotations

import pygame

from fabula.ui.menu_theme import ui_font


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
            if event.key == pygame.K_ESCAPE:
                return "back_to_menu"
            if event.key == pygame.K_RETURN and self.is_ready:
                return "start_game"
        return None

    def update(self) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((20, 20, 30))
        scale = max(0.9, min(self.width / 1600, self.height / 900))
        title = "FABULA — Mystery Generation"
        try:
            font_title = ui_font(48 * scale, bold=True)
            font_body = ui_font(24 * scale)
        except Exception:
            font_title = None
            font_body = None
        if font_title is not None:
            available = self.width - 80
            if font_title.size(title)[0] > available:
                font_title = ui_font(48 * scale * available / font_title.size(title)[0], bold=True)

        if font_title:
            title_surf = font_title.render(title, True, (240, 240, 255))
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

                hint_surf = font_body.render("ESC — Back to Menu", True, (150, 150, 160))
                surface.blit(
                    hint_surf,
                    (self.width // 2 - hint_surf.get_width() // 2, self.height - 80),
                )
