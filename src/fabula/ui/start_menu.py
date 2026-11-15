from __future__ import annotations

from typing import Any

import pygame

from fabula.ui.assets import place_variant, render_npc, render_place
from fabula.ui.menu_theme import (
    CREAM,
    GOLD,
    MUTED,
    MenuBackdrop,
    MenuButton,
    render_spaced,
    ui_font,
    wrap_text,
)

_CHIPS = ("THEFT", "DISAPPEARANCE", "MURDER")


class StartMenuView:
    """Front page: a night-time town, a case file, and the way in."""

    def __init__(self, width: int, height: int, app: Any) -> None:
        self.width = width
        self.height = height
        self.app = app
        self.scale = max(0.65, min(width / 1600, height / 900))
        self.tick = 0

        self.font_overline = self._font(18)
        self.font_title = self._font(100, bold=True)
        self.font_tagline = self._font(26)
        self.font_body = self._font(18)
        self.font_chip = self._font(15, bold=True)
        self.font_button = self._font(22)
        self.font_caption = self._font(15)
        self.font_footer = self._font(14)
        self.font_case_title = self._font(30, bold=True)
        self.font_case_small = self._font(14)
        self.font_case_value = self._font(18, bold=True)
        self.font_case_strip = self._font(12)

        self.backdrop = MenuBackdrop(width, height)
        self._scrim = self._build_scrim()
        self._draw_columns = width >= 1150
        self._build_case_board()
        self._layout()

    def _font(self, size: float, *, bold: bool = False) -> pygame.font.Font:
        return ui_font(size * self.scale, bold=bold)

    # ------------------------------------------------------------------
    # Artwork
    # ------------------------------------------------------------------

    def _build_scrim(self) -> pygame.Surface:
        scrim = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        span = max(1, round(self.width * 0.62))
        for x in range(span):
            strength = (1 - x / span) ** 1.8
            pygame.draw.line(
                scrim,
                (6, 10, 14, round(168 * strength)),
                (x, 0),
                (x, self.height),
            )
        return scrim

    def _build_case_board(self) -> None:
        self.case_shadow: pygame.Surface | None = None
        self.case_card: pygame.Surface | None = None
        self.case_rect = pygame.Rect(0, 0, 0, 0)
        self.case_note: pygame.Surface | None = None
        self.case_note_pos = (0, 0)
        if not self._draw_columns:
            return

        scale = self.scale
        card_w = min(round(440 * scale), round(self.width * 0.31))
        card_h = min(round(560 * scale), round(self.height * 0.68))
        pad = max(10, round(18 * scale))
        paper = (236, 226, 202)

        card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        pygame.draw.rect(card, paper, card.get_rect(), border_radius=6)
        for index in range(70):
            x = (index * 733 + 19) % card_w
            y = (index * 379 + 47) % card_h
            pygame.draw.circle(card, (224, 212, 186), (x, y), 1)
        pygame.draw.rect(card, (192, 178, 150), card.get_rect(), 2, border_radius=6)

        title = self.font_case_title.render("CASE FILE", True, (52, 44, 34))
        card.blit(title, (pad, pad))
        number = self.font_case_small.render("No. 0001", True, (110, 94, 72))
        card.blit(number, (card_w - pad - number.get_width(), pad + 5))
        rule_y = pad + title.get_height() + round(5 * scale)
        pygame.draw.line(
            card, (136, 118, 92), (pad, rule_y), (card_w - pad, rule_y), max(1, round(2 * scale))
        )

        photo_w = card_w - pad * 2
        photo_h = round(photo_w * 0.70)
        photo_rect = pygame.Rect(pad, rule_y + pad, photo_w, photo_h)
        variant = place_variant("residence", "menu-case-file")
        photo = render_place("residence", photo_rect.size, variant)
        card.blit(photo, photo_rect.topleft)
        pygame.draw.rect(card, (54, 46, 36), photo_rect, max(2, round(3 * scale)))

        stamp_font = self._font(22, bold=True)
        stamp_text = stamp_font.render("UNSOLVED", True, (158, 52, 44))
        stamp = pygame.Surface(
            (stamp_text.get_width() + 14, stamp_text.get_height() + 8), pygame.SRCALPHA
        )
        stamp.fill((0, 0, 0, 0))
        pygame.draw.rect(stamp, (158, 52, 44), stamp.get_rect(), 2, border_radius=3)
        stamp.blit(stamp_text, (7, 4))
        stamp = pygame.transform.rotozoom(stamp, 9, 1.0)
        card.blit(
            stamp,
            (
                min(
                    card_w - pad - stamp.get_width(),
                    photo_rect.right - stamp.get_width() + round(12 * scale),
                ),
                photo_rect.bottom - stamp.get_height() + round(8 * scale),
            ),
        )

        caption = self.font_case_small.render("THE SCENE OF THE CRIME", True, (104, 88, 68))
        card.blit(caption, (pad, photo_rect.bottom + round(7 * scale)))

        stats = (
            ("SUSPECTS", "6"),
            ("PLACES", "4"),
            ("TIME LIMIT", "10 MIN"),
            ("CLUES", "??"),
        )
        stats_top = photo_rect.bottom + round(30 * scale)
        cell_w = (card_w - pad * 2) // 2
        row_h = round(30 * scale)
        for index, (label, value) in enumerate(stats):
            cell_x = pad + (index % 2) * cell_w
            cell_y = stats_top + (index // 2) * row_h
            label_surface = self.font_case_small.render(label, True, (122, 104, 80))
            value_surface = self.font_case_value.render(value, True, (54, 46, 36))
            card.blit(label_surface, (cell_x, cell_y))
            card.blit(
                value_surface,
                (cell_x + cell_w - round(14 * scale) - value_surface.get_width(), cell_y - 2),
            )

        strip_h = max(34, round(card_h * 0.16))
        strip = pygame.Rect(pad, card_h - pad - strip_h, card_w - pad * 2, strip_h)
        pygame.draw.rect(card, (32, 36, 42), strip, border_radius=4)
        strip_label = self.font_case_strip.render("PERSONS OF INTEREST", True, (214, 190, 140))
        card.blit(strip_label, (strip.x + 8, strip.y + 4))
        avatar_h = strip_h - round(14 * scale)
        roster = (("librarian", "case-a"), ("market vendor", "case-b"), ("coach driver", "case-c"))
        cursor_x = strip.right - 8
        for role, seed in reversed(roster):
            avatar = render_npc(role, seed, avatar_h)
            cursor_x -= avatar.get_width()
            card.blit(avatar, (cursor_x, strip.bottom - avatar.get_height()))
            cursor_x -= round(6 * scale)

        self.case_card = pygame.transform.rotozoom(card, -2.4, 1.0)
        shadow = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 120), shadow.get_rect(), border_radius=10)
        self.case_shadow = pygame.transform.rotozoom(shadow, -2.4, 1.0)

        self.case_rect = self.case_card.get_rect()
        self.case_rect.centerx = self.width - round(self.width * 0.06) - self.case_rect.width // 2
        self.case_rect.centery = round(self.height * 0.54)
        if self.case_rect.right > self.width - round(self.width * 0.03):
            self.case_rect.right = self.width - round(self.width * 0.03)
        if self.case_rect.bottom > self.height - round(self.height * 0.03):
            self.case_rect.bottom = self.height - round(self.height * 0.03)

        note_font = self._font(16, bold=True)
        note_text = note_font.render("ONE OF THEM IS LYING", True, (246, 206, 116))
        note = pygame.Surface(
            (note_text.get_width() + 24, note_text.get_height() + 16), pygame.SRCALPHA
        )
        note.fill((24, 28, 34, 238))
        pygame.draw.rect(note, (148, 124, 82), note.get_rect(), 2, border_radius=4)
        note.blit(note_text, (12, 8))
        self.case_note = pygame.transform.rotozoom(note, 3.5, 1.0)
        self.case_note_pos = (
            max(
                round(self.width * 0.45),
                self.case_rect.left - self.case_note.get_width() - round(22 * self.scale),
            ),
            self.case_rect.bottom - self.case_note.get_height() - round(18 * self.scale),
        )

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _layout(self) -> None:
        scale = self.scale
        self.margin_x = max(30, round(self.width * 0.055))
        self.column_w = min(round(470 * scale), round(self.width * 0.44))

        y = round(self.height * 0.10)
        self.overline_pos = (self.margin_x, y)
        y += round(18 * scale) + round(8 * scale)

        self.title = render_spaced("FABULA", self.font_title, GOLD, max(2, round(6 * scale)))
        self.title_pos = (self.margin_x, y)
        y += self.title.get_height() + round(4 * scale)

        tagline = "Question the town. Catch the lie."
        tagline_lines = wrap_text(tagline, self.font_tagline, self.column_w)
        self.tagline = [self.font_tagline.render(line, True, CREAM) for line in tagline_lines]
        self.tagline_pos = (self.margin_x, y)
        y += sum(surface.get_height() for surface in self.tagline) + round(12 * scale)

        chip_font = self.font_chip
        chip_widths = [chip_font.size(chip)[0] + round(20 * scale) for chip in _CHIPS]
        total_chips = sum(chip_widths) + round(8 * scale) * (len(_CHIPS) - 1)
        if total_chips > self.column_w:
            chip_font = self._font(13, bold=True)
            chip_widths = [chip_font.size(chip)[0] + round(14 * scale) for chip in _CHIPS]
            total_chips = sum(chip_widths) + round(6 * scale) * (len(_CHIPS) - 1)
        self.chip_font = chip_font
        self.chip_widths = chip_widths
        self.chip_pos = (self.margin_x, y)
        self.chip_height = round(24 * scale)
        y += self.chip_height + round(16 * scale)

        description = "One town, a handful of suspects, and ten minutes to work out who is lying."
        self.description = [
            self.font_body.render(line, True, MUTED)
            for line in wrap_text(description, self.font_body, self.column_w)
        ]
        self.description_pos = (self.margin_x, y)
        y += sum(surface.get_height() for surface in self.description) + round(24 * scale)

        button_h = max(34, round(52 * scale))
        button_gap = max(8, round(13 * scale))

        def slot(index: int) -> pygame.Rect:
            return pygame.Rect(
                self.margin_x,
                y + index * (button_h + button_gap),
                self.column_w,
                button_h,
            )

        play_label = "New Game"
        self.play_button = MenuButton(
            slot(0), play_label, lambda: "go_new_game", self.font_button, primary=True
        )
        self.mode_button = MenuButton(
            slot(2), self._mode_label(), self._toggle_mode, self.font_button
        )
        self.buttons = [
            self.play_button,
            MenuButton(slot(1), "How to Play", lambda: "go_how_to_play", self.font_button),
            self.mode_button,
            MenuButton(slot(3), "Settings", lambda: "go_settings", self.font_button),
            MenuButton(slot(4), "Quit [Esc]", lambda: "quit_game", self.font_button),
        ]
        caption_y = y + 5 * button_h + 4 * button_gap + round(14 * scale)
        caption_text = (
            "Auto uses a live AI when an API key is available. Offline always uses written replies."
        )
        self.caption = [
            self.font_caption.render(line, True, (150, 150, 142))
            for line in wrap_text(caption_text, self.font_caption, self.column_w)
        ]
        self.caption_pos = (self.margin_x, caption_y)

        footer = self.font_footer.render(
            "Fabula  ·  a ten-minute mystery  ·  every case is fair", True, (134, 138, 132)
        )
        self.footer = footer
        self.footer_pos = (
            self.margin_x,
            self.height - round(self.height * 0.045) - footer.get_height(),
        )

    def _mode_label(self) -> str:
        mode = self.app.settings["conversation_mode"]
        if mode == "auto":
            return "NPC voices: Auto"
        if mode == "live":
            return "NPC voices: Live AI"
        return "NPC voices: Offline"

    def _toggle_mode(self) -> None:
        current = self.app.settings["conversation_mode"]
        mode = "scripted" if current in ("auto", "live") else "auto"
        if hasattr(self.app, "set_voice_mode"):
            self.app.set_voice_mode(mode)
        else:
            self.app.settings["conversation_mode"] = mode
        self.mode_button.text = self._mode_label()

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> str | None:
        for button in self.buttons:
            result = button.handle_event(event)
            if result:
                return result
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "quit_game"
        return None

    def update(self) -> None:
        self.tick += 1
        for button in self.buttons:
            button.update()

    def draw(self, surface: pygame.Surface) -> None:
        self.backdrop.draw(surface, self.tick)
        surface.blit(self._scrim, (0, 0))

        if self.case_card is not None and self.case_shadow is not None:
            surface.blit(self.case_shadow, self.case_rect.move(10, 14))
            surface.blit(self.case_card, self.case_rect)
            if self.case_note is not None:
                surface.blit(self.case_note, self.case_note_pos)

        overline = self.font_overline.render("A SMALL-TOWN MYSTERY", True, (196, 166, 108))
        surface.blit(overline, self.overline_pos)
        surface.blit(self.title, self.title_pos)

        y = self.tagline_pos[1]
        for line in self.tagline:
            surface.blit(line, (self.margin_x, y))
            y += line.get_height()

        x = self.chip_pos[0]
        for chip, chip_w in zip(_CHIPS, self.chip_widths, strict=False):
            rect = pygame.Rect(x, self.chip_pos[1], chip_w, self.chip_height)
            pygame.draw.rect(surface, (18, 22, 26), rect, border_radius=rect.height // 2)
            pygame.draw.rect(surface, (126, 106, 72), rect, 1, border_radius=rect.height // 2)
            text = self.chip_font.render(chip, True, (214, 188, 136))
            surface.blit(
                text,
                (
                    rect.centerx - text.get_width() // 2,
                    rect.centery - text.get_height() // 2,
                ),
            )
            x += chip_w + round(8 * self.scale)

        y = self.description_pos[1]
        for line in self.description:
            surface.blit(line, (self.margin_x, y))
            y += line.get_height()

        for button in self.buttons:
            button.draw(surface)

        y = self.caption_pos[1]
        for line in self.caption:
            surface.blit(line, (self.margin_x, y))
            y += line.get_height()
        surface.blit(self.footer, self.footer_pos)
