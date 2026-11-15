from __future__ import annotations

import os
from types import SimpleNamespace

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
import pytest

from fabula.conversation import ConversationConfig, create_conversation_service
from fabula.schemas import DiscoveryMethod, LocationType
from fabula.simulation import Session, location_graph
from fabula.training_data.skeletons.common import ROLES
from fabula.ui.accusation import AccusationView
from fabula.ui.app import FabulaApp
from fabula.ui.assets import (
    NPC_LOOKS,
    PLACE_ASSETS,
    get_place_asset,
    place_variant,
    render_npc,
    render_place,
    resolve_look,
)
from fabula.ui.dialogue import DialogueView
from fabula.ui.generation_screen import GenerationScreen
from fabula.ui.how_to_play import _SECTIONS as HOW_TO_PLAY_SECTIONS
from fabula.ui.how_to_play import HowToPlayView
from fabula.ui.journal import JournalView
from fabula.ui.map_view import MapView
from fabula.ui.start_menu import StartMenuView


@pytest.fixture(autouse=True)
def _pygame_ready():
    if not pygame.get_init():
        pygame.init()
    yield


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


def _distinct_colors(surface: pygame.Surface, step: int = 17) -> int:
    colours = set()
    for x in range(0, surface.get_width(), step):
        for y in range(0, surface.get_height(), step):
            colours.add(tuple(surface.get_at((x, y)))[:3])
    return len(colours)


def test_place_asset_library_covers_every_location_type() -> None:
    for location_type in LocationType:
        asset = get_place_asset(location_type.value)
        assert asset is PLACE_ASSETS[location_type]
        assert asset.variants >= 3
        for variant in range(asset.variants):
            art = render_place(location_type.value, (320, 230), variant, tick=6.0)
            assert art.get_size() == (320, 230)
            assert _distinct_colors(art) >= 6, location_type

    assert get_place_asset("not-a-place").label == "Building"


def test_place_variants_are_deterministic() -> None:
    for location_type in LocationType:
        asset = get_place_asset(location_type.value)
        first = place_variant(location_type.value, "loc:name")
        assert first == place_variant(location_type.value, "loc:name")
        assert 0 <= first < asset.variants


def test_npc_asset_library_covers_every_role() -> None:
    villager = NPC_LOOKS["villager"]
    for role in ROLES:
        look = resolve_look(role)
        assert look is not villager, role
        avatar = render_npc(role, f"seed:{role}", 120, tick=4.0)
        width, height = avatar.get_size()
        assert height == 120
        assert _distinct_colors(avatar) >= 4, role
        pixels = (avatar.get_at((x, y))[3] for x in range(0, width, 9) for y in range(0, height, 9))
        assert any(pixels), role

    assert resolve_look("wandering stranger") is villager


@pytest.mark.parametrize("size", [(1280, 720), (1600, 900), (1920, 1080)])
def test_map_layout_fits_surface(loaded, size: tuple[int, int]) -> None:
    session = Session(loaded)
    view = MapView(size[0], size[1], session)
    surface = pygame.Surface(size)
    for _ in range(2):
        view.update()
        view.draw(surface)

    bounds = surface.get_rect()
    scenes = list(view.place_rects.values())
    labels = list(view.label_rects.values())
    assert len(scenes) == len(loaded.world.locations)
    for rect in [*scenes, *labels]:
        assert bounds.contains(rect)
        assert rect.top >= view.hud_h
        assert rect.bottom <= size[1] - view.bar_h
    for npc_id, _loc_id, rect in view.npc_rects:
        assert bounds.contains(rect), npc_id

    assert view.player_rect is not None
    assert bounds.contains(view.player_rect)
    for npc_id, loc_id, rect in view.npc_rects:
        if loc_id == session.player_location:
            assert not rect.colliderect(view.player_rect), npc_id

    for index, first in enumerate(scenes):
        for second in scenes[index + 1 :]:
            assert not first.colliderect(second)
    for index, first in enumerate(labels):
        for second in labels[index + 1 :]:
            assert not first.colliderect(second)
    for scene in scenes:
        for label in labels:
            assert not scene.colliderect(label)
    for button in view.buttons:
        assert bounds.contains(button.rect)
        assert button.rect.top >= size[1] - view.bar_h


def test_detective_avatar_is_distinct_from_villagers() -> None:
    look = resolve_look("Detective")
    assert look is NPC_LOOKS["detective"]
    assert look is not NPC_LOOKS["villager"]
    avatar = render_npc(look.key, "player:detective", 120, tick=2.0)
    assert avatar.get_size() == (74, 120)
    assert _distinct_colors(avatar) >= 4


def test_map_detective_stands_at_the_player_location(loaded) -> None:
    session = Session(loaded)
    view = MapView(1280, 720, session)
    surface = pygame.Surface((1280, 720))
    view.update()
    view.draw(surface)

    assert view.player_rect is not None
    scene = view.place_rects[session.player_location]
    assert scene.contains(view.player_rect)
    assert view._player_display_rect() == view.player_rect


def test_map_detective_walks_to_the_next_place(loaded) -> None:
    session = Session(loaded)
    view = MapView(1280, 720, session)
    surface = pygame.Surface((1280, 720))
    view.update()
    view.draw(surface)
    start = view.player_rect.copy()

    adjacent = next(iter(location_graph(loaded.world)[session.player_location]))
    session.move_player(adjacent)
    view.update()
    assert view._walk_timer > 0
    mid = view._player_display_rect()
    assert mid is not None
    assert (mid.centerx, mid.centery) != (view.player_rect.centerx, view.player_rect.centery)
    view.draw(surface)

    for _ in range(25):
        view.update()
        view.draw(surface)
    assert view._walk_timer == 0
    assert view._player_display_rect() == view.player_rect
    assert view.place_rects[adjacent].contains(view.player_rect)
    assert view.player_rect != start


def test_examine_plays_a_short_animation(loaded) -> None:
    session = Session(loaded)
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    app = FabulaApp(session=session, conversation_service=service, width=1280, height=720)
    view = app.current_view
    surface = pygame.Surface((1280, 720))
    assert view.examine_timer == 0

    action = view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    app._handle_view_action(action)
    assert 30 <= view.examine_timer <= 60
    assert view.status_message is not None
    view.draw(surface)

    ticks = view.examine_timer
    for _ in range(ticks):
        view.update()
    assert view.examine_timer == 0
    view.draw(surface)


def test_map_click_travels_only_to_neighbours(loaded) -> None:
    session = Session(loaded)
    view = MapView(1600, 900, session)
    graph = location_graph(loaded.world)
    current = session.player_location
    adjacent = next(iter(graph[current]))
    far = next(
        loc.id
        for loc in loaded.world.locations
        if loc.id != current and loc.id not in graph[current]
    )

    def click(loc_id: str) -> str | dict | None:
        rect = view.place_rects[loc_id]
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(rect.left + 4, rect.top + 4)
        )
        return view.handle_event(event)

    assert click(current) == {"action": "examine_menu"}
    assert click(adjacent) == {"action": "move", "location_id": adjacent}
    assert click(far) is None
    assert view.status_message is not None
    assert "Too far" in view.status_message


def test_app_uses_explicit_window_when_sized(loaded) -> None:
    session = Session(loaded)
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    app = FabulaApp(session=session, conversation_service=service, width=800, height=600)
    assert not app.screen.get_flags() & pygame.FULLSCREEN
    assert (app.width, app.height) == (800, 600)


def test_app_is_fullscreen_by_default(loaded) -> None:
    session = Session(loaded)
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    try:
        app = FabulaApp(session=session, conversation_service=service)
        assert app.screen.get_flags() & pygame.FULLSCREEN
        assert app.screen.get_size() == (app.width, app.height)
    finally:
        pygame.display.set_mode((800, 600))


def test_app_can_start_at_the_menu_with_a_loaded_session(loaded) -> None:
    session = Session(loaded)
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    app = FabulaApp(
        session=session,
        conversation_service=service,
        width=800,
        height=600,
        start_menu=True,
    )

    assert app.state == "start_menu"
    assert isinstance(app.current_view, StartMenuView)
    menu = app.current_view
    surface = pygame.Surface((app.width, app.height))
    menu.update()
    menu.draw(surface)
    for button in menu.buttons:
        assert surface.get_rect().contains(button.rect)
    caption_bottom = menu.caption_pos[1] + sum(line.get_height() for line in menu.caption)
    assert caption_bottom <= menu.footer_pos[1]

    assert menu.play_button.text == "Play Mystery"
    app._handle_view_action(menu.play_button.callback())
    assert app.state == "map"
    assert app.session is session


def test_start_menu_without_session_offers_the_demo(loaded) -> None:
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    app = FabulaApp(conversation_service=service, width=800, height=600)
    assert app.state == "start_menu"
    assert app.current_view.play_button.text == "Play Demo Mystery"


def test_how_to_play_navigation_and_scrolling(loaded) -> None:
    session = Session(loaded)
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    app = FabulaApp(
        session=session,
        conversation_service=service,
        width=800,
        height=600,
        start_menu=True,
    )
    app._handle_view_action("go_how_to_play")
    assert app.state == "how_to_play"
    view = app.current_view
    assert isinstance(view, HowToPlayView)

    surface = pygame.Surface((app.width, app.height))
    view.update()
    view.draw(surface)
    assert view.max_scroll > 0
    view.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-2))
    assert view.scroll > 0
    assert view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END)) is None
    assert view.scroll == view.max_scroll
    assert (
        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)) == "back_to_menu"
    )

    app._handle_view_action("back_to_menu")
    assert app.state == "start_menu"


def test_how_to_play_explains_the_ai_plainly() -> None:
    text = " ".join(body for _kind, body in HOW_TO_PLAY_SECTIONS)
    assert "AI" in text
    assert "Characters with minds of their own" in text
    assert "Cases written before you arrive" in text
    assert "solution is locked away" in text
    assert "Generate New Game" in text


def test_generation_screen_can_return_to_the_menu() -> None:
    screen = GenerationScreen(800, 600)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    assert screen.handle_event(event) == "back_to_menu"


def test_map_quit_button_and_escape(loaded) -> None:
    session = Session(loaded)
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    app = FabulaApp(session=session, conversation_service=service, width=800, height=600)
    view = app.current_view
    quit_button = next(button for button in view.buttons if "Quit" in button.text)
    app._handle_view_action(quit_button.callback())
    assert app.running is False
    assert view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)) == {
        "action": "quit_game"
    }


@pytest.mark.parametrize("size", [(1280, 720), (1920, 1080)])
def test_menu_and_guide_fit_full_screen(loaded, size: tuple[int, int]) -> None:
    session = Session(loaded)
    app = SimpleNamespace(
        session=session,
        settings={"conversation_mode": "scripted"},
        set_voice_mode=lambda mode: None,
    )
    surface = pygame.Surface(size)

    menu = StartMenuView(size[0], size[1], app)
    menu.update()
    menu.draw(surface)
    assert menu.case_card is not None
    for button in menu.buttons:
        assert surface.get_rect().contains(button.rect)
    caption_bottom = menu.caption_pos[1] + sum(line.get_height() for line in menu.caption)
    assert caption_bottom <= menu.footer_pos[1]

    guide = HowToPlayView(size[0], size[1], app)
    guide.update()
    guide.draw(surface)
    assert surface.get_rect().contains(guide.card)
    assert guide.max_scroll > 0


def test_map_journal_and_accusation_open_from_key_and_click(loaded) -> None:
    session = Session(loaded)
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    app = FabulaApp(session=session, conversation_service=service, width=800, height=600)

    for key, expected, view_type in (
        (pygame.K_j, "journal", JournalView),
        (pygame.K_a, "accusation", AccusationView),
    ):
        action = app.current_view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        app._handle_view_action(action)
        assert app.state == expected
        assert isinstance(app.current_view, view_type)
        app._handle_view_action("back_to_map")
        assert isinstance(app.current_view, MapView)

    for label, expected, view_type in (
        ("Journal", "journal", JournalView),
        ("Accuse", "accusation", AccusationView),
    ):
        map_view = app.current_view
        button = next(button for button in map_view.buttons if label in button.text)
        map_view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=button.rect.center))
        action = map_view.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=button.rect.center)
        )
        app._handle_view_action(action)
        assert app.state == expected
        assert isinstance(app.current_view, view_type)
        app._handle_view_action("back_to_map")


def test_examining_every_location_only_discovers_searchable_clues(loaded) -> None:
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    for location in loaded.world.locations:
        session = Session(loaded)
        session.player_location = location.id
        app = FabulaApp(session=session, conversation_service=service, width=800, height=600)

        action = app.current_view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        assert action == {"action": "examine_location"}
        app._handle_view_action(action)
        app._handle_view_action({"action": "examine_menu"})

        searchable = {
            clue.id
            for clue in loaded.clues.clues
            if clue.location_id == location.id
            and clue.discovery is DiscoveryMethod.EXAMINE
            and not clue.requires
        }
        revealed = {
            clue.id
            for clue in loaded.clues.clues
            if clue.location_id == location.id and clue.discovery is DiscoveryMethod.NPC_REVEAL
        }
        assert session.discovered_ids == searchable, location.name
        assert not (session.discovered_ids & revealed), location.name
        assert app.current_view.status_message is not None

    # Regression: these two places only hold NPC-reveal clues and used to crash.
    for location_id in ("loc_residence", "loc_park"):
        location = next(loc for loc in loaded.world.locations if loc.id == location_id)
        assert any(
            clue.location_id == location_id and clue.discovery is DiscoveryMethod.NPC_REVEAL
            for clue in loaded.clues.clues
        )
        session = Session(loaded)
        session.player_location = location.id
        app = FabulaApp(session=session, conversation_service=service, width=800, height=600)
        app._handle_view_action({"action": "examine_location"})
        expected = {
            clue.id
            for clue in loaded.clues.clues
            if clue.location_id == location.id
            and clue.discovery is DiscoveryMethod.EXAMINE
            and not clue.requires
        }
        assert session.discovered_ids == expected


def test_examine_skips_clues_with_unmet_requirements(loaded) -> None:
    session = Session(loaded)
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    clue = next(clue for clue in loaded.clues.clues if clue.discovery is DiscoveryMethod.EXAMINE)
    session.player_location = clue.location_id
    clue.requires = ["clue_missing"]
    app = FabulaApp(session=session, conversation_service=service, width=800, height=600)
    app._handle_view_action({"action": "examine_location"})
    assert clue.id not in session.discovered_ids
    assert "lead" in app.current_view.status_message


@pytest.mark.parametrize("size", [(800, 600), (1280, 720), (1920, 1080)])
def test_case_screens_render_and_fit(loaded, size: tuple[int, int]) -> None:
    session = Session(loaded)
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    surface = pygame.Surface(size)
    bounds = surface.get_rect()

    journal = JournalView(size[0], size[1], session)
    journal.update()
    journal.draw(surface)
    assert bounds.contains(journal.card)
    assert bounds.contains(journal.back_button.rect)
    assert journal.max_scroll >= 0

    accusation = AccusationView(size[0], size[1], session)
    accusation.update()
    accusation.draw(surface)
    for column, rect in enumerate(accusation.column_rects):
        assert bounds.contains(rect)
        for (row_column, _index), row in accusation.row_rects.items():
            if row_column == column:
                assert rect.contains(row)
    assert bounds.contains(accusation.submit_button.rect)

    dialogue = DialogueView(size[0], size[1], session, service, loaded.world.npcs[0].id)
    dialogue.input_text = "Where were you at eight o'clock?"
    dialogue._send()
    assert dialogue.history[-1]["speaker"] in ("npc", "system")
    dialogue.update()
    dialogue.draw(surface)
    assert bounds.contains(dialogue.chat_rect)
    assert bounds.contains(dialogue.sidebar_rect)
    assert dialogue.max_scroll >= 0


def test_accusation_selection_keys_clicks_and_outcome(loaded) -> None:
    session = Session(loaded)
    view = AccusationView(800, 600, session)
    assert (
        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)) == "back_to_map"
    )

    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    assert view.selections[0] == 1
    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
    assert view.active == 1
    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    assert view.active == 2
    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2))
    assert view.active == 1
    assert view.selections[1] == 1

    method_rect = view.row_rects[(1, 2)]
    view.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=method_rect.center))
    assert view.active == 1
    assert view.selections[1] == 2
    suspect_rect = view.row_rects[(0, 3)]
    view.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=suspect_rect.center))
    assert view.active == 0
    assert view.selections[0] == 3

    view._submit_accusation()
    assert view.attempts_remaining == 2
    assert view.message_is_error

    solution = loaded.accusation_truth().solution
    view.selections = [
        [npc.id for npc in view.npcs].index(solution.correct_culprit_id),
        [method.id for method in view.methods].index(solution.correct_method_id),
        [motive.id for motive in view.motives].index(solution.correct_motive_id),
    ]
    view._submit_accusation()
    assert view.game_over == "won"
    surface = pygame.Surface((800, 600))
    view.update()
    view.draw(surface)
    assert (
        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)) == "back_to_map"
    )
    assert view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)) == "quit_game"


def test_dialogue_accepts_typed_input_and_replies(loaded) -> None:
    session = Session(loaded)
    service = create_conversation_service(ConversationConfig(mode="scripted"))
    view = DialogueView(800, 600, session, service, loaded.world.npcs[0].id)
    for character in "Hello":
        view.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h, unicode=character, mod=0)
        )
    assert view.input_text == "Hello"
    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode="", mod=0))
    assert view.input_text == "Hell"
    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r", mod=0))
    assert view.input_text == ""
    assert view.history[-1]["speaker"] in ("npc", "system")
    assert view.history[0]["speaker"] == "player"
