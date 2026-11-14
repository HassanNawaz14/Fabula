from __future__ import annotations

from typing import Any

import pygame

from fabula.simulation import Session
from fabula.ui.accusation import AccusationView
from fabula.ui.dialogue import DialogueView
from fabula.ui.generation_screen import GenerationScreen
from fabula.ui.journal import JournalView
from fabula.ui.map_view import MapView


class FabulaApp:
    """Main Pygame application runner for Fabula."""

    def __init__(
        self,
        session: Session | None = None,
        conversation_service: Any = None,
        width: int = 900,
        height: int = 650,
    ) -> None:
        self.width = width
        self.height = height
        self.session = session
        self.conversation_service = conversation_service

        if not pygame.get_init():
            pygame.init()

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Fabula — Mystery Investigation Game")
        self.clock = pygame.time.Clock()

        if self.session:
            self.state = "map"
            self.current_view = MapView(self.width, self.height, self.session)
        else:
            self.state = "generation"
            self.current_view = GenerationScreen(self.width, self.height)

    def set_session(self, session: Session) -> None:
        self.session = session
        self.state = "map"
        self.current_view = MapView(self.width, self.height, self.session)

    def run(self, max_ticks: int | None = None) -> None:
        running = True
        ticks = 0
        while running:
            if max_ticks and ticks >= max_ticks:
                break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                result = self.current_view.handle_event(event)
                if result:
                    self._handle_view_action(result)

            self.current_view.update()
            self.current_view.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(30)
            ticks += 1

        pygame.quit()

    def _handle_view_action(self, result: Any) -> None:
        if isinstance(result, str):
            if result == "start_game" and isinstance(self.current_view, GenerationScreen):
                pass  # needs session set
            elif result == "back_to_map" and self.session:
                self.state = "map"
                self.current_view = MapView(self.width, self.height, self.session)
            elif result == "open_journal" and self.session:
                self.state = "journal"
                self.current_view = JournalView(self.width, self.height, self.session)
            elif result == "open_accusation" and self.session:
                self.state = "accusation"
                self.current_view = AccusationView(self.width, self.height, self.session)
            elif result == "quit_game":
                pygame.quit()
        elif isinstance(result, dict):
            action = result.get("action")
            if action == "move" and self.session:
                loc_id = result.get("location_id")
                try:
                    self.session.move_player(loc_id)
                except Exception as e:
                    print(f"Movement error: {e}")
            elif action in ("examine_menu", "examine_location") and self.session:
                # Examine local clues if any
                loc_id = self.session.player_location
                clues = [
                    c
                    for c in self.session.loaded.clues.clues
                    if c.location_id == loc_id and c.id not in self.session.discovered_ids
                ]
                results = []
                for clue in clues:
                    try:
                        self.session.examine(loc_id, clue.id)
                        results.append(f"Found: {clue.description[:30]}...")
                    except Exception:
                        pass
                if isinstance(self.current_view, MapView):
                    if results:
                        self.current_view.status_message = results[0]
                    else:
                        self.current_view.status_message = "Nothing here."
                    self.current_view.status_timer = 120
            elif action == "talk_menu" and self.session:
                npc_id = result.get("npc_id")
                if npc_id:
                    self.state = "dialogue"
                    self.current_view = DialogueView(
                        self.width,
                        self.height,
                        self.session,
                        self.conversation_service,
                        npc_id,
                    )
            elif action == "open_journal" and self.session:
                self.state = "journal"
                self.current_view = JournalView(self.width, self.height, self.session)
            elif action == "open_accusation" and self.session:
                self.state = "accusation"
                self.current_view = AccusationView(self.width, self.height, self.session)
