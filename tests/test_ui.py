from __future__ import annotations

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame

from fabula.conversation import ConversationConfig, create_conversation_service
from fabula.simulation import Session
from fabula.ui.accusation import AccusationView
from fabula.ui.app import FabulaApp
from fabula.ui.dialogue import DialogueView
from fabula.ui.generation_screen import GenerationScreen
from fabula.ui.journal import JournalView
from fabula.ui.map_view import MapView


def test_generation_screen() -> None:
    screen = GenerationScreen(800, 600)
    screen.is_ready = True
    surface = pygame.Surface((800, 600))
    screen.draw(surface)

    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    res = screen.handle_event(event)
    assert res == "start_game"


def test_map_view_and_app_headless(loaded) -> None:
    session = Session(loaded)
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    app = FabulaApp(session=session, conversation_service=service, width=800, height=600)

    assert app.state == "map"
    assert isinstance(app.current_view, MapView)

    # Test map view key events
    event_journal = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j)
    res = app.current_view.handle_event(event_journal)
    assert res == {"action": "open_journal"}

    # Test journal view
    journal_view = JournalView(800, 600, session)
    surface = pygame.Surface((800, 600))
    journal_view.draw(surface)
    ev_back = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    assert journal_view.handle_event(ev_back) == "back_to_map"

    # Test accusation view
    acc_view = AccusationView(800, 600, session)
    acc_view.draw(surface)
    assert acc_view.handle_event(ev_back) == "back_to_map"

    # Test dialogue view
    first_npc = loaded.world.npcs[0].id
    dialogue_view = DialogueView(800, 600, session, service, first_npc)
    dialogue_view.draw(surface)
    assert dialogue_view.handle_event(ev_back) == "back_to_map"

    # Run app for 2 ticks headlessly
    app.run(max_ticks=2)
