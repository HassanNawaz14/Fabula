"""Scrollable picker for case bundles already written to the library."""

from __future__ import annotations

from typing import Any

import pygame

from fabula.case_library import CaseSummary, discover_cases
from fabula.ui.menu_theme import (
    CREAM,
    GOLD,
    MUTED,
    MenuBackdrop,
    MenuButton,
    draw_panel,
    ui_font,
    wrap_text,
)


class CasePickerView:
    """Browse validated cases and start one, with a sample fallback."""

    def __init__(
        self,
        width: int,
        height: int,
        app: Any = None,
        *,
        library_dir: str | None = None,
        error: str | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.app = app
        self.error = error
        self.scale = max(0.65, min(width / 1600, height / 900))
        self.tick = 0
        self.cases: list[CaseSummary] = discover_cases(library_dir)
        self.selected = 0
        self.scroll = 0
        self.hover_index: int | None = None

        self.font_overline = self._font(16, bold=True)
        self.font_title = self._font(40, bold=True)
        self.font_subtitle = self._font(18)
        self.font_row_title = self._font(21, bold=True)
        self.font_row_meta = self._font(15)
        self.font_button = self._font(21)
        self.font_body = self._font(17)
        self.font_error = self._font(15)
        self.font_footer = self._font(14)

        self.backdrop = MenuBackdrop(width, height)
        self._dim = pygame.Surface((width, height), pygame.SRCALPHA)
        self._dim.fill((4, 8, 12, 120))
        self._sample_button: MenuButton | None = None
        self._back_button: MenuButton | None = None
        self._layout()

    def _font(self, size: float, *, bold: bool = False) -> pygame.font.Font:
        return ui_font(size * self.scale, bold=bold)

    def _layout(self) -> None:
        scale = self.scale
        margin = max(20, round(32 * scale))
        pad = max(14, round(22 * scale))
        top = max(18, round(34 * scale))
        self.panel = pygame.Rect(
            margin,
            top,
            self.width - margin * 2,
            self.height - top - margin,
        )
        self.pad = pad
        header_h = (
            self.font_overline.get_height()
            + self.font_title.get_height()
            + self.font_subtitle.get_height()
            + max(18, round(26 * scale))
        )
        self.row_h = max(56, round(68 * scale))
        self.footer_h = self.font_footer.get_height() + max(12, round(18 * scale))
        error_lines = 2 if self.error else 0
        self.error_h = (
            error_lines * self.font_error.get_height() + max(8, round(12 * scale))
            if self.error
            else 0
        )
        self.list_rect = pygame.Rect(
            self.panel.x + pad,
            self.panel.y + pad + header_h,
            self.panel.width - pad * 2 - max(8, round(12 * scale)),
            self.panel.height - pad * 2 - header_h - self.footer_h - self.error_h,
        )
        self.visible_rows = max(1, self.list_rect.height // self.row_h)

        if not self.cases:
            button_w = min(round(320 * scale), self.panel.width - pad * 4)
            button_h = max(44, round(54 * scale))
            center_x = self.panel.centerx
            self._sample_button = MenuButton(
                pygame.Rect(
                    center_x - button_w // 2,
                    self.panel.centery + max(10, round(18 * scale)),
                    button_w,
                    button_h,
                ),
                "Play Sample Case",
                lambda: "start_dummy",
                self.font_button,
                primary=True,
            )
            self._back_button = MenuButton(
                pygame.Rect(
                    center_x - button_w // 2,
                    self.panel.centery
                    + max(10, round(18 * scale))
                    + button_h
                    + max(8, round(10 * scale)),
                    button_w,
                    button_h,
                ),
                "Back",
                lambda: "go_new_game",
                self.font_button,
            )

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def _row_at(self, pos: tuple[int, int]) -> int | None:
        if not self.list_rect.collidepoint(pos):
            return None
        row = (pos[1] - self.list_rect.y) // self.row_h
        index = self.scroll + int(row)
        return index if 0 <= index < len(self.cases) else None

    def _clamp(self) -> None:
        if not self.cases:
            self.selected = 0
            self.scroll = 0
            return
        self.selected = max(0, min(self.selected, len(self.cases) - 1))
        max_scroll = max(0, len(self.cases) - self.visible_rows)
        self.scroll = max(0, min(self.scroll, max_scroll))
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected >= self.scroll + self.visible_rows:
            self.scroll = self.selected - self.visible_rows + 1

    def _play(self) -> dict[str, str]:
        case = self.cases[self.selected]
        return {"action": "play_case", "path": str(case.path)}

    def handle_event(self, event: pygame.event.Event) -> Any:
        if not self.cases:
            for button in (self._sample_button, self._back_button):
                if button is not None:
                    result = button.handle_event(event)
                    if result:
                        return result
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "go_new_game"
            return None

        if event.type == pygame.MOUSEMOTION:
            self.hover_index = self._row_at(event.pos)
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll -= event.y
            self._clamp()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = self._row_at(event.pos)
            if index is not None:
                self.selected = index
                return self._play()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "go_new_game"
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected -= 1
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected += 1
            elif event.key == pygame.K_HOME:
                self.selected = 0
            elif event.key == pygame.K_END:
                self.selected = len(self.cases) - 1
            elif event.key == pygame.K_PAGEUP:
                self.selected -= self.visible_rows
            elif event.key == pygame.K_PAGEDOWN:
                self.selected += self.visible_rows
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self._play()
            self._clamp()
        return None

    def update(self) -> None:
        self.tick += 1
        if self._sample_button is not None:
            self._sample_button.update()
        if self._back_button is not None:
            self._back_button.update()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        self.backdrop.draw(surface, self.tick)
        surface.blit(self._dim, (0, 0))
        draw_panel(surface, self.panel)

        y = self.panel.y + self.pad
        overline = self.font_overline.render("CASE FILE", True, GOLD)
        surface.blit(overline, (self.panel.centerx - overline.get_width() // 2, y))
        y += overline.get_height() + max(2, round(4 * self.scale))
        title = self.font_title.render("READY CASES", True, CREAM)
        surface.blit(title, (self.panel.centerx - title.get_width() // 2, y))
        y += title.get_height() + max(2, round(4 * self.scale))
        subtitle_text = (
            f"{len(self.cases)} mysteries ready to play" if self.cases else "No generated cases yet"
        )
        subtitle = self.font_subtitle.render(subtitle_text, True, MUTED)
        surface.blit(subtitle, (self.panel.centerx - subtitle.get_width() // 2, y))

        if not self.cases:
            self._draw_empty(surface)
        else:
            self._draw_list(surface)

        if self.error:
            self._draw_error(surface)

        hint = self.font_footer.render(
            "Up/Down browse  ·  Enter play  ·  Esc back" if self.cases else "Esc back",
            True,
            (140, 144, 138),
        )
        surface.blit(
            hint,
            (
                self.panel.centerx - hint.get_width() // 2,
                self.panel.bottom - hint.get_height() - max(10, round(16 * self.scale)),
            ),
        )

    def _draw_empty(self, surface: pygame.Surface) -> None:
        message = (
            "Generate a mystery with Kaggle or the local model, then it appears here. "
            "You can also try the built-in sample case."
        )
        lines = wrap_text(message, self.font_body, self.panel.width - self.pad * 4)
        y = (
            self.panel.centery
            - max(40, round(62 * self.scale))
            - sum(self.font_body.get_height() for _ in lines) // 2
        )
        for line in lines:
            text = self.font_body.render(line, True, MUTED)
            surface.blit(text, (self.panel.centerx - text.get_width() // 2, y))
            y += text.get_height()
        if self._sample_button is not None:
            self._sample_button.draw(surface)
        if self._back_button is not None:
            self._back_button.draw(surface)

    def _draw_list(self, surface: pygame.Surface) -> None:
        old_clip = surface.get_clip()
        surface.set_clip(self.list_rect)
        for offset in range(self.visible_rows):
            index = self.scroll + offset
            if index >= len(self.cases):
                break
            case = self.cases[index]
            row = pygame.Rect(
                self.list_rect.x,
                self.list_rect.y + offset * self.row_h,
                self.list_rect.width,
                self.row_h - max(4, round(7 * self.scale)),
            )
            selected = index == self.selected
            hovered = index == self.hover_index
            fill = (46, 39, 24) if selected else (16, 20, 24)
            if hovered and not selected:
                fill = (28, 32, 34)
            pygame.draw.rect(surface, fill, row, border_radius=9)
            pygame.draw.rect(
                surface,
                GOLD if selected else (112, 96, 66),
                row,
                2 if selected else 1,
                border_radius=9,
            )

            text_x = row.x + max(14, round(20 * self.scale))
            title = self.font_row_title.render(case.title, True, CREAM)
            surface.blit(title, (text_x, row.y + max(6, round(9 * self.scale))))
            meta_text = (
                f"{case.town_name}  ·  {case.mystery_type}  ·  {case.tone}  ·  {case.difficulty}"
            )
            meta = self.font_row_meta.render(meta_text, True, (176, 178, 168))
            surface.blit(
                meta, (text_x, row.bottom - meta.get_height() - max(6, round(8 * self.scale)))
            )

            play = self.font_row_meta.render("PLAY", True, GOLD if selected else MUTED)
            tri = max(4, round(5 * self.scale))
            tri_x = row.right - max(12, round(18 * self.scale)) - tri
            play_x = tri_x - play.get_width() - max(8, round(10 * self.scale))
            surface.blit(play, (play_x, row.centery - play.get_height() // 2))
            pygame.draw.polygon(
                surface,
                GOLD if selected else MUTED,
                [
                    (tri_x, row.centery - tri),
                    (tri_x + tri, row.centery),
                    (tri_x, row.centery + tri),
                ],
            )
        surface.set_clip(old_clip)

        if len(self.cases) > self.visible_rows:
            track = pygame.Rect(
                self.list_rect.right + max(4, round(6 * self.scale)),
                self.list_rect.y,
                max(3, round(5 * self.scale)),
                self.list_rect.height,
            )
            pygame.draw.rect(surface, (48, 50, 48), track, border_radius=track.width)
            thumb_h = max(
                round(24 * self.scale), track.height * self.visible_rows // len(self.cases)
            )
            max_scroll = len(self.cases) - self.visible_rows
            thumb_y = track.y + round((track.height - thumb_h) * (self.scroll / max(1, max_scroll)))
            pygame.draw.rect(
                surface,
                (146, 124, 84),
                pygame.Rect(track.x, thumb_y, track.width, thumb_h),
                border_radius=track.width,
            )

    def _draw_error(self, surface: pygame.Surface) -> None:
        lines = wrap_text(
            f"Could not open this case: {self.error}", self.font_error, self.list_rect.width
        )
        y = self.panel.bottom - self.footer_h - self.error_h + 2
        for line in lines[:2]:
            text = self.font_error.render(line, True, (240, 148, 128))
            surface.blit(text, (self.list_rect.x, y))
            y += text.get_height()


__all__ = ["CasePickerView"]
