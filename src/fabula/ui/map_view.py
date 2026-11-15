from __future__ import annotations

import math
from typing import Any

import pygame

from fabula.simulation import location_graph
from fabula.ui.assets import get_place_asset, place_variant, render_npc, render_place
from fabula.ui.assets.common import mix, shade
from fabula.ui.components import Button
from fabula.ui.menu_theme import ui_font

_GOLD = (246, 206, 116)
_CREAM = (252, 244, 224)
_MUTED = (196, 196, 186)
_INK = (18, 22, 26)
_SCENE_RATIO = 0.72
_PLAYER_ROLE = "detective"
_PLAYER_SEED = "player:detective"
_WALK_TICKS = 20
_EXAMINE_TICKS = 45


class MapView:
    """Full-screen town board with illustrated places and living NPCs."""

    def __init__(self, width: int, height: int, session: Any) -> None:
        self.width = width
        self.height = height
        self.session = session
        self.scale = max(0.72, min(width / 1600, height / 900))
        self.tick = 0
        self.status_message: str | None = None
        self.status_timer = 0
        self.mouse_pos: tuple[int, int] | None = None
        self.hovered_place: str | None = None
        self.hovered_npc: str | None = None

        self.location_coords: dict[str, tuple[int, int]] = {}
        self.place_rects: dict[str, pygame.Rect] = {}
        self.label_rects: dict[str, pygame.Rect] = {}
        self.npc_rects: list[tuple[str, str, pygame.Rect]] = []
        self._variants: dict[str, int] = {}
        self.player_rect: pygame.Rect | None = None
        self.examine_timer = 0
        self._last_location = session.player_location
        self._walk_from: pygame.Rect | None = None
        self._walk_timer = 0

        self._locations = list(session.loaded.world.locations)
        self._npcs = session.loaded.npcs
        self._roster = {entry.id: entry for entry in session.loaded.world.npcs}
        self._place_names = {loc.id: loc.name for loc in self._locations}
        self._graph = location_graph(session.loaded.world)

        self._init_fonts()
        self.hud_h = max(
            56,
            round(24 * self.scale)
            + self.font_hud_title.get_height()
            + self.font_hud_small.get_height(),
        )
        self.bar_h = max(72, round(94 * self.scale))
        self.label_h = max(
            36,
            self.font_place.get_height() + self.font_type.get_height() + round(14 * self.scale),
        )
        self._layout()
        self._background = self._render_background()
        self._build_buttons()
        self._layout_npcs()

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def _font(self, size: float, *, bold: bool = False) -> pygame.font.Font:
        return ui_font(size * self.scale, bold=bold)

    def _init_fonts(self) -> None:
        self.font_hud_title = self._font(32, bold=True)
        self.font_hud = self._font(30)
        self.font_hud_small = self._font(18)
        self.font_place = self._font(27, bold=True)
        self.font_place_small = self._font(18)
        self.font_type = self._font(15)
        self.font_button = self._font(22)
        self.font_npc = self._font(17, bold=True)
        self.font_npc_role = self._font(14)
        self.font_tooltip_title = self._font(23, bold=True)
        self.font_tooltip = self._font(17)
        self.font_toast = self._font(20)

    def _layout(self) -> None:
        count = len(self._locations)
        if count >= 4:
            cols = 2
        elif count == 3:
            cols = 3
        else:
            cols = max(1, count)
        rows = max(1, math.ceil(count / cols))

        margin = max(16, round(self.width * 0.03))
        top = self.hud_h + max(10, round(self.height * 0.028))
        bottom = self.height - self.bar_h - max(8, round(self.height * 0.014))
        usable_w = max(200, self.width - margin * 2)
        usable_h = max(160, bottom - top)
        gap = max(8, round(20 * self.scale))
        col_gap = round(28 * self.scale) if cols > 1 else 0
        row_gap = round(42 * self.scale) if rows > 1 else 0
        usable_w -= col_gap * (cols - 1)
        usable_h -= row_gap * (rows - 1)
        cell_w = usable_w / cols
        cell_h = usable_h / rows

        for index, loc in enumerate(self._locations):
            row, col = divmod(index, cols)
            cell = pygame.Rect(
                round(margin + col * (cell_w + col_gap)),
                round(top + row * (cell_h + row_gap)),
                round(cell_w),
                round(cell_h),
            )
            max_scene_w = cell.width - gap * 2
            max_scene_h = cell.height - self.label_h - gap * 2
            scene_w = min(max_scene_w, max_scene_h / _SCENE_RATIO)
            scene_w = max(120, scene_w)
            scene_h = scene_w * _SCENE_RATIO
            content_h = self.label_h + gap + scene_h
            start_y = cell.y + max(0, round((cell.height - content_h) / 2))
            label = pygame.Rect(
                round(cell.centerx - scene_w / 2),
                start_y,
                round(scene_w),
                self.label_h,
            )
            scene = pygame.Rect(
                round(cell.centerx - scene_w / 2),
                round(start_y + self.label_h + gap),
                round(scene_w),
                round(scene_h),
            )
            self.location_coords[loc.id] = scene.center
            self.place_rects[loc.id] = scene
            self.label_rects[loc.id] = label
            self._variants[loc.id] = place_variant(loc.type.value, f"{loc.id}:{loc.name}")

    def _build_buttons(self) -> None:
        bar_top = self.height - self.bar_h
        labels = (
            ("Examine [E]", lambda: {"action": "examine_location"}),
            ("Talk [T]", self._talk_action),
            ("Journal [J]", lambda: {"action": "open_journal"}),
            ("Accuse [A]", lambda: {"action": "open_accusation"}),
            ("Quit [Esc]", lambda: {"action": "quit_game"}),
        )
        button_h = max(34, round(46 * self.scale))
        gap = max(7, round(13 * self.scale))
        left = round(max(18, self.width * 0.02))
        widest = max(self.font_button.size(text)[0] for text, _ in labels)
        per_button = (self.width - left * 2 - gap * (len(labels) - 1)) // len(labels)
        button_w = max(96, min(widest + round(30 * self.scale), per_button))
        y = bar_top + (self.bar_h - button_h) // 2
        self.buttons = [
            Button(
                pygame.Rect(left + i * (button_w + gap), y, button_w, button_h),
                text,
                callback,
                self.font_button,
            )
            for i, (text, callback) in enumerate(labels)
        ]

    def _render_background(self) -> pygame.Surface:
        surface = pygame.Surface((self.width, self.height))
        top_color = (42, 72, 50)
        bottom_color = (68, 106, 66)
        for y in range(self.height):
            pygame.draw.line(
                surface,
                mix(top_color, bottom_color, y / max(1, self.height - 1)),
                (0, y),
                (self.width, y),
            )
        # Soft meadow patches and grass tufts.
        for index in range(130):
            x = (index * 7339 + 411) % self.width
            y = (index * 1847 + 97) % self.height
            radius = 8 + (index * 37) % max(8, round(26 * self.scale))
            color = mix(top_color, bottom_color, ((index * 53) % 100) / 100)
            pygame.draw.circle(surface, shade(color, 1.035 if index % 2 else 0.97), (x, y), radius)
        for index in range(150):
            x = (index * 2657 + 89) % self.width
            y = (index * 1453 + 301) % self.height
            color = (86, 128, 78) if index % 2 else (60, 98, 62)
            pygame.draw.line(surface, color, (x, y), (x + 2, y - 6), 2)
            pygame.draw.line(surface, color, (x + 4, y), (x + 3, y - 5), 2)
        return surface

    def _layout_npcs(self) -> None:
        self.npc_rects = []
        self.player_rect = None
        for loc in self._locations:
            scene = self.place_rects.get(loc.id)
            if scene is None:
                continue
            npc_ids = self.session.npcs_at(loc.id)
            player_here = loc.id == self.session.player_location
            if not npc_ids and not player_here:
                continue
            avatar_h = max(44, round(scene.height * 0.36))
            avatar_w = max(14, round(avatar_h * 0.62))
            feet_y = scene.bottom - round(scene.height * 0.015)
            npc_left = scene.left + avatar_w * 0.55
            if player_here:
                player_h = max(50, round(avatar_h * 1.1))
                player_w = max(16, round(player_h * 0.62))
                player_x = scene.left + max(player_w * 0.95, scene.width * 0.16)
                self.player_rect = pygame.Rect(
                    round(player_x - player_w / 2),
                    feet_y - player_h,
                    player_w,
                    player_h,
                )
                npc_left = player_x + player_w * 0.85
            npc_right = scene.right - avatar_w * 0.55
            if not npc_ids:
                continue
            count = len(npc_ids)
            spacing = min(avatar_w * 1.6, max(avatar_w, npc_right - npc_left) / count)
            start_x = (npc_left + npc_right) / 2 - (count - 1) * spacing / 2
            for index, npc_id in enumerate(npc_ids):
                center_x = start_x + index * spacing
                rect = pygame.Rect(
                    round(center_x - avatar_w / 2),
                    feet_y - avatar_h,
                    avatar_w,
                    avatar_h,
                )
                self.npc_rects.append((npc_id, loc.id, rect))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def _display_name(self, npc_id: str) -> str:
        files = self._npcs.get(npc_id)
        if files is not None:
            return files.identity.name
        entry = self._roster.get(npc_id)
        return entry.display_name if entry else npc_id

    def _role(self, npc_id: str) -> str:
        files = self._npcs.get(npc_id)
        role = files.identity.role if files is not None else "villager"
        return role[:1].upper() + role[1:] if role else "Villager"

    def _traits(self, npc_id: str) -> list[str]:
        files = self._npcs.get(npc_id)
        return list(files.identity.traits) if files is not None else []

    def _say(self, message: str, ticks: int = 90) -> None:
        self.status_message = message
        self.status_timer = ticks

    def _talk_action(self) -> dict[str, Any] | None:
        npcs = self.session.npcs_at(self.session.player_location)
        if not npcs:
            self._say("No one is here right now.")
            return None
        npc_id = npcs[self.session.npc_cycle_index % len(npcs)]
        self.session.npc_cycle_index += 1
        return {"action": "talk_menu", "npc_id": npc_id}

    def _refresh_hover(self) -> None:
        pos = self.mouse_pos
        if pos is None:
            pos = pygame.mouse.get_pos()
        self.hovered_npc = None
        self.hovered_place = None
        for npc_id, _loc_id, rect in reversed(self.npc_rects):
            if rect.collidepoint(pos):
                self.hovered_npc = npc_id
                return
        for loc_id, rect in self.place_rects.items():
            if rect.collidepoint(pos) or self.label_rects[loc_id].collidepoint(pos):
                self.hovered_place = loc_id
                return

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> str | dict[str, Any] | None:
        for btn in self.buttons:
            res = btn.handle_event(event)
            if res:
                return res

        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            self._refresh_hover()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event.pos)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_j:
                return {"action": "open_journal"}
            if event.key == pygame.K_a:
                return {"action": "open_accusation"}
            if event.key == pygame.K_t:
                return self._talk_action()
            if event.key == pygame.K_e:
                return {"action": "examine_location"}
            if event.key == pygame.K_ESCAPE:
                return {"action": "quit_game"}
        return None

    def _handle_click(self, pos: tuple[int, int]) -> str | dict[str, Any] | None:
        for npc_id, loc_id, rect in reversed(self.npc_rects):
            if not rect.collidepoint(pos):
                continue
            if loc_id == self.session.player_location:
                return {"action": "talk_menu", "npc_id": npc_id}
            self._say(f"{self._display_name(npc_id)} is over at {self._place_names[loc_id]}.")
            return None

        for loc_id, rect in self.place_rects.items():
            if not (rect.collidepoint(pos) or self.label_rects[loc_id].collidepoint(pos)):
                continue
            if loc_id == self.session.player_location:
                return {"action": "examine_menu"}
            if loc_id in self._graph.get(self.session.player_location, ()):
                return {"action": "move", "location_id": loc_id}
            self._say("Too far away — travel through a neighbouring place first.")
            return None
        return None

    # ------------------------------------------------------------------
    # Update / draw
    # ------------------------------------------------------------------

    def update(self) -> None:
        self.tick += 1
        if self.status_timer > 0:
            self.status_timer -= 1
            if self.status_timer == 0:
                self.status_message = None
        if self.examine_timer > 0:
            self.examine_timer -= 1
        for btn in self.buttons:
            btn.update()
        previous = self.player_rect.copy() if self.player_rect is not None else None
        previous_location = self._last_location
        self._layout_npcs()
        if previous is not None and self.player_rect is not None:
            if self.session.player_location != previous_location:
                self._walk_from = previous
                self._walk_timer = _WALK_TICKS
                self.examine_timer = 0
        self._last_location = self.session.player_location
        if self._walk_timer > 0:
            self._walk_timer -= 1
        self._refresh_hover()

    def start_examine_animation(self) -> None:
        self.examine_timer = _EXAMINE_TICKS
        self._walk_timer = 0
        self._walk_from = None

    def _player_display_rect(self) -> pygame.Rect | None:
        target = self.player_rect
        if target is None or self._walk_timer <= 0 or self._walk_from is None:
            return target
        progress = 1 - self._walk_timer / _WALK_TICKS
        eased = progress * progress * (3 - 2 * progress)
        x = round(self._walk_from.x + (target.x - self._walk_from.x) * eased)
        y = round(self._walk_from.y + (target.y - self._walk_from.y) * eased)
        return pygame.Rect(x, y, target.width, target.height)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._background, (0, 0))
        self._draw_roads(surface)
        for loc in self._locations:
            self._draw_place(surface, loc)
        self._draw_current_marker(surface)
        self._draw_npcs(surface)
        self._draw_player(surface)
        self._draw_examine_fx(surface)
        self._draw_hud(surface)
        self._draw_bottom_bar(surface)
        self._draw_status(surface)
        self._draw_tooltip(surface)

    def _draw_roads(self, surface: pygame.Surface) -> None:
        seen: set[tuple[str, str]] = set()
        road_w = max(8, round(min(self.width, self.height) * 0.021))
        for loc_id, neighbors in self._graph.items():
            for other in neighbors:
                key = tuple(sorted((loc_id, other)))
                if key in seen or key[0] not in self.place_rects or key[1] not in self.place_rects:
                    continue
                seen.add(key)
                start = self.place_rects[key[0]].center
                end = self.place_rects[key[1]].center
                self._draw_road(surface, start, end, key[0] + key[1], road_w)

    def _draw_road(
        self,
        surface: pygame.Surface,
        start: tuple[int, int],
        end: tuple[int, int],
        seed: str,
        width: int,
    ) -> None:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = max(1.0, math.hypot(dx, dy))
        bend = distance * (0.10 if sum(map(ord, seed)) % 2 else -0.10)
        mid = (
            (start[0] + end[0]) / 2 - dy / distance * bend,
            (start[1] + end[1]) / 2 + dx / distance * bend,
        )
        points = [start, mid, end]
        pygame.draw.lines(surface, (50, 72, 46), False, points, width + max(4, width // 3))
        pygame.draw.lines(surface, (182, 164, 132), False, points, width)
        pygame.draw.circle(surface, (182, 164, 132), (round(mid[0]), round(mid[1])), width // 2)
        self._draw_dashes(surface, (238, 226, 196), points, width)

    def _draw_dashes(
        self,
        surface: pygame.Surface,
        color: tuple[int, int, int],
        points: list[tuple[float, float]],
        road_width: int,
    ) -> None:
        dash = max(4, road_width * 0.9)
        gap = max(4, road_width * 0.8)
        line_width = max(2, road_width // 8)
        for start, end in zip(points, points[1:], strict=False):
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.hypot(dx, dy)
            if length < 1:
                continue
            ux, uy = dx / length, dy / length
            position = 0.0
            while position < length:
                segment_end = min(position + dash, length)
                pygame.draw.line(
                    surface,
                    color,
                    (start[0] + ux * position, start[1] + uy * position),
                    (start[0] + ux * segment_end, start[1] + uy * segment_end),
                    line_width,
                )
                position += dash + gap

    def _draw_place(self, surface: pygame.Surface, loc: Any) -> None:
        scene = self.place_rects[loc.id]
        is_current = loc.id == self.session.player_location
        if is_current:
            pulse = 0.5 + 0.5 * math.sin(self.tick * 0.08)
            halo = pygame.Surface(scene.inflate(28, 28).size, pygame.SRCALPHA)
            pygame.draw.rect(
                halo,
                (*_GOLD, round(34 + 26 * pulse)),
                halo.get_rect(),
                border_radius=24,
            )
            surface.blit(halo, scene.inflate(28, 28).topleft)

        art = render_place(loc.type.value, scene.size, self._variants[loc.id], self.tick)
        surface.blit(art, scene.topleft)

        if is_current:
            pygame.draw.rect(surface, _GOLD, scene.inflate(8, 8), 3, border_radius=18)
        elif self.hovered_place == loc.id:
            pygame.draw.rect(surface, (250, 250, 240), scene.inflate(6, 6), 2, border_radius=16)

        self._draw_place_label(surface, loc, is_current)

    def _draw_place_label(self, surface: pygame.Surface, loc: Any, is_current: bool) -> None:
        area = self.label_rects[loc.id]
        asset = get_place_asset(loc.type.value)
        name_surf = self.font_place.render(loc.name, True, _CREAM if not is_current else _GOLD)
        if name_surf.get_width() > area.width - 16:
            name_surf = self.font_place_small.render(loc.name, True, _CREAM)
        type_surf = self.font_type.render(asset.label.upper(), True, (206, 188, 140))
        width = min(area.width, max(name_surf.get_width(), type_surf.get_width()) + 28)
        height = name_surf.get_height() + type_surf.get_height() + 10
        pill = pygame.Rect(0, 0, width, height)
        pill.center = (area.centerx, area.centery)
        pill.clamp_ip(area.inflate(20, 30))

        background = pygame.Surface(pill.size, pygame.SRCALPHA)
        background.fill((20, 24, 28, 225) if not is_current else (58, 46, 26, 235))
        surface.blit(background, pill.topleft)
        scene_top = self.place_rects[loc.id].top
        if pill.bottom < scene_top:
            connector = _GOLD if is_current else (120, 124, 126)
            pygame.draw.line(
                surface,
                connector,
                (pill.centerx, pill.bottom),
                (pill.centerx, scene_top),
                2,
            )
        border = _GOLD if is_current else (120, 124, 126)
        pygame.draw.rect(surface, border, pill, 2, border_radius=12)
        surface.blit(name_surf, (pill.centerx - name_surf.get_width() // 2, pill.y + 5))
        surface.blit(
            type_surf,
            (pill.centerx - type_surf.get_width() // 2, pill.y + name_surf.get_height() + 6),
        )

    def _draw_current_marker(self, surface: pygame.Surface) -> None:
        scene = self.place_rects.get(self.session.player_location)
        if scene is None:
            return
        badge = pygame.Rect(0, 0, round(64 * self.scale), round(24 * self.scale))
        badge.topright = (scene.right - round(10 * self.scale), scene.top + round(10 * self.scale))
        pygame.draw.rect(surface, _GOLD, badge, border_radius=8)
        text = self.font_npc_role.render("HERE", True, (40, 32, 18))
        surface.blit(
            text, (badge.centerx - text.get_width() // 2, badge.centery - text.get_height() // 2)
        )

    def _draw_npcs(self, surface: pygame.Surface) -> None:
        for index, (npc_id, loc_id, rect) in enumerate(self.npc_rects):
            files = self._npcs.get(npc_id)
            role = files.identity.role if files is not None else "villager"
            avatar = render_npc(role, npc_id, rect.height, self.tick)
            bob = math.sin(self.tick * 0.09 + index * 1.3) * (2.0 + 2.0 * self.scale)
            position = (rect.x, round(rect.y + bob))
            surface.blit(avatar, position)
            self._draw_npc_label(surface, npc_id, rect, round(bob), loc_id, index)

    def _draw_npc_label(
        self,
        surface: pygame.Surface,
        npc_id: str,
        rect: pygame.Rect,
        bob: int,
        loc_id: str,
        index: int,
    ) -> None:
        name = self._display_name(npc_id)
        role = self._role(npc_id)
        name_surf = self.font_npc.render(name, True, _CREAM)
        role_surf = self.font_npc_role.render(role, True, (206, 204, 190))
        width = max(name_surf.get_width(), role_surf.get_width()) + 16
        height = name_surf.get_height() + role_surf.get_height() + 6
        stagger = (height + 6) * (index % 2)
        pill = pygame.Rect(
            round(rect.centerx - width / 2),
            rect.y + bob - height - 4 - stagger,
            width,
            height,
        )
        background = pygame.Surface(pill.size, pygame.SRCALPHA)
        background.fill((18, 22, 26, 205))
        surface.blit(background, pill.topleft)
        if self.hovered_npc == npc_id:
            pygame.draw.rect(surface, _GOLD, pill, 2, border_radius=8)
        if loc_id == self.session.player_location:
            pygame.draw.circle(surface, (126, 220, 150), (pill.left - 6, pill.centery), 3)
        surface.blit(name_surf, (pill.centerx - name_surf.get_width() // 2, pill.y + 2))
        surface.blit(
            role_surf,
            (pill.centerx - role_surf.get_width() // 2, pill.y + name_surf.get_height() + 2),
        )

    def _draw_player(self, surface: pygame.Surface) -> None:
        rect = self._player_display_rect()
        if rect is None:
            return
        walking = self._walk_timer > 0
        bob = math.sin(self.tick * (0.36 if walking else 0.09)) * (
            (3.2 if walking else 1.1) * self.scale
        )
        halo = pygame.Surface(
            (max(6, round(rect.width * 2.2)), max(4, round(rect.height * 0.2))),
            pygame.SRCALPHA,
        )
        pygame.draw.ellipse(halo, (*_GOLD, 54), halo.get_rect())
        surface.blit(
            halo,
            (
                round(rect.centerx - halo.get_width() / 2),
                round(rect.bottom - halo.get_height() * 0.55 + bob),
            ),
        )
        avatar = render_npc(_PLAYER_ROLE, _PLAYER_SEED, rect.height, self.tick)
        if self.examine_timer > 0:
            avatar = pygame.transform.smoothscale(
                avatar,
                (round(rect.width * 1.08), round(rect.height * 0.92)),
            )
        surface.blit(
            avatar,
            (
                round(rect.centerx - avatar.get_width() / 2),
                round(rect.bottom - avatar.get_height() + bob),
            ),
        )
        self._draw_player_label(surface, rect, round(bob))

    def _draw_player_label(self, surface: pygame.Surface, rect: pygame.Rect, bob: int) -> None:
        title = self.font_npc.render("Detective", True, _GOLD)
        subtitle = self.font_npc_role.render("You", True, (238, 220, 176))
        width = max(title.get_width(), subtitle.get_width()) + 16
        height = title.get_height() + subtitle.get_height() + 6
        pill = pygame.Rect(
            round(rect.centerx + rect.width * 0.25 - width),
            rect.y + bob - height - 4,
            width,
            height,
        )
        background = pygame.Surface(pill.size, pygame.SRCALPHA)
        background.fill((20, 17, 12, 222))
        surface.blit(background, pill.topleft)
        pygame.draw.rect(surface, _GOLD, pill, 2, border_radius=8)
        surface.blit(title, (pill.centerx - title.get_width() // 2, pill.y + 2))
        surface.blit(
            subtitle,
            (pill.centerx - subtitle.get_width() // 2, pill.y + title.get_height() + 2),
        )

    def _draw_examine_fx(self, surface: pygame.Surface) -> None:
        if self.examine_timer <= 0:
            return
        rect = self._player_display_rect()
        scene = self.place_rects.get(self.session.player_location)
        if rect is None or scene is None:
            return
        progress = 1 - self.examine_timer / _EXAMINE_TICKS
        radius = max(7, round(scene.height * 0.065))

        wave = max(6, round(rect.width * (0.85 + 1.5 * progress)))
        ring = pygame.Surface((wave * 2 + 4, wave + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(
            ring,
            (*_GOLD, round(96 * (1 - progress))),
            ring.get_rect(),
            max(2, round(3 * self.scale)),
        )
        surface.blit(
            ring,
            (
                round(rect.centerx - ring.get_width() / 2),
                round(rect.bottom - ring.get_height() * 0.7),
            ),
        )

        hand = (rect.centerx + round(rect.width * 0.32), rect.bottom - round(rect.height * 0.34))
        sway = math.sin(progress * math.tau) * radius * 0.5
        lens_x = hand[0] + round(radius * 1.1 + sway)
        lens_y = hand[1] + round(radius * 0.5 + math.cos(progress * math.tau * 2) * radius * 0.16)
        grip = (lens_x - round(radius * 0.7), lens_y + round(radius * 0.72))
        pygame.draw.line(surface, (74, 54, 36), hand, grip, max(2, round(radius * 0.3)))
        pygame.draw.line(surface, (150, 112, 64), hand, grip, max(1, round(radius * 0.12)))

        lens = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        center = (lens.get_width() // 2, lens.get_height() // 2)
        pygame.draw.circle(lens, (196, 224, 224, 112), center, radius)
        pygame.draw.circle(lens, (246, 214, 140, 240), center, radius, max(2, radius // 4))
        pygame.draw.line(
            lens,
            (250, 250, 244, 210),
            (center[0] - radius // 3, center[1] - radius // 3),
            (center[0] + radius // 5, center[1] - radius // 2),
            max(1, radius // 6),
        )
        surface.blit(lens, (lens_x - center[0], lens_y - center[1]))

        for index in range(4):
            angle = progress * math.tau * 1.6 + index * math.pi / 2
            sparkle = max(
                1, round(radius * (0.16 + 0.08 * math.sin(progress * math.tau * 3 + index)))
            )
            pygame.draw.circle(
                surface,
                (255, 238, 176),
                (
                    round(lens_x + math.cos(angle) * radius * 1.4),
                    round(lens_y + math.sin(angle) * radius * 1.1),
                ),
                sparkle,
            )

    def _draw_hud(self, surface: pygame.Surface) -> None:
        hud = pygame.Surface((self.width, self.hud_h), pygame.SRCALPHA)
        hud.fill((14, 18, 22, 214))
        surface.blit(hud, (0, 0))
        pygame.draw.line(
            surface, (94, 82, 58), (0, self.hud_h - 1), (self.width, self.hud_h - 1), 2
        )

        world = self.session.loaded.world
        title = self.font_hud_title.render(world.town_name, True, _GOLD)
        subtitle = self.font_hud_small.render(
            f"{world.mystery_type.value.title()} case · {world.title}",
            True,
            _MUTED,
        )
        block_h = title.get_height() + subtitle.get_height() + 2
        block_y = (self.hud_h - block_h) // 2
        surface.blit(title, (round(self.width * 0.02), block_y))
        surface.blit(subtitle, (round(self.width * 0.02), block_y + title.get_height() + 2))

        minute = self.session.clock.minute
        clock_surf = self.font_hud.render(f"{minute // 60:02d}:{minute % 60:02d}", True, _CREAM)
        place = self._place_names.get(self.session.player_location, "")
        location_surf = self.font_hud_small.render(f"You are at {place}", True, _MUTED)
        right = self.width - round(self.width * 0.02)
        right_h = clock_surf.get_height() + location_surf.get_height() + 2
        right_y = (self.hud_h - right_h) // 2
        surface.blit(clock_surf, (right - clock_surf.get_width(), right_y))
        surface.blit(
            location_surf,
            (right - location_surf.get_width(), right_y + clock_surf.get_height() + 2),
        )

    def _draw_bottom_bar(self, surface: pygame.Surface) -> None:
        bar_top = self.height - self.bar_h
        bar = pygame.Surface((self.width, self.bar_h), pygame.SRCALPHA)
        bar.fill((14, 18, 22, 220))
        surface.blit(bar, (0, bar_top))
        pygame.draw.line(surface, (86, 76, 56), (0, bar_top), (self.width, bar_top), 2)
        for btn in self.buttons:
            btn.draw(surface)

        hint = self.font_type.render(
            "Click a place to walk · click your place to examine · hover for details",
            True,
            (156, 156, 148),
        )
        hint_x = self.width - hint.get_width() - round(self.width * 0.02)
        if hint.get_width() < self.width * 0.42 and hint_x > self.buttons[-1].rect.right + 12:
            surface.blit(
                hint,
                (
                    hint_x,
                    bar_top + self.bar_h // 2 - hint.get_height() // 2,
                ),
            )

    def _draw_status(self, surface: pygame.Surface) -> None:
        if not self.status_message:
            return
        text = self.font_toast.render(self.status_message, True, (255, 240, 200))
        width = text.get_width() + 34
        height = text.get_height() + 18
        rect = pygame.Rect(0, 0, width, height)
        rect.center = (self.width // 2, self.height - self.bar_h - height)
        background = pygame.Surface(rect.size, pygame.SRCALPHA)
        background.fill((26, 24, 20, 232))
        surface.blit(background, rect.topleft)
        pygame.draw.rect(surface, (170, 146, 92), rect, 2, border_radius=10)
        surface.blit(
            text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2)
        )

    def _draw_tooltip(self, surface: pygame.Surface) -> None:
        if self.hovered_npc:
            info = self._npc_tooltip(self.hovered_npc)
        elif self.hovered_place:
            info = self._place_tooltip(self.hovered_place)
        else:
            return
        title, subtitle, body, action = info

        max_width = min(round(430 * self.scale), round(self.width * 0.42))
        title_surf = self.font_tooltip_title.render(title, True, _CREAM)
        subtitle_surf = self.font_tooltip.render(subtitle, True, (206, 188, 140))
        lines = self._wrap(body, self.font_tooltip, max_width - 24, 3)
        body_surfs = [self.font_tooltip.render(line, True, (218, 218, 210)) for line in lines]
        action_surf = self.font_type.render(action, True, (156, 212, 168))
        height = (
            title_surf.get_height()
            + subtitle_surf.get_height()
            + sum(line.get_height() for line in body_surfs)
            + action_surf.get_height()
            + 30
        )
        width = (
            max(
                title_surf.get_width(),
                subtitle_surf.get_width(),
                action_surf.get_width(),
                *(line.get_width() for line in body_surfs) if body_surfs else (0,),
            )
            + 24
        )
        width = min(width, max_width)

        anchor = self.mouse_pos or pygame.mouse.get_pos()
        x = anchor[0] + 20
        if x + width > self.width - 12:
            x = anchor[0] - width - 20
        x = max(12, min(x, self.width - width - 12))
        y = anchor[1] + 20
        if y + height > self.height - self.bar_h - 10:
            y = anchor[1] - height - 20
        y = max(self.hud_h + 8, min(y, self.height - self.bar_h - height - 8))

        rect = pygame.Rect(x, y, width, height)
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((18, 22, 26, 238))
        surface.blit(panel, rect.topleft)
        pygame.draw.rect(surface, (166, 150, 110), rect, 2, border_radius=10)

        cursor_y = rect.y + 9
        surface.blit(title_surf, (rect.x + 12, cursor_y))
        cursor_y += title_surf.get_height()
        surface.blit(subtitle_surf, (rect.x + 12, cursor_y))
        cursor_y += subtitle_surf.get_height() + 2
        for line in body_surfs:
            surface.blit(line, (rect.x + 12, cursor_y))
            cursor_y += line.get_height()
        surface.blit(action_surf, (rect.x + 12, cursor_y + 2))

    def _place_tooltip(self, loc_id: str) -> tuple[str, str, str, str]:
        loc = next(item for item in self._locations if item.id == loc_id)
        asset = get_place_asset(loc.type.value)
        if loc_id == self.session.player_location:
            action = "You are here — click to examine this place"
        elif loc_id in self._graph.get(self.session.player_location, ()):
            action = "Click to travel here"
        else:
            action = "Too far — travel through a neighbouring place first"
        return loc.name, asset.label, loc.description, action

    def _npc_tooltip(self, npc_id: str) -> tuple[str, str, str, str]:
        role = self._role(npc_id)
        traits = self._traits(npc_id)
        body = " · ".join(traits[:4]) if traits else "A local resident."
        location = next(
            (loc_id for found_id, loc_id, _rect in self.npc_rects if found_id == npc_id),
            None,
        )
        if location == self.session.player_location:
            action = "Click to talk"
        elif location is not None:
            action = f"Currently at {self._place_names.get(location, 'somewhere')}"
        else:
            action = "Not in town right now"
        return self._display_name(npc_id), role, body, action

    @staticmethod
    def _wrap(text: str, font: pygame.font.Font, max_width: int, max_lines: int) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            if current and font.size(trial)[0] > max_width:
                lines.append(current)
                current = word
                if len(lines) == max_lines:
                    break
            else:
                current = trial
        if len(lines) < max_lines and current:
            lines.append(current)
        if len(lines) == max_lines and words:
            last = lines[-1]
            ellipsis = "…"
            while last and font.size(last + ellipsis)[0] > max_width:
                last = last[:-1]
            lines[-1] = last + ellipsis
        return lines
