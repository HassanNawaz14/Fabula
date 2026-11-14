from __future__ import annotations

from typing import Any

import pygame

from fabula.simulation import Session
from fabula.ui.accusation import AccusationView
from fabula.ui.dialogue import DialogueView
from fabula.ui.generation_screen import GenerationScreen
from fabula.ui.journal import JournalView
from fabula.ui.map_view import MapView
from fabula.ui.start_menu import StartMenuView
from fabula.ui.settings import SettingsView
from fabula.simulation.loader import load_bundle, LoadedBundle
from fabula.simulation import Session
from fabula.training_data import generate_skeleton
from types import MappingProxyType
from pathlib import Path


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
        self.settings = {"conversation_mode": "auto", "api_key": "Set in env"}

        if not pygame.get_init():
            pygame.init()

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Fabula — Mystery Investigation Game")
        self.clock = pygame.time.Clock()

        self.state = "start_menu"
        self.current_view = StartMenuView(self.width, self.height, self)

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
            if result == "start_dummy":
                bundle = generate_skeleton("theft", seed=1, tone="cozy", difficulty="easy")
                loaded = LoadedBundle(root=Path("."), world=bundle.world, clues=bundle.clues, npcs=MappingProxyType({npc.id: bundle.npcs[npc.id] for npc in bundle.world.npcs}), _truth=bundle.truth)
                self.set_session(Session(loaded))
            elif result == "go_generation":
                self.state = "generation"
                self.current_view = GenerationScreen(self.width, self.height)
            elif result == "go_settings":
                self.state = "settings"
                self.current_view = SettingsView(self.width, self.height, self)
            elif result == "back_to_menu":
                self.state = "start_menu"
                self.current_view = StartMenuView(self.width, self.height, self)
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
                exit()
        elif isinstance(result, dict):
            # Existing handling for map actions
            action = result.get("action")
            if action == "move" and self.session:
                self.session.move_player(result.get("location_id"))
            elif action == "talk_menu" and self.session:
                npc_id = result.get("npc_id")
                self.state = "dialogue"
                self.current_view = DialogueView(self.width, self.height, self.session, self.conversation_service, npc_id)
            elif action in ("examine_menu", "examine_location") and self.session:
                loc_id = self.session.player_location
                clues = [c for c in self.session.loaded.clues.clues if c.location_id == loc_id and c.id not in self.session.discovered_ids]
                for clue in clues:
                    self.session.examine(loc_id, clue.id)
                if isinstance(self.current_view, MapView):
                    self.current_view.status_message = "Examined."
                    self.current_view.status_timer = 60

