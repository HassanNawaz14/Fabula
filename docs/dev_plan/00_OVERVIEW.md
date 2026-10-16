# Fabula Development Plan — Overview

## Purpose and authority
This plan is the implementation contract for Fabula. `FABULA_DEVPLAN_SOURCE.md` is the sole product authority. `features.md` was consulted only as corroborating reference; conflicts are resolved in favor of the source brief. The plan adds engineering detail, not product scope. No product code is created by this plan.

## Architecture
Fabula has a pre-play generation phase and a play phase. Phase 1 runs a staged, fine-tuned ~3–4B model locally and writes a validated JSON bundle. Stages are world → cast → truth/clues → one identity/memory pair per NPC. Each stage has a typed input/output contract, constrained JSON decoding, validation, up to three retries by default, and a clear terminal error. Phase 2 loads the bundle read-only. A pure-Python simulation owns time, movement, perception, clues, journal state, accusations, and truth. A thin selected-engine UI renders the simulation. NPC movement uses schedules and A*. Conversation is mediated by a provider interface to live APIs only. A prompt builder receives the selected NPC's identity, memory, that NPC's chat history and session facts, and player input. It cannot accept a bundle root, truth, or another NPC's files. No local chat model or fine-tuned model is called during play.

## Repository layout (planned)
```
pyproject.toml
src/fabula/{schemas,generation,training_data,simulation,conversation,ui,cli}/
tests/{unit,integration,fixtures}/
training/{notebooks,data_manifest}/
evaluation/{probes,results}/
assets/tiles/
docs/{00_OVERVIEW.md,01_HUMAN_GATES.md,WS-*.md,90_EVALUATION_PLAN.md,99_ACCEPTANCE.md,decisions.md}
```
Exact interfaces and schema fields are frozen by WS-A before dependent modules are implemented. Keep secrets and generated artifacts out of source control.

## Shared context block (copy verbatim at the start of every coding-agent prompt)
```text
Project: Fabula, a single-player Python mystery game. Follow the task prompt and frozen contracts in docs/; source brief is not assumed available.
Non-negotiables: fine-tuned small LLM generates the complete game before play; Kaggle T4 QLoRA SFT with Unsloth; local generation; live APIs only for runtime NPC conversation; no fine-tuned model or local chat model at runtime; JSON bundle consumed by Python; 5–6 NPCs, 3–4 locations, about 4–6 clues, about 10 minutes; evaluation measures NPC behaviour.
Spoiler firewall: truth.json is engine-only and MUST NEVER enter any NPC prompt or API request. An NPC prompt may use only that NPC's own identity.json, memory.json, own chat history/session facts, and player input. Only culprit memory contains the true account. Enforce this with tests; do not rely on prompt wording.
Architecture: headless pure-Python simulation with no UI imports; thin UI; scheduled NPC movement with A*; Pydantic bundle validation; staged generation with constrained JSON, per-stage validation, max 3 retries, explicit failure.
Scope: v1 theft, disappearance, murder; fixed location-type enum; placeholder tiles; free-text player/NPC conversation via live API; journal, visible timer, accusation who/how/why. No generated art, no scraping, no runtime local chat, no GA/MLP/K-Means, no mystery-quality headline evaluation.
Conventions: Python 3.11+, src layout, type annotations, Pydantic v2, pytest, Ruff (format + lint), deterministic fixtures/seeds, pathlib, JSON UTF-8. Run `python -m pytest` and `ruff check .`; add no network/GPU requirement to unit tests.
Before dependent work, inspect docs/decisions.md and honor recorded gate answers. Never silently decide an OPEN item. For a blocked gate, stop before dependent steps, show options/default, wait, then record the answer in docs/decisions.md.
```

## Workstream map
| WS | Deliverable | Key dependencies |
|---|---|---|
| A | Frozen Pydantic schemas, stage contracts, validators, fixtures | HG-04/05/06, HG-18 |
| B | Deterministic symbolic skeleton generator and three templates | A |
| C | Licensed teacher expansion and training-data pipeline | A, B, HG-11/13/17 |
| D | Baselines and Kaggle T4 QLoRA training/export | C, HG-02, HA-01 |
| E | Local staged generation CLI and inference adapter | A, D, HG-03/16 |
| F | Headless simulation | A, HG-05/06 |
| G | Isolated live-API conversation | A, HG-07/08/09/13 |
| H | Thin game UI and interaction loop | F/G, HG-01, HA-06 |
| I | NPC probe suite, metrics, experiments | E/G, HG-12, HA-02/05 |
| J | Integration, packaging, playtest, licensing, release | all, HG-14/16/17, HA-03/04/07/08 |

## Dependency graph and parallel plan
```text
A (schema freeze) → B → C → D → E ─┐
                 ├→ F ──────────────┼→ H → J
                 └→ G ──────────────┤
                       E + G → I ────┘
```
A is the sole initial blocker. After HG-18 sign-off, B, F, and G can start independently; E can begin with mock model output after A and finalize with D/HG-03/HG-16. C follows A+B. D follows C. H uses mock generation and mock providers. I uses deterministic fixtures and mock providers in CI, then live providers for the authorized experiment. J integrates all deliverables.

## Milestones and indicative timeline
Indicative eight weeks, subject to HG-14 and real Kaggle/API availability: W1 decisions, schemas, project setup; W2 skeletons, simulation and conversation foundations; W3 data pipeline and mocked generator; W4 baseline and first fine-tune; W5 local model runtime and UI; W6 integration and initial probes; W7 evaluation and playtests; W8 fixes, report, license review, release decision. Do not claim timeline feasibility until roles, hours, hardware and quota are confirmed.

## Coding conventions
Use Python 3.11+, Pydantic v2, strict JSON parsing, explicit enums/literals, typed public functions, small modules, deterministic seeded tests, and no import-time network/GPU work. Ruff is the formatter/linter and pytest the test runner. Keep UI imports under `src/fabula/ui`; imports from `fabula.simulation` must work without Pygame/Arcade installed. Provider secrets come from environment/keyring and never logs. Bundle contents are immutable during play. `docs/decisions.md` records gate ID, decision, date, rationale, and affected contract/version. CI must run without credentials, network, GPU, or model weights.

## Brief issues
1. **Stage inventory mismatch:** flow says world → cast → truth → per-NPC files, but bundle also has `clues.json`. Proposed resolution: truth stage emits `truth.json` and `clues.json` as a single atomic output pair, both validated together.
2. **Solvability versus player options:** clue `implies` can reference fact/truth, while HG-06 asks how/how why choices are authored. Proposed resolution: freeze explicit solution option IDs and clue-to-solution evidence links in WS-A after HG-06; keep prose options for display, stable IDs for engine checking.
3. **Time semantics:** `schedule.at_minute` is incompatible with a purely eventless tick clock unless mapped. Proposed resolution: recommend one-minute simulation ticks driven by monotonic real time, pause only when window loses focus if approved; WS-A must encode chosen semantics.
4. **Mystery type `random` versus generated type:** settings allow `random`, but bundle mystery type must be concrete. Proposed resolution: random is an input-only setting resolved to one of the three v1 types and recorded concretely in output.
5. **NPC fact and secret consistency:** “only culprit(s) know what actually happened” must coexist with witnesses and clues. Proposed resolution: non-culprits may know partial observations and unrelated secrets, never the complete true account; validator checks the culprit-only account representation.
6. **Five or six NPCs / three or four locations / four to six clues:** precise bounds are not explicit. Proposed resolution: inclusive bounds in schema validators, with deterministic fixture at minimum and maximum.
7. **`truth.json` reference exposure:** clues may cite `truth_ref`, which could accidentally be passed to prompts. Proposed resolution: truth references remain engine-side opaque IDs; prompt DTO excludes clues/truth entirely unless a specific public clue has been discovered and represented as a player-visible session fact.
8. **Performance target:** “low-end machine” and estimated latency have no hardware definition. Proposed resolution: HG-16 selects minimum CPU/RAM/distribution, then HA-03 captures actual generation time and peak memory against that profile.
9. **Feature reference claims authority:** `features.md` labels itself authoritative, while the requested agent prompt and source brief designate the source brief as sole source of truth. Proposed resolution: for this deliverable only, follow the explicit user hierarchy and use `features.md` as reference.
