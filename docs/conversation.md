# Runtime Conversation

Fabula's runtime conversation layer gives each NPC a voice while keeping the mystery's
truth inside the engine. There are two paths:

- **Live mode** sends the selected NPC's own prompt to Gemini or xAI and returns a
  parsed in-character reply.
- **Scripted mode** is a deterministic, local, authored fallback. It requires no API
  key, makes no network calls, and keeps the full game playable.

Neither path runs a local chat model, Ollama, or the fine-tuned generator.

## Installation

`httpx` is a runtime dependency for the live provider adapters:

```powershell
python -m pip install -e .
```

## Quick Start

```python
from fabula.conversation import config_from_env, create_conversation_service
from fabula.simulation import Session, load_bundle

loaded = load_bundle("bundles/my-mystery")
session = Session(loaded)
service = create_conversation_service(config_from_env())

files = loaded.npcs["npc_01"]
reply = service.reply(
    files,
    "What did you see that night?",
    discovered_clue_ids=session.discovered_ids,
    clues=loaded.clues.clues,
)
print(reply.text, reply.mood)

for clue_id in reply.revealed_clue_ids:
    session.npc_reveal("npc_01", clue_id)

service.close()
```

The caller must apply `reply.revealed_clue_ids` through `Session.npc_reveal`. Both
paths return eligible clue IDs: scripted mode reveals deterministically on case
questions, and live mode returns an ID when the model shares one of the eligible
evidence items listed in its prompt (see below).

## Modes

Set the mode with `FABULA_CONVERSATION_MODE` or `ConversationConfig.mode`.

| Mode | Behaviour |
|---|---|
| `auto` (default) | Uses a live provider when a key is configured; otherwise uses scripted mode. |
| `live` | Requires a key. Raises `ConversationSetupError` at startup if none is available. Never silently degrades. |
| `scripted` | Hard kill switch. Never constructs or calls a provider, even when keys are present. |

`ConversationStatus.mode` reports the resolved mode (`live` or `scripted`), and
`ConversationStatus.reason` reports why (`live`, `no_api_key`, or `forced_scripted`).

## Provider Configuration

Bring your own keys. Keys are read from the environment or an untracked JSON file;
they are never written to a bundle, reply, or log.

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Gemini key. |
| `XAI_API_KEY` | xAI key. |
| `FABULA_CONVERSATION_MODE` | `auto`, `live`, or `scripted`. |
| `FABULA_KEYS_FILE` | Optional JSON file with `{"gemini": "...", "xai": "..."}`. Environment values win. |
| `FABULA_GEMINI_MODEL` | Gemini model ID; default `gemini-2.0-flash`. |
| `FABULA_XAI_MODEL` | xAI model ID; default `grok-3-mini`. |
| `FABULA_TOKEN_CAP` | Per-service token budget; default 20,000. |
| `FABULA_LEAK_FILTER` | `1` enables the output leak filter; default off. |
| `FABULA_GATED_REVEAL` | `1` enables clue-gated secret inclusion; default off. |

Do not commit a keys file. Set a spend cap in each provider console and keep the token
cap low when testing. Provider default model IDs are implementation defaults, not
permanent product guarantees; override them when a provider renames or retires a model.

The game UI resolves its configuration with `config_from_env()`, so these variables
apply when launching `python -m fabula`. The Settings screen changes only the mode and
preserves the other flags.

If only one key is present, `auto` uses that provider. If both are present, Gemini is
tried first by default. `ConversationConfig.provider` and `provider_order` control the
preference.

## What Is Sent

A live request contains only:

- system rules for staying in character and following disclosure policy;
- the selected NPC's `identity.json` and `memory.json`;
- that NPC's own recent chat history;
- the player's current input;
- the eligible NPC-reveal clues this NPC may share (id and player-visible description),
  when any remain undiscovered and their prerequisites are met.

`truth.json`, the roster, another NPC's files, other NPCs' clues, and engine state never
enter a live request. The prompt DTO enforces this structurally, and tests plant canaries
in truth and in another NPC's memory. The selected NPC's file IDs must match each other.

The player input is filtered before any provider call. Hate, sexual, and self-harm
content is blocked, and blocked input makes zero calls. Prompt-injection attempts are
not stripped because they are part of the evaluation probe suite.

## Replies, Limits, and Fallbacks

Live providers return `{ "reply": "...", "mood": "...", "clue": "..." }`. Parsing is
forgiving:

- missing or invalid `mood` becomes `neutral`;
- `clue` is optional: it is honored only when it names one of the eligible evidence
  items listed in that request, and ignored otherwise;
- plain text becomes the reply;
- an unparsable or empty response degrades to the scripted responder (below).

Provider timeouts/errors, empty replies, and token-cap exhaustion also degrade to the
scripted responder instead of a placeholder. The reply keeps `mode: live` but sets
`fallback: true` and `fallback_reason` (`provider_error`, `empty_reply`, or `token_cap`),
and its text is authored, not model output. Degraded turns still honor clue eligibility,
so a provider outage cannot make a case unsolvable. The dialogue screen shows one notice
per conversation when this happens. Replies are clipped to 4,000 characters; history is
per-NPC and capped at 12 messages by default. Provider errors and keys are never logged.

## Scripted Mode

Scripted mode is deterministic by default and can be varied with
`ConversationConfig.scripted_seed`. It uses the selected NPC's own identity, traits,
backstory, and public clue descriptions to answer greetings, identity questions, case
questions, pressure, and farewells. It does not read truth or another NPC's files.

When the player asks about the case, the responder may reveal an eligible NPC-reveal
clue in character. Clue prerequisites (`requires`) and already-discovered clues are
honored. The returned `revealed_clue_ids` list tells the caller which clue to apply via
`Session.npc_reveal`.

Use scripted mode when demonstrating the game without keys, in offline tests, and as a
playability fallback. Its dialogue is authored behavior, not model output, and it is
**excluded from live-provider evaluation metrics** (secret-keeping, persona, provider
robustness, and related scores). The same responder supplies degraded live turns, which
are marked `fallback: true` so evaluation can exclude or report them separately.

## Optional Safeguards

Both safeguards are off by default (HG-09) because the baseline evaluation measures the
models' own behavior:

- **Leak filter (`leak_filter`)**: fact-matches a live reply against the selected NPC's
  protected `hide`/`lie` facts and replaces a match with a deflection. The raw reply is
  preserved when the toggle is off; `ConversationReply.leak_blocked` reports a block.
- **Gated reveal (`gated_reveal`)**: includes fact content only after its
  `reveal_requires` clue IDs have been discovered. The baseline includes secrets and
  relies on the model.

Both toggle values are recorded in every `ConversationReply` for evaluation.

## Evaluation Notes

- Run probe suites against live providers only; do not mix scripted output into their
  metrics.
- Keep toggles off for the baseline unless `docs/decisions.md` says otherwise.
- Store provider/model revision, latency, token counts, fallback flags, toggle values,
  seed, and schema version with each result. Never store keys.
- Offline tests use `httpx.MockTransport` and require no network, credentials, or GPU.
  Any future live smoke test must be explicitly opt-in and disabled by default.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Startup raises `ConversationSetupError` | `live` mode is selected but no key is configured. Add a key or use `scripted`/`auto`. |
| NPCs answer with fixed phrasing | No key was found, so `auto` resolved to scripted mode. Check `ConversationStatus.reason`. |
| `401`/`403` from a provider | Invalid or expired key, or a provider account issue. |
| `404` from a provider | The configured model ID is unavailable; override `FABULA_GEMINI_MODEL` or `FABULA_XAI_MODEL`. |
| NPCs switch to authored dialogue mid-conversation | A live call timed out, failed, returned empty, or hit the token cap. Check `ConversationReply.fallback_reason` and `ConversationStatus.tokens_used`. |
| No clue is revealed in live mode | No eligible NPC-reveal clue remains for that NPC, or the reply omitted `clue`. Degraded turns reveal through the scripted responder instead. |

## Running the Tests

```powershell
python -m pytest -q tests/test_conversation_prompt.py tests/test_conversation_providers.py tests/test_conversation_service.py tests/test_conversation_scripted.py
ruff check src/fabula/conversation tests/test_conversation_*.py
ruff format --check src/fabula/conversation tests/test_conversation_*.py
```
