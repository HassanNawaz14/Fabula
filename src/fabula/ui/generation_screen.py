"""Progress screen for a running local or Kaggle generation job."""

from __future__ import annotations

import math
from typing import Any

import pygame

from fabula.ui.menu_theme import (
    CREAM,
    GOLD,
    MUTED,
    MenuBackdrop,
    draw_panel,
    ui_font,
    wrap_text,
)


class GenerationScreen:
    """Show live progress for a case job, or the legacy static loading view."""

    def __init__(
        self,
        width: int,
        height: int,
        job: Any = None,
        *,
        title: str | None = None,
        estimate: str | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.job = job
        self.scale = max(0.65, min(width / 1600, height / 900))
        self.tick = 0
        self.title = title or (getattr(job, "label", None) or "MYSTERY GENERATION")
        self.estimate = estimate or getattr(job, "estimate", "")
        self.status_message = "Preparing the case…"
        self.progress = 0.0
        self.error: str | None = None
        self.is_ready = False
        self.updates: list[Any] = []
        self._action_taken = False

        self.font_overline = self._font(16, bold=True)
        self.font_title = self._font(38, bold=True)
        self.font_subtitle = self._font(18)
        self.font_status = self._font(22)
        self.font_body = self._font(16)
        self.font_log = self._font(14)
        self.font_footer = self._font(14)

        self.backdrop = MenuBackdrop(width, height)
        self._dim = pygame.Surface((width, height), pygame.SRCALPHA)
        self._dim.fill((4, 8, 12, 130))
        self._layout()

    def _font(self, size: float, *, bold: bool = False) -> pygame.font.Font:
        return ui_font(size * self.scale, bold=bold)

    def _layout(self) -> None:
        scale = self.scale
        margin = max(20, round(30 * scale))
        top = max(18, round(30 * scale))
        self.panel = pygame.Rect(
            margin,
            top,
            self.width - margin * 2,
            self.height - top - margin,
        )
        self.pad = max(16, round(26 * scale))

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def _consume_job(self) -> None:
        if self.job is None:
            return
        updates = self.job.drain()
        if updates:
            self.updates.extend(updates)
            self.updates = self.updates[-6:]
            self.status_message = updates[-1].message
        if self.job.is_done:
            if self.job.error:
                self.error = str(self.job.error)
            elif self.job.result_path is not None:
                self.is_ready = True
                self.progress = 1.0
                self.status_message = "The case is ready."

    def take_action(self) -> dict[str, str] | None:
        if self.job is None or not self.is_ready or self._action_taken:
            return None
        path = getattr(self.job, "result_path", None)
        if path is None:
            return None
        self._action_taken = True
        return {"action": "session_ready", "path": str(path)}

    def handle_event(self, event: pygame.event.Event) -> Any:
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_ESCAPE:
            if self.job is not None and not self.job.is_done:
                self.job.cancel()
            return "back_to_menu"
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.is_ready:
            if self.job is not None:
                return self.take_action()
            return "start_game"
        return None

    def update(self) -> None:
        self.tick += 1
        self._consume_job()

    @property
    def elapsed(self) -> float:
        return float(getattr(self.job, "elapsed", 0.0)) if self.job is not None else 0.0

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        self.backdrop.draw(surface, self.tick)
        surface.blit(self._dim, (0, 0))
        draw_panel(surface, self.panel)

        center = self.panel.centerx
        y = self.panel.y + self.pad
        overline = self.font_overline.render("PRE-PLAY GENERATION", True, GOLD)
        surface.blit(overline, (center - overline.get_width() // 2, y))
        y += overline.get_height() + max(2, round(5 * self.scale))

        title = self.font_title.render(self.title, True, CREAM)
        surface.blit(title, (center - title.get_width() // 2, y))
        y += title.get_height() + max(2, round(5 * self.scale))

        if self.estimate:
            estimate = self.font_subtitle.render(self.estimate, True, MUTED)
            surface.blit(estimate, (center - estimate.get_width() // 2, y))

        if self.error:
            self._draw_error(surface)
            self._draw_footer(surface, "Esc returns to the menu")
            return

        self._draw_status(surface, y + max(24, round(38 * self.scale)))
        if self.is_ready:
            prompt = self.font_status.render(
                "Press ENTER to begin the investigation", True, (156, 226, 164)
            )
            prompt_y = (
                self.panel.bottom
                - self.font_footer.get_height()
                - prompt.get_height()
                - max(24, round(36 * self.scale))
            )
            surface.blit(prompt, (center - prompt.get_width() // 2, prompt_y))
        self._draw_footer(
            surface,
            "Esc cancels and returns to the menu"
            if self.job and not self.job.is_done
            else "Esc back",
        )

    def _draw_status(self, surface: pygame.Surface, y: int) -> None:
        center = self.panel.centerx
        if self.job is not None and not self.job.is_done:
            self._draw_spinner(surface, (center, y + 22), max(12, round(18 * self.scale)))
            y += max(44, round(66 * self.scale))

        message = self.status_message
        if self.job is not None and not self.is_ready and not self.error:
            message = getattr(self.job, "status_message", message) or message
        lines = wrap_text(message, self.font_status, self.panel.width - self.pad * 3)
        for line in lines[:3]:
            text = self.font_status.render(line, True, CREAM)
            surface.blit(text, (center - text.get_width() // 2, y))
            y += text.get_height() + max(2, round(3 * self.scale))

        if self.job is not None:
            elapsed = self._format_elapsed(self.elapsed)
            meta = self.font_body.render(f"Elapsed  {elapsed}", True, MUTED)
            surface.blit(meta, (center - meta.get_width() // 2, y + max(8, round(12 * self.scale))))
            y += max(32, round(48 * self.scale))
            self._draw_progress_bar(surface, y)

        log_top = self.panel.bottom - max(150, round(190 * self.scale))
        y = max(y + max(24, round(36 * self.scale)), log_top)
        for update in self.updates[-4:]:
            line = f"• {update.message}"
            text = self.font_log.render(line, True, (168, 170, 160))
            surface.blit(
                text,
                (self.panel.x + self.pad, y),
            )
            y += text.get_height() + max(1, round(2 * self.scale))

    def _draw_spinner(self, surface: pygame.Surface, center: tuple[int, int], radius: int) -> None:
        for index in range(8):
            angle = (self.tick * 0.12) + index * 0.785
            step = 70 + index * 22
            x = center[0] + round(math.cos(angle) * radius)
            y = center[1] + round(math.sin(angle) * radius)
            pygame.draw.circle(surface, (step, step, min(255, step + 20)), (x, y), 3)

    def _draw_progress_bar(self, surface: pygame.Surface, y: int) -> None:
        bar = pygame.Rect(
            self.panel.x + self.pad,
            y,
            self.panel.width - self.pad * 2,
            max(6, round(9 * self.scale)),
        )
        pygame.draw.rect(surface, (32, 34, 32), bar, border_radius=bar.height)
        if self.progress >= 1.0:
            width = bar.width
            offset = 0
        else:
            width = max(round(bar.width * 0.22), 40)
            span = bar.width - width
            offset = round((self.tick * 6) % max(1, span + 1)) if span > 0 else 0
        pygame.draw.rect(
            surface,
            GOLD,
            pygame.Rect(bar.x + offset, bar.y, width, bar.height),
            border_radius=bar.height,
        )

    def _draw_error(self, surface: pygame.Surface) -> None:
        center = self.panel.centerx
        y = self.panel.centery - max(40, round(70 * self.scale))
        lines = wrap_text(
            self.error or "Unknown error", self.font_body, self.panel.width - self.pad * 3
        )
        for line in lines[:8]:
            text = self.font_body.render(line, True, (246, 156, 136))
            surface.blit(text, (center - text.get_width() // 2, y))
            y += text.get_height() + max(2, round(4 * self.scale))

    def _draw_footer(self, surface: pygame.Surface, hint_text: str) -> None:
        hint = self.font_footer.render(hint_text, True, (146, 148, 140))
        surface.blit(
            hint,
            (
                self.panel.centerx - hint.get_width() // 2,
                self.panel.bottom - hint.get_height() - max(10, round(16 * self.scale)),
            ),
        )

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        total = max(0, int(seconds))
        return f"{total // 60:02d}:{total % 60:02d}"


__all__ = ["GenerationScreen"]
