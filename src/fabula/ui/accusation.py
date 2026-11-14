from __future__ import annotations

from typing import Any

import pygame

from fabula.simulation import AccusationService
from fabula.ui.components import Button, Panel


class AccusationView:
    """Accusation deduction screen (who/how/why, 3 attempts)."""

    def __init__(self, width: int, height: int, session: Any) -> None:
        self.width = width
        self.height = height
        self.session = session
        self.accusation_service = AccusationService(
            session.loaded.accusation_truth(), session.loaded.world, clock=session.clock
        )

        # Options from bundle
        self.npcs = session.loaded.world.npcs
        self.methods = session.loaded.world.accusation_options.methods
        self.motives = session.loaded.world.accusation_options.motives

        self.selected_npc_idx = 0
        self.selected_method_idx = 0
        self.selected_motive_idx = 0
        self.message = ""
        self.game_over_status: str | None = None
        
        self.font_title = pygame.font.Font(None, 36)
        self.font_section = pygame.font.Font(None, 24)
        self.font_body = pygame.font.Font(None, 20)

        # UI Components
        self.panel = Panel(pygame.Rect(20, 80, width - 40, height - 200))
        self.submit_button = Button(pygame.Rect(width // 2 - 100, height - 100, 200, 40), "Submit Accusation", self._submit_accusation, self.font_section)
        self.exit_button = Button(pygame.Rect(width - 200, height - 60, 180, 40), "Back [ESC]", lambda: "back_to_map", self.font_section)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if self.game_over_status:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return "quit_game"
            return None

        if self.submit_button.handle_event(event):
            pass
        if self.exit_button.handle_event(event):
            return "back_to_map"

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back_to_map"
            # Cycle options (simplified for now to keep it usable)
            elif event.key == pygame.K_1:
                self.selected_npc_idx = (self.selected_npc_idx + 1) % len(self.npcs)
            elif event.key == pygame.K_2:
                self.selected_method_idx = (self.selected_method_idx + 1) % len(self.methods)
            elif event.key == pygame.K_3:
                self.selected_motive_idx = (self.selected_motive_idx + 1) % len(self.motives)
        return None

    def _submit_accusation(self) -> None:
        culprit = self.npcs[self.selected_npc_idx].id
        method = self.methods[self.selected_method_idx].id
        motive = self.motives[self.selected_motive_idx].id

        try:
            result = self.accusation_service.submit(culprit, method, motive)
            if result.correct:
                self.game_over_status = "VICTORY! You solved the mystery!"
            elif result.terminal:
                rem = result.attempts_remaining
                self.game_over_status = f"DEFEAT! Out of attempts (Remaining: {rem})"
            else:
                rem = result.attempts_remaining
                self.message = f"Incorrect accusation. Attempts remaining: {rem}"
        except Exception as e:
            self.message = f"Accusation error: {e}"

    def update(self) -> None:
        self.submit_button.update()
        self.exit_button.update()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((30, 20, 30))
        t = self.font_title.render("Formal Accusation (Who / How / Why)", True, (255, 150, 150))
        surface.blit(t, (30, 30))

        if self.game_over_status:
            go_surf = self.font_section.render(self.game_over_status, True, (255, 255, 100))
            surface.blit(go_surf, (30, 150))
            return

        self.panel.draw(surface)
        y = 100
        # Draw selection fields
        self._draw_field(surface, "1. Culprit", self.npcs[self.selected_npc_idx].display_name, y)
        y += 60
        self._draw_field(surface, "2. Method", self.methods[self.selected_method_idx].text, y)
        y += 60
        self._draw_field(surface, "3. Motive", self.motives[self.selected_motive_idx].text, y)
        y += 60
        
        if self.message:
            msg_surf = self.font_body.render(self.message, True, (255, 100, 100))
            surface.blit(msg_surf, (40, y))

        self.submit_button.draw(surface)
        self.exit_button.draw(surface)
        
        ctrl_text = "[1] Suspect [2] Method [3] Motive [ESC] Back"
        ctrl_surf = self.font_body.render(ctrl_text, True, (150, 150, 170))
        surface.blit(ctrl_surf, (30, self.height - 40))

    def _draw_field(self, surface, label, value, y):
        l_surf = self.font_section.render(label, True, (220, 220, 255))
        surface.blit(l_surf, (40, y))
        v_surf = self.font_body.render(f"> {value}", True, (255, 220, 100))
        surface.blit(v_surf, (60, y + 25))

