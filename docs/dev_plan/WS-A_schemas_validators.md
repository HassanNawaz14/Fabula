# WS-A — Schemas and Validators

### A-01 Freeze bundle schemas and stage contracts
Goal: Specify versioned Pydantic models and exact input/output for every generation stage. Depends on: none. Inputs: source brief vocabulary and decisions. Outputs: `src/fabula/schemas/{world,truth,clues,npc,bundle,stages}.py`, `docs/contracts/schema-v1.md`. Steps: resolve HG-04/05/06; define bounds, IDs, enums, schema version, stable accusation IDs, evidence references and paths; contracts settings→world, world→cast, world+cast→truth+clues atomically, world+cast+truth/clues+npc_id→only selected NPC identity/memory; define time/perception; no truth/other-NPC fields in prompt DTO. Tests: examples round-trip and invalid bounds/refs reject. HUMAN GATE / HUMAN ACTION: HG-04/05/06; no default for HG-06; stop and record choices before freeze.
Coding-agent prompt:
```text
Project: Fabula Python mystery game. Follow task prompt and frozen docs; source brief unavailable.
Non-negotiables: fine-tuned small LLM generates full game before play; Kaggle T4 QLoRA SFT Unsloth; local generation; live APIs only for NPC chat; no fine-tuned or local chat model at runtime; JSON bundle; 5–6 NPCs, 3–4 locations, 4–6 clues, ~10 minutes; evaluate NPC behavior.
Firewall: truth.json engine-only, never in any NPC prompt/API request. Prompt may use only selected NPC identity/memory, own history/session facts and player input. Only culprit knows full true account. Enforce with tests.
Architecture: headless Python core, thin UI, scheduled movement+A*, Pydantic, staged constrained JSON, per-stage validation and max 3 retries. Scope v1 theft/disappearance/murder; no scraping, generated art, runtime local chat or GA/MLP/K-Means. Python 3.11+, pytest, Ruff, offline fixtures.
Task: Freeze complete schemas and stage contracts as specified in this task. Stop at unresolved HG-04/05/06 and record decisions. Acceptance: typed schemas and stage DTOs; clue/truth cross refs; accusation stable IDs; no truth/other-NPC fields in NPC prompt DTO.
```

### A-02 Validators and fixtures
Goal: Validate each stage and bundle integrity. Depends on A-01/HG-18. Inputs: frozen schemas. Outputs: `src/fabula/schemas/validators.py`, fixtures and tests. Steps: implement schema parse, cross refs, connected graph, timeline consistency, unique culprit set and concrete solvability evidence chain; stable issue codes. Tests: valid fixtures pass; each invalid fixture fails expected code. HUMAN GATE / HUMAN ACTION: HG-18/HA-07.
Coding-agent prompt:
```text
Project: Fabula Python mystery game. Obey approved schema v1.
Non-negotiables: pre-play fine-tuned local generator; live APIs only for runtime NPC conversation; no local chat model; truth.json and other NPC files never enter an NPC prompt. Python 3.11+, Pydantic v2, pytest/Ruff, deterministic offline fixtures.
Task: Implement full stage/bundle validators and fixtures. Do not change frozen contracts; propose versioned migration if needed. Acceptance: references, connectivity, timeline, unique culprit and solvability produce stable codes; tests run offline.
```
