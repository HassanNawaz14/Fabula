"""Tests for Fabula web server and REST simulation API."""

from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path

import pytest

from fabula.conversation import ConversationConfig, ConversationMode, create_conversation_service
from fabula.server.app import (
    FabulaServer,
    FabulaServerState,
    build_game_state_payload,
)
from fabula.simulation.loader import load_bundle


@pytest.fixture
def loaded_test_bundle():
    bundle_path = Path("bundles/my_case")
    if not bundle_path.exists():
        pytest.skip("bundles/my_case not found")
    return load_bundle(bundle_path)


def test_build_game_state_payload_spoiler_firewall(loaded_test_bundle):
    state = FabulaServerState(loaded_test_bundle)
    payload = build_game_state_payload(state)

    assert "scenario" in payload
    assert payload["scenario"]["title"] == "The Mystery of Puddlewick"
    assert "locations" in payload
    assert len(payload["locations"]) > 0
    assert "npcs" in payload
    assert len(payload["npcs"]) > 0
    assert "clues" in payload
    assert "accusation_options" in payload
    assert "journal" in payload

    # STRICT PROHIBITION: Truth ground truth and solutions must NEVER be in game state
    payload_str = json.dumps(payload)
    assert "correct_culprit_id" not in payload_str
    assert "solution" not in payload_str
    assert "narrative_summary" not in payload_str


def test_server_http_endpoints(loaded_test_bundle, tmp_path):
    # Create dummy web directory
    web_dir = tmp_path / "web"
    web_dir.mkdir()
    (web_dir / "index.html").write_text("<html>Fabula 3D</html>", encoding="utf-8")

    service = create_conversation_service(ConversationConfig(mode=ConversationMode.SCRIPTED))
    server = FabulaServer(
        loaded=loaded_test_bundle,
        web_dir=web_dir,
        conversation_service=service,
        host="127.0.0.1",
        port=8089,
    )
    server.start()

    try:
        import urllib.request

        # 1. Test Static file serving
        with urllib.request.urlopen("http://127.0.0.1:8089/index.html") as resp:
            assert resp.status == HTTPStatus.OK
            body = resp.read().decode("utf-8")
            assert "Fabula 3D" in body

        # 2. Test GET /api/game-state
        with urllib.request.urlopen("http://127.0.0.1:8089/api/game-state") as resp:
            assert resp.status == HTTPStatus.OK
            data = json.loads(resp.read().decode("utf-8"))
            assert data["scenario"]["title"] == "The Mystery of Puddlewick"
            assert len(data["locations"]) == 4

        # 3. Test POST /api/chat
        npc_id = data["npcs"][0]["id"]
        req_body = json.dumps({"npc_id": npc_id, "message": "Where were you?"}).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8089/api/chat",
            data=req_body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == HTTPStatus.OK
            chat_data = json.loads(resp.read().decode("utf-8"))
            assert "reply" in chat_data
            assert len(chat_data["reply"]) > 0

        # 3b. Test POST /api/chat with Constable Higgins (town watchman)
        higgins_body = json.dumps(
            {"npc_id": "higgins", "message": "Where are the suspects?"}
        ).encode("utf-8")
        higgins_req = urllib.request.Request(
            "http://127.0.0.1:8089/api/chat",
            data=higgins_body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(higgins_req) as resp:
            assert resp.status == HTTPStatus.OK
            higgins_data = json.loads(resp.read().decode("utf-8"))
            assert "reply" in higgins_data
            assert "Puddlewick" in higgins_data["reply"]

        # 4. Test POST /api/move
        server.state.session.player_location = data["locations"][0]["id"]
        conn = data["locations"][0]["connections"][0]
        req_body = json.dumps({"location_id": conn}).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8089/api/move",
            data=req_body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == HTTPStatus.OK
            move_data = json.loads(resp.read().decode("utf-8"))
            assert move_data["player_location"] == conn

        # 5. Test POST /api/examine
        clue = data["clues"][0]
        req_body = json.dumps(
            {
                "clue_id": clue["id"],
                "location_id": clue["location_id"],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8089/api/examine",
            data=req_body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == HTTPStatus.OK
            examine_data = json.loads(resp.read().decode("utf-8"))
            assert examine_data["success"] is True

        # 6. Test POST /api/accuse (incorrect attempt)
        req_body = json.dumps(
            {
                "who_id": data["npcs"][0]["id"],
                "how_id": data["accusation_options"]["methods"][0]["id"],
                "why_id": data["accusation_options"]["motives"][0]["id"],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8089/api/accuse",
            data=req_body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == HTTPStatus.OK
            accuse_data = json.loads(resp.read().decode("utf-8"))
            assert "correct" in accuse_data
            assert "attempts_remaining" in accuse_data
            assert accuse_data["attempts_remaining"] == 2

        # 7. Test POST /api/reset
        req = urllib.request.Request(
            "http://127.0.0.1:8089/api/reset",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == HTTPStatus.OK
            reset_data = json.loads(resp.read().decode("utf-8"))
            assert reset_data["status"] == "reset"
            assert reset_data["game_state"]["scenario"]["title"] == "The Mystery of Puddlewick"

        # 8. Test POST /api/generate (on-the-fly procedural case generation)
        gen_body = json.dumps(
            {
                "mystery_type": "theft",
                "tone": "cozy",
                "difficulty": "easy",
                "seed": 42,
                "use_neural": False,
            }
        ).encode("utf-8")
        gen_req = urllib.request.Request(
            "http://127.0.0.1:8089/api/generate",
            data=gen_body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(gen_req) as resp:
            assert resp.status == HTTPStatus.OK
            gen_data = json.loads(resp.read().decode("utf-8"))
            assert "scenario" in gen_data
            assert gen_data["scenario"]["mystery_type"] == "theft"
            assert gen_data["scenario"]["tone"] == "cozy"
            assert len(gen_data["locations"]) > 0
            assert len(gen_data["npcs"]) > 0
            assert "engine_used" in gen_data

    finally:
        server.stop()


def test_realistic_demo_html_integration():
    """Verify realistic_demo.html integrates all phases of the 3D integration plan."""
    demo_path = Path("web/realistic_demo.html")
    assert demo_path.exists(), "web/realistic_demo.html must exist"
    content = demo_path.read_text(encoding="utf-8")

    # Phase 1: State sync, top HUD, countdown clock, dossier
    assert "fetchGameState" in content
    assert 'id="timerDisplay"' in content
    assert 'id="cluesDisplay"' in content
    assert 'id="dossierModal"' in content
    assert "renderDossier" in content

    # Phase 2: Dynamic doorways and scene transitions
    assert "syncMoveToBackend" in content
    assert "mapLocationIdToScene" in content
    assert "function switchScene" in content

    # Phase 3: NPC Spawning and AI Interrogation dialogue (The Voice)
    assert "buildProceduralNPC" in content
    assert "openDialogueFor" in content
    assert "sendCustomDialogue" in content
    assert "/api/chat" in content
    assert 'id="dialogueOverlay"' in content
    assert "Constable Higgins" in content
    assert "clickRaycaster" in content
    assert "dossierSuspectsList" in content

    # Phase 4: Physical Clues inspection and Case Journal
    assert "buildPhysicalClue" in content
    assert "collectActiveEvidence" in content
    assert "/api/examine" in content
    assert 'id="journalModal"' in content
    assert "filterJournal" in content

    # Phase 5: Accusation Tribunal and climax
    assert 'id="tribunalModal"' in content
    assert "submitAccusation" in content
    assert "/api/accuse" in content
    assert "victory()" in content
    assert "wrong()" in content

    # Phase 6: Case generation and procedural synthesis (H-03)
    assert 'id="generateModal"' in content
    assert "/api/generate" in content
    assert "toggleGenerateModal" in content
    assert "submitCaseGeneration" in content
    assert "genProgressBox" in content

    # Physics, Obstacle Colliders & Calibrated Locomotion
    assert "PLAYER_RADIUS" in content
    assert "SCENE_COLLIDERS" in content
    assert "isColliding" in content

    # Phase 7: Settings Modal, Speed Multiplier & Camera-Relative Locomotion
    assert 'id="settingsModal"' in content
    assert 'id="settingsBtn"' in content
    assert "toggleSettingsModal" in content
    assert "updateSpeedMultiplier" in content
    assert "detectiveSpeedMultiplier" in content
    assert "camForward" in content
    assert 'id="speedSlider"' in content


def test_server_startup_dialogue_mode(loaded_test_bundle):
    service = create_conversation_service(ConversationConfig(mode=ConversationMode.SCRIPTED))
    status = service.status
    mode_desc = (
        f"LIVE ({status.provider})"
        if status.mode is ConversationMode.LIVE
        else f"SCRIPTED ({status.reason} - set GEMINI_API_KEY for live LLM)"
    )
    assert "SCRIPTED" in mode_desc
