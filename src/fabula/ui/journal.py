from __future__ import annotations

from typing import Any

import pygame

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


class JournalView:
    """Case file: discovered clues and notes from every conversation."""

    def __init__(self, width: int, height: int, session: Any) -> None:
        self.width = width
        self.height = height
        self.session = session
        self.scale = max(0.65, min(width / 1600, height / 900))
        self.tick = 0
        self.scroll = 0

        self.font_overline = self._font(16)
        self.font_title = self._font(46, bold=True)
        self.font_subtitle = self._font(18)
        self.font_heading = self._font(21, bold=True)
        self.font_body = self._font(18)
        self.font_small = self._font(14)
        self.font_badge = self._font(18, bold=True)
        self.font_footer = self._font(14)

        world = session.loaded.world
        self._roster = {entry.id: entry for entry in world.npcs}
        self._npcs = session.loaded.npcs
        self._places = {loc.id: loc.name for loc in world.locations}
        self._clues = {clue.id: clue for clue in session.loaded.clues.clues}

        self.backdrop = MenuBackdrop(width, height)
        self._dim = pygame.Surface((width, height), pygame.SRCALPHA)
        self._dim.fill((4, 8, 12, 138))

        margin_x = max(20, round(width * 0.035))
        self.header_top = max(14, round(height * 0.032))
        self.overline = render_spaced(
            "CASE FILE", self.font_overline, (196, 166, 108), max(1, round(3 * self.scale))
        )
        self.title = render_spaced(
            "INVESTIGATION JOURNAL",
            self.font_title,
            GOLD,
            max(2, round(4 * self.scale)),
        )
        minute = session.clock.minute
        self.subtitle = self.font_subtitle.render(
            f"{world.town_name} · {world.title} · {minute // 60:02d}:{minute % 60:02d}",
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

        footer_h = max(62, round(84 * self.scale))
        self.card = pygame.Rect(
            0,
            0,
            min(width - margin_x * 2, round(1020 * self.scale)),
            max(180, height - footer_h - round(14 * self.scale) - header_bottom - 16),
        )
        self.card.midtop = (width // 2, header_bottom + round(14 * self.scale))

        self.pad = max(14, round(24 * self.scale))
        self.strip_h = max(44, round(58 * self.scale))
        self.scrollbar_w = max(6, round(9 * self.scale))
        self.viewport = pygame.Rect(
            self.card.x + self.pad,
            self.card.y + self.strip_h + round(8 * self.scale),
            self.card.width - self.pad * 2 - self.scrollbar_w - round(6 * self.scale),
            self.card.height - self.strip_h - self.pad - round(8 * self.scale),
        )
        self.content_width = self.viewport.width

        font_button = self._font(20)
        button_w = max(
            170,
            menu_button_width("Back to Map [Esc]", font_button, scale=self.scale),
        )
        button_h = max(36, round(46 * self.scale))
        self.back_button = MenuButton(
            pygame.Rect(
                self.card.x,
                height - footer_h + (footer_h - button_h) // 2,
                button_w,
                button_h,
            ),
            "Back to Map [Esc]",
            lambda: "back_to_map",
            font_button,
        )
        self.footer_hint = self.font_footer.render(
            "Mouse wheel or Up / Down to scroll  ·  J or Esc to return", True, (150, 150, 142)
        )

        self.content = self._build_content()

    def _font(self, size: float, *, bold: bool = False) -> pygame.font.Font:
        return ui_font(size * self.scale, bold=bold)

    @property
    def max_scroll(self) -> int:
        return max(0, self.content.get_height() - self.viewport.height)

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------

    def _source_label(self, source: str) -> str:
        kind, _, ref = source.partition(":")
        if kind == "examine":
            return f"Searched {self._places.get(ref, 'the area')}"
        if kind == "npc_reveal":
            files = self._npcs.get(ref)
            name = files.identity.name if files is not None else ref
            return f"Told by {name}"
        return source

    def _display_name(self, npc_id: str) -> str:
        files = self._npcs.get(npc_id)
        if files is not None:
            return files.identity.name
        entry = self._roster.get(npc_id)
        return entry.display_name if entry is not None else npc_id

    def _role(self, npc_id: str) -> str:
        files = self._npcs.get(npc_id)
        role = files.identity.role if files is not None else "villager"
        return role[:1].upper() + role[1:] if role else "Villager"

    @staticmethod
    def _format_time(minute: int) -> str:
        return f"{minute // 60:02d}:{minute % 60:02d}"

    def _clue_card(self, index: int, entry: Any) -> pygame.Surface:
        pad = max(10, round(14 * self.scale))
        badge = max(26, round(36 * self.scale))
        line_h = self.font_body.get_linesize()
        text_x = pad * 2 + badge
        text_w = self.content_width - text_x - pad
        clue = self._clues.get(entry.clue_id)
        description = clue.description if clue is not None else entry.clue_id
        description = humanize(description, self._places)
        lines = wrap_text(description, self.font_body, text_w)
        meta = f"{self._source_label(entry.source)} · {self._format_time(entry.minute)}"
        meta_surface = self.font_small.render(meta, True, (176, 166, 142))
        height = pad * 2 + max(badge, len(lines) * line_h + meta_surface.get_height() + 4)

        card = pygame.Surface((self.content_width, height), pygame.SRCALPHA)
        rect = card.get_rect()
        pygame.draw.rect(card, (22, 26, 30, 222), rect, border_radius=10)
        pygame.draw.rect(card, (74, 68, 54), rect, 1, border_radius=10)
        pygame.draw.rect(card, GOLD, (0, 0, max(3, round(4 * self.scale)), height), border_radius=2)

        center = (pad + badge // 2, pad + badge // 2)
        pygame.draw.circle(card, (58, 46, 26), center, badge // 2)
        pygame.draw.circle(card, GOLD, center, badge // 2, 2)
        number = self.font_badge.render(str(index), True, CREAM)
        card.blit(
            number,
            (center[0] - number.get_width() // 2, center[1] - number.get_height() // 2),
        )

        y = pad
        for line in lines:
            card.blit(self.font_body.render(line, True, (232, 230, 220)), (text_x, y))
            y += line_h
        card.blit(meta_surface, (text_x, y + 2))
        return card

    def _note_card(self, npc_id: str, statements: tuple[str, ...]) -> pygame.Surface:
        pad = max(10, round(14 * self.scale))
        avatar_h = max(40, round(62 * self.scale))
        avatar = render_npc(self._role(npc_id), npc_id, avatar_h)
        text_x = pad * 2 + avatar.get_width()
        text_w = self.content_width - text_x - pad
        line_h = self.font_body.get_linesize()
        latest = statements[-1] if statements else ""
        latest = humanize(latest, self._places)
        lines = wrap_text(f"“{latest}”", self.font_body, text_w)[:3]
        name_surface = self.font_heading.render(self._display_name(npc_id), True, CREAM)
        role_surface = self.font_small.render(self._role(npc_id), True, (196, 188, 168))
        count = len(statements)
        meta_surface = self.font_small.render(
            f"{count} question{'s' if count != 1 else ''} answered", True, (160, 154, 136)
        )
        text_h = (
            name_surface.get_height()
            + role_surface.get_height()
            + 4
            + len(lines) * line_h
            + meta_surface.get_height()
            + 4
        )
        height = pad * 2 + max(avatar_h, text_h)

        card = pygame.Surface((self.content_width, height), pygame.SRCALPHA)
        rect = card.get_rect()
        pygame.draw.rect(card, (20, 24, 28, 218), rect, border_radius=10)
        pygame.draw.rect(card, (66, 62, 52), rect, 1, border_radius=10)
        pygame.draw.rect(
            card, (108, 96, 68), (0, 0, max(3, round(4 * self.scale)), height), border_radius=2
        )
        card.blit(avatar, (pad, pad + 2))

        y = pad
        card.blit(name_surface, (text_x, y))
        y += name_surface.get_height()
        card.blit(role_surface, (text_x, y))
        y += role_surface.get_height() + 3
        for line in lines:
            card.blit(self.font_body.render(line, True, (218, 216, 206)), (text_x, y))
            y += line_h
        card.blit(meta_surface, (text_x, y + 2))
        return card

    def _heading_block(self, text: str, note: str) -> pygame.Surface:
        heading = self.font_heading.render(text, True, GOLD)
        note_surface = self.font_small.render(note, True, (156, 150, 136))
        height = heading.get_height() + 4 + note_surface.get_height()
        block = pygame.Surface((self.content_width, height), pygame.SRCALPHA)
        block.blit(heading, (0, 0))
        block.blit(note_surface, (0, heading.get_height() + 4))
        return block

    def _empty_block(self, text: str) -> pygame.Surface:
        lines = wrap_text(text, self.font_body, self.content_width - 20)
        line_h = self.font_body.get_linesize()
        block = pygame.Surface((self.content_width, len(lines) * line_h + 12), pygame.SRCALPHA)
        for index, line in enumerate(lines):
            block.blit(self.font_body.render(line, True, (160, 158, 148)), (10, 6 + index * line_h))
        return block

    def _build_content(self) -> pygame.Surface:
        blocks: list[tuple[int, pygame.Surface]] = []
        journal = self.session.journal
        total_clues = len(self._clues)
        gap_unit = max(6, round(10 * self.scale))

        blocks.append(
            (
                0,
                self._heading_block(
                    "Clues Discovered",
                    f"{len(journal)} of {total_clues} pieces of evidence in your case file",
                ),
            )
        )
        if journal:
            for index, entry in enumerate(journal, start=1):
                blocks.append((gap_unit, self._clue_card(index, entry)))
        else:
            blocks.append(
                (
                    gap_unit,
                    self._empty_block(
                        "The journal is blank. Search the place you are standing in with E, "
                        "or question someone with T."
                    ),
                )
            )

        blocks.append(
            (
                round(22 * self.scale),
                self._heading_block("Witness Notes", "What you have been told so far"),
            )
        )
        noted = 0
        for entry in self.session.loaded.world.npcs:
            statements = self.session.statements_for(entry.id)
            if not statements:
                continue
            noted += 1
            blocks.append((gap_unit, self._note_card(entry.id, statements)))
        if not noted:
            blocks.append(
                (
                    gap_unit,
                    self._empty_block(
                        "No conversations yet. Ask people where they were and who was with "
                        "them — everyone remembers the evening differently."
                    ),
                )
            )

        total = sum(gap + block.get_height() for gap, block in blocks) + round(10 * self.scale)
        content = pygame.Surface((self.content_width, total), pygame.SRCALPHA)
        y = 0
        for gap, block in blocks:
            y += gap
            content.blit(block, (0, y))
            y += block.get_height()
        return content

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    def _scroll_by(self, amount: int) -> None:
        self.scroll = max(0, min(self.max_scroll, self.scroll + amount))

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if self.back_button.handle_event(event):
            return "back_to_map"
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_by(-event.y * round(70 * self.scale))
        elif event.type == pygame.KEYDOWN:
            step = round(52 * self.scale)
            if event.key in (pygame.K_ESCAPE, pygame.K_j):
                return "back_to_map"
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self._scroll_by(step)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._scroll_by(-step)
            elif event.key == pygame.K_PAGEDOWN:
                self._scroll_by(round(self.viewport.height * 0.85))
            elif event.key == pygame.K_PAGEUP:
                self._scroll_by(-round(self.viewport.height * 0.85))
            elif event.key == pygame.K_HOME:
                self.scroll = 0
            elif event.key == pygame.K_END:
                self.scroll = self.max_scroll
        return None

    def update(self) -> None:
        self.tick += 1
        self.back_button.update()

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
        draw_panel(surface, self.card, fill=(11, 15, 19, 226))

        self._draw_progress(surface)
        surface.set_clip(self.viewport)
        surface.blit(
            self.content,
            self.viewport.topleft,
            pygame.Rect(0, self.scroll, self.viewport.width, self.viewport.height),
        )
        surface.set_clip(None)
        self._draw_scrollbar(surface)

        self.back_button.draw(surface)
        surface.blit(
            self.footer_hint,
            (
                self.width - self.footer_hint.get_width() - max(20, round(self.width * 0.035)),
                self.back_button.rect.centery - self.footer_hint.get_height() // 2,
            ),
        )

    def _draw_progress(self, surface: pygame.Surface) -> None:
        found = len(self.session.journal)
        total = max(1, len(self._clues))
        x = self.card.x + self.pad
        y = self.card.y + max(10, round(14 * self.scale))
        label = self.font_small.render("CLUES FOUND", True, (196, 166, 108))
        count = self.font_heading.render(f"{found} / {total}", True, CREAM)
        surface.blit(label, (x, y))
        surface.blit(count, (x, y + label.get_height() + 1))

        bar_w = min(round(self.card.width * 0.44), self.card.width - self.pad * 2 - 180)
        bar_h = max(6, round(10 * self.scale))
        bar = pygame.Rect(x + self.card.width - self.pad * 2 - bar_w, y + 12, bar_w, bar_h)
        pygame.draw.rect(surface, (38, 42, 44), bar, border_radius=bar_h // 2)
        filled = round(bar_w * found / total)
        if filled > 0:
            pygame.draw.rect(
                surface,
                GOLD,
                (bar.x, bar.y, filled, bar_h),
                border_radius=bar_h // 2,
            )
        pygame.draw.rect(surface, (96, 84, 58), bar, 1, border_radius=bar_h // 2)

        notes = sum(
            1 for npc in self.session.loaded.world.npcs if self.session.statements_for(npc.id)
        )
        note_text = self.font_small.render(
            f"{notes} witness{'es' if notes != 1 else ''} questioned", True, MUTED
        )
        surface.blit(note_text, (bar.x, bar.bottom + 3))

    def _draw_scrollbar(self, surface: pygame.Surface) -> None:
        if self.max_scroll <= 0:
            return
        track = pygame.Rect(
            self.viewport.right + round(6 * self.scale),
            self.viewport.y,
            self.scrollbar_w,
            self.viewport.height,
        )
        pygame.draw.rect(surface, (44, 48, 50), track, border_radius=track.width // 2)
        thumb_h = max(
            round(36 * self.scale),
            round(track.height * self.viewport.height / self.content.get_height()),
        )
        travel = track.height - thumb_h
        thumb_y = track.y + round(travel * (self.scroll / self.max_scroll))
        pygame.draw.rect(
            surface,
            (186, 158, 104),
            (track.x, thumb_y, track.width, thumb_h),
            border_radius=track.width // 2,
        )
