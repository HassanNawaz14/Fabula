# Fabula Remediation Plan

Source: code audit of `main` @ `62a387c` (2026-11-16), cross-checked against
`docs/features.md`, `docs/FABULA_DEVPLAN_SOURCE.md`, and `docs/md/DOCUMENTATION.md`.
This file is the working register for the remaining work **outside WP-I (model
evaluation)**. Each item names the verified code location, the defect, and the
acceptance criterion. Checked items are fixed on the branch named in the item.

**Branch:** `wp-fh-game-runtime` (P0–P3 below)
**Tracking:** this file is now tracked (the old `.gitignore` rule was removed).
**Explicitly out of scope:** WP-I evaluation harness; P4 packaging/CI/release.

---

## P0 — the 10-minute game session does not actually run

- [x] **P0.1 Clock never advances.**
  `FabulaApp.run()` ([`src/fabula/ui/app.py:98`](src/fabula/ui/app.py)) only pumps pygame
  events and draws; nothing calls `Clock.advance()`. `Session` defaults to `FakeClock`
  ([`src/fabula/simulation/session.py:17`](src/fabula/simulation/session.py)), so
  `npcs_at()` always returns the same NPCs, `Clock.finished` is never true, and the
  session never ends.
  **Fix:** `Session` owns a real `Clock`; the app advances it from measured frame time
  while the player is on the map or in dialogue (paused in menus, journal, accusation,
  generation). On expiry, resolve the accusation as timed out.
  **Accept:** running the map for N frames advances `session.clock.elapsed_seconds`;
  NPC locations change across schedule boundaries; menus do not advance time.

- [x] **P0.2 HUD timer is wrong.**
  The HUD renders game minutes as `MM:SS`
  ([`src/fabula/ui/map_view.py:713`](src/fabula/ui/map_view.py)), which shows `00:00`
  forever and would show `00:10` after ten minutes.
  **Fix:** render a real countdown (`MM:SS` of remaining seconds) with a `TIME LEFT`
  caption; turn amber inside the last minute.
  **Accept:** at start the HUD reads `10:00`; after 90 simulated seconds it reads
  `08:30`; at expiry `00:00`.

- [x] **P0.3 Accusation attempts reset on every visit.**
  `AccusationView.__init__` constructs a fresh `AccusationService`
  ([`src/fabula/ui/accusation.py:36`](src/fabula/ui/accusation.py)), so backing out to
  the map restores all three attempts; the service also owns the terminal/timeout state
  that the map needs.
  **Fix:** create one `AccusationService` on `Session`, give it the session clock, and
  have the view read/write that instance. Expose `remaining`, `max_attempts`,
  `terminal`, `solved`, `timed_out`.
  **Accept:** a wrong accusation then Back to Map then Accuse shows 2 attempts left;
  a resolved case re-opens in game-over state.

- [x] **P0.4 Game over quits the application.**
  Enter on the game-over overlay returns `quit_game`
  ([`src/fabula/ui/accusation.py:259`](src/fabula/ui/accusation.py)), which calls
  `pygame.quit()` — the player cannot start another case.
  **Fix:** Enter returns to the start menu; hint text updated.
  **Accept:** Enter on game over lands on the start menu with the app still running.

---

## P1 — conversation and clue progression

- [x] **P1.5 Discovered clues are not passed into dialogue.**
  `DialogueView._send` calls `reply(files, text, clues=clues)` without
  `discovered_clue_ids` ([`src/fabula/ui/dialogue.py:179`](src/fabula/ui/dialogue.py)),
  although the service supports it
  ([`src/fabula/conversation/service.py:252`](src/fabula/conversation/service.py)).
  Gated scripted reveals and `reveal_requires` prompt gating therefore never open.
  **Fix:** pass `discovered_clue_ids=session.discovered_ids` (snapshot per turn).
  **Accept:** a clue whose `requires` is already discovered can be revealed; a locked
  one cannot.

- [x] **P1.6 Live mode never reveals a clue.**
  The live return path sets no `revealed_clue_ids`
  ([`src/fabula/conversation/service.py:333`](src/fabula/conversation/service.py)); only
  scripted replies do ([`.../service.py:353`](src/fabula/conversation/service.py)).
  `NPC_REVEAL` clues are unobtainable in live mode, so a case can be unsolvable.
  **Fix:** append the eligible NPC-reveal evidence list (id + description, this NPC
  only) to the system prompt; ask the model to add `"clue": "<id>"` when it shares an
  item; parse and validate that id against the eligible set and return it in
  `revealed_clue_ids`. Shared helper used by both paths.
  **Accept:** a mock provider returning a valid eligible id yields that reveal; an
  unknown/foreign id yields `()`; the prompt still never contains truth or another
  NPC's facts.

- [x] **P1.7 Live provider calls block the pygame loop.**
  `_send` calls the provider synchronously inside event handling with a 20 s HTTP
  timeout ([`src/fabula/ui/dialogue.py:164`](src/fabula/ui/dialogue.py)).
  **Fix:** run the reply on a daemon worker thread; apply history/reveals in
  `update()`; keep the `loading` guard so one request is in flight per view.
  **Accept:** the event handler returns immediately; headless tests pump `update()`
  until the reply lands; a provider error becomes a system line.

- [x] **P1.8 The UI ignores conversation env configuration.**
  `FabulaApp` builds `ConversationConfig(mode=...)` directly
  ([`src/fabula/ui/app.py:90`](src/fabula/ui/app.py),
  [`src/fabula/ui/app.py:94`](src/fabula/ui/app.py)), so `FABULA_LEAK_FILTER`,
  `FABULA_GATED_REVEAL`, `FABULA_TOKEN_CAP`, and model overrides documented in
  `docs/conversation.md` do not apply in the game.
  **Fix:** resolve the app config with `config_from_env()`; change only `mode` when the
  Settings screen switches voice mode.
  **Accept:** with `FABULA_LEAK_FILTER=1`, the app's service config has
  `leak_filter=True`; switching to scripted preserves the other flags.

- [x] **P1.9 Firewall claim must match the code.**
  `truth.json` never reaches prompts (canary tests pass), but `secret=True` facts do
  enter the prompt by design ([`src/fabula/conversation/prompt_builder.py:37`](src/fabula/conversation/prompt_builder.py)),
  and the leak filter is off by default
  ([`src/fabula/conversation/config.py:50`](src/fabula/conversation/config.py)).
  **Fix:** keep defaults, make the env flags actually reachable from the UI (P1.8),
  and document that leak deflection is opt-in.

- [x] **P1.10 Live failures degrade silently to "Not now" lines.**
  Provider timeouts/errors/empty replies and token-cap exhaustion returned fixed
  placeholder lines ([`src/fabula/conversation/service.py:63-67`](src/fabula/conversation/service.py))
  with no notice, so every NPC looked evasive and no clue could be revealed — a failing
  key made cases unsolvable. Observed in play with `GOOGLE_API_KEY` set: `auto` resolved
  `live`, all turns returned `fallback=True` placeholders.
  **Fix:** degraded turns answer through the scripted responder (eligible clue reveals
  included), carry `fallback=True` + `fallback_reason`, and the dialogue screen shows
  one notice per conversation. Authored degraded turns are flagged for evaluation.
  **Accept:** provider failure yields the deterministic scripted line for that intent,
  keeps `revealed_clue_ids` working, and shows exactly one notice.

---

## P2 — fast local generation correctness

- [x] **P2.1 Requested type/tone/difficulty are not enforced.** They are sent to the
  model but never validated for the fast route; the synthetic fallback picks them from
  the seed ([`src/fabula/generation/orchestrator.py:415`](src/fabula/generation/orchestrator.py),
  [`src/fabula/generation/synthetic_blueprint.py:28`](src/fabula/generation/synthetic_blueprint.py)).
  The staged route validates them ([`orchestrator.py:166`](src/fabula/generation/orchestrator.py)).
  **Fix:** the compiler receives `expected_type`/`expected_tone`/`expected_difficulty`
  and the request wins over the blueprint header; the synthetic sample generator
  accepts the same settings. Tests cover both paths.
- [x] **P2.2 The compiler discards the blueprint.** Culprit is always `npc_01` and the
  cast is fixed ([`src/fabula/generation/compiler.py:239`](src/fabula/generation/compiler.py));
  blueprint clues/knowledge are replaced by a canned set, so every case has the same
  skeleton. `verify_solvability` is a consistency check, not candidate elimination.
  **Fix:** the compiler now carries the blueprint's culprit, cast, scene, minute,
  timeline, clues and knowledge into the bundle and synthesizes only schema-required
  structure; `verify_solvability` is a real elimination proof (exactly the culprit owns
  a clue-reachable secret `did` fact, every innocent's alibi is clue-reachable).
- [x] **P2.3 Failures are silent.** Both the model call and compilation swallow every
  exception and substitute the synthetic sample
  ([`orchestrator.py:423`](src/fabula/generation/orchestrator.py),
  [`orchestrator.py:441`](src/fabula/generation/orchestrator.py)).
  **Fix:** `GenerationResult` records `blueprint_source` and `fallback_reason`; the
  progress stream emits a `bundle_notice`, the CLI prints `Blueprint: model|synthetic`
  plus the reason, and the game shows a one-time notice. `GenerationCancelled` is
  re-raised instead of being swallowed.
- [x] **P2.4 The 1B fast model is not in the repository.** `models/` currently holds
  only the Qwen2.5-3B GGUF, so Generate Locally always takes the synthetic path.
  **Fix (owner):** `Llama-3.2-1B-Instruct.Q4_K_M.gguf` is now in `models/` and its
  SHA-256 is verified against the `fast_model` manifest entry.

---

## P3 — Kaggle route robustness

- [x] **P3.1 No retry around `kernels_status`.** One transient API error aborts a
  ~10-minute run ([`src/fabula/generation/kaggle_runner.py:659`](src/fabula/generation/kaggle_runner.py)).
  Add bounded retry/backoff for status polling.
  **Fix:** `_status_with_retry` retries four times with exponential backoff (capped at
  30 s) before raising `KaggleRunError`.
- [x] **P3.2 Kernel workspace and model selection.** The kernel clones the whole repo
  and picks `models[0]` without a manifest/hash check
  ([`kaggle_runner.py:219`](src/fabula/generation/kaggle_runner.py)); the kernel
  string-patches `local_runner.py` and monkeypatches private `_run_stage`. Clone only
  `src/` + `training/`, select by manifest hash, and avoid private-API patching.
  **Fix:** sparse checkout of `src/` + `models/model_manifest.json` (full-clone
  fallback), selection by requested file name with manifest default and SHA-256
  verification, and the official `generate_bundle(stage_validators=...)` hook instead of
  source patching or private-API monkeypatches.
- [x] **P3.3 Non-atomic download/install.** Output download and case installation are a
  copytree ([`kaggle_runner.py:764-775`](src/fabula/generation/kaggle_runner.py)); route
  through the atomic bundle publication path.
  **Fix:** the downloaded case is copied to a sibling temp directory and swapped in with
  `replace_directory`, so a failure leaves the previous library untouched.

---

## P4 — packaging and release readiness

- [ ] **P4.1 No console entry point.** No `[project.scripts]` in `pyproject.toml`;
  add `fabula = "fabula.cli:main"`, a `llama-cpp` optional extra, and pin `kaggle`.
- [ ] **P4.2 No CI.** Add a workflow running the AGENTS.md gates
  (`pytest`, `ruff check .`, `ruff format --check .`) without credentials.
- [ ] **P4.3 Missing release files.** LICENSE, NOTICE/asset attribution, and a model
  card; wire the Qwen hash check into a normal command, not only `model check`.
- [ ] **P4.4 Root clutter.** Remove or relocate `run_test_game.py`, `run_ui_test.py`,
  `test_intent.py`, `test_npc.py`, `generate_test_bundle.py`, `bundle/`,
  `deliv1_docs/`, and `web/` per AGENTS.md §3. (`plan.md` stays tracked in root.)

---

## Documentation drift (fix alongside the code)

| Document claim | Code reality | Action | Status |
|---|---|---|---|
| A* pathfinding (`docs/features.md:197`, dev plan) | Dijkstra, uniform cost ([`src/fabula/simulation/pathfinding.py:22`](src/fabula/simulation/pathfinding.py)) | Reword to shortest-path/Dijkstra or implement A* | Fixed |
| “You only get one accusation” ([`src/fabula/ui/how_to_play.py:119`](src/fabula/ui/how_to_play.py)) | Three attempts ([`docs/contracts/schema-v1.md:57`](docs/contracts/schema-v1.md)) | Fix How to Play copy | Fixed |
| “People move around town as the day goes on” ([`how_to_play.py:113`](src/fabula/ui/how_to_play.py)) | Was false because the clock was frozen | True after P0.1; keep copy | Fixed |
| Dev plan: staged generation only | Neurosymbolic fast route is the UI default | Sync WS-E/F/H docs | Fixed |
| README “~12–24 s” fast generation | UI copy says “under a minute”; synthetic path is instant | State the condition (model present vs fallback) | Fixed |
| Ten-minute session | Never started | True after P0.1/P0.2 | Fixed |
| Live mode “leaves discovery to the engine/UI” (`docs/conversation.md`) | Live mode could not reveal at all | Update after P1.6 | Fixed |
| Conversation env flags | Ignored by the UI and `fabula play` | True after P1.8 | Fixed |
| Evaluation plan assumed one base-vs-fine-tune generator | Two fine-tuned generators exist (`fast-1b` blueprint, `staged-3b` staged JSON) | Make both explicit conditions and add the cross-generator comparison in `90_EVALUATION_PLAN.md`, `WS-I_evaluation.md`, `99_ACCEPTANCE.md`, `features.md`, `FABULA_DEVPLAN_SOURCE.md`, `DOCUMENTATION.md` | Fixed |

---

## Verification for this branch

- [x] `python -m pytest` — 270 passed
- [x] `ruff check .` — clean
- [x] `ruff format --check .` — clean (151 files)
- [x] Real fast-route smoke test: `generate --fast --type disappearance --tone dark
      --difficulty hard --seed 4242` used the 1B model (`Blueprint: model`), honored
      all three settings, and published a valid bundle (45.5 s on this CPU).
- [ ] Headless end-to-end: `python -m fabula` → New Game → Ready Case → map timer
      counts down, NPCs move, accusation attempts persist, dialogue replies do not
      freeze the window.

## Out of scope for this plan

- **WP-I**: probe suite, metrics, base-vs-fine-tune experiment, results packaging.
- Generated art, scraping, runtime local chat, GA/MLP/K-Means — excluded by the MVP.
