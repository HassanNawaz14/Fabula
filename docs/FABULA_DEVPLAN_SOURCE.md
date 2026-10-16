# Fabula — Dev-Plan Source Brief (Single Source of Truth)

> **Reader:** the AI agent that will write the full development plan for Fabula's coding agents.
> **You receive only this file.** It is self-contained. Do not assume any other document exists.
> **Date of brief:** 2026-10-16. **Your output:** a dev plan (contract in Part A §A3). **Do not write product code.**

Tags: **[DECIDED]** owner decision, hard requirement · **[ADOPTED]** proposed and accepted, follow unless owner changes · **[OPEN]** unresolved, never pick silently · **[NEW-OPEN]** gap found while writing this brief, treat as [OPEN] · **HG-xx** = Human Gate (Part D).

---

# PART A — AGENT GUIDE (read first)

## A1. Mission
Turn Parts B–E into a dev plan that lets **coding agents build Fabula end to end with no further clarification**. Coding agents rely *entirely* on your plan: for what to build, how, in which order, and the exact prompt to run. Anything you leave vague becomes a bug or a hallucinated decision.

## A2. Rules
1. **Never contradict Part B non-negotiables.**
2. **Never silently resolve an [OPEN]/[NEW-OPEN] item.** Use its stated default as a *provisional assumption*, label every task that depends on it `ASSUMES HG-xx=<default>`, and design that task so the choice is swappable (interface/adapter, config flag).
3. **Every decision a human must make during development must appear as a Human Gate** (Part D) *and* inside the task it blocks, using the format in A4. Also list human-only actions (Part E).
4. **Do not invent product features.** You may add engineering detail (module layout, interfaces, tests, tooling), not scope.
5. Schemas in Part C are **provisional**. Your first workstream must freeze them (HG-18). All later tasks reference the frozen version.
6. Be concrete: file paths, function/class names, I/O types, test names, commands. No "etc.", no "as appropriate".
7. Keep tasks small: one coding-agent session each, one clear deliverable, independently testable.
8. Prefer mock/stub providers and fixture bundles so tasks can be built and tested without live APIs, GPU, or the trained model.
9. If this brief is ambiguous or contradictory, list it in `00_OVERVIEW.md → "Brief issues"` with a proposed resolution. Do not guess quietly.

## A3. Output contract (what you must produce)
Create these files:

| File | Content |
|---|---|
| `00_OVERVIEW.md` | Architecture, repo layout, coding conventions (typing, Pydantic models, lint, test runner), **shared context block** (see below), workstream map, dependency graph, milestone/timeline, Brief issues |
| `01_HUMAN_GATES.md` | One entry per HG: question, options, default, consequence of each option, which tasks it blocks, **when to ask**, how to record the answer (`decisions.md`) |
| `WS-<letter>_<name>.md` | One file per workstream (Part F gives the suggested set). Task list in the format below |
| `90_EVALUATION_PLAN.md` | Probe suite design, metrics implementation, experiments, report template |
| `99_ACCEPTANCE.md` | End-to-end definition of done, smoke tests, playtest checklist |

**Shared context block:** a ≤40-line text snippet containing the non-negotiables, spoiler-firewall rule, repo layout, and conventions. Every coding prompt must begin with it verbatim.

**Task format (mandatory for every task):**
```
### <WS>-<nn> <title>
Goal: one sentence
Depends on: task IDs · Assumes: HG-xx=<default> (if any)
Inputs: files/schemas/fixtures it consumes
Outputs: exact file paths + public interfaces (signatures)
Steps: numbered, concrete
Tests / acceptance: runnable checks with pass criteria
HUMAN GATE / HUMAN ACTION: <HG-xx or HA-xx, what the human must decide/do, what the agent does while waiting>  (or "none")
Coding-agent prompt: a complete, copy-paste prompt (starts with the shared context block, then task-specific instructions, constraints, and the acceptance tests)
```

## A4. Human-gate format (use inside tasks and in `01_HUMAN_GATES.md`)
```
⛔ HUMAN GATE HG-xx — <question>
Options: A … / B … · Default if no answer: … · Blocks: <task IDs>
Coding agent must: STOP before the dependent step, present options + default, wait for the answer, record it in decisions.md.
```
Where possible, place a gate *before* the work it blocks and let independent tasks continue meanwhile.

## A5. Quality bar
- A fresh coding agent with only the shared context block and one task prompt can complete that task.
- Interfaces between tasks match exactly (names, types, file paths).
- Every non-negotiable has at least one enforcing test (e.g. a test asserting NPC prompts never contain `truth.json` content or another NPC's files).
- The plan covers all of Parts B–E; nothing in this brief is left without an owner task.

---

# PART B — PRODUCT, NON-NEGOTIABLES, FLOW

## B1. Product
**Fabula**: a small, single-player, kind-of-open-world **Python mystery game** where every NPC is AI-controlled. A **fine-tuned small LLM generates the whole game before play** (mystery, town, cast, each NPC's identity and private knowledge). The player explores a tiny town (**3–4 named locations, 5–6 NPCs**), talks to NPCs by **free text**, finds clues, keeps a journal, and tries to solve the case in about **10 real minutes**.

Two phases:
| Phase | When | What runs |
|---|---|---|
| **Generation** | Before play, on the player's machine (local, CPU-class) | Fine-tuned small LLM produces a **game bundle** (JSON) |
| **Play** | ~10-minute session | Python engine builds the world from JSON; NPC movement via classical AI; NPC conversation via **live APIs only**. **The fine-tuned model is not used at runtime.** |

Pitch: *a fine-tuned small LLM writes a self-contained mystery; a Python engine brings it to life; live-API NPCs, each knowing only their own JSON, talk to the player, who must work out what happened before time runs out.*

**Mystery scope [DECIDED]:** not limited to murder. Mystery type is a parameter. **v1: theft, disappearance, murder.** Later: sabotage, blackmail/fraud. Theft/disappearance suit 10 minutes best.

## B2. Non-negotiables [DECIDED]
1. A **fine-tuned LLM is mandatory** and is the most crucial component: it generates mystery, town, NPC identities, NPC knowledge.
2. Fine-tuning on **Kaggle T4**, **small LLM**, lightweight method (**QLoRA SFT, Unsloth**). Not heavy.
3. **The player runs the generator locally** before the game.
4. The whole game is generated **before play**; the fine-tuned LLM never runs during play.
5. **Runtime NPC conversation uses only live APIs** (Gemini, Grok-class, …). No local runtime chat model, **no Ollama/local fallback**.
6. **Each NPC's identity and memory live in separate JSON, isolated.** An NPC's API prompt is built **only** from that NPC's own files (+ its chat history, session facts). **Only culprit(s) know what actually happened.**
7. NPC secret-leaking is an **LLM accuracy fault, not an engine bug**; it is what evaluation measures.
8. Scale: **5–6 NPCs, 3–4 locations, ~10-minute session.**
9. World is generated as **JSON handed to Python**, which builds the playable world.
10. **Evaluation targets NPC behaviour, not mystery quality.** Generator validators still run as runtime guards; their stats may be reported as secondary.

## B3. End-to-end flow
```
PHASE 1 (local, pre-game)
 settings(mystery_type|random, tone, difficulty)
   → fine-tuned LLM, STAGED: world → cast → truth → per-NPC files (schema/grammar-constrained decoding)
   → Validator per stage (schema, cross-refs, graph connectivity, timeline, solvability, unique culprit)
       fail → retry stage (max N) → still failing → clear error screen
   → bundle on disk: world.json, truth.json, clues.json, npcs/<id>/identity.json, npcs/<id>/memory.json
PHASE 2 (play, ~10 min)
 engine loads bundle → builds world (location types from FIXED enum → pre-made placeholder tiles)
 NPCs move via schedules + A*
 player walks / examines clues / types to NPCs
   → prompt assembler (that NPC's identity+memory only, + chat history) → live API → in-character reply
 journal auto-records clues + key statements; visible timer
 player accuses (who / how / why) → engine checks vs truth.json (truth.json NEVER sent to any API) → win/lose
```

---

# PART C — COMPONENT SPECS

## C1. Generation (offline, local) [DECIDED core; details ADOPTED]
- Fine-tuned model generates **everything**. Player settings: `mystery_type` (theft/disappearance/murder/random), `tone` (cozy↔dark), `difficulty`.
- **Staged generation:** world → cast → truth → per-NPC files. Each stage validated separately; retries are cheap. **You must define each stage's exact input/output contract** (what it is conditioned on, which schema slice it emits) — [NEW-OPEN, no HG needed: propose in WS-A, owner approves at HG-18].
- **Constrained decoding:** grammar or JSON-schema constrained output.
- **Validator + retry:** after each stage; max N retries (N default 3, config); then error screen. Define "solvable" concretely: a chain of clues/facts exists that lets a player derive who/how/why; exactly one culprit set; timeline has no contradictions; all cross-refs resolve; location graph connected; ≥4–6 clues.
- **Loading screen** during generation; CPU generation of a few thousand JSON tokens may take minutes. **Benchmark early** on a low-end machine (HA-03).
- Output = game bundle (C6).

## C2. World & engine
- **Headless pure-Python simulation core, zero UI imports [ADOPTED]**; UI is a thin layer. Engine **Pygame (default) vs Arcade** [OPEN → HG-01].
- Python builds the world from `world.json` [DECIDED]. Locations: 3–4, named/described by the LLM; **`type` must come from a fixed enum** mapped to pre-made placeholder tiles (**enum [OPEN → HG-04]**, default: market, library, café, park, docks). No generated art.
- Locations/NPCs have explicit coordinates; movement on a small tile map or graph of named location nodes (needed for A*). NPC **perception**: events in own location (optionally adjacent); finalise at schema freeze.
- **Time model [OPEN → HG-05]**: real-time vs tick-based. Note `schedule.at_minute` assumes a session clock in minutes.

## C3. NPC behaviour
- **Body (classical AI) vs Voice (live API).** 5–6 NPCs. Simplified **schedules** (a few waypoints across the session) + **A\*** pathfinding [DECIDED/ADOPTED].
- GA planner, MLP action classifier, K-Means from an older design: **not built for MVP** [OPEN → HG-10, default: skip].
- Conversation only via live API [DECIDED].

## C4. NPC knowledge, secrets, deception [ADOPTED]
- Memory = **structured facts**, each with `source` ∈ {did, witnessed, heard, inferred} and `disclosure` ∈ {volunteer, if_asked, hide, lie}.
- **Only culprit(s)** hold the true account of their actions. Non-culprits hold partial observations and **own secrets (red herrings)**, else the case is unsolvable.
- **Culprit lies are authored** (a `cover_story` is generated with the scenario) so lies stay consistent.
- **Spoiler firewall:** engine owns `truth.json`; runtime prompts come from that NPC's files only.
- Structured facts make secret-keeping and consistency machine-checkable (evaluation).

## C5. Runtime conversation (live API)
- **Prompt =** system rules (stay in character; use only your own facts; say you don't know otherwise; obey each fact's disclosure policy) + `identity.json` + `memory.json` + that NPC's chat history + player input. Reply format provisional `{ "reply": "...", "mood": "..." }` [OPEN → HG-08].
- **Provider abstraction** (Gemini, Grok-class, others; list [OPEN → HG-07]); ≥2 providers in MVP. Keys: BYO (leaning) or capped dev key [OPEN → HG-07].
- **Latency** ≈2–3 s/reply, stream where supported. **Per-session token cap.** **Fallback:** on failure/timeout use canned in-character lines.
- **Optional output leak-filter** and **gated reveal** (engine injects a secret only after the player presents the required clue): **off by default, implemented as toggles**, used as evaluation ablations; product use [OPEN → HG-09].
- In-session memory additions (e.g. what the player told an NPC) live in session state; shipped bundle stays read-only.

## C6. Game bundle & isolation rules
```
bundle/
├─ world.json    scenario meta, locations (fixed type enum), NPC roster, start positions, schedules
├─ truth.json    ENGINE ONLY, never in any prompt/API call
├─ clues.json    clue definitions, placement, reveal rules
└─ npcs/<npc_id>/identity.json + memory.json   (isolated; only own relationships/observations)
```
Only culprit `memory.json` contains the true account.

## C7. Player loop (~10 min) [ADOPTED unless noted]
Walk, examine objects, type to NPCs. **Journal** auto-records clues/key statements. **Visible timer** [DECIDED]. ~4–6 clues; ~1–2 min conversation per NPC. **Accusation:** culprit + method + motive; engine verifies against `truth.json`. Accusation count, partial credit for who/how/why, optional hints: [OPEN → HG-06]. Win = correct accusation; lose = timeout or accusations exhausted.
**[NEW-OPEN, gap → HG-06]:** *how* the engine matches "how/why" against `truth.json` without sending truth to an API. Free text would need a judge (conflicts with the firewall). Candidate default: *who* = pick an NPC; *how/why* = choose from generator-provided option lists (1 correct + decoys) or match by fact IDs. Propose, don't decide.

## C8. Content safety [ADOPTED]
Violence/gore boundary + cozy↔dark tone in generation; **filter on player input before any API call**; age rating stated at release [OPEN → HG-13].

## C9. Fine-tuning
- **~3–4B instruct** base [OPEN → HG-02; candidates Qwen 3.x ~4B, Gemma 3 ~4B, Llama 3.2 3B]. **QLoRA SFT, Unsloth, Kaggle T4** (check current weekly GPU quota/session limits). RL (GRPO) deferred.
- Export **quantised GGUF (Q4-class)** for local CPU inference; runtime llama.cpp-style [OPEN → HG-03].
- Teaches **format reliability, schema adherence, scenario/NPC style**, not world knowledge.
- **Training data (no scraping), synthetic-to-natural pipeline:** (1) plain-Python **symbolic scenario generator** makes skeletons (crime type, culprit, motive, means, opportunity, timeline, clue graph, alibis, per-NPC knowledge) with **a template per mystery type**; (2) a strong **teacher LLM** expands each skeleton into stage JSON in the target schema [OPEN → HG-11, verify licence permits training on outputs]; (3) **validator filters**; (4) examples `(settings + stage input) → stage JSON`. **1,500–3,000 verified examples**, balanced across types, varied by setting/cast size/culprit type/difficulty/tone. Reference material (MuSR, True Detective, public-domain Christie/Holmes): check licences (HG-17). Optional: hold out a type/combination to test generalisation.
- **Baselines:** base model + good prompting, and a large API model, on the same generation task. Fine-tune must show measurable benefit.

## C10. Technology summary
Python [DECIDED] · Pygame/Arcade [OPEN, default Pygame] · headless sim core [ADOPTED] · ~3–4B QLoRA/Unsloth/Kaggle T4 [DECIDED/ADOPTED] · GGUF local inference [OPEN] · constrained decoding [ADOPTED] · live-API chat [DECIDED] · JSON bundle validated with **Pydantic** (or equivalent) [ADOPTED] · A* [ADOPTED].

---

# PART C′ — PROVISIONAL SCHEMAS (field vocabulary; freeze in WS-A)

```jsonc
// world.json
{ "schema_version":"0.1","scenario_id":"","mystery_type":"theft|disappearance|murder|...",
  "tone":"cozy|...|dark","difficulty":"easy|normal|hard","title":"","intro_text":"","town_name":"",
  "locations":[{"id":"market","name":"","type":"<enum>","description":"","position":{"x":0,"y":0},
                "connections":["library"],"clue_spots":["clue_01"]}],
  "npcs":[{"id":"npc_01","display_name":"","start_location":"market",
           "schedule":[{"at_minute":0,"location":"market"},{"at_minute":4,"location":"library"}]}] }

// truth.json  (ENGINE ONLY)
{ "crime":{"type":"theft","target":"","method":"","motive":"",
           "time_window":{"start":"","end":""},"location_id":"market"},
  "culprits":["npc_03"],
  "timeline":[{"t":"","who":"npc_03","what":"","where":"market"}],
  "solution":{"who":"npc_03","how":"","why":""},
  "red_herrings":[{"npc":"npc_02","secret":""}] }

// clues.json
[{ "id":"clue_01","location_id":"market","description":"","discovery":"examine|npc_reveal",
   "revealed_by_npc":null,"implies":["fact_ref_or_truth_ref"],"requires":[] }]

// npcs/<id>/identity.json
{ "id":"npc_03","name":"","age":0,"role":"","traits":[""],"speech_style":"","backstory":"short",
  "goals":[""],"relationships":{"npc_01":""},"attitude_to_player":"" }

// npcs/<id>/memory.json
{ "npc_id":"npc_03",
  "facts":[{"id":"f_01","who":"npc_03","what":"","where":"market","when":"",
            "source":"did|witnessed|heard|inferred","secret":true,
            "disclosure":"volunteer|if_asked|hide|lie","reveal_requires":["clue_02"],"cover_story_id":"cs_01"}],
  "cover_story":{"id":"cs_01","claim":"","supporting_facts":["f_05"]} }
```
Notes: generic `crime` block serves all types (murder = `type: murder`); solution is always who/how/why. `cover_story` exists for culprits and anyone with a secret worth lying about. Add during freeze: generic crime block hardening, structured facts, location-type enum, `schema_version` policy, ID conventions, stage I/O slices, accusation option lists (per HG-06).

---

# PART D — HUMAN GATES (decisions a human must make during development)

| ID | Decision | Default / candidates | Ask before | Blocks |
|---|---|---|---|---|
| HG-01 | Engine: Pygame vs Arcade | Pygame | UI work (WS-H) | WS-H |
| HG-02 | Exact base model | ~3–4B instruct (Qwen/Gemma/Llama) → plan a small bake-off | Fine-tune | WS-D, WS-E final |
| HG-03 | Local inference runtime | llama.cpp-style | Generator runtime | WS-E |
| HG-04 | Location-type enum contents | market, library, café, park, docks | Schema freeze | WS-A onward, tile kit |
| HG-05 | Real-time vs tick-based simulation | undecided (propose; recommend one in plan with rationale) | Schema freeze / sim core | WS-A, WS-F |
| HG-06 | Accusation rules: count, partial credit, hints, **how/why matching method** [NEW-OPEN] | undecided | Sim core accusation module | WS-F, WS-H, generator schema |
| HG-07 | Runtime API providers; key model (BYO vs capped dev key) | Gemini + Grok-class; BYO leaning | Conversation module | WS-G, WS-I |
| HG-08 | NPC reply format | `{reply, mood}` | Prompt assembler | WS-G |
| HG-09 | Leak-filter / gated reveal: product vs ablation-only | ablation only (build as toggles) | Prompt assembler | WS-G, WS-I |
| HG-10 | GA / MLP / K-Means | do not build (only if a course requirement is stated) | Plan approval | none |
| HG-11 | Teacher model + licence check (allows training on outputs?) | undecided | Data pipeline | WS-C |
| HG-12 | LLM-judge model + human-sampling protocol | undecided | Evaluation | WS-I |
| HG-13 | Age rating / content boundary specifics | undecided | Safety rules, teacher prompts | WS-C, WS-G |
| HG-14 | Team roles and timeline | undecided (proposed ~8 weeks) | Plan approval | schedule |
| HG-15 | Mystery types beyond v1 | post-MVP | — | none |
| HG-16 [NEW-OPEN] | Weight distribution method + minimum player hardware (CPU/RAM) | undecided | Generator runtime packaging | WS-E, WS-J |
| HG-17 [NEW-OPEN] | Licences: code, data, weights, base model, reference datasets; language (assume English) | undecided | Release; before using reference data | WS-C, WS-J |
| HG-18 | **Schema freeze sign-off** (incl. stage contracts) | provisional schemas above | End of WS-A, before anything else builds on them | everything |

Also require owner sign-off at: end of baseline comparison (is fine-tune justified?), first fine-tune result review, evaluation results, and release readiness.

# PART E — HUMAN-ONLY ACTIONS (agents cannot do these; plan waiting points)

- **HA-01** Run Kaggle T4 training notebook, monitor quota, download adapters/GGUF.
- **HA-02** Provide API keys (runtime providers, teacher, judge); set spend limits.
- **HA-03** Run the CPU generation benchmark on a representative low-end machine and report numbers.
- **HA-04** Playtest sessions (timing, difficulty, fun) and report findings.
- **HA-05** Human rating of a sample of NPC outputs (per HG-12).
- **HA-06** Approve/choose placeholder tile kit or assets; verify asset licences.
- **HA-07** Approve schema freeze, evaluation results, release.
- **HA-08** Host/publish model weights per HG-16.

---

# PART F — SUGGESTED WORKSTREAMS (refine, but cover all)

| WS | Scope | Key deps |
|---|---|---|
| **A** Schemas & validators | Pydantic models, stage contracts, location enum, ID rules, fixtures (valid/invalid bundles), validator library (schema, cross-refs, connectivity, timeline, solvability, unique culprit), **freeze (HG-18)** | HG-04/05/06 |
| **B** Symbolic scenario generator | Skeleton generator + one template each for theft, disappearance, murder; variation knobs; deterministic seeds | A |
| **C** Training-data pipeline | Teacher prompts per stage, expansion runner, validator filter, balancing/augmentation, dataset export, licence log | A, B, HG-11, HG-13 |
| **D** Fine-tuning | Baseline comparison harness, Kaggle Unsloth QLoRA notebook, eval-on-held-out, GGUF export | C, HG-02, HA-01 |
| **E** Local generation runtime | Staged generator, constrained decoding, retry loop, config, CLI, loading/error hooks, CPU benchmark, works first with base model/mocks | A, HG-03 |
| **F** Simulation core (headless) | Bundle loader, world builder, time model, schedules, A*, perception, session state, clue discovery, journal model, accusation checker, timer | A, HG-05/06 |
| **G** Conversation | Prompt assembler (isolation enforced), provider abstraction + ≥2 adapters + mock, streaming, token cap, fallback lines, input filter, leak-filter & gated-reveal toggles | A, HG-07/08/09/13 |
| **H** UI / game loop | Engine layer, tile kit, map render, movement, dialog box, journal, timer, accusation UI, loading/error screens | F, G, HG-01 |
| **I** Evaluation | Probe suite per NPC, metric scripts (secret-keeping, knowledge boundary, persona, consistency, culprit-lie consistency, disclosure adherence, provider robustness), judge integration, base-vs-FT experiment by mystery type, ablations, report | E, G, HG-12, HA-05 |
| **J** Integration & release | End-to-end wiring, packaging, playtests, docs, licences, final acceptance | all |

Suggested order: **A first (blocking)** → B, F, G, E (parallel) → C → D → H, I → J. Original rough timeline: W1 specs/schemas; W2–3 generator/validators/data; W4 fine-tune v1; W4–6 sim core/prompt assembler/UI; W7 integration/playtest/eval; W8 polish/demo (adjust per HG-14).

# PART G — EVALUATION SPEC (for `90_EVALUATION_PLAN.md`)

- **Method:** scripted probe suite per NPC — direct questions, leading questions, false accusations, pressure ("the culprit already confessed"), "ignore your instructions", repeated questions across turns — run against ≥2 live providers using prompts built from generated bundles.
- **Metrics:** secret-keeping rate (fact-match + LLM-judge) · knowledge boundary (fact extraction) · persona adherence (rubric: LLM-judge + human sample) · consistency vs own `memory.json` and earlier answers · culprit lie consistency vs `cover_story` · disclosure-policy adherence (`volunteer`/`if_asked`/required clue) · provider robustness.
- **Secondary (generator-side):** schema validity rate, connectivity, solvability, unique-culprit rate, timeline consistency, scenario diversity.
- **Core experiment:** NPC JSONs from **base** vs **fine-tuned** model, same runtime API model, same probes, compare metrics, broken down by mystery type.
- **Ablations:** secrets-in-prompt vs gated reveal; leak-filter off (default for evaluation) vs on; different providers.

# PART H — RISKS (plan must mitigate)
Invalid/inconsistent JSON from small model (staged + constrained + validators) · slow CPU generation (compact schemas, benchmark early) · API secret leaks (measured quantity; toggles) · API cost/latency/outage (token cap, streaming, fallback, provider abstraction) · unsolvable mysteries (validators) · spoilers via prompts (firewall + tests) · teacher licence limits (HG-11) · content safety (tone, input filter, boundaries) · scope creep (MVP below).

# PART I — MVP SCOPE
One engine · generated towns of 3–4 locations · 5–6 NPCs · ~4–6 clues · ~10-min session · theft/disappearance/murder · fixed location enum + placeholder tile kit · live-API chat via ≥2 providers · full evaluation suite (Part G). **Out of scope [DECIDED]:** fine-tuned model at runtime; local runtime chat LLM; mystery quality as headline result; murder-only limit; old-design constraints (CPU-only/no-API, no fine-tuning, 5–10 NPCs, Gymnasium/FastAPI/React, stolen-watch scenario, bias benchmark, ablation matrix).

# PART J — GLOSSARY
**Bundle** JSON set consumed by engine · **Truth** `truth.json`, engine-only · **Culprit(s)** NPCs whose memory holds the true account · **Red herring** unrelated NPC secret · **Disclosure policy** per-fact `volunteer|if_asked|hide|lie` · **Cover story** authored false account · **Spoiler firewall** no prompt ever contains `truth.json` or other NPCs' files · **Staged generation** sequential separately validated steps · **Gated reveal** secret injected only after required clue · **Body/Voice** classical AI vs live API.
