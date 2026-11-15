from __future__ import annotations

from typing import Any

import pygame

from fabula.simulation import AccusationService
from fabula.ui.assets import render_npc
from fabula.ui.menu_theme import (
    CREAM,
    GOLD,
    MUTED,
    MenuBackdrop,
    MenuButton,
    draw_centered_header,
    draw_panel,
    humanize,
    menu_button_width,
    render_spaced,
    ui_font,
    wrap_text,
)

_MAX_ATTEMPTS = 3


class AccusationView:
    """Formal accusation screen: who did it, how, and why."""

    def __init__(self, width: int, height: int, session: Any) -> None:
        self.width = width
        self.height = height
        self.session = session
        self.scale = max(0.65, min(width / 1600, height / 900))
        self.tick = 0
        self.accusation_service = AccusationService(
            session.loaded.accusation_truth(), session.loaded.world, clock=session.clock
        )

        world = session.loaded.world
        self._npcs = session.loaded.npcs
        self._places = {loc.id: loc.name for loc in world.locations}
        self.npcs = world.npcs
        self.methods = world.accusation_options.methods
        self.motives = world.accusation_options.motives

        self.selections = [0, 0, 0]
        self.active = 0
        self.hovered: tuple[int, int] | None = None
        self.message = "Choose one suspect, one method, and one motive."
        self.message_is_error = False
        self.game_over: str | None = None
        self.last_choice: tuple[str, str, str] | None = None

        self.font_overline = self._font(16)
        self.font_title = self._font(44, bold=True)
        self.font_subtitle = self._font(18)
        self.font_section = self._font(20, bold=True)
        self.font_name = self._font(20, bold=True)
        self.font_role = self._font(14)
        self.font_option = self._font(17)
        self.font_small = self._font(14)
        self.font_button = self._font(20)
        self.font_overlay_title = self._font(44, bold=True)
        self.font_overlay_body = self._font(20)

        self.backdrop = MenuBackdrop(width, height)
        self._dim = pygame.Surface((width, height), pygame.SRCALPHA)
        self._dim.fill((5, 4, 8, 158))

        margin_x = max(20, round(width * 0.035))
        self.header_top = max(14, round(height * 0.028))
        self.overline = render_spaced(
            "THE FINAL STEP", self.font_overline, (196, 166, 108), max(1, round(3 * self.scale))
        )
        self.title = render_spaced(
            "MAKE YOUR ACCUSATION", self.font_title, GOLD, max(2, round(4 * self.scale))
        )
        self.subtitle = self.font_subtitle.render(
            "Name the culprit, the method, and the motive — carefully.",
            True,
            MUTED,
        )
        header_bottom = (
            self.header_top
            + self.overline.get_height()
            + round(5 * self.scale)
            + self.title.get_height()
            + round(4 * self.scale)
            + self.subtitle.get_height()
        )

        self.message_h = max(34, round(40 * self.scale))
        self.message_rect = pygame.Rect(
            margin_x,
            header_bottom + round(12 * self.scale),
            width - margin_x * 2,
            self.message_h,
        )

        self.gap = max(10, round(18 * self.scale))
        self.footer_h = max(62, round(88 * self.scale))
        columns_top = self.message_rect.bottom + round(10 * self.scale)
        columns_bottom = height - self.footer_h - round(8 * self.scale)
        area = pygame.Rect(
            margin_x,
            columns_top,
            width - margin_x * 2,
            max(120, columns_bottom - columns_top),
        )
        col_w = (area.width - self.gap * 2) // 3
        self.column_rects = [
            pygame.Rect(area.x + index * (col_w + self.gap), area.y, col_w, area.height)
            for index in range(3)
        ]

        self.row_heights = [
            max(40, round(60 * self.scale)),
            max(44, round(56 * self.scale)),
            max(44, round(56 * self.scale)),
        ]
        row_gap = max(5, round(8 * self.scale))
        heading_h = max(26, round(36 * self.scale))
        self.row_rects: dict[tuple[int, int], pygame.Rect] = {}
        counts = [len(self.npcs), len(self.methods), len(self.motives)]
        for column, rect in enumerate(self.column_rects):
            y = rect.y + heading_h + round(4 * self.scale)
            inset = max(6, round(9 * self.scale))
            for index in range(counts[column]):
                row = pygame.Rect(
                    rect.x + inset,
                    y,
                    rect.width - inset * 2,
                    self.row_heights[column],
                )
                self.row_rects[(column, index)] = row
                y += self.row_heights[column] + row_gap

        button_h = max(36, round(46 * self.scale))
        button_y = height - self.footer_h + (self.footer_h - button_h) // 2
        back_w = max(
            150,
            menu_button_width("Back [Esc]", self.font_button, scale=self.scale),
        )
        self.back_button = MenuButton(
            pygame.Rect(margin_x, button_y, back_w, button_h),
            "Back [Esc]",
            lambda: "back_to_map",
            self.font_button,
        )
        submit_w = max(
            210,
            menu_button_width("Submit Accusation", self.font_button, scale=self.scale),
        )
        self.submit_button = MenuButton(
            pygame.Rect(width // 2 - submit_w // 2, button_y, submit_w, button_h),
            "Submit Accusation",
            self._submit_accusation,
            self.font_button,
            primary=True,
        )
        overlay_w = min(width - 80, round(720 * self.scale))
        self.overlay_rect = pygame.Rect(0, 0, overlay_w, max(250, round(300 * self.scale)))
        self.overlay_rect.center = (width // 2, height // 2)
        overlay_button_w = max(
            150,
            max(
                menu_button_width("Quit Game", self.font_button, scale=self.scale),
                menu_button_width("Back to Map", self.font_button, scale=self.scale),
            ),
        )
        overlay_button_y = self.overlay_rect.bottom - max(34, round(46 * self.scale)) - button_h
        self.quit_button = MenuButton(
            pygame.Rect(0, overlay_button_y, overlay_button_w, button_h),
            "Quit Game",
            lambda: "quit_game",
            self.font_button,
            primary=True,
        )
        self.quit_button.rect.centerx = self.overlay_rect.centerx - overlay_button_w // 2 - 12
        self.map_button = MenuButton(
            pygame.Rect(0, overlay_button_y, overlay_button_w, button_h),
            "Back to Map",
            lambda: "back_to_map",
            self.font_button,
        )
        self.map_button.rect.centerx = self.overlay_rect.centerx + overlay_button_w // 2 + 12

        self.footer_hint = self.font_small.render(
            "Up / Down choose · Left / Right switch column · Enter to accuse · Esc to go back",
            True,
            (150, 150, 142),
        )

    def _font(self, size: float, *, bold: bool = False) -> pygame.font.Font:
        return ui_font(size * self.scale, bold=bold)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    @property
    def attempts_remaining(self) -> int:
        return _MAX_ATTEMPTS - self.accusation_service.attempts_used

    def _display_name(self, npc_id: str) -> str:
        files = self._npcs.get(npc_id)
        return files.identity.name if files is not None else npc_id

    def _role(self, npc_id: str) -> str:
        files = self._npcs.get(npc_id)
        role = files.identity.role if files is not None else "villager"
        return role[:1].upper() + role[1:] if role else "Villager"

    def _cycle(self, column: int, delta: int = 1) -> None:
        counts = (len(self.npcs), len(self.methods), len(self.motives))
        self.selections[column] = (self.selections[column] + delta) % counts[column]

    def _submit_accusation(self) -> None:
        if self.game_over is not None:
            return
        culprit = self.npcs[self.selections[0]]
        method = self.methods[self.selections[1]]
        motive = self.motives[self.selections[2]]
        try:
            result = self.accusation_service.submit(culprit.id, method.id, motive.id)
        except Exception as error:  # surfaced in the message bar instead of crashing
            self.message = f"That accusation could not be filed: {error}"
            self.message_is_error = True
            return

        self.last_choice = (culprit.display_name, method.text, motive.text)
        if result.correct:
            self.game_over = "won"
            self.message = "Case closed."
            self.message_is_error = False
        elif result.terminal:
            self.game_over = "lost"
            self.message = "That was your final accusation."
            self.message_is_error = True
        else:
            remaining = result.attempts_remaining
            self.message = (
                f"That account does not hold up. "
                f"{remaining} accusation{'s' if remaining != 1 else ''} left."
            )
            self.message_is_error = True

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if self.game_over is not None:
            if self.quit_button.handle_event(event):
                return "quit_game"
            if self.map_button.handle_event(event):
                return "back_to_map"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return "quit_game"
                if event.key == pygame.K_ESCAPE:
                    return "back_to_map"
            return None

        if self.back_button.handle_event(event):
            return "back_to_map"
        self.submit_button.handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self.hovered = next(
                (key for key, rect in self.row_rects.items() if rect.collidepoint(event.pos)),
                None,
            )
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in self.row_rects.items():
                if rect.collidepoint(event.pos):
                    column, index = key
                    self.active = column
                    self.selections[column] = index
                    break
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back_to_map"
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._submit_accusation()
            elif event.key == pygame.K_TAB:
                self.active = (self.active + 1) % 3
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                delta = -1 if event.key == pygame.K_LEFT else 1
                self.active = (self.active + delta) % 3
            elif event.key in (pygame.K_UP, pygame.K_DOWN):
                delta = -1 if event.key == pygame.K_UP else 1
                self._cycle(self.active, delta)
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.active = event.key - pygame.K_1
                self._cycle(self.active)
        return None

    def update(self) -> None:
        self.tick += 1
        self.back_button.update()
        self.submit_button.update()
        self.quit_button.update()
        self.map_button.update()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        self.backdrop.draw(surface, self.tick)
        surface.blit(self._dim, (0, 0))
        draw_centered_header(
            surface,
            self.width,
            self.header_top,
            self.overline,
            self.title,
            self.subtitle,
            scale=self.scale,
        )
        self._draw_message(surface)
        for column in range(3):
            self._draw_column(surface, column)
        self._draw_footer(surface)
        if self.game_over is not None:
            self._draw_game_over(surface)

    def _draw_message(self, surface: pygame.Surface) -> None:
        draw_panel(
            surface,
            self.message_rect,
            fill=(14, 18, 22, 214),
            border=(96, 84, 60),
            radius=10,
            shadow=False,
        )
        color = (240, 150, 130) if self.message_is_error else (206, 202, 188)
        text = self.font_option.render(self.message, True, color)
        surface.blit(
            text,
            (
                self.message_rect.x + 14,
                self.message_rect.centery - text.get_height() // 2,
            ),
        )

        label = self.font_small.render("ATTEMPTS", True, (166, 156, 132))
        pips = 3
        pip_r = max(4, round(6 * self.scale))
        spacing = pip_r * 3
        right = self.message_rect.right - 14
        surface.blit(
            label, (right - label.get_width(), self.message_rect.centery - label.get_height() // 2)
        )
        start = right - label.get_width() - 12 - (pips - 1) * spacing
        for index in range(pips):
            center = (start + index * spacing, self.message_rect.centery)
            if index < self.attempts_remaining:
                pygame.draw.circle(surface, GOLD, center, pip_r)
            else:
                pygame.draw.circle(surface, (92, 84, 70), center, pip_r, 2)

    def _draw_column(self, surface: pygame.Surface, column: int) -> None:
        rect = self.column_rects[column]
        active = column == self.active and self.game_over is None
        draw_panel(
            surface,
            rect,
            fill=(11, 15, 19, 240),
            border=GOLD if active else (92, 84, 68),
            radius=12,
            shadow=False,
        )
        subtitle = ("SUSPECT", "METHOD", "MOTIVE")[column]
        heading = self.font_section.render(
            f"{column + 1} · {subtitle}", True, GOLD if active else CREAM
        )
        surface.blit(heading, (rect.x + 12, rect.y + max(6, round(8 * self.scale))))
        pygame.draw.line(
            surface,
            (104, 90, 62) if active else (70, 66, 58),
            (rect.x + 12, rect.y + max(26, round(32 * self.scale))),
            (rect.right - 12, rect.y + max(26, round(32 * self.scale))),
            1,
        )

        for index in range(len(self._options(column))):
            row = self.row_rects[(column, index)]
            self._draw_row(surface, column, index, row)

    def _options(self, column: int) -> list[Any]:
        return [self.npcs, self.methods, self.motives][column]

    def _draw_row(
        self, surface: pygame.Surface, column: int, index: int, rect: pygame.Rect
    ) -> None:
        selected = self.selections[column] == index
        hovered = self.hovered == (column, index)
        if selected:
            fill = (48, 40, 26, 240)
            border = GOLD
        elif hovered:
            fill = (26, 32, 38, 232)
            border = (176, 156, 112)
        else:
            fill = (18, 22, 26, 216)
            border = (62, 60, 54)
        pygame.draw.rect(surface, fill, rect, border_radius=9)
        pygame.draw.rect(surface, border, rect, 2 if selected else 1, border_radius=9)
        if selected:
            pygame.draw.rect(surface, GOLD, (rect.x + 4, rect.y + 6, 3, rect.height - 12), 3)

        if column == 0:
            npc = self.npcs[index]
            avatar_h = max(18, rect.height - 8)
            avatar = render_npc(self._role(npc.id), npc.id, avatar_h)
            surface.blit(avatar, (rect.x + 10, rect.centery - avatar_h // 2))
            name = self.font_name.render(
                npc.display_name, True, CREAM if selected else (226, 222, 208)
            )
            surface.blit(name, (rect.x + 14 + avatar.get_width(), rect.y + 5))
            role = self.font_role.render(self._role(npc.id), True, (186, 178, 158))
            surface.blit(role, (rect.x + 14 + avatar.get_width(), rect.y + 7 + name.get_height()))
        else:
            option = self._options(column)[index]
            text = humanize(option.text, self._places)
            lines = wrap_text(text, self.font_option, rect.width - 34)
            line_h = self.font_option.get_linesize()
            max_lines = max(1, (rect.height - 8) // line_h)
            if len(lines) > max_lines:
                lines = lines[:max_lines]
                lines[-1] = self._ellipsis(lines[-1], self.font_option, rect.width - 34)
            y = rect.centery - (len(lines) * line_h) // 2
            for line in lines:
                surface.blit(
                    self.font_option.render(line, True, CREAM if selected else (214, 212, 202)),
                    (rect.x + 16, y),
                )
                y += line_h

        if selected:
            check_r = max(6, round(8 * self.scale))
            center = (rect.right - 16, rect.centery)
            pygame.draw.circle(surface, GOLD, center, check_r)
            pygame.draw.circle(surface, (42, 34, 18), center, check_r - 3, 2)

    @staticmethod
    def _ellipsis(text: str, font: pygame.font.Font, width: int) -> str:
        ellipsis = "…"
        while text and font.size(text + ellipsis)[0] > width:
            text = text[:-1]
        return text.rstrip() + ellipsis

    def _draw_footer(self, surface: pygame.Surface) -> None:
        self.back_button.draw(surface)
        if self.game_over is None:
            self.submit_button.draw(surface)
        hint_right = self.width - max(20, round(self.width * 0.035))
        hint_x = hint_right - self.footer_hint.get_width()
        if hint_x > self.submit_button.rect.right + 16:
            surface.blit(
                self.footer_hint,
                (hint_x, self.submit_button.rect.centery - self.footer_hint.get_height() // 2),
            )

    def _draw_game_over(self, surface: pygame.Surface) -> None:
        veil = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        veil.fill((4, 6, 10, 168))
        surface.blit(veil, (0, 0))

        rect = self.overlay_rect
        draw_panel(surface, rect, fill=(14, 16, 20, 244), radius=16)
        won = self.game_over == "won"
        title = self.font_overlay_title.render(
            "CASE CLOSED" if won else "THE CASE GOES COLD",
            True,
            GOLD if won else (232, 132, 116),
        )
        surface.blit(
            title,
            (rect.centerx - title.get_width() // 2, rect.y + round(24 * self.scale)),
        )

        if self.last_choice is not None:
            name, method, motive = self.last_choice
            summary = humanize(f"{name} — {method} — {motive}", self._places)
        else:
            summary = ""
        body = (
            "The accusation holds. The town has its answer, and your notes were right."
            if won
            else "Your last accusation did not hold up. The true culprit leaves town unchallenged."
        )
        lines = wrap_text(body, self.font_overlay_body, rect.width - 64)
        y = rect.y + round(24 * self.scale) + title.get_height() + round(10 * self.scale)
        for line in lines:
            line_surface = self.font_overlay_body.render(line, True, (224, 222, 210))
            surface.blit(line_surface, (rect.centerx - line_surface.get_width() // 2, y))
            y += line_surface.get_height()
        if summary:
            y += round(6 * self.scale)
            for line in wrap_text(summary, self.font_small, rect.width - 80):
                line_surface = self.font_small.render(line, True, (196, 186, 160))
                surface.blit(line_surface, (rect.centerx - line_surface.get_width() // 2, y))
                y += line_surface.get_height()

        self.quit_button.draw(surface)
        self.map_button.draw(surface)
        hint = self.font_small.render("Enter to quit · Esc to return to the map", True, MUTED)
        surface.blit(
            hint,
            (
                rect.centerx - hint.get_width() // 2,
                rect.bottom - hint.get_height() - round(5 * self.scale),
            ),
        )
