from __future__ import annotations

from typing import Any

import pygame

from fabula.ui.components import Button, Panel


class DialogueView:
    """Renders conversation UI with an NPC using ConversationService."""

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
        self.npc = next(n for n in session.loaded.world.npcs if n.id == npc_id)
        self.input_text = ""
        self.history: list[dict[str, str]] = []
        self.current_mood = "neutral"
        self.loading = False
        
        self.font_title = pygame.font.Font(None, 28)
        self.font_body = pygame.font.Font(None, 20)
        
        self.panel = Panel(pygame.Rect(10, 80, width - 20, height - 160))
        self.exit_button = Button(pygame.Rect(width - 150, 15, 120, 30), "Return [ESC]", lambda: "back_to_map", self.font_body)

        # Load initial greeting or recent messages if any
        existing_statements = session.statements_for(npc_id)
        for st in existing_statements:
            self.history.append({"speaker": "Player", "text": st, "mood": ""})

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if self.exit_button.handle_event(event):
            return "back_to_map"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back_to_map"
            elif event.key == pygame.K_RETURN:
                if self.input_text.strip() and not self.loading:
                    text = self.input_text.strip()
                    self.input_text = ""
                    self._send_message(text)
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                if event.unicode and event.unicode.isprintable():
                    self.input_text += event.unicode
        return None

    def _send_message(self, text: str) -> None:
        self.history.append({"speaker": "Player", "text": text, "mood": ""})
        self.session.record_player_statement(self.npc_id, text)
        self.loading = True

        try:
            # Call ConversationService
            files = self.session.loaded.npcs[self.npc_id]
            clues = self.session.loaded.clues.clues
            reply_dto = self.conversation_service.reply(files, text, clues=clues)
            for clue_id in reply_dto.revealed_clue_ids:
                try:
                    self.session.npc_reveal(self.npc_id, clue_id)
                except Exception:
                    pass
            self.history.append(
                {"speaker": self.npc.display_name, "text": reply_dto.text, "mood": reply_dto.mood}
            )
            self.current_mood = reply_dto.mood
        except Exception as e:
            self.history.append(
                {
                    "speaker": self.npc.display_name,
                    "text": f"(Error reaching conversation service: {e})",
                    "mood": "nervous",
                }
            )
        finally:
            self.loading = False

    def update(self) -> None:
        self.exit_button.update()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((25, 30, 40))
        
        # Header
        pygame.draw.rect(surface, (40, 45, 60), (0, 0, self.width, 60))
        title_text = f"Conversation with {self.npc.display_name} — Mood: {self.current_mood}"
        title_surf = self.font_title.render(title_text, True, (255, 255, 255))
        surface.blit(title_surf, (20, 18))
        self.exit_button.draw(surface)

        # Chat history area
        self.panel.draw(surface)
        y_offset = 90
        for msg in self.history[-10:]:  # show last 10 messages
            speaker = msg["speaker"]
            txt = msg["text"]
            mood_str = f" [{msg['mood']}]" if msg["mood"] else ""
            line = f"{speaker}{mood_str}: {txt}"
            color = (255, 220, 100) if speaker != "Player" else (150, 220, 255)
            text_surf = self.font_body.render(line[:100], True, color)
            surface.blit(text_surf, (20, y_offset))
            y_offset += 25

        # Input box footer
        pygame.draw.rect(surface, (40, 40, 50), (10, self.height - 60, self.width - 20, 45))
        pygame.draw.rect(surface, (100, 120, 160), (10, self.height - 60, self.width - 20, 45), 2)

        prompt_str = f"> {self.input_text}"
        if self.loading:
            prompt_str = "Thinking..."
        input_surf = self.font_body.render(prompt_str, True, (240, 240, 255))
        surface.blit(input_surf, (20, self.height - 47))

