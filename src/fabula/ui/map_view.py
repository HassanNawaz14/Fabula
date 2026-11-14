from __future__ import annotations
import math
import pygame
from typing import Any
from fabula.simulation import location_graph
from fabula.ui.components import Button, Panel

class MapView:
    """Renders the town with styled locations, roads, and animated NPCs."""

    def __init__(self, width: int, height: int, session: Any) -> None:
        self.width = width
        self.height = height
        self.session = session
        self.location_coords: dict[str, tuple[int, int]] = {}
        self.status_message: str | None = None
        self.status_timer = 0
        self.tick = 0
        self._init_layout()
        
        self.font = pygame.font.Font(None, 24)
        self.font_title = pygame.font.Font(None, 36)
        
        # HUD Panel
        self.panel = Panel(pygame.Rect(0, self.height - 80, self.width, 80))
        
        # Buttons
        self.buttons = [
            Button(pygame.Rect(40, self.height - 60, 120, 40), "Examine [E]", lambda: {"action": "examine_location"}, self.font),
            Button(pygame.Rect(180, self.height - 60, 120, 40), "Talk [T]", self._talk_action, self.font),
            Button(pygame.Rect(320, self.height - 60, 120, 40), "Journal [J]", lambda: {"action": "open_journal"}, self.font),
            Button(pygame.Rect(460, self.height - 60, 120, 40), "Accuse [A]", lambda: {"action": "open_accusation"}, self.font),
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
        locations = self.session.loaded.world.locations
        for i, loc in enumerate(locations):
            x = 150 + (i % 3) * 300
            y = 150 + (i // 3) * 200
            self.location_coords[loc.id] = (x, y)

    def handle_event(self, event: pygame.event.Event) -> str | dict[str, Any] | None:
        for btn in self.buttons:
            res = btn.handle_event(event)
            if res: return res

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for loc_id, (x, y) in self.location_coords.items():
                if pygame.Rect(x-60, y-40, 120, 80).collidepoint(event.pos):
                    if loc_id == self.session.player_location:
                        return {"action": "examine_menu"}
                    elif loc_id in location_graph(self.session.loaded.world).get(self.session.player_location, []):
                        return {"action": "move", "location_id": loc_id}

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_j: return {"action": "open_journal"}
            elif event.key == pygame.K_a: return {"action": "open_accusation"}
            elif event.key == pygame.K_t: return self._talk_action()
            elif event.key == pygame.K_e:
                self.status_message = "Examining..."
                self.status_timer = 60
                return {"action": "examine_location"}
        return None

    def update(self) -> None:
        self.tick += 1
        if self.status_timer > 0:
            self.status_timer -= 1
            if self.status_timer == 0: self.status_message = None
        for btn in self.buttons: btn.update()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((40, 50, 40)) # Grass ground

        # Roads
        graph = location_graph(self.session.loaded.world)
        for loc_id, neighbors in graph.items():
            start = self.location_coords.get(loc_id)
            if not start: continue
            for n_id in neighbors:
                end = self.location_coords.get(n_id)
                if end and loc_id < n_id:
                    pygame.draw.line(surface, (100, 90, 80), start, end, 15)
                    pygame.draw.line(surface, (120, 110, 100), start, end, 3)

        # Locations
        for loc in self.session.loaded.world.locations:
            pos = self.location_coords.get(loc.id)
            if not pos: continue
            
            # Pulse effect
            pulse = math.sin(self.tick * 0.1) * 5
            rect = pygame.Rect(pos[0]-60-pulse, pos[1]-40-pulse, 120+2*pulse, 80+2*pulse)
            
            color = (100, 200, 150) if loc.id == self.session.player_location else (60, 90, 140)
            pygame.draw.rect(surface, color, rect, border_radius=15)
            pygame.draw.rect(surface, (255, 255, 255), rect, 4, border_radius=15)
            
            name_surf = self.font.render(loc.name, True, (255, 255, 255))
            surface.blit(name_surf, (pos[0] - name_surf.get_width() // 2, pos[1] - 20))

            # Animated NPCs
            npcs_here = self.session.npcs_at(loc.id)
            for i, npc_id in enumerate(npcs_here):
                npc_pos = (pos[0] - 40 + i*30 + math.sin(self.tick*0.2 + i)*5, pos[1] + 20 + math.cos(self.tick*0.2 + i)*5)
                npc_surf = self.font.render("👤", True, (255, 220, 100))
                surface.blit(npc_surf, npc_pos)

        # UI
        self.panel.draw(surface)
        for btn in self.buttons: btn.draw(surface)
        
        title_surf = self.font_title.render(f"{self.session.loaded.world.mystery_type.value.capitalize()} Case", True, (255, 100, 100))
        surface.blit(title_surf, (20, 20))
        
        minute = self.session.clock.minute
        time_text = f"Time: {minute//60:02d}:{minute%60:02d}"
        surface.blit(self.font.render(time_text, True, (200, 200, 200)), (self.width - 150, 20))
        
        if self.status_message:
            surf = self.font.render(self.status_message, True, (255, 255, 200))
            surface.blit(surf, (self.width//2 - surf.get_width()//2, self.height - 120))
