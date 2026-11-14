from __future__ import annotations

from typing import Any

import pygame


class JournalView:
    """Renders the player's journal, discovered clues, and timeline."""

    def __init__(self, width: int, height: int, session: Any) -> None:
        self.width = width
        self.height = height
        self.session = session

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_j):
                return "back_to_map"
        return None

    def update(self) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((20, 25, 35))
        try:
            font_title = pygame.font.Font(None, 36)
            font_section = pygame.font.Font(None, 24)
            font_body = pygame.font.Font(None, 18)
        except Exception:
            font_title = None
            font_section = None
            font_body = None

        if font_title:
            t_surf = font_title.render("Detective Journal & Notes", True, (240, 240, 255))
            surface.blit(t_surf, (30, 30))

        y = 90
        if font_section:
            clue_total = len(self.session.loaded.clues.clues)
            s1_text = f"Discovered Clues ({len(self.session.journal)} / {clue_total})"
            s1 = font_section.render(s1_text, True, (100, 255, 150))
            surface.blit(s1, (30, y))
            y += 30

        if font_body:
            if not self.session.journal:
                no_clue_text = "No clues discovered yet. Explore locations and talk to NPCs."
                surface.blit(
                    font_body.render(no_clue_text, True, (180, 180, 180)),
                    (40, y),
                )
                y += 30
            else:
                for entry in self.session.journal:
                    clue_obj = next(
                        (c for c in self.session.loaded.clues.clues if c.id == entry.clue_id),
                        None,
                    )
                    desc = clue_obj.description if clue_obj else entry.clue_id
                    line = f"• [Min {entry.minute}] {desc} (Source: {entry.source})"
                    surf = font_body.render(line[:120], True, (220, 220, 240))
                    surface.blit(surf, (40, y))
                    y += 25

        y += 20
        if font_section:
            s2 = font_section.render("Investigation Notes", True, (100, 200, 255))
            surface.blit(s2, (30, y))
            y += 30

        if font_body:
            notes = []
            for npc in self.session.loaded.world.npcs:
                for st in self.session.statements_for(npc.id):
                    notes.append(f"• [{npc.display_name}]: {st}")
            if not notes:
                no_note_text = "No notes recorded from NPC conversations yet."
                surface.blit(
                    font_body.render(no_note_text, True, (180, 180, 180)),
                    (40, y),
                )
            else:
                for note in notes[:5]:
                    surf = font_body.render(note[:120], True, (200, 200, 220))
                    surface.blit(surf, (40, y))
                    y += 22

        if font_section:
            exit_surf = font_section.render("[ESC or J] Return to Map", True, (180, 180, 180))
            surface.blit(exit_surf, (30, self.height - 50))
