from __future__ import annotations

from typing import Any

import pygame

from fabula.simulation import AccusationService


class AccusationView:
    """Accusation deduction screen (who/how/why, 3 attempts)."""

    def __init__(self, width: int, height: int, session: Any) -> None:
        self.width = width
        self.height = height
        self.session = session
        self.accusation_service = AccusationService(
            session.loaded.accusation_truth(),
            session.loaded.world,
            clock=session.clock
        )
        
        # Options from bundle
        self.npcs = session.loaded.world.npcs
        self.methods = session.loaded.world.accusation_options.methods
        self.motives = session.loaded.world.accusation_options.motives

        self.selected_npc_idx = 0
        self.selected_method_idx = 0
        self.selected_motive_idx = 0
        self.focus_field = 0  # 0: npc, 1: method, 2: motive, 3: submit button
        self.message = ""
        self.game_over_status: str | None = None

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if self.game_over_status:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return "quit_game"
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back_to_map"
            elif event.key == pygame.K_TAB:
                self.focus_field = (self.focus_field + 1) % 4
            elif event.key == pygame.K_UP:
                if self.focus_field == 0:
                    self.selected_npc_idx = (self.selected_npc_idx - 1) % len(self.npcs)
                elif self.focus_field == 1:
                    self.selected_method_idx = (self.selected_method_idx - 1) % len(self.methods)
                elif self.focus_field == 2:
                    self.selected_motive_idx = (self.selected_motive_idx - 1) % len(self.motives)
            elif event.key == pygame.K_DOWN:
                if self.focus_field == 0:
                    self.selected_npc_idx = (self.selected_npc_idx + 1) % len(self.npcs)
                elif self.focus_field == 1:
                    self.selected_method_idx = (self.selected_method_idx + 1) % len(self.methods)
                elif self.focus_field == 2:
                    self.selected_motive_idx = (self.selected_motive_idx + 1) % len(self.motives)
            elif event.key == pygame.K_RETURN:
                if self.focus_field == 3 or True:  # submit
                    self._submit_accusation()
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
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((30, 20, 30))
        try:
            font_title = pygame.font.Font(None, 36)
            font_section = pygame.font.Font(None, 24)
            font_body = pygame.font.Font(None, 18)
        except Exception:
            font_title = None
            font_section = None
            font_body = None

        if font_title:
            t = font_title.render("Formal Accusation (Who / How / Why)", True, (255, 150, 150))
            surface.blit(t, (30, 30))

        if self.game_over_status:
            if font_section:
                go_surf = font_section.render(self.game_over_status, True, (255, 255, 100))
                surface.blit(go_surf, (30, 150))
                ret_surf = font_section.render("Press ENTER to Exit", True, (200, 200, 200))
                surface.blit(ret_surf, (30, 200))
            return

        y = 90
        if font_section:
            sel_1 = "[SELECTED] " if self.focus_field == 0 else ""
            s1 = font_section.render(
                f"1. Culprit (Suspect): {sel_1}", True, (220, 220, 255)
            )
            surface.blit(s1, (30, y))
            y += 25
            npc_obj = self.npcs[self.selected_npc_idx]
            surface.blit(
                font_body.render(f"   > {npc_obj.display_name}", True, (255, 220, 100)),
                (40, y),
            )
            y += 40

            sel_2 = "[SELECTED] " if self.focus_field == 1 else ""
            s2 = font_section.render(
                f"2. Method: {sel_2}", True, (220, 220, 255)
            )
            surface.blit(s2, (30, y))
            y += 25
            meth_obj = self.methods[self.selected_method_idx]
            surface.blit(
                font_body.render(f"   > {meth_obj.text}", True, (255, 220, 100)),
                (40, y),
            )
            y += 40

            sel_3 = "[SELECTED] " if self.focus_field == 2 else ""
            s3 = font_section.render(
                f"3. Motive: {sel_3}", True, (220, 220, 255)
            )
            surface.blit(s3, (30, y))
            y += 25
            mot_obj = self.motives[self.selected_motive_idx]
            surface.blit(
                font_body.render(f"   > {mot_obj.text}", True, (255, 220, 100)),
                (40, y),
            )
            y += 50

            if self.message:
                msg_surf = font_body.render(self.message, True, (255, 100, 100))
                surface.blit(msg_surf, (30, y))
                y += 30

            btn_label = (
                "[> SUBMIT ACCUSATION <]"
                if self.focus_field == 3
                else "Submit Accusation"
            )
            used = self.accusation_service.attempts_used
            sub_text = f"{btn_label} (Attempts used: {used})"
            sub_surf = font_section.render(sub_text, True, (100, 255, 150))
            surface.blit(sub_surf, (30, y))

            ctrl_text = "[TAB] Field [UP/DOWN] Option [ENTER] Submit [ESC] Back"
            ctrl_surf = font_body.render(ctrl_text, True, (150, 150, 170))
            surface.blit(ctrl_surf, (30, self.height - 40))
