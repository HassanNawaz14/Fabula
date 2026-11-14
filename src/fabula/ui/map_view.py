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
        self.font_small = pygame.font.Font(None, 18)
        self.font_title = pygame.font.Font(None, 40)
        
        self.panel = Panel(pygame.Rect(0, self.height - 80, self.width, 80))
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
        # Smaller grid layout
        locations = self.session.loaded.world.locations
        for i, loc in enumerate(locations):
            x = 150 + (i % 3) * 300
            y = 150 + (i // 3) * 200
            self.location_coords[loc.id] = (x, y)

    def _get_npc_rect(self, pos: tuple[int, int], i: int) -> pygame.Rect:
        return pygame.Rect(pos[0] - 60 + i*60 - 20, pos[1] + 20 + math.sin(self.tick * 0.1 + i) * 5 - 60, 40, 80)

    def handle_event(self, event: pygame.event.Event) -> str | dict[str, Any] | None:
        for btn in self.buttons:
            res = btn.handle_event(event)
            if res: return res

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check NPCs first
            npcs_here = self.session.npcs_at(self.session.player_location)
            pos = self.location_coords.get(self.session.player_location)
            if pos:
                for i, npc_id in enumerate(npcs_here):
                    if self._get_npc_rect(pos, i).collidepoint(event.pos):
                        return {"action": "talk_menu", "npc_id": npc_id}
            
            # Check locations
            for loc_id, (x, y) in self.location_coords.items():
                if pygame.Rect(x-60, y-60, 120, 120).collidepoint(event.pos):
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

    def _draw_npc(self, surface: pygame.Surface, pos: tuple[int, int], npc_id: str, npc_files: Any, i: int) -> None:
        role = npc_files.identity.role.lower() if npc_files else "vendor"
        color = (150, 200, 255)
        if "police" in role: color = (100, 100, 200)
        elif "baker" in role: color = (200, 150, 100)
        
        # Vertical-only wobble
        wobble_y = math.sin(self.tick * 0.1 + i) * 5
        npc_x = pos[0] - 60 + i*60
        npc_y = pos[1] + 20 + wobble_y
        
        # Figure
        pygame.draw.ellipse(surface, color, (npc_x-20, npc_y-60, 40, 50)) # Body
        pygame.draw.circle(surface, (255, 220, 180), (npc_x, npc_y-65), 15) # Head
        
        # Name and Role
        name = npc_files.identity.name if npc_files else "NPC"
        surf = self.font_small.render(name, True, (255, 255, 255))
        surface.blit(surf, (npc_x - surf.get_width()//2, npc_y+15))

    def _draw_building(self, surface: pygame.Surface, pos: tuple[int, int], loc_type: str, is_player: bool) -> None:
        rect = pygame.Rect(pos[0]-60, pos[1]-60, 120, 120)
        color = (100, 220, 140) if is_player else (100, 120, 150)
        pygame.draw.rect(surface, color, rect, border_radius=15)
        pygame.draw.rect(surface, (255, 255, 255), rect, 6, border_radius=15)
        
        # Detail
        pygame.draw.rect(surface, (60, 40, 30), (pos[0]-30, pos[1]-20, 60, 60), border_radius=10)
        
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((40, 50, 40))
        graph = location_graph(self.session.loaded.world)
        
        # Roads
        for loc_id, neighbors in graph.items():
            start = self.location_coords.get(loc_id)
            if not start: continue
            for n_id in neighbors:
                end = self.location_coords.get(n_id)
                if end and loc_id < n_id:
                    pygame.draw.line(surface, (80, 70, 60), start, end, 20)

        # Buildings & NPCs
        for loc in self.session.loaded.world.locations:
            pos = self.location_coords.get(loc.id)
            if not pos: continue
            self._draw_building(surface, pos, loc.type.value, loc.id == self.session.player_location)
            
            # Name
            name_surf = self.font_title.render(loc.name, True, (255, 255, 255))
            pygame.draw.rect(surface, (0,0,0,180), (pos[0]-name_surf.get_width()//2-10, pos[1]-100, name_surf.get_width()+20, 30), border_radius=10)
            surface.blit(name_surf, (pos[0] - name_surf.get_width() // 2, pos[1] - 95))
            
            # NPCs
            npcs_here = self.session.npcs_at(loc.id)
            for i, npc_id in enumerate(npcs_here):
                self._draw_npc(surface, pos, npc_id, self.session.loaded.npcs.get(npc_id), i)

        # UI
        self.panel.draw(surface)
        for btn in self.buttons: btn.draw(surface)
        
        # HUD
        title_surf = self.font_title.render(f"{self.session.loaded.world.mystery_type.value.capitalize()} Case", True, (255, 100, 100))
        surface.blit(title_surf, (20, 20))
        minute = self.session.clock.minute
        surface.blit(self.font.render(f"Time: {minute//60:02d}:{minute%60:02d}", True, (200, 200, 200)), (self.width - 150, 20))
        if self.status_message:
            surf = self.font.render(self.status_message, True, (255, 255, 200))
            surface.blit(surf, (self.width//2 - surf.get_width()//2, self.height - 110))
