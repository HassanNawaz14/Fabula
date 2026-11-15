from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Any

import pygame

from fabula.conversation import ConversationConfig, create_conversation_service
from fabula.generation.jobs import KaggleCaseJob, LocalCaseJob
from fabula.schemas import DiscoveryMethod, GenerationSettings
from fabula.simulation import Session
from fabula.simulation.loader import BundleLoadError, LoadedBundle, load_bundle
from fabula.training_data import generate_skeleton
from fabula.ui.accusation import AccusationView
from fabula.ui.case_picker import CasePickerView
from fabula.ui.dialogue import DialogueView
from fabula.ui.generation_screen import GenerationScreen
from fabula.ui.how_to_play import HowToPlayView
from fabula.ui.journal import JournalView
from fabula.ui.map_view import MapView
from fabula.ui.new_game import NewGameView
from fabula.ui.settings import SettingsView
from fabula.ui.start_menu import StartMenuView


class FabulaApp:
    """Main Pygame application runner for Fabula."""

    def __init__(
        self,
        session: Session | None = None,
        conversation_service: Any = None,
        width: int | None = None,
        height: int | None = None,
        fullscreen: bool | None = None,
        start_menu: bool = False,
    ) -> None:
        self.session = session
        self.conversation_service = conversation_service
        self.settings = {"conversation_mode": "auto", "api_key": "Set in env"}
        config = getattr(conversation_service, "config", None)
        mode = getattr(config, "mode", None)
        if mode is not None:
            self.settings["conversation_mode"] = getattr(mode, "value", str(mode))
        self.running = True

        if not pygame.get_init():
            pygame.init()

        self.screen = self._open_display(width, height, fullscreen)
        self.width, self.height = self.screen.get_size()
        pygame.display.set_caption("Fabula — Mystery Investigation Game")
        self.clock = pygame.time.Clock()

        if session is None or start_menu:
            self.state = "start_menu"
            self.current_view = StartMenuView(self.width, self.height, self)
        else:
            self.state = "map"
            self.current_view = MapView(self.width, self.height, session)

    def _open_display(
        self, width: int | None, height: int | None, fullscreen: bool | None
    ) -> pygame.Surface:
        info = pygame.display.Info()
        desktop_w = info.current_w if info.current_w > 0 else 1600
        desktop_h = info.current_h if info.current_h > 0 else 900

        if width is None or height is None:
            use_fullscreen = True if fullscreen is None else fullscreen
            if use_fullscreen:
                try:
                    return pygame.display.set_mode((desktop_w, desktop_h), pygame.FULLSCREEN)
                except pygame.error:
                    pass
            return pygame.display.set_mode((desktop_w, desktop_h))

        flags = pygame.FULLSCREEN if fullscreen else 0
        return pygame.display.set_mode((width, height), flags)

    def set_session(self, session: Session) -> None:
        self.session = session
        self._ensure_service()
        self.state = "map"
        self.current_view = MapView(self.width, self.height, self.session)

    def set_voice_mode(self, mode: str) -> None:
        self.settings["conversation_mode"] = mode
        self.conversation_service = create_conversation_service(ConversationConfig(mode=mode))

    def _ensure_service(self) -> None:
        if self.conversation_service is None:
            self.conversation_service = create_conversation_service(
                ConversationConfig(mode=self.settings["conversation_mode"])
            )

    def run(self, max_ticks: int | None = None) -> None:
        running = True
        ticks = 0
        while running and self.running:
            if max_ticks and ticks >= max_ticks:
                break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                result = self.current_view.handle_event(event)
                if result:
                    self._handle_view_action(result)

            if not self.running:
                break
            self.current_view.update()
            take_action = getattr(self.current_view, "take_action", None)
            if take_action is not None:
                action = take_action()
                if action:
                    self._handle_view_action(action)
            self.current_view.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(30)
            ticks += 1

        pygame.quit()

    def _start_session(self) -> None:
        if self.session is not None:
            self.set_session(self.session)
            return
        bundle = generate_skeleton("theft", seed=1, tone="cozy", difficulty="easy")
        loaded = LoadedBundle(
            root=Path("."),
            world=bundle.world,
            clues=bundle.clues,
            npcs=MappingProxyType({npc.id: bundle.npcs[npc.id] for npc in bundle.world.npcs}),
            _truth=bundle.truth,
        )
        self.set_session(Session(loaded))

    def _generation_settings(self) -> GenerationSettings:
        return GenerationSettings(mystery_type="random", tone="cozy", difficulty="normal")

    def _begin_job(self, job: Any, title: str) -> None:
        self.state = "generation"
        self.current_view = GenerationScreen(
            self.width, self.height, job, title=title, estimate=job.estimate
        )
        job.start()

    def _play_case(self, path: str) -> None:
        try:
            loaded = load_bundle(path)
        except BundleLoadError as exc:
            self.state = "case_library"
            self.current_view = CasePickerView(self.width, self.height, self, error=str(exc))
            return
        self.set_session(Session(loaded))

    def _handle_view_action(self, result: Any) -> None:
        if isinstance(result, str):
            if result in ("start_dummy", "start_game"):
                self._start_session()
            elif result == "go_new_game":
                self.state = "new_game"
                self.current_view = NewGameView(self.width, self.height, self)
            elif result == "open_case_library":
                self.state = "case_library"
                self.current_view = CasePickerView(self.width, self.height, self)
            elif result == "start_kaggle_generation":
                self._begin_job(KaggleCaseJob(self._generation_settings()), "GENERATING ON KAGGLE")
            elif result == "start_local_generation":
                self._begin_job(LocalCaseJob(self._generation_settings()), "GENERATING LOCALLY")
            elif result == "go_how_to_play":
                self.state = "how_to_play"
                self.current_view = HowToPlayView(self.width, self.height, self)
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
                self.running = False
        elif isinstance(result, dict):
            action = result.get("action")
            if action in ("play_case", "session_ready"):
                path = result.get("path")
                if path:
                    self._play_case(str(path))
            elif action == "move" and self.session:
                self.session.move_player(result.get("location_id"))
            elif action == "talk_menu" and self.session:
                npc_id = result.get("npc_id")
                self._ensure_service()
                self.state = "dialogue"
                self.current_view = DialogueView(
                    self.width, self.height, self.session, self.conversation_service, npc_id
                )
            elif action == "quit_game":
                self.running = False
            elif action == "open_journal" and self.session:
                self.state = "journal"
                self.current_view = JournalView(self.width, self.height, self.session)
            elif action == "open_accusation" and self.session:
                self.state = "accusation"
                self.current_view = AccusationView(self.width, self.height, self.session)
            elif action in ("examine_menu", "examine_location") and self.session:
                self._examine_here()

    def _examine_here(self) -> None:
        if self.session is None:
            return
        loc_id = self.session.player_location
        found = 0
        blocked = False
        for clue in self.session.loaded.clues.clues:
            if clue.location_id != loc_id or clue.id in self.session.discovered_ids:
                continue
            if clue.discovery is not DiscoveryMethod.EXAMINE:
                continue
            if set(clue.requires) - self.session.discovered_ids:
                blocked = True
                continue
            if self.session.examine(loc_id, clue.id) is not None:
                found += 1

        if not isinstance(self.current_view, MapView):
            return
        self.current_view.start_examine_animation()
        if found:
            plural = "s" if found > 1 else ""
            self.current_view.status_message = f"Found {found} new clue{plural}."
        elif blocked:
            self.current_view.status_message = "That search needs another lead first."
        else:
            self.current_view.status_message = "Nothing new to find here."
        self.current_view.status_timer = 75
