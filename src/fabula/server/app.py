"""HTTP Server bridging Fabula headless simulation and AI conversation to the 3D Web UI."""

from __future__ import annotations

import json
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from fabula.conversation.config import ConversationConfig, ConversationMode
from fabula.conversation.service import ConversationService, create_conversation_service
from fabula.generation.orchestrator import generate_neurosymbolic_bundle
from fabula.schemas.enums import (
    Difficulty,
    SettingsMysteryType,
    Tone,
)
from fabula.schemas.stages import GenerationSettings
from fabula.simulation.accusation import AccusationService
from fabula.simulation.clock import Clock
from fabula.simulation.loader import LoadedBundle, load_bundle
from fabula.simulation.session import Session


class RealtimeClock(Clock):
    """Realtime wall clock for the 10-minute web investigation session."""

    def __init__(self, duration_minutes: int = 10) -> None:
        super().__init__(duration_minutes=duration_minutes)
        self._start_perf = time.perf_counter()

    @property
    def elapsed_seconds(self) -> float:
        if self._paused:
            return self._elapsed_seconds
        return time.perf_counter() - self._start_perf


class FabulaServerState:
    """Encapsulates the mutable game session and services."""

    def __init__(
        self,
        loaded: LoadedBundle,
        conversation_service: ConversationService | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.initial_loaded = loaded
        self.clock = clock or RealtimeClock()
        self.session = Session(loaded, clock=self.clock)
        self.conversation_service = conversation_service or create_conversation_service(
            ConversationConfig(mode=ConversationMode.AUTO)
        )
        self.accusation_service = AccusationService(
            loaded.accusation_truth(),
            loaded.world,
            max_attempts=3,
            clock=self.clock,
        )
        self._fast_runner: Any | None = None
        self.lock = threading.RLock()

    def get_fast_runner(self) -> Any | None:
        """Lazily initialize and cache local Llama-3.2-1B model runner for neural synthesis."""
        with self.lock:
            if self._fast_runner is None:
                from fabula.generation.config import config_from_env, resolve_fast_model_path
                from fabula.generation.local_runner import LocalModelRunner

                fast_path = resolve_fast_model_path()
                if fast_path.is_file():
                    try:
                        self._fast_runner = LocalModelRunner(fast_path, config_from_env())
                    except Exception:
                        self._fast_runner = None
            return self._fast_runner

    def reset_case(self, loaded: LoadedBundle) -> None:
        with self.lock:
            self.initial_loaded = loaded
            self.clock = RealtimeClock()
            self.session = Session(loaded, clock=self.clock)
            self.accusation_service = AccusationService(
                loaded.accusation_truth(),
                loaded.world,
                max_attempts=3,
                clock=self.clock,
            )
            # Retain existing conversation service or reset history
            self.conversation_service.reset_history()

    def reset(self) -> None:
        self.reset_case(self.initial_loaded)


def generate_constable_reply(state: FabulaServerState, message: str) -> str:
    """Generate in-character municipal watchman responses to guide the player."""
    world = state.session.loaded.world
    town_name = world.town_name
    title = world.title
    loc_names = {loc.id: loc.name for loc in world.locations}
    roster_locations = [
        f"{entry.display_name} in {loc_names.get(entry.start_location, entry.start_location)}"
        for entry in world.npcs
    ]
    roster_summary = ", ".join(roster_locations)

    msg_lower = message.lower()
    if any(w in msg_lower for w in ["who", "where", "suspect", "people", "everyone", "find"]):
        return (
            f"According to my patrol ledger for {town_name}, the key persons of interest "
            f"are currently in their quarters: {roster_summary}. North doorway leads to Library, "
            "East to Residence, West to Park, South to Market."
        )
    if any(w in msg_lower for w in ["clue", "evidence", "search", "trace", "item"]):
        return (
            "We've preserved the scene as best we could in this rain. Search each room for "
            "glowing traces [E]. Examine them closely to log official exhibits into your "
            "Detective Case Journal [J]."
        )
    if any(w in msg_lower for w in ["accuse", "tribunal", "arrest", "solve", "guilty"]):
        return (
            "When you have established who committed the crime, their method, and motive, "
            "convene the Tribunal with [T]. Be judicious, Inspector—you have limited attempts "
            "before the magistrate intervenes."
        )
    if any(w in msg_lower for w in ["happen", "crime", "murder", "theft", "case", "incident"]):
        return (
            f"Regarding {title}: {world.intro_text} "
            "Town is on edge tonight. I suggest interrogating everyone before the clock runs out."
        )
    return (
        f"At your service, Inspector. I'm standing watch here in {town_name} Square. "
        f"Interrogate the suspects across the four quarters ({roster_summary}) and examine "
        "all physical evidence."
    )


def build_game_state_payload(state: FabulaServerState) -> dict[str, Any]:
    """Serialize the public world and player state, strictly honoring the spoiler firewall."""
    session = state.session
    world = session.loaded.world
    npcs = session.loaded.npcs
    clues = session.loaded.clues.clues

    locations_data = []
    for loc in world.locations:
        locations_data.append(
            {
                "id": loc.id,
                "name": loc.name,
                "type": loc.type.value,
                "description": loc.description,
                "position": {"x": loc.position.x, "y": loc.position.y},
                "connections": list(loc.connections),
                "clue_spots": list(loc.clue_spots),
            }
        )

    npcs_data = []
    for roster_entry in world.npcs:
        npc_files = npcs.get(roster_entry.id)
        identity = npc_files.identity if npc_files else None
        npcs_data.append(
            {
                "id": roster_entry.id,
                "name": identity.name if identity else roster_entry.display_name,
                "role": identity.role if identity else "Citizen",
                "traits": list(identity.traits) if identity else [],
                "speech_style": identity.speech_style if identity else "",
                "start_location": roster_entry.start_location,
                "schedule": [
                    {"at_minute": s.at_minute, "location": s.location}
                    for s in roster_entry.schedule
                ],
                "relationships": dict(identity.relationships) if identity else {},
                "attitude_to_player": identity.attitude_to_player if identity else "neutral",
            }
        )

    clues_data = []
    for clue in clues:
        clues_data.append(
            {
                "id": clue.id,
                "location_id": clue.location_id,
                "description": clue.description,
                "discovery": clue.discovery.value,
                "revealed_by_npc": clue.revealed_by_npc,
                "requires": list(clue.requires),
            }
        )

    journal_data = [
        {
            "clue_id": entry.clue_id,
            "description": entry.description,
            "source": entry.source,
            "minute": entry.minute,
        }
        for entry in session.journal
    ]

    time_remaining = max(0.0, 600.0 - state.clock.elapsed_seconds)

    return {
        "scenario": {
            "id": world.scenario_id,
            "title": world.title,
            "intro_text": world.intro_text,
            "town_name": world.town_name,
            "mystery_type": world.mystery_type.value,
            "tone": world.tone.value,
            "difficulty": world.difficulty.value,
        },
        "locations": locations_data,
        "npcs": npcs_data,
        "clues": clues_data,
        "accusation_options": {
            "methods": [{"id": m.id, "text": m.text} for m in world.accusation_options.methods],
            "motives": [{"id": m.id, "text": m.text} for m in world.accusation_options.motives],
        },
        "player_location": session.player_location,
        "discovered_clue_ids": sorted(session.discovered_ids),
        "journal": journal_data,
        "minute": state.clock.minute,
        "time_remaining_seconds": round(time_remaining, 1),
        "conversation_mode": state.conversation_service.mode.value,
    }


def make_request_handler(
    state: FabulaServerState,
    web_dir: Path,
) -> type[SimpleHTTPRequestHandler]:
    """Factory creating an HTTP request handler bound to server state and web directory."""

    class FabulaHTTPHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(web_dir), **kwargs)

        def log_message(self, format: str, *args: Any) -> None:
            # Minimal clean logging
            pass

        def _send_json(self, status: int, data: Any) -> None:
            body = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

        def _read_json_body(self) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                return {}
            raw = self.rfile.read(content_length)
            return json.loads(raw.decode("utf-8"))

        def do_OPTIONS(self) -> None:
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self) -> None:
            parsed_path = self.path.split("?")[0]

            if parsed_path == "/api/game-state":
                with state.lock:
                    payload = build_game_state_payload(state)
                self._send_json(HTTPStatus.OK, payload)
                return

            if parsed_path == "/api/journal":
                with state.lock:
                    journal = [
                        {
                            "clue_id": entry.clue_id,
                            "description": entry.description,
                            "source": entry.source,
                            "minute": entry.minute,
                        }
                        for entry in state.session.journal
                    ]
                self._send_json(HTTPStatus.OK, {"journal": journal})
                return

            # Default to static file handler
            super().do_GET()

        def do_POST(self) -> None:
            parsed_path = self.path.split("?")[0]

            try:
                body = self._read_json_body()
            except Exception as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"Invalid JSON body: {exc}"})
                return

            if parsed_path == "/api/chat":
                self._handle_chat(body)
                return

            if parsed_path == "/api/examine":
                self._handle_examine(body)
                return

            if parsed_path == "/api/move":
                self._handle_move(body)
                return

            if parsed_path == "/api/accuse":
                self._handle_accuse(body)
                return

            if parsed_path == "/api/generate":
                self._handle_generate(body)
                return

            if parsed_path == "/api/reset":
                self._handle_reset()
                return

            if parsed_path == "/api/save-recording":
                self._handle_save_recording(body)
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Endpoint {parsed_path!r} not found"})

        def _handle_chat(self, body: dict[str, Any]) -> None:
            npc_id = body.get("npc_id")
            message = (body.get("message") or "").strip()

            if not npc_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing 'npc_id'"})
                return
            if not message:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Message cannot be empty"})
                return

            with state.lock:
                if npc_id == "higgins":
                    reply_text = generate_constable_reply(state, message)
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "reply": reply_text,
                            "mood": "neutral",
                            "revealed_clues": [],
                            "discovered_clue_ids": sorted(state.session.discovered_ids),
                        },
                    )
                    return

                npc_files = state.session.loaded.npcs.get(npc_id)
                if not npc_files:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Unknown NPC {npc_id!r}"})
                    return

                try:
                    reply = state.conversation_service.reply(
                        files=npc_files,
                        player_input=message,
                        discovered_clue_ids=state.session.discovered_ids,
                        clues=state.session.loaded.clues.clues,
                    )
                    state.session.record_player_statement(npc_id, message)
                    mode_str = f"LIVE ({reply.provider})" if not reply.scripted else "SCRIPTED"
                    print(f"[Chat] {npc_files.identity.name} replied via {mode_str}")
                except Exception as exc:
                    self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
                    return

                # Record any clues revealed by the NPC
                revealed = []
                for clue_id in reply.revealed_clue_ids:
                    try:
                        entry = state.session.npc_reveal(npc_id, clue_id)
                        if entry:
                            revealed.append(
                                {
                                    "clue_id": entry.clue_id,
                                    "description": entry.description,
                                    "source": entry.source,
                                }
                            )
                    except Exception:
                        pass

                self._send_json(
                    HTTPStatus.OK,
                    {
                        "reply": reply.text,
                        "mood": reply.mood.value,
                        "revealed_clues": revealed,
                        "discovered_clue_ids": sorted(state.session.discovered_ids),
                    },
                )

        def _handle_examine(self, body: dict[str, Any]) -> None:
            clue_id = body.get("clue_id")
            location_id = body.get("location_id") or state.session.player_location

            if not clue_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing 'clue_id'"})
                return

            with state.lock:
                try:
                    entry = state.session.examine(location_id, clue_id)
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "success": True,
                            "already_discovered": entry is None,
                            "entry": {
                                "clue_id": entry.clue_id,
                                "description": entry.description,
                                "source": entry.source,
                                "minute": entry.minute,
                            }
                            if entry
                            else None,
                            "discovered_clue_ids": sorted(state.session.discovered_ids),
                        },
                    )
                except ValueError as exc:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def _handle_move(self, body: dict[str, Any]) -> None:
            location_id = body.get("location_id")
            if not location_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing 'location_id'"})
                return

            with state.lock:
                try:
                    state.session.move_player(location_id)
                    self._send_json(
                        HTTPStatus.OK,
                        {"player_location": state.session.player_location},
                    )
                except ValueError as exc:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def _handle_accuse(self, body: dict[str, Any]) -> None:
            who_id = body.get("who_id")
            how_id = body.get("how_id")
            why_id = body.get("why_id")

            if not who_id or not how_id or not why_id:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Accusation requires 'who_id', 'how_id', and 'why_id'"},
                )
                return

            with state.lock:
                try:
                    result = state.accusation_service.submit(who_id, how_id, why_id)
                except Exception as exc:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return

                response: dict[str, Any] = {
                    "correct": result.correct,
                    "attempts_remaining": result.attempts_remaining,
                    "terminal": result.terminal,
                    "timed_out": result.timed_out,
                }

                # Only when terminal (win or exhausted), reveal the truth narrative
                if result.terminal:
                    truth = state.session.loaded.accusation_truth()
                    culprit_id = truth.solution.correct_culprit_id
                    culprit_name = culprit_id
                    if culprit_id in state.session.loaded.npcs:
                        culprit_name = state.session.loaded.npcs[culprit_id].identity.name
                    response["solution"] = {
                        "correct_culprit_id": culprit_id,
                        "correct_culprit_name": culprit_name,
                        "correct_method_id": truth.solution.correct_method_id,
                        "correct_motive_id": truth.solution.correct_motive_id,
                        "crime_type": truth.crime.type.value,
                        "crime_target": truth.crime.target,
                        "crime_location": truth.crime.location_id,
                    }

                self._send_json(HTTPStatus.OK, response)

        def _handle_generate(self, body: dict[str, Any]) -> None:
            """Generate a brand-new mystery case on the fly directly from the web client."""
            mystery_type = body.get("mystery_type", "murder")
            tone = body.get("tone", "dark")
            difficulty = body.get("difficulty", "normal")
            seed_val = body.get("seed")
            seed: int | None = None
            if seed_val is not None and str(seed_val).strip() != "":
                try:
                    seed = int(seed_val)
                except (ValueError, TypeError):
                    seed = None

            use_neural_raw = body.get("use_neural")
            if use_neural_raw is not None:
                use_neural = bool(use_neural_raw)
            else:
                engine = str(body.get("engine", "fast")).lower()
                use_neural = engine in ("neural", "1b_neural", "llama", "true", "1")

            try:
                runner = state.get_fast_runner() if use_neural else None
                tone_str = str(tone).lower().strip()
                if tone_str in ("melodramatic", "melodrama", "dramatic"):
                    tone_val = Tone.DARK
                elif tone_str in ("cozy", "gaslight"):
                    tone_val = Tone.COZY
                elif tone_str in ("dark", "noir"):
                    tone_val = Tone.DARK
                else:
                    tone_val = Tone.NEUTRAL

                settings = GenerationSettings(
                    mystery_type=SettingsMysteryType(mystery_type),
                    tone=tone_val,
                    difficulty=Difficulty(difficulty),
                )
                gen_dir = Path("bundles/web_generated")
                gen_dir.mkdir(parents=True, exist_ok=True)

                generate_neurosymbolic_bundle(
                    settings=settings,
                    model_runner=runner,
                    output_dir=gen_dir,
                    seed=seed,
                )
                new_loaded = load_bundle(gen_dir)
                state.reset_case(new_loaded)
                with state.lock:
                    payload = build_game_state_payload(state)
                payload["engine_used"] = "1b_neural" if runner is not None else "fast_symbolic"
                self._send_json(HTTPStatus.OK, payload)
            except Exception as exc:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Generation failed: {exc}"}
                )

        def _handle_save_recording(self, body: dict[str, Any]) -> None:
            import base64

            data_b64 = body.get("video_base64")
            fps_log = body.get("fps_log", [])
            test_results = body.get("test_results", {})
            out_path = Path("web/gameplay_recording.webm")
            if data_b64:
                if "," in data_b64:
                    data_b64 = data_b64.split(",", 1)[1]
                video_bytes = base64.b64decode(data_b64)
                out_path.write_bytes(video_bytes)

            metrics_path = Path("web/gameplay_metrics.json")
            metrics_path.write_text(
                json.dumps(
                    {
                        "fps_log": fps_log,
                        "test_results": test_results,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            self._send_json(HTTPStatus.OK, {"saved": True, "path": str(out_path)})

        def _handle_reset(self) -> None:
            with state.lock:
                state.reset()
                payload = build_game_state_payload(state)
            self._send_json(
                HTTPStatus.OK,
                {"status": "reset", "game_state": payload},
            )

    return FabulaHTTPHandler


class ReusableThreadingServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class FabulaServer:
    """Threaded web server serving Fabula 3D web client and REST simulation API."""

    def __init__(
        self,
        loaded: LoadedBundle,
        web_dir: Path,
        conversation_service: ConversationService | None = None,
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> None:
        self.host = host
        self.port = port
        self.web_dir = web_dir.resolve()
        self.state = FabulaServerState(loaded, conversation_service=conversation_service)

        handler_cls = make_request_handler(self.state, self.web_dir)
        httpd: ReusableThreadingServer | None = None
        last_err: OSError | None = None
        for candidate_port in range(self.port, self.port + 50):
            try:
                httpd = ReusableThreadingServer((self.host, candidate_port), handler_cls)
                self.port = candidate_port
                break
            except OSError as err:
                last_err = err

        if httpd is None:
            raise last_err or RuntimeError(
                f"Could not bind to any port in range {port}-{port + 50}"
            )
        self.httpd = httpd
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the server in a daemon thread."""
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Shutdown the server."""
        if getattr(self.state, "_fast_runner", None) is not None:
            try:
                self.state._fast_runner.close()
            except Exception:
                pass
        self.httpd.shutdown()
        self.httpd.server_close()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


def run_server(
    bundle_path: Path,
    web_dir: Path,
    host: str = "127.0.0.1",
    port: int = 8000,
    auto_open: bool = True,
    conversation_mode: str = "auto",
) -> None:
    """Blocking runner for the web server."""
    loaded = load_bundle(bundle_path)
    service = create_conversation_service(
        ConversationConfig(mode=ConversationMode(conversation_mode))
    )
    server = FabulaServer(
        loaded=loaded, web_dir=web_dir, conversation_service=service, host=host, port=port
    )

    status = service.status
    mode_desc = (
        f"LIVE ({status.provider})"
        if status.mode is ConversationMode.LIVE
        else f"SCRIPTED ({status.reason} - set GEMINI_API_KEY for live LLM)"
    )

    models_info = ""
    if (
        service.mode is ConversationMode.LIVE
        and service.provider is not None
        and hasattr(service.provider, "verify_connection")
    ):
        models = service.provider.verify_connection()
        if models:
            models_info = f"\n  Verified Models: {', '.join(models[:4])}"

    print("\n========================================================")
    print("  Fabula 3D Noir Web Server running at:")
    print(f"  {server.url}")
    print(f"  Case: {loaded.world.title} ({loaded.world.town_name})")
    print(f"  Dialogue Mode: {mode_desc}{models_info}")
    print("  Press Ctrl+C to stop.")
    print("========================================================\n")

    if auto_open:
        webbrowser.open(server.url)

    server.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
