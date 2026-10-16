# WS-B — Symbolic Scenario Generator

### B-01 Seeded skeleton templates
Goal: Generate deterministic skeletons for theft, disappearance and murder. Depends on A-01/A-02. Inputs: frozen schemas and validators. Outputs: `src/fabula/training_data/skeletons/{models,common,theft,disappearance,murder}.py`, tests. Steps: create culprit/motive/means/opportunity/timeline/evidence graph/alibis/red herrings/partial NPC knowledge; enforce counts; same seed same normalized output; only culprit has complete account. Tests: 100 seeds/type validate and diversity asserted. HUMAN GATE / HUMAN ACTION: none.
Coding-agent prompt:
```text
Project: Fabula Python mystery game. Follow frozen contracts in docs.
Non-negotiables: fine-tuned small LLM generates complete game before play; Kaggle T4 QLoRA SFT Unsloth; runtime NPC chat only through live APIs; no local chat model; 5–6 NPCs, 3–4 locations, 4–6 clues. truth.json never enters prompts; NPC files are isolated. No scraping.
Conventions: Python 3.11+, Pydantic v2, deterministic seeds, pytest, Ruff, no GPU/network in unit tests.
Task: Implement symbolic skeleton templates for all three v1 mystery types. Acceptance: 100 seeds/type validate; same seed is identical, different seeds vary, only culprit skeleton has full account.
```

### B-02 Balanced skeleton export
Goal: Export reproducible validated skeleton JSONL and provenance manifest. Depends on B-01. Inputs: skeleton generator/validators. Outputs: `src/fabula/training_data/build_skeleton_dataset.py`, tests and README. Steps: variation knobs; balance type/tone/difficulty; atomic UTF-8 JSONL; record seeds/config/validation; reject invalid rows. Tests: repeatability and reconciled counts. HUMAN GATE / HUMAN ACTION: HG-13/17 before reference material.
Coding-agent prompt:
```text
Project: Fabula Python mystery game; follow approved frozen contracts. Pre-play fine-tuned generator; live API NPCs only; no local chat at runtime; no scraping. Isolate NPC knowledge and keep truth out of prompts. Use typed Python, pytest/Ruff, offline deterministic fixtures.
Task: Add balanced skeleton dataset export. Acceptance: same seed/config creates identical JSONL and manifest; invalid rows fail with line diagnostics; counts reconcile.
```
