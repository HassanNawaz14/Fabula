from __future__ import annotations

from typing import Any

import pygame

from fabula.ui.assets import render_npc
from fabula.ui.menu_theme import (
    GOLD,
    MUTED,
    MenuBackdrop,
    MenuButton,
    draw_panel,
    humanize,
    ui_font,
    wrap_text,
)

_MOOD_COLORS: dict[str, tuple[int, int, int]] = {
    "neutral": (156, 156, 150),
    "friendly": (126, 210, 150),
    "nervous": (230, 190, 110),
    "angry": (232, 124, 112),
    "sad": (132, 162, 218),
    "amused": (204, 164, 232),
}

_MAX_INPUT = 400


class DialogueView:
    """Conversation screen with an illustrated portrait and chat transcript."""

    def __init__(
        self,
        width: int,
        height: int,
        session: Any,
        conversation_service: Any,
        npc_id: str,
    ) -> None:
        self.width = width
        self.height = height
        self.session = session
        self.conversation_service = conversation_service
        self.npc_id = npc_id
        self.files = session.loaded.npcs[npc_id]
        self.identity = self.files.identity
        self.name = self.identity.name
        self.role = self.identity.role[:1].upper() + self.identity.role[1:]
        self.traits = list(self.identity.traits)[:4]
        places = {loc.id: loc.name for loc in session.loaded.world.locations}
        self._places = places
        self.place_name = places.get(session.player_location, "town")

        self.input_text = ""
        self.history: list[dict[str, Any]] = []
        self.current_mood = "neutral"
        self.loading = False
        self.tick = 0
        self.scroll = 0
        self.stick_to_bottom = True
        self._chat_surface: pygame.Surface | None = None
        self._chat_dirty = True

        for statement in session.statements_for(npc_id):
            self.history.append(
                {"speaker": "player", "text": statement, "mood": "", "earlier": True}
            )

        self.scale = max(0.65, min(width / 1600, height / 900))
        self.font_overline = self._font(15)
        self.font_title = self._font(36, bold=True)
        self.font_subtitle = self._font(17)
        self.font_heading = self._font(18, bold=True)
        self.font_npc = self._font(18, bold=True)
        self.font_body = self._font(19)
        self.font_meta = self._font(13)
        self.font_small = self._font(14)
        self.font_input = self._font(20)
        self.font_button = self._font(19)

        self.backdrop = MenuBackdrop(width, height)
        self._dim = pygame.Surface((width, height), pygame.SRCALPHA)
        self._dim.fill((5, 8, 12, 142))

        margin = max(14, round(width * 0.028))
        self.gap = max(9, round(14 * self.scale))
        header_h = (
            self.font_overline.get_height()
            + self.font_title.get_height()
            + self.font_subtitle.get_height()
            + max(26, round(38 * self.scale))
        )
        self.header_rect = pygame.Rect(
            margin, max(12, round(height * 0.026)), width - margin * 2, header_h
        )

        input_h = max(48, round(64 * self.scale))
        input_y = height - margin - input_h
        body_top = self.header_rect.bottom + self.gap
        body_h = max(120, input_y - self.gap - body_top)
        self.body_rect = pygame.Rect(margin, body_top, width - margin * 2, body_h)

        sidebar_w = max(150, min(round(width * 0.23), round(330 * self.scale)))
        self.sidebar_rect = pygame.Rect(self.body_rect.x, self.body_rect.y, sidebar_w, body_h)
        self.chat_rect = pygame.Rect(
            self.sidebar_rect.right + self.gap,
            self.body_rect.y,
            self.body_rect.right - self.sidebar_rect.right - self.gap,
            body_h,
        )
        self.input_rect = pygame.Rect(self.chat_rect.x, input_y, self.chat_rect.width, input_h)

        self.pad = max(10, round(16 * self.scale))
        self.chat_strip_h = max(28, round(36 * self.scale))
        self.chat_viewport = pygame.Rect(
            self.chat_rect.x + self.pad,
            self.chat_rect.y + self.chat_strip_h + round(4 * self.scale),
            self.chat_rect.width - self.pad * 2,
            self.chat_rect.height - self.chat_strip_h - self.pad - round(6 * self.scale),
        )

        self.portrait_h = max(80, min(round(body_h * 0.38), round(280 * self.scale)))
        button_h = max(34, round(42 * self.scale))
        self.back_button = MenuButton(
            pygame.Rect(
                self.sidebar_rect.x + self.pad,
                self.sidebar_rect.bottom - self.pad - button_h,
                self.sidebar_rect.width - self.pad * 2,
                button_h,
            ),
            "Return to Map",
            lambda: "back_to_map",
            self.font_button,
        )
        send_w = max(74, round(96 * self.scale))
        self.send_button = MenuButton(
            pygame.Rect(
                self.input_rect.right - send_w - 6,
                self.input_rect.y + 6,
                send_w,
                input_h - 12,
            ),
            "Send",
            self._send,
            self.font_button,
            primary=True,
        )

    def _font(self, size: float, *, bold: bool = False) -> pygame.font.Font:
        return ui_font(size * self.scale, bold=bold)

    @property
    def max_scroll(self) -> int:
        if self._chat_surface is None:
            return 0
        return max(0, self._chat_surface.get_height() - self.chat_viewport.height)

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------

    def _send(self) -> None:
        if self.loading:
            return
        text = self.input_text.strip()
        if not text:
            return
        self.input_text = ""
        self.history.append({"speaker": "player", "text": text, "mood": ""})
        self.session.record_player_statement(self.npc_id, text)
        self.loading = True
        self._chat_dirty = True

        try:
            files = self.session.loaded.npcs[self.npc_id]
            clues = self.session.loaded.clues.clues
            reply = self.conversation_service.reply(files, text, clues=clues)
            revealed = 0
            for clue_id in reply.revealed_clue_ids:
                try:
                    if self.session.npc_reveal(self.npc_id, clue_id) is not None:
                        revealed += 1
                except ValueError:
                    continue
            self.history.append(
                {
                    "speaker": "npc",
                    "text": humanize(reply.text, self._places),
                    "mood": getattr(reply.mood, "value", str(reply.mood)),
                }
            )
            self.current_mood = getattr(reply.mood, "value", str(reply.mood))
            if revealed:
                self.history.append(
                    {
                        "speaker": "system",
                        "text": "New evidence — press J to read your journal.",
                        "mood": "",
                    }
                )
        except Exception as error:  # keep the scene alive if the service fails
            self.history.append(
                {
                    "speaker": "system",
                    "text": f"The conversation falters for a moment. ({error})",
                    "mood": "",
                }
            )
        finally:
            self.loading = False
            self._chat_dirty = True
            self.stick_to_bottom = True

    # ------------------------------------------------------------------
    # Chat rendering
    # ------------------------------------------------------------------

    def _bubble(
        self,
        text: str,
        mood: str,
        *,
        speaker: str,
    ) -> tuple[pygame.Surface, bool]:
        pad = max(9, round(12 * self.scale))
        max_w = max(160, round(self.chat_viewport.width * 0.76))
        lines = wrap_text(text, self.font_body, max_w - pad * 2)
        line_h = self.font_body.get_linesize()
        meta_h = self.font_meta.get_height()
        meta = self.name if speaker == "npc" else "You"
        if speaker == "npc" and mood:
            meta = f"{self.name} · {mood}"
        text_w = max((self.font_body.size(line)[0] for line in lines), default=0)
        width = max(140, min(max_w, text_w + pad * 2))
        height = pad * 2 + meta_h + 2 + len(lines) * line_h

        bubble = pygame.Surface((width, height), pygame.SRCALPHA)
        if speaker == "npc":
            fill, border, meta_color = (30, 28, 24, 240), (132, 112, 76), (216, 190, 138)
        else:
            fill, border, meta_color = (22, 38, 50, 240), (88, 126, 154), (168, 196, 214)
        rect = bubble.get_rect()
        pygame.draw.rect(bubble, fill, rect, border_radius=12)
        pygame.draw.rect(bubble, border, rect, 1, border_radius=12)
        bubble.blit(self.font_meta.render(meta, True, meta_color), (pad, pad))
        y = pad + meta_h + 2
        for line in lines:
            bubble.blit(self.font_body.render(line, True, (232, 230, 220)), (pad, y))
            y += line_h
        return bubble, speaker == "player"

    def _system_line(self, text: str) -> pygame.Surface:
        lines = wrap_text(text, self.font_small, self.chat_viewport.width - 40)
        line_h = self.font_small.get_linesize()
        block = pygame.Surface((self.chat_viewport.width, len(lines) * line_h + 8), pygame.SRCALPHA)
        for index, line in enumerate(lines):
            surface = self.font_small.render(line, True, (188, 180, 160))
            block.blit(
                surface,
                (self.chat_viewport.width // 2 - surface.get_width() // 2, 4 + index * line_h),
            )
        return block

    def _render_chat(self) -> pygame.Surface:
        width = self.chat_viewport.width
        gap = max(6, round(10 * self.scale))
        blocks: list[tuple[pygame.Surface, bool, str]] = []
        for message in self.history:
            speaker = message["speaker"]
            if speaker == "system":
                blocks.append((self._system_line(message["text"]), False, "system"))
            else:
                bubble, right = self._bubble(
                    message["text"], message.get("mood", ""), speaker=speaker
                )
                blocks.append((bubble, right, speaker))

        height = max(
            self.chat_viewport.height,
            sum(block.get_height() for block, _right, _speaker in blocks) + gap * len(blocks) + 10,
        )
        content = pygame.Surface((width, height), pygame.SRCALPHA)
        used = sum(block.get_height() for block, _right, _speaker in blocks) + gap * len(blocks)
        y = 4 if used + 10 >= height else height - used - 4
        for block, right, speaker in blocks:
            if speaker == "system":
                x = 0
            elif right:
                x = width - block.get_width() - 8
            else:
                x = 6
            content.blit(block, (x, y))
            if speaker == "npc":
                tail_y = y + 14
                pygame.draw.polygon(
                    content,
                    (132, 112, 76),
                    [(x, tail_y), (x - 6, tail_y + 7), (x, tail_y + 14)],
                )
            elif speaker == "player":
                tail_x = x + block.get_width()
                tail_y = y + 14
                pygame.draw.polygon(
                    content,
                    (88, 126, 154),
                    [(tail_x, tail_y), (tail_x + 6, tail_y + 7), (tail_x, tail_y + 14)],
                )
            y += block.get_height() + gap
        return content

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    def _scroll_by(self, amount: int) -> None:
        self.stick_to_bottom = False
        self.scroll = max(0, min(self.max_scroll, self.scroll + amount))

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if self.back_button.handle_event(event):
            return "back_to_map"
        self.send_button.handle_event(event)

        if event.type == pygame.MOUSEWHEEL:
            self._scroll_by(-event.y * round(70 * self.scale))
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back_to_map"
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._send()
                return None
            if event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key in (pygame.K_DOWN, pygame.K_PAGEDOWN):
                self._scroll_by(round(self.chat_viewport.height * 0.6))
            elif event.key in (pygame.K_UP, pygame.K_PAGEUP):
                self._scroll_by(-round(self.chat_viewport.height * 0.6))
            elif event.key == pygame.K_HOME:
                self.stick_to_bottom = False
                self.scroll = 0
            elif event.key == pygame.K_END:
                self.stick_to_bottom = True
            elif not getattr(event, "mod", 0) & pygame.KMOD_CTRL:
                character = getattr(event, "unicode", "")
                if character and character.isprintable() and len(self.input_text) < _MAX_INPUT:
                    self.input_text += character
        return None

    def update(self) -> None:
        self.tick += 1
        self.back_button.update()
        self.send_button.update()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        self.backdrop.draw(surface, self.tick)
        surface.blit(self._dim, (0, 0))
        self._draw_header(surface)
        self._draw_sidebar(surface)
        self._draw_chat(surface)
        self._draw_input(surface)

    def _mood_color(self) -> tuple[int, int, int]:
        return _MOOD_COLORS.get(self.current_mood, (156, 156, 150))

    def _draw_header(self, surface: pygame.Surface) -> None:
        draw_panel(
            surface,
            self.header_rect,
            fill=(12, 16, 20, 226),
            border=(120, 102, 70),
            radius=12,
            shadow=False,
        )
        x = self.header_rect.x + self.pad + 4
        y = self.header_rect.y + max(6, round(9 * self.scale))
        overline = self.font_overline.render("IN CONVERSATION", True, (196, 166, 108))
        surface.blit(overline, (x, y))
        y += overline.get_height() + 2
        name = self.font_title.render(self.name, True, GOLD)
        surface.blit(name, (x, y))
        y += name.get_height()
        subtitle = self.font_subtitle.render(f"{self.role} · {self.place_name}", True, MUTED)
        surface.blit(subtitle, (x, y))

        text = self.current_mood[:1].upper() + self.current_mood[1:]
        pill_font = self.font_small
        label = pill_font.render(text, True, (238, 236, 226))
        dot_r = max(4, round(5 * self.scale))
        pill_h = max(24, round(30 * self.scale))
        pill_w = label.get_width() + dot_r * 2 + 30
        pill = pygame.Rect(
            self.header_rect.right - pill_w - self.pad,
            self.header_rect.centery - pill_h // 2,
            pill_w,
            pill_h,
        )
        pygame.draw.rect(surface, (24, 28, 30, 230), pill, border_radius=pill_h // 2)
        pygame.draw.rect(surface, self._mood_color(), pill, 1, border_radius=pill_h // 2)
        pygame.draw.circle(surface, self._mood_color(), (pill.x + dot_r + 8, pill.centery), dot_r)
        surface.blit(
            label,
            (pill.x + dot_r * 2 + 14, pill.centery - label.get_height() // 2),
        )
        hint = self.font_meta.render("Esc leaves the conversation", True, (150, 146, 136))
        surface.blit(
            hint,
            (pill.right - hint.get_width(), pill.bottom + max(3, round(4 * self.scale))),
        )

    def _draw_sidebar(self, surface: pygame.Surface) -> None:
        rect = self.sidebar_rect
        draw_panel(surface, rect, fill=(11, 15, 19, 238), border=(102, 90, 66), radius=12)

        portrait = pygame.Rect(
            rect.x + self.pad,
            rect.y + self.pad,
            rect.width - self.pad * 2,
            self.portrait_h,
        )
        pygame.draw.rect(surface, (20, 24, 28), portrait, border_radius=10)
        pygame.draw.rect(surface, (78, 70, 54), portrait, 1, border_radius=10)
        avatar_h = portrait.height - round(16 * self.scale)
        avatar = render_npc(self.identity.role, self.npc_id, avatar_h, self.tick)
        px = portrait.centerx - avatar.get_width() // 2
        py = portrait.bottom - avatar.get_height() - round(6 * self.scale)
        pygame.draw.ellipse(
            surface,
            (8, 10, 12),
            (
                px - round(avatar.get_width() * 0.25),
                portrait.bottom - round(10 * self.scale),
                round(avatar.get_width() * 1.5),
                round(10 * self.scale),
            ),
        )
        surface.blit(avatar, (px, py))

        y = portrait.bottom + round(12 * self.scale)
        heading = self.font_heading.render("KNOWN TO BE", True, (196, 166, 108))
        surface.blit(heading, (rect.x + self.pad, y))
        y += heading.get_height() + 3
        for trait in self.traits:
            lines = wrap_text(trait, self.font_small, rect.width - self.pad * 2 - 14)
            pygame.draw.circle(surface, GOLD, (rect.x + self.pad + 3, y + 6), 2)
            for line in lines:
                surface.blit(
                    self.font_small.render(line, True, (218, 214, 202)),
                    (rect.x + self.pad + 12, y),
                )
                y += self.font_small.get_linesize()

        tips_top = self.back_button.rect.top - round(10 * self.scale)
        tips = (
            "Ask where they were.",
            "Ask who was with them.",
            "Ask what seemed odd.",
        )
        tip_h = 22 + self.font_meta.get_height() * len(tips) + 10
        tips_y = tips_top - tip_h

        story_top = y + round(10 * self.scale)
        story_bottom = tips_y - round(10 * self.scale)
        line_h = self.font_small.get_linesize()
        heading_h = self.font_heading.get_height()
        if story_bottom - story_top >= heading_h + line_h * 3:
            story_heading = self.font_heading.render("BACKSTORY", True, (196, 166, 108))
            surface.blit(story_heading, (rect.x + self.pad, story_top))
            story_y = story_top + heading_h + 3
            max_lines = max(1, min(7, (story_bottom - story_y) // line_h))
            lines = wrap_text(self.identity.backstory, self.font_small, rect.width - self.pad * 2)
            if len(lines) > max_lines:
                lines = lines[:max_lines]
                lines[-1] = self._ellipsis(lines[-1], self.font_small, rect.width - self.pad * 2)
            for line in lines:
                surface.blit(
                    self.font_small.render(line, True, (198, 194, 182)),
                    (rect.x + self.pad, story_y),
                )
                story_y += line_h

        if tips_y > y + 8:
            pygame.draw.line(
                surface,
                (70, 66, 56),
                (rect.x + self.pad, tips_y - 8),
                (rect.right - self.pad, tips_y - 8),
                1,
            )
            for index, tip in enumerate(tips):
                text = self.font_meta.render(f"· {tip}", True, (172, 168, 154))
                surface.blit(
                    text, (rect.x + self.pad, tips_y + index * self.font_meta.get_linesize())
                )

        self.back_button.draw(surface)

    @staticmethod
    def _ellipsis(text: str, font: pygame.font.Font, width: int) -> str:
        ellipsis = "…"
        while text and font.size(text + ellipsis)[0] > width:
            text = text[:-1]
        return text.rstrip() + ellipsis

    def _draw_chat(self, surface: pygame.Surface) -> None:
        rect = self.chat_rect
        draw_panel(surface, rect, fill=(10, 14, 18, 238), border=(102, 90, 66), radius=12)

        label = self.font_meta.render("CONVERSATION", True, (196, 166, 108))
        surface.blit(label, (rect.x + self.pad, rect.y + max(6, round(7 * self.scale))))
        hint = self.font_meta.render("scroll to reread", True, (140, 136, 124))
        surface.blit(
            hint,
            (
                rect.right - self.pad - hint.get_width(),
                rect.y + max(6, round(7 * self.scale)),
            ),
        )
        pygame.draw.line(
            surface,
            (70, 66, 56),
            (rect.x + self.pad, rect.y + self.chat_strip_h),
            (rect.right - self.pad, rect.y + self.chat_strip_h),
            1,
        )

        if self._chat_dirty:
            self._chat_surface = self._render_chat()
            self._chat_dirty = False
        assert self._chat_surface is not None
        if self.stick_to_bottom:
            self.scroll = self.max_scroll

        surface.set_clip(self.chat_viewport)
        surface.blit(
            self._chat_surface,
            self.chat_viewport.topleft,
            pygame.Rect(
                0,
                self.scroll,
                self.chat_viewport.width,
                self.chat_viewport.height,
            ),
        )
        surface.set_clip(None)

        if not self.history:
            lines = (
                "Nobody has said anything yet.",
                "Say hello, then ask where they were when it happened.",
            )
            line_h = self.font_body.get_linesize()
            top = self.chat_viewport.centery - line_h
            for index, line in enumerate(lines):
                text = self.font_body.render(line, True, (158, 156, 146))
                surface.blit(
                    text,
                    (self.chat_viewport.centerx - text.get_width() // 2, top + index * line_h),
                )

        if self.max_scroll > 0:
            track = pygame.Rect(
                self.chat_viewport.right + round(2 * self.scale),
                self.chat_viewport.y + 4,
                max(4, round(6 * self.scale)),
                self.chat_viewport.height - 8,
            )
            pygame.draw.rect(surface, (40, 44, 46), track, border_radius=track.width // 2)
            thumb_h = max(
                round(28 * self.scale),
                round(track.height * self.chat_viewport.height / self._chat_surface.get_height()),
            )
            travel = track.height - thumb_h
            ratio = self.scroll / self.max_scroll if self.max_scroll else 0
            pygame.draw.rect(
                surface,
                (160, 138, 94),
                (track.x, track.y + round(travel * ratio), track.width, thumb_h),
                border_radius=track.width // 2,
            )

    def _draw_input(self, surface: pygame.Surface) -> None:
        rect = self.input_rect
        draw_panel(
            surface,
            rect,
            fill=(12, 16, 20, 236),
            border=(GOLD if self.input_text else (108, 96, 72)),
            radius=11,
            shadow=False,
        )
        field = pygame.Rect(
            rect.x + 6,
            rect.y + 6,
            max(40, self.send_button.rect.x - rect.x - 14),
            rect.height - 12,
        )
        pygame.draw.rect(surface, (8, 11, 14), field, border_radius=8)

        prompt_x = field.x + 12
        baseline = field.centery
        if self.input_text:
            text = self.font_input.render(self.input_text, True, (238, 236, 226))
            surface.blit(text, (prompt_x, baseline - text.get_height() // 2))
            caret_x = prompt_x + text.get_width() + 2
        else:
            placeholder = self.font_input.render(
                f"Ask {self.name} something…", True, (122, 122, 116)
            )
            surface.blit(placeholder, (prompt_x, baseline - placeholder.get_height() // 2))
            caret_x = prompt_x
        if self.tick // 18 % 2 == 0 and not self.loading:
            caret_h = max(14, round(20 * self.scale))
            pygame.draw.line(
                surface,
                GOLD,
                (caret_x, baseline - caret_h // 2),
                (caret_x, baseline + caret_h // 2),
                2,
            )

        self.send_button.draw(surface)
