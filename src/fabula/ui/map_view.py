from __future__ import annotations

from typing import Any

import pygame

from fabula.simulation import location_graph


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

    def _init_layout(self) -> None:
        locations = self.session.loaded.world.locations
        n = len(locations)
        center_x, center_y = self.width // 2, self.height // 2 - 40
        radius = min(self.width, self.height) // 3
        import math

        for i, loc in enumerate(locations):
            angle = (2 * math.pi * i) / max(1, n)
            x = int(center_x + radius * math.cos(angle))
            y = int(center_y + radius * math.sin(angle))
            self.location_coords[loc.id] = (x, y)

    def handle_event(self, event: pygame.event.Event) -> str | dict[str, Any] | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            # Check click on location nodes
            for loc_id, (x, y) in self.location_coords.items():
                if (mouse_pos[0] - x) ** 2 + (mouse_pos[1] - y) ** 2 <= 35**2:
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
                npcs = self.session.npcs_at(self.session.player_location)
                if not npcs:
                    self.status_message = "No NPCs here."
                    self.status_timer = 60
                    return None
                npc_id = npcs[self.session.npc_cycle_index % len(npcs)]
                self.session.npc_cycle_index += 1
                return {"action": "talk_menu", "npc_id": npc_id}
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

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((30, 30, 45))
        try:
            font_title = pygame.font.Font(None, 32)
            font_body = pygame.font.Font(None, 20)
        except Exception:
            font_title = None
            font_body = None

        # Draw connections (edges)
        graph = location_graph(self.session.loaded.world)
        for loc_id, neighbors in graph.items():
            start_pos = self.location_coords.get(loc_id)
            if not start_pos:
                continue
            for n_id in neighbors:
                end_pos = self.location_coords.get(n_id)
                if end_pos and loc_id < n_id:  # draw once per edge
                    pygame.draw.line(surface, (80, 80, 110), start_pos, end_pos, 2)

        # Draw locations
        for loc in self.session.loaded.world.locations:
            pos = self.location_coords.get(loc.id)
            if not pos:
                continue
            is_player_here = loc.id == self.session.player_location
            color = (80, 200, 120) if is_player_here else (70, 100, 150)
            pygame.draw.circle(surface, color, pos, 35)
            pygame.draw.circle(surface, (255, 255, 255), pos, 35, 2)

            # NPCs at this location
            npcs_here = self.session.npcs_at(loc.id)
            npc_names = [
                n.display_name.split()[0]
                for n in self.session.loaded.world.npcs
                if n.id in npcs_here
            ]

            if font_title:
                name_surf = font_title.render(loc.name, True, (255, 255, 255))
                surface.blit(name_surf, (pos[0] - name_surf.get_width() // 2, pos[1] - 55))

            if font_body and npc_names:
                npc_surf = font_body.render(f"NPCs: {', '.join(npc_names)}", True, (255, 220, 100))
                surface.blit(npc_surf, (pos[0] - npc_surf.get_width() // 2, pos[1] + 40))

        # Draw mystery type at top
        if font_title:
            mystery_text = f"Case: {self.session.loaded.world.mystery_type.value.capitalize()}"
            m_surf = font_title.render(mystery_text, True, (255, 100, 100))
            # Display mystery description below the title
            surface.blit(m_surf, (self.width - 220, 20))

            desc_text = f"Objective: {self.session.loaded.world.title}"
            desc_surf = font_body.render(desc_text, True, (255, 255, 255))
            surface.blit(desc_surf, (self.width - 220, 50))

        # Status message
        if self.status_message and font_body:
            status_surf = font_body.render(self.status_message, True, (255, 255, 200))
            surface.blit(status_surf, (20, self.height - 90))

        # HUD bottom bar
        pygame.draw.rect(surface, (20, 20, 30), (0, self.height - 70, self.width, 70))
        pygame.draw.line(
            surface,
            (100, 100, 130),
            (0, self.height - 70),
            (self.width, self.height - 70),
            2,
        )

        if font_body:
            minute = self.session.clock.minute
            time_str = f"Time: {minute // 60:02d}:{minute % 60:02d} (Min {minute})"
            loc_name = next(
                (
                    loc_item.name
                    for loc_item in self.session.loaded.world.locations
                    if loc_item.id == self.session.player_location
                ),
                "",
            )
            hud_text = f"Location: {loc_name} | {time_str}"
            info_surf = font_body.render(hud_text, True, (220, 220, 240))
            surface.blit(info_surf, (20, self.height - 45))

            controls_text = "[Click adjacent to move] [E] Examine [T] Talk [J] Journal [A] Accuse"
            ctrl_surf = font_body.render(controls_text, True, (160, 180, 200))
            surface.blit(ctrl_surf, (20, self.height - 25))
