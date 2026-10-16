# Fabula — Product & Feature Specification (Single Source of Truth)

> **Status:** Authoritative. Written 2026-10-16 at the end of the pre-development planning session.
> **Supersedes:** `README.md`, `docs/md/DOCUMENTATION.md`, `docs/latex/*`, and `AGENTS.md` project-context sections. Those describe an older, different (course-style, classical-AI-only) design and are **outdated**. If anything there conflicts with this file, **this file wins**. Do not open `docs/latex/` (it only duplicates the old markdown doc).

---

## 0. How to Use This File (for AI agents)

1. Read sections 1–4 first to understand the whole product end to end.
2. Treat every statement tagged **[DECIDED]** as a hard requirement made by the project owner.
3. Treat **[ADOPTED]** as proposed during planning and accepted by the owner. Follow it unless the owner changes it.
4. Treat **[OPEN]** as not yet decided. Do not silently pick an answer: surface it, propose options, or use the stated default only if one is given.
5. Schemas in section 8 are **PROVISIONAL sketches**. They define intent and field vocabulary, not final contracts. The first development task is to freeze them (section 14).
6. Never contradict the **non-negotiables** in section 2.

Legend: **[DECIDED]** = owner decision · **[ADOPTED]** = assistant proposal accepted by owner · **[OPEN]** = unresolved.

---

## 1. Product Overview

**Fabula** is a small, kind-of-open-world, single-player **Python mystery game** in which every NPC is AI-controlled. The game feels AI-generated because **a fine-tuned small LLM generates the entire game before play begins**: the mystery, the town, the cast, and each NPC's private knowledge and identity.

The player explores a tiny town (3–4 named locations, 5–6 NPCs), talks to NPCs in free-text conversations, finds clues, and tries to solve the mystery within about **10 minutes**.

### 1.1 Two-phase design

| Phase | When | What runs | LLM involved |
|---|---|---|---|
| **Generation** | Before the game starts, on the player's machine | The **fine-tuned small LLM** produces a complete game bundle (JSON files) | Fine-tuned model (local) |
| **Play** | During the 10-minute session | Python engine builds the world from JSON; NPCs move via classical AI; NPC conversation uses **live APIs** | Live API (Gemini, Grok, etc.) only. **No fine-tuned model at runtime** |

### 1.2 One-sentence pitch
> A fine-tuned small LLM writes a self-contained mystery (crime, town, suspects, secrets); a Python engine brings it to life; live-API-driven NPCs, each knowing only their own JSON, converse with the player, who must work out what happened before time runs out.

### 1.3 Mystery scope [DECIDED]
The game is **not limited to murder**. Mystery type is a parameter, not a baked-in genre. Initial target types: **theft, disappearance, murder** (v1). Later candidates: sabotage, blackmail/fraud. Theft and disappearance suit a 10-minute session particularly well (less backstory, lighter tone).

---

## 2. Non-Negotiables [DECIDED]

1. A **fine-tuned LLM is mandatory**. It is the most crucial component. It generates the mystery, the town setting, NPC identities, and all NPC knowledge.
2. Fine-tuning happens on **Kaggle T4**, with a **small LLM** and a lightweight method (QLoRA-class). Not heavy.
3. **The player runs the generator locally** before starting the game.
4. The **whole game is generated before play**. The fine-tuned LLM does **not** interfere at runtime.
5. **Runtime NPC conversation relies only on live APIs** (e.g. Grok, Gemini). No local runtime conversation model.
6. **Each NPC's memory and identity live in separate JSON, isolated from other NPCs.** An NPC's API prompt is built only from that NPC's own JSON. **Only the culprit(s) know what actually happened.**
7. If an NPC fails to keep a secret, that is treated as **LLM accuracy fault**, not an engine bug. It is what the evaluation measures.
8. **Scale:** very small open world, **5–6 NPCs**, **3–4 named locations** (market, library, etc., chosen by the generator per mystery), **~10-minute** target session.
9. The world is generated as **JSON handed to Python**, which builds the playable world from it.
10. Evaluation targets **NPC behaviour**, not mystery quality (see section 11).

---

## 3. End-to-End Flow

```
┌──────────────────────── PHASE 1: GENERATION (local, before game) ────────────────────────┐
│ Player settings: mystery_type (or random), tone, difficulty                               │
│        │                                                                                  │
│        ▼                                                                                  │
│ Fine-tuned small LLM  ── staged generation ──►  world → cast → truth → per-NPC files      │
│        │            (grammar/schema-constrained decoding)                                 │
│        ▼                                                                                  │
│ Validator (schema, cross-refs, consistency)  ──fail──► retry stage (max N) ──►            │
│        │ pass                                                              error screen   │
│        ▼                                                                                  │
│ Game bundle on disk:                                                                      │
│   world.json · truth.json · clues.json · npcs/<id>/identity.json · npcs/<id>/memory.json  │
└───────────────────────────────────────────┬───────────────────────────────────────────────┘
                                            │
┌───────────────────────────── PHASE 2: PLAY (10 minutes) ──────────────────────────────────┐
│ Python engine loads bundle ─► builds world from world.json (tiles from fixed type enum)   │
│ NPCs move/act via classical AI (A*, schedules)                                            │
│ Player walks, examines clues, talks (free text)                                           │
│     └─► Prompt assembler: identity.json + memory.json of THAT NPC only (+ chat history)   │
│            └─► Live API (Gemini / Grok / …) ─► in-character reply                         │
│ Journal records clues; player makes an accusation (who / how / why)                       │
│ Engine checks accusation against truth.json (never sent to any API) ─► win / lose         │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Feature Specification

### 4.1 Mystery Generation (offline, local) [DECIDED]

- The fine-tuned model generates **everything**: mystery, town, NPC roster, NPC identities, NPC memories/secrets, clue placement.
- Player-facing generation settings **[ADOPTED]**: `mystery_type` (theft / disappearance / murder / random), `tone` (cozy ↔ dark), `difficulty`.
- **Staged generation [ADOPTED]**: world → cast → truth → per-NPC files, instead of one giant output. Reasons: small models stay more consistent, each stage is validated separately, retries are cheap.
- **Constrained decoding [ADOPTED]**: grammar- or JSON-schema-constrained output to avoid malformed JSON.
- **Validator + retry loop [ADOPTED]**: runs after each stage (schema validity, cross-reference integrity, graph connectivity, timeline consistency, solvability and unique-culprit checks). Failure → retry the stage up to N times → clear error screen if still failing. This is a **runtime safety guard**, not the project's headline evaluation.
- **Loading screen [ADOPTED]**: local CPU generation of a few thousand JSON tokens may take minutes on low-end machines (estimate; **benchmark early**).
- Output is a **game bundle** (section 8).

### 4.2 World & Engine

- **Engine [OPEN]:** Pygame or Arcade (default if undecided: Pygame). Whichever is chosen, the simulation core is a **pure-Python, headless library with no UI imports** (testable and batch-runnable); the UI is a thin layer on top **[ADOPTED]**.
- **World construction [DECIDED]:** Python builds the world from `world.json`.
- **Locations [DECIDED/ADOPTED]:** 3–4 named locations per game, named and described by the LLM, but their **type must come from a fixed enum** (e.g. market, library, café, park, docks; **exact enum [OPEN]**) that maps to **pre-made tiles/placeholder assets**. This keeps generated worlds renderable without generated art.
- **Coordinates [ADOPTED]:** locations and NPC positions use explicit coordinates / tile positions (needed for A* heuristics); movement is on a small tile map or graph with named location nodes.
- **Perception [ADOPTED]:** an NPC perceives events in its own location (optionally adjacent). Specific rule finalised at schema freeze.
- **Time model [OPEN]:** real-time vs tick-based simulation. The session target is 10 real minutes.

### 4.3 NPC Behaviour (classical AI = "body", live API = "voice")

- **Count [DECIDED]:** 5–6 NPCs per game.
- **Movement & schedules [DECIDED/ADOPTED]:** NPCs follow simplified **schedules** (a few waypoints over the 10-minute session) so the town feels alive; **A\*** handles pathfinding between locations.
- **Other classical algorithms [OPEN]:** Genetic Algorithm planner, MLP action classifier, and K-Means from the old design are **not committed**. They survive only if justified (e.g. a course requirement). Default: do not build them for MVP.
- **Conversation [DECIDED]:** only through **live APIs** at runtime.
- **Knowledge isolation [DECIDED]:** each NPC's prompt contains only its own identity and memory. Other NPCs' files and `truth.json` are never included.

### 4.4 NPC Knowledge, Secrets & Deception [ADOPTED]

- NPC memory is **structured facts**, not free-text strings. Each fact has a source: `did` / `witnessed` / `heard` / `inferred`.
- Each fact carries a **disclosure policy**: `volunteer`, `if_asked`, `hide`, or `lie`.
- **Only the culprit(s)** hold the true account of what happened (their own actions). **Non-culprits** hold partial observations and their **own secrets** (red herrings), otherwise the case is unsolvable.
- **Culprit lies are authored, not improvised**: the culprit's memory includes a **cover story/alibi** generated with the scenario, so lies stay consistent.
- **Spoiler firewall [ADOPTED]:** the engine owns the truth (`truth.json`). The generator emits persona and knowledge; runtime prompts are assembled per NPC from that NPC's files only.
- Memory as structured facts also makes **consistency measurable** (section 11).

### 4.5 Runtime Conversation (live API)

- **Prompt assembly:** system instructions (stay in character, use only your own facts, say you don't know otherwise, follow each fact's disclosure policy) + `identity.json` + `memory.json` + that NPC's chat history + player input. Output format: structured, e.g. `{ "reply": "...", "mood": "..." }` (**format [OPEN]**, provisional).
- **Provider abstraction [ADOPTED]:** the engine can swap among live API providers (Gemini, Grok, others; **final list [OPEN]**).
- **API keys [ADOPTED/OPEN]:** default plan is bring-your-own key, or a capped developer key; final choice open.
- **Latency budget [ADOPTED]:** about 2–3 seconds per reply; use streaming where supported.
- **Cost control [ADOPTED]:** per-session token cap.
- **Failure handling [ADOPTED]:** if the API fails or times out, fall back to canned in-character lines.
- **No local runtime LLM.** (Do not add an Ollama/local fallback.)
- **Optional output leak-check [OPEN, evaluation-relevant]:** a string/fact-match filter on replies could block secret leaks. For evaluation it is **disabled** so that raw LLM secret-keeping is measured; it may be enabled as an ablation or product safeguard.
- **Optional gated reveal [OPEN, ablation]:** the engine injects a secret fact into a prompt only after the player presents the right clue. Baseline mode keeps secrets in the prompt and relies on the LLM.

### 4.6 Player Loop (≈10-minute session) [ADOPTED unless noted]

- Walk around a tiny open world; examine objects/clues; talk to NPCs by typing free text.
- **Journal:** automatically records discovered clues and key statements.
- **Visible timer** for the ~10-minute session [DECIDED target].
- **Clue budget:** roughly 4–6 clues; roughly 1–2 minutes of conversation per NPC.
- **Accusation:** player names **culprit + method + motive**. Limited number of accusations (**number [OPEN]**). Engine verifies against `truth.json`.
- **Win/lose:** correct accusation wins; time out or exhausted accusations loses. Partial credit for who/how/why is possible (**[OPEN]**).
- **Hints [OPEN]:** optional hint mechanism.

### 4.7 Content Safety [ADOPTED]

- Violence/gore boundary and cozy-vs-dark tone setting in generation.
- Filter on player-typed input before sending to APIs.
- Intended age rating to be stated at release (**rating [OPEN]**).

---

## 5. Fine-Tuning Plan

### 5.1 Model & method
- **Small instruct LLM, ~3–4B parameters [ADOPTED]**; exact base model **[OPEN]**. Candidates: Qwen 3.x ~4B, Gemma 3 ~4B, Llama 3.2 3B. (Large MoE models are too heavy for a local game.)
- **QLoRA supervised fine-tuning (SFT) with Unsloth on Kaggle T4 [DECIDED/ADOPTED]**. Check Kaggle's current weekly GPU quota and session limits before scheduling runs.
- SFT first; RL (e.g. GRPO) is deferred.
- Export a quantised model (e.g. Q4 GGUF) for **local CPU inference**; inference runtime **[OPEN]** (llama.cpp-style runner).
- The fine-tune teaches **format reliability, schema adherence, and the style of scenarios/NPC identities**, not general knowledge.

### 5.2 Training data [ADOPTED]
- **No scraping.** Use a **synthetic-to-natural pipeline** (inspired by MuSR, which generates mysteries from a symbolic skeleton first, then narrates):
  1. A **symbolic scenario generator** (plain Python) creates skeletons: crime type, culprit, motive, means, opportunity, timeline, clue graph, alibis, per-NPC knowledge.
  2. A strong **teacher LLM** expands each skeleton into the full bundle (JSON in the target schema).
  3. The **validator filters** bad examples.
  4. Result: SFT examples of `(settings + stage input) → stage JSON`.
- **Size:** ~1,500–3,000 verified examples. Quality over volume.
- **Balance** across mystery types; the prompt includes `mystery_type` (and tone/difficulty) as conditioning. Augment by varying setting, cast size, culprit type, difficulty, tone.
- **Templates needed per type:** public murder-mystery datasets do not cover theft/disappearance, so each type needs its own skeleton template.
- **Seed/reference material:** MuSR (synthetic murder mysteries), True Detective (human-authored), public-domain Christie/Holmes for style. Check each licence.
- **Teacher-model licensing [OPEN]:** verify the teacher provider's terms allow using outputs to train another model.

### 5.3 Baselines
Before/while fine-tuning, test **base model + good prompting** and a large API model on the same generation task. The fine-tune must show a measurable benefit (section 11.3).

---

## 6. Technology Summary

| Area | Choice | Status |
|---|---|---|
| Language | Python | DECIDED |
| Game library | Pygame or Arcade | OPEN (default Pygame) |
| Simulation core | Headless pure-Python library | ADOPTED |
| Generation model | Small (~3–4B) instruct LLM, QLoRA, Unsloth, Kaggle T4 | DECIDED/ADOPTED |
| Local inference | Quantised (e.g. GGUF Q4), runner TBD | OPEN |
| Constrained decoding | Grammar / JSON-schema | ADOPTED |
| Runtime conversation | Live APIs only (Gemini, Grok, …) | DECIDED |
| Data format | JSON bundle, validated with Pydantic (or equivalent) | ADOPTED |
| Pathfinding | A* | ADOPTED |

---

## 7. Game Bundle (output of Phase 1)

```
bundle/
├── world.json           # scenario meta, locations (fixed type enum), NPC roster, start positions, schedules
├── truth.json           # ENGINE ONLY. Ground truth; never sent to any API or NPC prompt
├── clues.json           # clue definitions, placement, how they are revealed
└── npcs/
    └── <npc_id>/
        ├── identity.json   # who the NPC is: persona, traits, speech style, goals, relationships
        └── memory.json     # structured facts: what they know, hide, or lie about (+ cover story if any)
```

Rules:
- `npcs/<id>/` files are **isolated**: no cross-NPC content beyond that NPC's own relationships and observations.
- Only the **culprit(s)** `memory.json` contains the true account of the crime.
- Runtime may append to an NPC's in-session memory (e.g. things the player told them) in session state; the shipped bundle stays read-only.

---

## 8. Provisional Schema Sketches (**freeze before development**)

### 8.1 `world.json`
```json
{
  "schema_version": "0.1",
  "scenario_id": "string",
  "mystery_type": "theft | disappearance | murder | ...",
  "tone": "cozy | ... | dark",
  "difficulty": "easy | normal | hard",
  "title": "string",
  "intro_text": "string",
  "town_name": "string",
  "locations": [
    {
      "id": "market",
      "name": "Saffron Market",
      "type": "market",                 // MUST be from the fixed location-type enum
      "description": "string",
      "position": { "x": 0, "y": 0 },
      "connections": ["library"],
      "clue_spots": ["clue_01"]
    }
  ],
  "npcs": [
    {
      "id": "npc_01",
      "display_name": "string",
      "start_location": "market",
      "schedule": [
        { "at_minute": 0, "location": "market" },
        { "at_minute": 4, "location": "library" }
      ]
    }
  ]
}
```

### 8.2 `truth.json` (engine only)
```json
{
  "crime": {
    "type": "theft",
    "target": "string",                 // victim, stolen object, missing person, sabotaged thing
    "method": "string",
    "motive": "string",
    "time_window": { "start": "string", "end": "string" },
    "location_id": "market"
  },
  "culprits": ["npc_03"],
  "timeline": [ { "t": "string", "who": "npc_03", "what": "string", "where": "market" } ],
  "solution": { "who": "npc_03", "how": "string", "why": "string" },
  "red_herrings": [ { "npc": "npc_02", "secret": "string" } ]
}
```

### 8.3 `clues.json`
```json
[
  {
    "id": "clue_01",
    "location_id": "market",
    "description": "string",
    "discovery": "examine | npc_reveal",
    "revealed_by_npc": null,
    "implies": ["fact_ref_or_truth_ref"],
    "requires": []
  }
]
```

### 8.4 `npcs/<id>/identity.json`
```json
{
  "id": "npc_03",
  "name": "string",
  "age": 0,
  "role": "string",
  "traits": ["string"],
  "speech_style": "string",
  "backstory": "short string",
  "goals": ["string"],
  "relationships": { "npc_01": "string" },
  "attitude_to_player": "string"
}
```

### 8.5 `npcs/<id>/memory.json`
```json
{
  "npc_id": "npc_03",
  "facts": [
    {
      "id": "f_01",
      "who": "npc_03",
      "what": "string",
      "where": "market",
      "when": "string",
      "source": "did | witnessed | heard | inferred",
      "secret": true,
      "disclosure": "volunteer | if_asked | hide | lie",
      "reveal_requires": ["clue_02"],
      "cover_story_id": "cs_01"
    }
  ],
  "cover_story": {
    "id": "cs_01",
    "claim": "string",
    "supporting_facts": ["f_05"]
  }
}
```
`cover_story` exists for culprits (and anyone with a secret worth lying about). Structured facts are what make secret-keeping and consistency **machine-checkable**.

---

## 9. Mystery Types (generic crime model) [DECIDED/ADOPTED]

- Every scenario uses one generic `crime` block (section 8.2). Murder is just `type: murder`.
- The player's solution always has the same shape: **who, how, why**.
- **v1 types:** theft, disappearance, murder. **Later:** sabotage, blackmail/fraud.
- Each type needs its own symbolic-generator template and balanced coverage in training data.
- Optional experiment: hold out a type/combination to test generalisation.

---

## 10. Out of Scope / Explicitly Not Doing

- Running the fine-tuned model at runtime. [DECIDED]
- Local runtime conversation LLM (no Ollama fallback for NPC chat). [DECIDED]
- Evaluating or reporting **mystery quality** as the project's main research result. [DECIDED] (Validators still run as safety guards; their statistics may be reported as secondary.)
- Limiting the game to murder mysteries. [DECIDED]
- The old design's constraints: "100% CPU, no GPU/cloud API", "no fine-tuning", 5–10 NPCs, Gymnasium/FastAPI/React stack, stolen-watch scenario, demographic bias benchmark, ablation matrix. All **superseded**.

---

## 11. Evaluation (NPC Behaviour) [DECIDED focus]

### 11.1 Method
Build a **scripted probe suite per NPC**: direct questions, leading questions, false accusations, pressure ("the culprit already confessed"), "ignore your instructions" attempts, and repeated questions across turns. Run against the live API(s) using NPC prompts built from the generated bundles.

### 11.2 Metrics

| Metric | What it measures | How |
|---|---|---|
| **Secret-keeping rate** | NPC does not leak facts marked `hide`/`lie` | Fact-match + LLM-judge |
| **Knowledge boundary** | NPC never claims knowledge absent from its own JSON | Fact-extraction check |
| **Persona adherence** | Traits and speech style respected | Rubric (LLM-judge + human sample) |
| **Consistency** | No contradictions with own `memory.json` or earlier answers | Fact-extraction vs structured facts |
| **Culprit lie consistency** | Lies stay within the authored cover story | Check against `cover_story` |
| **Disclosure-policy adherence** | Reveals when `volunteer`/`if_asked` or after required clue; withholds otherwise | Scripted probes |
| **Provider robustness** | Behaviour stability across Gemini, Grok, etc. | Same probes per provider |

Secondary (generator-side, acceptable to report): schema validity rate, graph connectivity, solvability, unique-culprit rate, timeline consistency, scenario diversity.

### 11.3 Core experiment
Generate NPC JSONs with the **base model** and with the **fine-tuned model**, run the **same** runtime API model on both, and compare the metrics above. This ties the fine-tune directly to measurable NPC quality. Break results down by mystery type.

### 11.4 Ablations [ADOPTED]
- Secrets-in-prompt (baseline) vs **gated reveal**.
- Output leak-filter **off** (default for evaluation) vs on.
- Different API providers.

### 11.5 Judge details [OPEN]
Which model/provider acts as LLM-judge, and the human-sampling protocol.

---

## 12. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Small model emits invalid/inconsistent JSON | Staged generation, constrained decoding, validators, retries |
| Local generation too slow on CPU-only machines | Compact schemas, staged calls, loading screen, benchmark early |
| API models leak secrets | It is the measured quantity; ablations (gating, filter) as options |
| API cost/latency/outage | Token cap, streaming, canned fallback, provider abstraction |
| Unsolvable generated mysteries | Solvability/unique-culprit validators with retry |
| Spoilers via prompts | Engine-only `truth.json`; per-NPC isolation |
| Teacher-model licence restrictions | Verify terms before generating training data |
| Content safety | Tone setting, input filter, boundary rules |
| Scope creep | MVP scope below |

---

## 13. MVP Scope [ADOPTED]

- One engine, generated towns of 3–4 locations, 5–6 NPCs, ~4–6 clues, ~10-minute session.
- Mystery types: theft, disappearance, murder.
- Fixed location-type enum with placeholder tile kit.
- Live-API conversation via at least two providers (for robustness evaluation).
- Evaluation suite from section 11.

---

## 14. Pre-Development Checklist / Next Steps

1. Freeze schemas (section 8) including the generic `crime` block, structured facts, and location-type enum.
2. Write the **symbolic scenario generator** with templates for the three v1 types.
3. Build the training-data pipeline: skeleton → teacher LLM → validator filter.
4. Choose base model; set up the Kaggle T4 QLoRA notebook (Unsloth).
5. Build staged generation + validator with constrained decoding; benchmark local CPU speed.
6. Design the runtime prompt assembler, provider abstraction, token cap, fallbacks.
7. Write the probe suite and metric scripts for evaluation.
8. Define the 10-minute player loop; pick engine (Pygame/Arcade); prepare placeholder asset kit.
9. Settle licences (code, data, model weights, base-model licence, teacher-model terms) and content-safety rules.
10. Confirm team roles and revised timeline.

### Proposed timeline (adjustable, roughly 8 weeks)
- **Week 1:** specs, schemas, repo setup
- **Weeks 2–3:** symbolic generator, validators, data pipeline
- **Week 4:** fine-tune v1 and first generation-quality checks
- **Weeks 4–6:** simulation core, NPC schedules/A*, prompt assembler, UI
- **Week 7:** integration, playtests, NPC-behaviour evaluation
- **Week 8:** polish, results, demo

---

## 15. Open Decisions Register

| # | Decision | Default / note |
|---|---|---|
| 1 | Engine: Pygame vs Arcade | Default Pygame |
| 2 | Exact base model | ~3–4B instruct (Qwen / Gemma / Llama candidates) |
| 3 | Local inference runtime | llama.cpp-style |
| 4 | Location-type enum contents | Start: market, library, café, park, docks |
| 5 | Mystery types beyond v1 | Sabotage, blackmail/fraud |
| 6 | Real-time vs tick-based simulation | Undecided |
| 7 | Number of accusations; partial credit; hint system | Undecided |
| 8 | Runtime API providers; key model (BYO vs capped dev key) | Gemini + Grok-class; BYO leaning |
| 9 | NPC reply output format | `{reply, mood}` provisional |
| 10 | Output leak-filter / gated reveal in product vs ablation only | Ablation only by default |
| 11 | Fate of GA / MLP / K-Means | Not built for MVP unless required |
| 12 | LLM-judge model and human-sampling protocol | Undecided |
| 13 | Teacher model for training data and its licence terms | Verify before use |
| 14 | Age rating / content boundary specifics | Undecided |
| 15 | Team roles and exact timeline | Undecided |

---

## 16. Glossary

- **Bundle:** the set of JSON files produced by generation and consumed by the engine.
- **Truth / ground truth:** `truth.json`; what actually happened. Engine-only.
- **Culprit(s):** the NPC(s) whose memory contains the true account of the crime.
- **Red herring:** an NPC secret unrelated to the crime that makes suspicion ambiguous.
- **Disclosure policy:** per-fact rule (`volunteer`, `if_asked`, `hide`, `lie`) for what an NPC may say.
- **Cover story:** authored false account a culprit (or secret-holder) gives instead of the truth.
- **Spoiler firewall:** rule that no NPC prompt ever contains `truth.json` or another NPC's files.
- **Staged generation:** producing the bundle in sequential, separately validated steps.
- **Gated reveal:** engine injects a secret fact into a prompt only after the required clue is presented.
- **Body / Voice:** classical AI (movement, schedules) vs live API (conversation).
