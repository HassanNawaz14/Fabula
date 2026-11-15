from __future__ import annotations

from typing import Any

import pygame

from fabula.ui.menu_theme import (
    CREAM,
    GOLD,
    MUTED,
    MenuBackdrop,
    MenuButton,
    menu_button_width,
    render_spaced,
    ui_font,
    wrap_text,
)

_SECTIONS: tuple[tuple[str, str], ...] = (
    (
        "heading",
        "YOUR JOB",
    ),
    (
        "body",
        "Something has gone wrong in a small town: a theft, a disappearance, or a "
        "murder. You have about ten minutes to work out who did it, how they did it, "
        "and why. When you are sure, name the culprit.",
    ),
    ("heading", "FINDING YOUR WAY"),
    (
        "bullet",
        "Click a nearby place to walk there. The roads show which places are connected.",
    ),
    (
        "bullet",
        "Click the place where you are standing, or press E, to search it for clues.",
    ),
    ("bullet", "Click a villager, or press T, to start a conversation."),
    ("bullet", "Press J for your journal and A to make an accusation."),
    (
        "bullet",
        "Hover over anything for a short explanation. On the town map, use Quit or "
        "press Esc to leave the game.",
    ),
    ("heading", "WHAT TO DO FIRST"),
    (
        "body",
        "Search the scene of the crime, then read your journal. Talk to everyone, even "
        "the people who seem harmless. Two villagers will describe the same moment "
        "differently, and one of them is lying.",
    ),
    ("heading", "TALKING TO PEOPLE"),
    (
        "body",
        "Ask short, specific questions: 'Where were you at eight o'clock?' 'Who was "
        "with you?' 'Did you see anyone near the library?' The townsfolk answer in "
        "their own words and remember what you asked them before. If someone dodges a "
        "question, try asking it another way.",
    ),
    ("heading", "THE AI BEHIND THE STORY"),
    (
        "body",
        "Two kinds of AI help make Fabula. You never have to write a prompt or "
        "understand the technology to play.",
    ),
    ("subheading", "Characters with minds of their own"),
    (
        "body",
        "Each villager is played by an AI that knows only that character's memories, "
        "opinions and secrets. It does not know the solution. That is why people can be "
        "mistaken, evasive, or convincing liars, just like real witnesses. The AI stays "
        "in character, keeping the same voice, mood and loyalties for the whole case.",
    ),
    (
        "body",
        "How to use it: talk naturally, in your own words. The character remembers your "
        "conversation and reacts to what you say. With an internet connection and an API "
        "key (GEMINI_API_KEY or XAI_API_KEY), replies are written live. Without a key, a "
        "hand-written understudy takes over, so the case is always playable.",
    ),
    ("subheading", "Cases written before you arrive"),
    (
        "body",
        "A new mystery can be written by AI before the game begins. A small AI writer, "
        "trained for this game, invents the town, the people, their secrets, the clues "
        "and the truth. The game then checks the story for contradictions: for example, "
        "it makes sure nobody is in two places at once.",
    ),
    (
        "body",
        "How to use it: choose Generate New Game on the menu. The game writes and checks "
        "a fresh case before you arrive. This takes longer than opening the ready-made "
        "case, so Play Mystery is the quick option.",
    ),
    (
        "callout",
        "A promise of fairness: the solution is locked away from every character and "
        "every conversation. A character can lie to you, but the AI can never peek at "
        "the answer.",
    ),
    ("heading", "A FEW GOOD QUESTIONS"),
    ("bullet", "Where were you when it happened?"),
    ("bullet", "Who was with you?"),
    ("bullet", "What did you notice that seemed odd?"),
    ("bullet", "What do you think of the other villagers?"),
    ("bullet", "Is there anything you are not telling me?"),
    ("heading", "STUCK?"),
    (
        "body",
        "Revisit places you have already searched: people move around town as the day "
        "goes on. A clue in one place often makes sense of a story told somewhere else.",
    ),
    ("heading", "WHEN YOU ARE READY"),
    (
        "body",
        "Press A or click Accuse. Choose who did it, how, and why. You only get one "
        "accusation, so think it through.",
    ),
)


class HowToPlayView:
    """Scrollable, plain-language guide to the game and its AI."""

    def __init__(self, width: int, height: int, app: Any) -> None:
        self.width = width
        self.height = height
        self.app = app
        self.scale = max(0.65, min(width / 1600, height / 900))
        self.tick = 0
        self.scroll = 0

        self.font_overline = self._font(17)
        self.font_title = self._font(58, bold=True)
        self.font_subtitle = self._font(19)
        self.heading_font = self._font(27, bold=True)
        self.subheading_font = self._font(21, bold=True)
        self.body_font = self._font(19)
        self.footer_font = self._font(15)
        self.button_font = self._font(22)

        self.backdrop = MenuBackdrop(width, height)
        self._dim = pygame.Surface((width, height), pygame.SRCALPHA)
        self._dim.fill((5, 9, 13, 120))

        margin_x = max(24, round(width * 0.05))
        self.header_top = round(height * 0.055)
        self.overline = self.font_overline.render("FIELD GUIDE", True, (196, 166, 108))
        self.title = render_spaced(
            "HOW TO PLAY", self.font_title, GOLD, max(2, round(5 * self.scale))
        )
        self.subtitle = self.font_subtitle.render(
            "Everything you need to know — no experience required.", True, MUTED
        )

        header_bottom = (
            self.header_top
            + self.overline.get_height()
            + round(4 * self.scale)
            + self.title.get_height()
            + round(6 * self.scale)
            + self.subtitle.get_height()
        )
        footer_h = max(66, round(height * 0.12))
        card_top = header_bottom + round(22 * self.scale)
        card_bottom = self.height - footer_h
        card_w = min(width - margin_x * 2, round(840 * self.scale))
        card_h = max(200, card_bottom - card_top)
        self.card = pygame.Rect(0, 0, card_w, card_h)
        self.card.midtop = (width // 2, card_top)

        self.pad = max(14, round(30 * self.scale))
        self.scrollbar_w = max(6, round(10 * self.scale))
        self.viewport = pygame.Rect(
            self.card.x + self.pad,
            self.card.y + self.pad,
            self.card.width - self.pad * 2 - self.scrollbar_w - round(6 * self.scale),
            self.card.height - self.pad * 2,
        )
        self.content_width = self.viewport.width - round(4 * self.scale)

        button_h = max(36, round(46 * self.scale))
        button_w = max(
            round(240 * self.scale),
            menu_button_width("Back to Menu", self.button_font, scale=self.scale),
        )
        self.back_button = MenuButton(
            pygame.Rect(
                width // 2 - button_w // 2,
                self.height - footer_h + (footer_h - button_h) // 2,
                button_w,
                button_h,
            ),
            "Back to Menu",
            lambda: "back_to_menu",
            self.button_font,
        )
        self.footer_hint = self.footer_font.render(
            "Mouse wheel or arrow keys to scroll  ·  Esc to go back", True, (142, 142, 136)
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

    def _line_block(self, lines: list[str], font: pygame.font.Font, color: Any) -> pygame.Surface:
        line_h = font.get_linesize()
        block = pygame.Surface((self.content_width, line_h * len(lines)), pygame.SRCALPHA)
        for index, line in enumerate(lines):
            block.blit(font.render(line, True, color), (0, index * line_h))
        return block

    def _bullet_block(self, text: str) -> pygame.Surface:
        prefix = "•  "
        indent = self.body_font.size(prefix)[0]
        lines: list[str] = []
        current = ""
        for word in text.split():
            trial = f"{current} {word}".strip()
            limit = self.content_width - (indent if lines else 0)
            if current and self.body_font.size(trial)[0] > limit:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
        line_h = self.body_font.get_linesize()
        block = pygame.Surface((self.content_width, line_h * len(lines)), pygame.SRCALPHA)
        for index, line in enumerate(lines):
            text_line = (prefix + line) if index == 0 else line
            x = 0 if index == 0 else indent
            block.blit(
                self.body_font.render(text_line, True, (214, 214, 206)),
                (x, index * line_h),
            )
        return block

    def _callout_block(self, text: str) -> pygame.Surface:
        pad = round(18 * self.scale)
        lines = wrap_text(text, self.body_font, self.content_width - pad * 2)
        line_h = self.body_font.get_linesize()
        block = pygame.Surface((self.content_width, line_h * len(lines) + pad * 2), pygame.SRCALPHA)
        pygame.draw.rect(block, (26, 30, 34, 228), block.get_rect(), border_radius=8)
        pygame.draw.rect(block, (170, 146, 92), block.get_rect(), 2, border_radius=8)
        for index, line in enumerate(lines):
            block.blit(
                self.body_font.render(line, True, (238, 226, 198)),
                (pad, pad + index * line_h),
            )
        return block

    def _build_content(self) -> pygame.Surface:
        blocks: list[tuple[int, pygame.Surface]] = []
        for kind, text in _SECTIONS:
            if kind == "heading":
                heading = self.heading_font.render(text, True, GOLD)
                block = pygame.Surface(
                    (self.content_width, heading.get_height() + round(8 * self.scale)),
                    pygame.SRCALPHA,
                )
                block.blit(heading, (0, 0))
                rule_y = heading.get_height() + round(4 * self.scale)
                pygame.draw.line(
                    block,
                    (138, 116, 78),
                    (0, rule_y),
                    (min(self.content_width, round(96 * self.scale)), rule_y),
                    2,
                )
                blocks.append((round(26 * self.scale) if blocks else 0, block))
            elif kind == "subheading":
                blocks.append(
                    (
                        round(18 * self.scale),
                        self.subheading_font.render(text, True, CREAM),
                    )
                )
            elif kind == "bullet":
                blocks.append((round(5 * self.scale), self._bullet_block(text)))
            elif kind == "callout":
                blocks.append((round(14 * self.scale), self._callout_block(text)))
            else:
                lines = wrap_text(text, self.body_font, self.content_width)
                blocks.append(
                    (
                        round(10 * self.scale),
                        self._line_block(lines, self.body_font, (214, 214, 206)),
                    )
                )

        total = sum(gap + block.get_height() for gap, block in blocks) + round(16 * self.scale)
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
            return "back_to_menu"
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_by(-event.y * round(70 * self.scale))
        elif event.type == pygame.KEYDOWN:
            step = round(52 * self.scale)
            if event.key == pygame.K_ESCAPE:
                return "back_to_menu"
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

        x = self.width // 2
        y = self.header_top
        surface.blit(self.overline, (x - self.overline.get_width() // 2, y))
        y += self.overline.get_height() + round(4 * self.scale)
        surface.blit(self.title, (x - self.title.get_width() // 2, y))
        y += self.title.get_height() + round(6 * self.scale)
        surface.blit(self.subtitle, (x - self.subtitle.get_width() // 2, y))

        shadow = self.card.move(0, 8)
        shadow_surface = pygame.Surface(shadow.size, pygame.SRCALPHA)
        pygame.draw.rect(
            shadow_surface, (0, 0, 0, 110), shadow_surface.get_rect(), border_radius=14
        )
        surface.blit(shadow_surface, shadow.topleft)
        panel = pygame.Surface(self.card.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (12, 16, 20, 232), panel.get_rect(), border_radius=14)
        surface.blit(panel, self.card.topleft)
        pygame.draw.rect(surface, (146, 124, 84), self.card, 2, border_radius=14)

        surface.set_clip(self.viewport)
        surface.blit(
            self.content,
            self.viewport.topleft,
            pygame.Rect(0, self.scroll, self.viewport.width, self.viewport.height),
        )
        surface.set_clip(None)

        if self.max_scroll > 0:
            track = pygame.Rect(
                self.viewport.right + round(7 * self.scale),
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
            thumb = pygame.Rect(track.x, thumb_y, track.width, thumb_h)
            pygame.draw.rect(surface, (186, 158, 104), thumb, border_radius=thumb.width // 2)

        self.back_button.draw(surface)
        hint_x = self.width - self.footer_hint.get_width() - max(24, round(self.width * 0.05))
        if hint_x > self.back_button.rect.right + 16:
            surface.blit(
                self.footer_hint,
                (
                    hint_x,
                    self.back_button.rect.centery - self.footer_hint.get_height() // 2,
                ),
            )
