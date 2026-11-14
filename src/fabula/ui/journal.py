from __future__ import annotations

from typing import Any

import pygame

from fabula.ui.components import Button, Panel


class JournalView:
    """Renders the player's journal, discovered clues, and timeline."""

    def __init__(self, width: int, height: int, session: Any) -> None:
        self.width = width
        self.height = height
        self.session = session
        
        self.font_title = pygame.font.Font(None, 36)
        self.font_section = pygame.font.Font(None, 24)
        self.font_body = pygame.font.Font(None, 20)
        
        self.panel = Panel(pygame.Rect(20, 80, width - 40, height - 140))
        self.exit_button = Button(pygame.Rect(width - 200, height - 60, 180, 40), "Return [ESC/J]", lambda: "back_to_map", self.font_section)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if self.exit_button.handle_event(event):
            return "back_to_map"
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_j):
                return "back_to_map"
        return None

    def update(self) -> None:
        self.exit_button.update()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((20, 25, 35))
        
        t_surf = self.font_title.render("Detective Journal & Notes", True, (240, 240, 255))
        surface.blit(t_surf, (30, 30))

        self.panel.draw(surface)
        y = 100
        clue_total = len(self.session.loaded.clues.clues)
        s1_text = f"Discovered Clues ({len(self.session.journal)} / {clue_total})"
        s1 = self.font_section.render(s1_text, True, (100, 255, 150))
        surface.blit(s1, (40, y))
        y += 30

        if not self.session.journal:
            no_clue_text = "No clues discovered yet. Explore locations and talk to NPCs."
            surface.blit(self.font_body.render(no_clue_text, True, (180, 180, 180)), (50, y))
            y += 30
        else:
            for entry in self.session.journal:
                clue_obj = next(
                    (c for c in self.session.loaded.clues.clues if c.id == entry.clue_id),
                    None,
                )
                desc = clue_obj.description if clue_obj else entry.clue_id
                line = f"• [Min {entry.minute}] {desc} (Source: {entry.source})"
                surf = self.font_body.render(line[:100], True, (220, 220, 240))
                surface.blit(surf, (50, y))
                y += 25

        y += 20
        s2 = self.font_section.render("Investigation Notes", True, (100, 200, 255))
        surface.blit(s2, (40, y))
        y += 30

        notes = []
        for npc in self.session.loaded.world.npcs:
            for st in self.session.statements_for(npc.id):
                notes.append(f"• [{npc.display_name}]: {st}")
        
        if not notes:
            no_note_text = "No notes recorded from NPC conversations yet."
            surface.blit(self.font_body.render(no_note_text, True, (180, 180, 180)), (50, y))
        else:
            for note in notes[-5:]:
                surf = self.font_body.render(note[:100], True, (200, 200, 220))
                surface.blit(surf, (50, y))
                y += 22

        self.exit_button.draw(surface)

