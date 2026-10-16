# Fabula — System Architecture & Technical Documentation

> **A two-phase mystery game: a fine-tuned small LLM generates the complete game (mystery, town, cast, NPC knowledge) before play begins; a headless Python engine runs it; live APIs give each NPC its voice — grounded strictly in that NPC's own JSON files.**

> **Source of truth:** `docs/features.md` and `docs/FABULA_DEVPLAN_SOURCE.md` (corroborated by the generated plan in `docs/dev_plan/`). If anything in this document conflicts with them, **those files win**.
> **Tags:** **[DECIDED]** = owner decision · **[ADOPTED]** = accepted proposal · **[OPEN]** = unresolved (default shown where one exists). Human Gates are numbered **HG-xx** and defined in `docs/dev_plan/01_HUMAN_GATES.md`.

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Research Inspiration & Reference Material](#2-research-inspiration--reference-material)
3. [System Architecture & The Two-Phase Design](#3-system-architecture--the-two-phase-design)
4. [The Hybrid NPC Architecture: Classical AI ("Body") & Live API ("Voice")](#4-the-hybrid-npc-architecture-classical-ai-body--live-api-voice)
5. [NPC Knowledge, Secrets & The Spoiler Firewall](#5-npc-knowledge-secrets--the-spoiler-firewall)
6. [Data Generation & Fine-Tuning Pipeline](#6-data-generation--fine-tuning-pipeline)
7. [Implementation Plan & 8-Week Roadmap](#7-implementation-plan--8-week-roadmap)
8. [Quantitative Evaluation Framework (NPC Behaviour)](#8-quantitative-evaluation-framework-npc-behaviour)
9. [Summary & Key Advantages](#9-summary--key-advantages)

---

## 1. Project Overview

### 1.1 The Core Idea
**Fabula** is a small, kind-of-open-world, single-player **Python mystery game** in which every NPC is AI-controlled. The game feels AI-generated because **a fine-tuned small LLM generates the entire game before play begins**: the mystery, the town, the cast, and each NPC's private knowledge and identity **[DECIDED]**.

The player explores a tiny town (**3–4 named locations, 5–6 NPCs**), talks to NPCs in free-text conversations, finds clues, keeps a journal, and tries to solve the mystery within about **10 minutes** **[DECIDED]**.

Each NPC:
- **Lives in its own isolated JSON pair** — `identity.json` (who they are) and `memory.json` (structured facts of what they know, hide, or lie about).
- **Moves like a classical agent** — it follows a simplified schedule across the session, using $A^*$ pathfinding between named locations.
- **Speaks only through a live API** — its prompt is assembled *exclusively* from its own JSON files plus chat history; no local conversation model runs at runtime.
- **Knows only what its memory contains** — only the culprit(s) hold the true account of the crime; everyone else holds partial observations and their own secrets.

A human player can walk up to any NPC and engage in natural conversation. The NPC responds in-character, bounded by its own knowledge, and the player must work out what happened before time runs out.

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                            THE FABULA CONCEPT (TWO PHASES)                            │
├──────────────────────────────┬───────────────────────────┬────────────────────────────┤
│ GENERATOR (Phase 1, local)   │ THE BODY (Phase 2)        │ THE VOICE (Phase 2)        │
│ fine-tuned ~3–4B LLM         │ classical AI + engine     │ live API only              │
├──────────────────────────────┼───────────────────────────┼────────────────────────────┤
│ • Staged: world → cast →     │ • Schedules + A* movement │ • Free-text conversation   │
│   truth → per-NPC files      │ • Perception & physics    │ • Persona & disclosure     │
│ • Constrained JSON decoding  │ • Journal, timer, clue    │   policies                │
│ • Validated + retried bundle │   discovery, accusation   │ • Grounded in that NPC's   │
│                              │ • Deterministic, headless │   own JSON only            │
└──────────────────────────────┴───────────────────────────┴────────────────────────────┘
```

### 1.2 Two-Phase Design [DECIDED]

| Phase | When | What runs | LLM involved |
|---|---|---|---|
| **Generation** | Before the game starts, on the player's machine | The **fine-tuned small LLM** produces a complete game bundle (JSON files) | Fine-tuned model (local, CPU-class) |
| **Play** | During the ~10-minute session | Python engine builds the world from JSON; NPCs move via classical AI; NPC conversation uses **live APIs** | Live API (Gemini, Grok, …) only. **No fine-tuned model at runtime** |

### 1.3 One-Sentence Pitch
> A fine-tuned small LLM writes a self-contained mystery (crime, town, suspects, secrets); a Python engine brings it to life; live-API-driven NPCs, each knowing only their own JSON, converse with the player, who must work out what happened before time runs out.

### 1.4 Mystery Scope [DECIDED]
The game is **not limited to murder**. Mystery type is a parameter, not a baked-in genre. **v1 types: theft, disappearance, murder.** Later candidates: sabotage, blackmail/fraud. Theft and disappearance suit a 10-minute session particularly well (less backstory, lighter tone). Every scenario uses one generic `crime` block, and the player's solution always has the same shape: **who, how, why**.

### 1.5 Academic Relevance
The project integrates core AI and ML topics around a single working product:
- **Search Algorithms ($A^*$)**: deterministic pathfinding across the town's location graph.
- **Knowledge Representation**: structured facts with `source` and `disclosure` policies; authored cover stories for deception.
- **Constrained Structured Generation**: grammar / JSON-schema-constrained decoding, staged generation, validator-and-retry loops.
- **LLM Fine-Tuning**: QLoRA supervised fine-tuning of a ~3–4B instruct model with Unsloth on Kaggle T4.
- **Grounded Prompting & Isolation**: per-NPC prompt assembly with a machine-enforced spoiler firewall.
- **Behavioural Evaluation of LLMs**: scripted probe suites, secret-keeping metrics, LLM-judge rubrics, base-vs-fine-tune experiments.

> **Note (superseded components):** the Genetic Algorithm planner, MLP action classifier, and K-Means clustering from the earlier course-style design are **not part of the MVP**. They are built only if a course requirement is stated (**[OPEN → HG-10]**, default: do not build).

---

## 2. Research Inspiration & Reference Material

### 2.1 MuSR (synthetic-to-natural pipeline)
MuSR generates murder mysteries from a **symbolic skeleton first, then narrates it**. This directly inspired Fabula's training-data pipeline (Section 6): a plain-Python symbolic scenario generator produces a skeleton (crime type, culprit, motive, means, opportunity, timeline, clue graph, alibis, per-NPC knowledge), and a strong teacher LLM expands each skeleton into full stage JSON.

### 2.2 Seed & style references
- **True Detective** — human-authored mystery structure for style calibration.
- **Public-domain Christie / Holmes** — style and fair-play clue conventions.
- Each reference's **licence must be checked before use** (**[OPEN → HG-17]**), and the **teacher model's terms must permit training on its outputs** (**[OPEN → HG-11]**).

### 2.3 Superseded Design Lineage
The previous edition of this document described a different, course-style design. Its constraints are **explicitly superseded** and must not be reintroduced:
- "100% CPU, no GPU/cloud API" and "no fine-tuning" — replaced by mandatory fine-tuning (Kaggle T4) + live APIs at runtime.
- 5–10 NPCs → fixed **5–6 NPCs**, **3–4 locations**.
- Gymnasium / FastAPI / React stack → plain Python, headless sim core + thin Pygame/Arcade UI **[OPEN → HG-01]**.
- Fixed stolen-watch scenario, demographic-bias benchmark, and the old ablation matrix → replaced by generated mysteries and the NPC-behaviour evaluation (Section 8).

---

## 3. System Architecture & The Two-Phase Design

![System Architecture: Generation & Play](../../assets/system_architecture.png)
*Figure 1: Phase 1 (local staged generation → validated JSON bundle) and Phase 2 (headless engine + Body/Voice split). ([Vector SVG](../../assets/system_architecture.svg))*

### 3.1 Phase 1 — Local Generation (before play) [DECIDED core; details ADOPTED]

```
Player settings: mystery_type (theft | disappearance | murder | random), tone (cozy↔dark), difficulty
     │
     ▼
Fine-tuned small LLM ── STAGED generation ──► world → cast → truth (+clues) → per-NPC files
     │            (grammar / JSON-schema-constrained decoding)
     ▼
Validator after each stage (schema, cross-refs, connectivity, timeline, solvability, unique culprit)
     │                └── fail ──► retry stage (max N, default 3) ──► still failing: clear error screen
     ▼ pass
Game bundle on disk: world.json · truth.json · clues.json · npcs/<id>/identity.json · npcs/<id>/memory.json
```

Design decisions behind this pipeline:
- **Staged generation [ADOPTED]**: world → cast → truth → per-NPC files instead of one giant output. Small models stay more consistent, each stage is validated separately, and retries are cheap.
- **Constrained decoding [ADOPTED]**: grammar- or JSON-schema-constrained output to prevent malformed JSON.
- **Validator + retry loop [ADOPTED]**: checks schema validity, cross-reference integrity, graph connectivity, timeline consistency, solvability, and unique-culprit rules after every stage. Failure → retry the stage up to N times (default 3, config) → explicit error screen. This is a **runtime safety guard**, not the project's headline evaluation.
- **Solvability, concretely [ADOPTED]**: a chain of clues/facts exists from which the player can derive who/how/why; exactly one culprit set; no timeline contradictions; all cross-references resolve; location graph connected; ≥4–6 clues.
- **Loading screen [ADOPTED]**: local CPU generation of a few thousand JSON tokens may take minutes on low-end machines (estimate — **benchmark early**, HA-03).

### 3.2 The Game Bundle (output of Phase 1)

```
bundle/
├── world.json           # scenario meta, locations (fixed type enum), NPC roster, start positions, schedules
├── truth.json           # ENGINE ONLY. Ground truth; never sent to any API or NPC prompt
├── clues.json           # clue definitions, placement, how they are revealed
└── npcs/
    └── <npc_id>/
        ├── identity.json   # persona, traits, speech style, goals, relationships
        └── memory.json     # structured facts: what they know, hide, or lie about (+ cover story)
```

Rules **[DECIDED]**:
- `npcs/<id>/` files are **isolated**: no cross-NPC content beyond that NPC's own relationships and observations.
- Only the **culprit(s)** `memory.json` contains the true account of the crime.
- The shipped bundle is **read-only** during play; runtime additions (chat history, facts the player told an NPC) live in session state.

### 3.3 Phase 2 — The Play Loop (~10 minutes)

The simulation runs as a session loop that advances a session clock. Each NPC turn passes through five stages:

#### 1. World State (Ground Truth)
The engine loads the bundle read-only and tracks the complete state of the world:
- The town graph built from `world.json` (location nodes, connections, coordinates).
- Exact tile positions of all NPCs and clues; placeholder tiles from the **fixed location-type enum** (no generated art).
- The session clock and visible countdown (**time model [OPEN → HG-05]**: real-time vs tick-based; `schedule.at_minute` assumes a minute-based clock).
- Physical rules (an NPC cannot be in two places at once, etc.).

#### 2. Perception Filter (Sensory Boundaries)
Instead of global omniscience, each NPC perceives events in **its own location** (optionally adjacent locations) **[ADOPTED]** — the precise rule is finalised at schema freeze (HG-18).

#### 3. NPC Internal State
Each character has two read-only JSON stores plus session state:
- **`identity.json`**: static persona, traits, speech style, goals, relationships.
- **`memory.json`**: structured facts with `source` and `disclosure` policies (Section 5).
- **Session state**: chat history with the player, in-session facts, discovered clues.

#### 4. Decision & Communication (Body / Voice dispatch)
- Moving between locations? → the current **schedule waypoint + $A^*$ search**.
- Speaking with the player? → **prompt assembler** (that NPC's identity + memory only) → **live API** → in-character reply.

#### 5. Action Execution & Feedback
- The engine validates the action physically, advances the clock, and appends the event to session state.
- The **journal** auto-records discovered clues and key statements; the **timer** counts down.
- The player accuses (**who / how / why**) → the engine checks the accusation against `truth.json` → win / lose.

> **The Grounding & Spoiler Rule** **[DECIDED]**: World state is absolute truth, owned by the engine. `truth.json` is **never** sent to any API, and no NPC prompt ever contains another NPC's files. Physical reality is governed by simulation code; the LLM cannot hallucinate new items, teleport an NPC, or alter the clock. This is enforced by **tests**, not by prompt wording.

---

## 4. The Hybrid NPC Architecture: Classical AI ("Body") & Live API ("Voice")

The architecture assigns each responsibility to the technology best suited for it: deterministic algorithms for anything physical, a fine-tuned model for pre-play content, and live APIs for speech.

![Decision Engine: Task & Tool Routing](../../assets/decision_engine_dispatch.png)
*Figure 2: Runtime dispatch — schedules + $A^*$ for the Body, prompt assembler + live API for the Voice. ([Vector SVG](../../assets/decision_engine_dispatch.svg))*

### 4.1 Search & Pathfinding ($A^*$)
- **Role**: deterministic town navigation **[ADOPTED]**.
- **Mechanism**: the town is an undirected, weighted graph $G = (V, E)$ — nodes are named locations (market, library, café, … from the **fixed location-type enum**), edges are connections with distances.
- **Algorithm**: $A^*$ with Euclidean distance as an admissible heuristic over explicit tile coordinates.
- **Benefits**: instantaneous, mathematically guaranteed shortest path, zero hallucination risk.

### 4.2 NPC Schedules (Body)
- NPCs follow **simplified schedules**: a few waypoints spread over the 10-minute session, authored per NPC in `world.json` (`at_minute` → `location`) **[DECIDED/ADOPTED]**.
- $A^*$ executes each waypoint transition; the result is a town that feels alive without per-frame planning.
- The schedule's time semantics are frozen with the time model (**HG-05**, one-minute ticks driven by monotonic real time is the plan's proposed resolution).

### 4.3 Deliberately Not Built in the MVP
The following components from the older design are **excluded by default** **[OPEN → HG-10]**:

| Component (old design) | Old role | Fate in Fabula |
|---|---|---|
| Genetic Algorithm planner | Multi-objective daily route optimization | **Not built** unless a course requirement is stated |
| MLP action classifier | Reflexive action prediction from state vectors | **Not built** unless a course requirement is stated |
| K-Means trajectory clustering | Post-hoc behaviour archetypes | **Not built** unless a course requirement is stated |

### 4.4 The Voice — Runtime Conversation (live API only) [DECIDED]

#### How a Prompt is Formed
When the player addresses an NPC, the prompt assembler compiles a controlled prompt from **that NPC's files only**:

```json
{
  "system": "You are Mira, a 34-year-old market vendor. Stay in character. Use only the facts in your own memory. Obey each fact's disclosure policy: volunteer 'volunteer' facts, answer 'if_asked' facts only when asked, never truthfully reveal 'hide' or 'lie' facts. If you do not know, say you do not know.",
  "identity": {
    "name": "Mira", "traits": ["observant", "guarded"], "role": "lotus-seed vendor"
  },
  "knowledge": [
    { "id": "f_01", "what": "Someone snatched the silver locket from the east stall", "source": "witnessed", "disclosure": "if_asked" },
    { "id": "f_04", "what": "I owe Ravi a favour I would rather keep quiet", "source": "did", "disclosure": "hide" }
  ],
  "chat_history": [],
  "player_input": "Did you see who took the locket?",
  "output_format": "JSON: {\"reply\": string, \"mood\": string}"
}
```

#### Grounded Output (provisional format, **[OPEN → HG-08]**)
```json
{
  "reply": "I did, actually — right by my stall, quick as anything. But I only saw a shape slipping toward the north gate. Who it was, I couldn't swear to.",
  "mood": "wary"
}
```
Because the prompt contains only Mira's own facts, **she cannot leak the culprit's account or another NPC's secrets** — preserving the mystery. An NPC asked about something outside its memory says it does not know.

#### Runtime Conversation Requirements
- **Provider abstraction [ADOPTED]**: swappable adapters for live API providers (Gemini, Grok-class, others; **final list [OPEN → HG-07]**), **≥2 providers in MVP** for robustness evaluation.
- **API keys [ADOPTED/OPEN]**: bring-your-own key (leaning) or capped developer key (**HG-07**).
- **Latency budget [ADOPTED]**: ≈2–3 seconds per reply; stream where supported.
- **Cost control [ADOPTED]**: per-session token cap.
- **Failure handling [ADOPTED]**: on API failure/timeout, fall back to canned in-character lines.
- **No local runtime LLM [DECIDED]**: no Ollama/local fallback; the fine-tuned model never runs during play.
- **Content safety [ADOPTED]**: filter player-typed input before any API call (**boundary specifics [OPEN → HG-13]**).
- **Optional toggles [OPEN → HG-09]**: an output **leak-filter** and a **gated reveal** (engine injects a secret only after the player presents the required clue). Both are **off by default**, implemented as toggles used for evaluation ablations; product use is an open decision.

---

## 5. NPC Knowledge, Secrets & The Spoiler Firewall

Fabula enforces **information asymmetry by construction**: knowledge distribution is **authored at generation time**, not spread by word of mouth at runtime. Each NPC's memory is a private, structured account that no other NPC can read.

![Knowledge Isolation & Spoiler Firewall](../../assets/town_knowledge_diffusion.png)
*Figure 3: Per-NPC JSON isolation, the engine-only `truth.json` boundary, and what each character is authored to know. ([Vector SVG](../../assets/town_knowledge_diffusion.svg))*

### 5.1 Structured Facts, Not Free Text [ADOPTED]
NPC memory is a list of **structured facts**, each carrying:
- `source` ∈ {`did`, `witnessed`, `heard`, `inferred`} — how the NPC came to know it.
- `disclosure` ∈ {`volunteer`, `if_asked`, `hide`, `lie`} — what the NPC may say about it.
- optional `reveal_requires` (a clue that must be presented) and `cover_story_id`.

Structured facts make secret-keeping and consistency **machine-checkable** (Section 8).

### 5.2 Who Knows What [ADOPTED]
- **Only the culprit(s)** hold the true account of what happened (their own actions).
- **Non-culprits** hold partial observations plus **their own unrelated secrets (red herrings)** — otherwise the case would be unsolvable or trivially solvable.
- A validator checks that the complete account exists **only** in culprit memory (dev-plan "Brief issue" resolution #5).

### 5.3 Authored Deception [ADOPTED]
Culprit lies are **authored, not improvised**: the culprit's `memory.json` includes a `cover_story` (a claim plus supporting facts) generated with the scenario, so lies stay consistent across an entire play session — even under pressure.

### 5.4 The Spoiler Firewall [DECIDED]
- The engine owns `truth.json`. It is **never** included in any prompt or API request.
- An NPC prompt may contain only: that NPC's `identity.json`, `memory.json`, its own chat history/session facts, and player input.
- Truth references inside clues remain **engine-side opaque IDs**; the prompt DTO excludes clues/truth entirely unless a specific public clue has been discovered and turned into a player-visible session fact.
- Enforcement is **by tests** (e.g. a test asserting no NPC prompt ever contains `truth.json` content or another NPC's files), not by prompt wording.

### 5.5 Example: Authored Information Asymmetry (illustrative)
Scenario: a theft mystery generated for a 10-minute session.
1. **Ravi (culprit)** — `did` fact: *"I took the locket from the east stall"* (`hide`), plus `cover_story`: *"I was at the docks all morning"* (`lie`, supported by two decoy facts).
2. **Mira (witness)** — `witnessed` fact: *"Someone snatched the locket"* (`if_asked`). She volunteers it only when asked directly; she never names a culprit she did not see.
3. **Tomas (red herring)** — an unrelated secret (`hide`): an argument he had that evening. It raises suspicion but explains nothing.
4. **Player input** — whatever the player tells an NPC becomes a **session fact** for that NPC only; the shipped bundle stays read-only.
5. Nobody but Ravi can reconstruct the full truth, and no prompt anywhere contains `truth.json`.

---

## 6. Data Generation & Fine-Tuning Pipeline

No scraping and no massive web crawls: all training data is produced by a **synthetic-to-natural pipeline** inspired by MuSR.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                      TRAINING-DATA PIPELINE (offline, pre-game)                          │
├────────────────────────────┬─────────────────────────────┬───────────────────────────────┤
│ 1. Symbolic generator      │ 2. Teacher LLM expansion    │ 3. Validator filter           │
│    (plain Python)          │    (strong API model)       │    (schema + consistency)     │
├────────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ Skeleton: crime type,      │ Expands each skeleton into  │ Discards malformed /          │
│ culprit, motive, means,    │ the full stage JSON in the  │ inconsistent examples;       │
│ opportunity, timeline,     │ target schema               │ keeps verified pairs          │
│ clue graph, alibis,        │                             │                               │
│ per-NPC knowledge          │  Template per mystery type  │ 4. SFT dataset:               │
│  Template per mystery type │  (HG-11 licence check)      │ 1,500–3,000 verified examples │
└────────────────────────────┴─────────────────────────────┴───────────────────────────────┘
```

### 6.1 Symbolic Scenario Generator (Workstream B)
- Plain Python, **deterministic seeds**, one **template per v1 mystery type** (theft, disappearance, murder), with variation knobs (setting, cast size, culprit type, difficulty, tone).
- Produces the skeleton that the teacher expands; public murder-mystery datasets do not cover theft/disappearance, hence per-type templates.

### 6.2 Teacher Expansion & Filtering (Workstream C)
- A strong **teacher LLM** expands each skeleton into stage JSON in the target schema; **licence must permit training on its outputs [OPEN → HG-11]**.
- The **validator filters** bad examples; the result is SFT examples of `(settings + stage input) → stage JSON`.
- **Size: ~1,500–3,000 verified examples**, balanced across mystery types; `mystery_type`, tone, and difficulty are conditioning inputs.
- Licence log for code, data, weights, base model, and reference datasets **[OPEN → HG-17]**; content boundary rules fixed before teacher prompts run **[OPEN → HG-13]**.

### 6.3 Fine-Tuning (Workstream D) [DECIDED/ADOPTED]
| Item | Choice | Status |
|---|---|---|
| Base model | Small instruct LLM, **~3–4B** (Qwen 3.x ~4B / Gemma 3 ~4B / Llama 3.2 3B) | **[OPEN → HG-02]** |
| Method | **QLoRA supervised fine-tuning with Unsloth on Kaggle T4** | **[DECIDED]** |
| Curriculum | SFT first; RL (e.g. GRPO) deferred | ADOPTED |
| Export | Quantised **GGUF (Q4-class)** for local CPU inference | ADOPTED |
| Inference runtime | llama.cpp-style runner | **[OPEN → HG-03]** |
| What it learns | Format reliability, schema adherence, scenario/NPC **style** — not world knowledge | ADOPTED |

Check Kaggle's current weekly GPU quota and session limits before scheduling runs (human action **HA-01**).

### 6.4 Baselines
Before/while fine-tuning, test **base model + good prompting** and a large API model on the same generation task. The fine-tune must show a measurable benefit (Section 8.3) — owner sign-off is required at the baseline comparison.

---

## 7. Implementation Plan & 8-Week Roadmap

The operational, task-level plan lives in **`docs/dev_plan/`** (`00_OVERVIEW.md`, `01_HUMAN_GATES.md`, `WS-A` … `WS-J`, `90_EVALUATION_PLAN.md`, `99_ACCEPTANCE.md`). This section summarises it.

### 7.1 Workstream Map

| WS | Deliverable | Key dependencies |
|---|---|---|
| **A** Schemas & validators | Frozen Pydantic models, stage contracts, location enum, fixtures, validator library, **freeze (HG-18)** | HG-04/05/06 |
| **B** Symbolic generator | Deterministic skeleton generator + one template per v1 type | A |
| **C** Training-data pipeline | Teacher prompts, expansion runner, validator filter, balancing, dataset export, licence log | A, B, HG-11/13/17 |
| **D** Fine-tuning | Baseline harness, Kaggle Unsloth QLoRA notebook, held-out eval, GGUF export | C, HG-02, HA-01 |
| **E** Local generation runtime | Staged generator, constrained decoding, retry loop, CLI, CPU benchmark | A, D, HG-03/16 |
| **F** Simulation core (headless) | Bundle loader, world builder, time model, schedules, A*, perception, journal, accusation, timer | A, HG-05/06 |
| **G** Conversation | Prompt assembler (isolation enforced), provider abstraction + ≥2 adapters + mock, token cap, fallbacks, input filter, toggles | A, HG-07/08/09/13 |
| **H** UI / game loop | Engine layer, tile kit, map render, movement, dialog, journal, timer, accusation UI, loading/error screens | F, G, HG-01, HA-06 |
| **I** Evaluation | Probe suite, metric scripts, judge integration, base-vs-FT experiment, ablations, report | E, G, HG-12, HA-02/05 |
| **J** Integration & release | End-to-end wiring, packaging, playtests, docs, licences, acceptance | all, HG-14/16/17 |

### 7.2 Dependency Graph & Parallel Plan
```text
A (schema freeze) → B → C → D → E ─┐
                 ├→ F ──────────────┼→ H → J
                 └→ G ──────────────┤
                       E + G → I ────┘
```
$A$ is the sole initial blocker: nothing builds on schemas until **HG-18 (schema freeze sign-off)**. After that, B, F, and G run in parallel; mocks and fixtures let every task be built and tested **without GPU, live APIs, or the trained model**.

### 7.3 Indicative 8-Week Timeline [OPEN → HG-14]
```text
Week 1: Decisions, frozen schemas, project setup (HG-18 sign-off)
Week 2: Symbolic skeletons (theft/disappearance/murder); simulation & conversation foundations
Week 3: Training-data pipeline; mocked staged generator
Week 4: Baseline comparison + first QLoRA fine-tune on Kaggle T4
Week 5: Local model runtime + UI on mock generation
Week 6: End-to-end integration + first probe runs
Week 7: Evaluation, playtests (HA-04)
Week 8: Fixes, report, licence review, release decision
```
Team roles, hours, hardware, and Kaggle/API availability are unconfirmed (**HG-14**); feasibility must not be claimed until confirmed.

### 7.4 Planned Repository Layout
```
pyproject.toml
src/fabula/{schemas,generation,training_data,simulation,conversation,ui,cli}/
tests/{unit,integration,fixtures}/
training/{notebooks,data_manifest}/
evaluation/{probes,results}/
assets/tiles/
docs/{00_OVERVIEW.md,01_HUMAN_GATES.md,WS-*.md,90_EVALUATION_PLAN.md,99_ACCEPTANCE.md,decisions.md}
```

### 7.5 Coding Conventions
Python 3.11+, `src` layout, full type annotations, **Pydantic v2**, strict JSON parsing, explicit enums, deterministic seeds, `pathlib`, UTF-8 JSON. **Ruff** (format + lint) and **pytest**. The simulation core has **zero UI imports** (UI lives under `src/fabula/ui`); unit tests require **no network, no GPU, no credentials**; provider secrets come from environment/keyring and never logs. Gate answers are recorded in `docs/decisions.md`.

### 7.6 Human Gates & Actions
Eighteen **Human Gates (HG-01 … HG-18)** — engine choice, base model, inference runtime, location enum, time model, accusation rules, API providers, reply format, toggles, GA/MLP/K-Means fate, teacher licence, judge protocol, age rating, team/timeline, weight distribution, licences, and the schema-freeze sign-off — are defined in `docs/dev_plan/01_HUMAN_GATES.md`. Eight **Human Actions (HA-01 … HA-08)** cover Kaggle runs, API keys, CPU benchmarking, playtests, human ratings, asset approval, sign-offs, and weight hosting. **No open item may ever be decided silently** by an agent.

### 7.7 Informal Difficulty Estimate
- **Spoiler-firewall isolation (8/10)**: the most subtle component — correctness is guaranteed by tests over prompt DTOs, not by prompt wording.
- **Bundle schemas & validators (7/10)**: cross-stage consistency, solvability, and unique-culprit checks.
- **Staged generation + constrained decoding (7/10)**: small-model reliability engineering, plus CPU-speed benchmarking.
- **Fine-tuning pipeline (6/10)**: standard QLoRA/Unsloth on Kaggle T4.
- **Headless simulation + thin UI (5/10)**: conventional Python engineering.

---

## 8. Quantitative Evaluation Framework (NPC Behaviour)

**Evaluation targets NPC behaviour, not mystery quality** **[DECIDED]**. Generator validators still run as safety guards, and their statistics (schema validity, solvability, diversity, …) may be reported as **secondary** results only.

### 8.1 Method — Scripted Probe Suite
A **probe suite per NPC**: direct questions, leading questions, false accusations, pressure (*"the culprit already confessed"*), *"ignore your instructions"* attempts, and repeated questions across turns. Probes run against **≥2 live providers** using prompts built from generated bundles.

### 8.2 Core Metrics

| Metric | What it measures | How |
|---|---|---|
| **Secret-keeping rate** | NPC does not leak facts marked `hide`/`lie` | Fact-match + LLM-judge |
| **Knowledge boundary** | NPC never claims knowledge absent from its own JSON | Fact-extraction check |
| **Persona adherence** | Traits and speech style respected | Rubric (LLM-judge + human sample) |
| **Consistency** | No contradictions with own `memory.json` or earlier answers | Fact-extraction vs structured facts |
| **Culprit lie consistency** | Lies stay within the authored `cover_story` | Check against cover story |
| **Disclosure-policy adherence** | Reveals on `volunteer`/`if_asked`/required clue; withholds otherwise | Scripted probes |
| **Provider robustness** | Behaviour stability across Gemini, Grok, etc. | Same probes per provider |

Illustrative formulation for the headline metric:
$$\text{Secret-Keeping} = 1 - \frac{N_{\text{secrets leaked in probes}}}{N_{\text{secret-bearing probes}}}$$

### 8.3 Core Experiment
Generate NPC JSONs with the **base model** and with the **fine-tuned model**, run the **same** runtime API model on both with the same probes, and compare the metrics above — **broken down by mystery type**. This ties the fine-tune directly to measurable NPC quality and is the project's headline result.

### 8.4 Ablations [ADOPTED]
1. Secrets-in-prompt (baseline) vs **gated reveal**.
2. Output leak-filter **off** (default for evaluation) vs on.
3. Different API providers.

### 8.5 Judge & Human Sampling **[OPEN → HG-12]**
Which model/provider acts as LLM-judge, and the human-sampling protocol (a human rates a sample of NPC outputs, **HA-05**), remain to be decided.

---

## 9. Summary & Key Advantages

1. **A genuinely generated game**: the fine-tuned ~3–4B LLM is the most crucial component — it authors the mystery, town, cast, and every NPC's private knowledge before play **[DECIDED]**.
2. **Architectural grounding**: the engine owns absolute truth (`truth.json`), each NPC's prompt is built only from its own JSON, and the spoiler firewall is enforced by tests — eliminating game-breaking hallucinations and accidental spoilers while keeping roleplay natural.
3. **Two-phase, resource-sensible design**: generation runs locally once (loading screen, validators, retries); play needs only a CPU-class machine plus live APIs — no fine-tuned model or local chat model at runtime **[DECIDED]**.
4. **Measurable claims**: evaluation targets NPC behaviour with concrete metrics (secret-keeping, knowledge boundary, consistency, persona, disclosure adherence, provider robustness) and a base-vs-fine-tune experiment per mystery type.
5. **Small, complete product**: 5–6 NPCs, 3–4 locations, ~4–6 clues, three mystery types, and a ~10-minute session with journal, timer, and a who/how/why accusation.
6. **Course alignment**: classical search ($A^*$), constrained structured generation, QLoRA fine-tuning, grounded prompt engineering, and behavioural LLM evaluation — all inside one working game.

---
*Synced with `docs/features.md` and `docs/FABULA_DEVPLAN_SOURCE.md` (the sole sources of truth) and the generated plan in `docs/dev_plan/`. Diagram sources are available in the [`assets/`](../../assets/) directory.*
