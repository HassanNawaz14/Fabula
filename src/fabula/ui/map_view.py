from __future__ import annotations

from typing import Any

import pygame

from fabula.simulation import location_graph
from fabula.ui.components import Button, Panel


class MapView:
    """Renders the world map, player/NPC locations, and action controls."""

    def __init__(self, width: int, height: int, session: Any) -> None:
        self.width = width
        self.height = height
        self.session = session
        # Compute layout positions for locations
        self.location_coords: dict[str, tuple[int, int]] = {}
        self.status_message: str | None = None
        self.status_timer = 0
        self._init_layout()
        
        self.font = pygame.font.Font(None, 20)
        self.font_title = pygame.font.Font(None, 32)
        
        self.panel = Panel(pygame.Rect(10, self.height - 80, self.width - 20, 70))
        self.buttons = [
            Button(pygame.Rect(20, self.height - 60, 100, 30), "Examine [E]", lambda: {"action": "examine_location"}, self.font),
            Button(pygame.Rect(130, self.height - 60, 100, 30), "Talk [T]", self._talk_action, self.font),
            Button(pygame.Rect(240, self.height - 60, 100, 30), "Journal [J]", lambda: {"action": "open_journal"}, self.font),
            Button(pygame.Rect(350, self.height - 60, 100, 30), "Accuse [A]", lambda: {"action": "open_accusation"}, self.font),
        ]

    def _talk_action(self) -> dict[str, Any] | None:
        npcs = self.session.npcs_at(self.session.player_location)
        if not npcs:
            self.status_message = "No NPCs here."
            self.status_timer = 60
            return None
        npc_id = npcs[self.session.npc_cycle_index % len(npcs)]
        self.session.npc_cycle_index += 1
        return {"action": "talk_menu", "npc_id": npc_id}

    def _init_layout(self) -> None:
        # Grid layout for locations
        locations = self.session.loaded.world.locations
        for i, loc in enumerate(locations):
            x = 150 + (i % 2) * 300
            y = 100 + (i // 2) * 150
            self.location_coords[loc.id] = (x, y)

    def handle_event(self, event: pygame.event.Event) -> str | dict[str, Any] | None:
        # Handle buttons
        for btn in self.buttons:
            res = btn.handle_event(event)
            if res:
                return res

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            # Check click on location nodes
            for loc_id, (x, y) in self.location_coords.items():
                rect = pygame.Rect(x-60, y-30, 120, 60)
                if rect.collidepoint(mouse_pos):
                    if loc_id == self.session.player_location:
                        return {"action": "examine_menu"}
                    elif loc_id in location_graph(self.session.loaded.world).get(
                        self.session.player_location, []
                    ):
                        return {"action": "move", "location_id": loc_id}

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_j:
                return {"action": "open_journal"}
            elif event.key == pygame.K_a:
                return {"action": "open_accusation"}
            elif event.key == pygame.K_t:
                return self._talk_action()
            elif event.key == pygame.K_e:
                self.status_message = "Examining..."
                self.status_timer = 60
                return {"action": "examine_location"}

        return None

    def update(self) -> None:
        if self.status_timer > 0:
            self.status_timer -= 1
            if self.status_timer == 0:
                self.status_message = None
        for btn in self.buttons:
            btn.update()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((30, 30, 45))
        
        # Draw connections (edges)
        graph = location_graph(self.session.loaded.world)
        for loc_id, neighbors in graph.items():
            start_pos = self.location_coords.get(loc_id)
            if not start_pos: continue
            for n_id in neighbors:
                end_pos = self.location_coords.get(n_id)
                if end_pos and loc_id < n_id:
                    pygame.draw.line(surface, (80, 80, 110), start_pos, end_pos, 4)

        # Draw locations as styled boxes
        for loc in self.session.loaded.world.locations:
            pos = self.location_coords.get(loc.id)
            if not pos: continue
            is_player_here = loc.id == self.session.player_location
            rect = pygame.Rect(pos[0]-60, pos[1]-30, 120, 60)
            color = (100, 220, 140) if is_player_here else (60, 90, 140)
            
            pygame.draw.rect(surface, color, rect, border_radius=10)
            pygame.draw.rect(surface, (255, 255, 255), rect, 3, border_radius=10)

            name_surf = self.font.render(loc.name, True, (255, 255, 255))
            surface.blit(name_surf, (pos[0] - name_surf.get_width() // 2, pos[1] - 15))

            # NPCs at this location with emojis
            npcs_here = self.session.npcs_at(loc.id)
            if npcs_here:
                npc_text = "👤" * len(npcs_here)
                npc_surf = self.font.render(npc_text, True, (255, 220, 100))
                surface.blit(npc_surf, (pos[0] - npc_surf.get_width() // 2, pos[1] + 10))

        # HUD
        self.panel.draw(surface)
        for btn in self.buttons:
            btn.draw(surface)
            
        # Draw mystery type at top
        mystery_text = f"Case: {self.session.loaded.world.mystery_type.value.capitalize()} | {self.session.loaded.world.title}"
        surface.blit(self.font_title.render(mystery_text, True, (255, 100, 100)), (20, 20))
        
        # HUD bottom info
        minute = self.session.clock.minute
        time_str = f"Time: {minute // 60:02d}:{minute % 60:02d}"
        hud_text = f"Location: {self.session.player_location} | {time_str}"
        surface.blit(self.font.render(hud_text, True, (220, 220, 240)), (20, self.height - 45))

        if self.status_message:
            surface.blit(self.font.render(self.status_message, True, (255, 255, 200)), (20, self.height - 90))
