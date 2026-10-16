# WS-C — Training Data Pipeline

### C-01 Training policy and teacher prompts
Goal: Define stage prompts and license/provenance controls without calling a teacher. Depends on A-01/B-01. Inputs: frozen contracts, HG-11/13/17. Outputs: `training/prompts/{world,cast,truth_clues,npc}.md`, manifest schema, `docs/training-data-policy.md`. Steps: map inputs to exact target JSON; require faithful IDs, partial nonculprit knowledge, culprit cover story and approved content boundary; track source/license/terms/model/seed/schema; block unclear sources. Tests: manifest rejects missing rights state; NPC stage inputs exclude truth. HUMAN GATE / HUMAN ACTION: HG-11/13/17.
Coding-agent prompt:
```text
Fabula: complete game generated before play by fine-tuned small LLM; runtime NPC voice uses live APIs only; no local chat. Structured isolated NPC files; truth.json never enters NPC prompts. Follow frozen schema. Use Python/docs, deterministic offline tests; no scraping or teacher calls without approval.
Task: Create stage-specific teacher prompts and provenance/license policy. Acceptance: each prompt maps exact stage schema; manifest records rights and model provenance; truth and other NPC files are excluded from NPC-stage inputs.
```

### C-02 Teacher expansion and validator filter
Goal: Expand approved skeletons and retain only validated examples. Depends on C-01/B-02/A-02. Inputs: approved teacher, keys/spend (HA-02), prompts and skeletons. Outputs: `src/fabula/training_data/{teacher,expand,filter}.py`, tests. Steps: protocol+mock; explicit live opt-in; resumable stage checkpoints; validate every stage and bundle; target 1,500–3,000 verified examples balanced by type; provenance required. Tests: mock resume, invalid rejection, no credential dependency. HUMAN GATE / HUMAN ACTION: HG-11/13/17, HA-02.
Coding-agent prompt:
```text
Fabula training data uses symbolic skeleton→licensed teacher expansion→validator filter. Never scrape. Fine-tune is pre-play only; runtime NPCs use live APIs and isolated per-NPC files. Frozen Pydantic contracts apply.
Task: Implement resumable teacher expansion and validation filter with mock default and explicit live opt-in. Acceptance: fixture pipeline resumes, rejects invalid rows, records provenance, and does not call a teacher absent approvals/credentials.
```

### C-03 SFT export and audit
Goal: Produce balanced stage-specific SFT records and leakage-safe splits. Depends on C-02. Inputs: validated expansions/license ledger. Outputs: `src/fabula/training_data/export_sft.py`, tests, training README. Steps: split by scenario seed; export settings+stage input→stage JSON; counts by type/tone/difficulty/stage; enforce rights and prevent truth in NPC stage input. Tests: deterministic export, disjoint splits, unauthorized records fail closed. HUMAN GATE / HUMAN ACTION: HG-11/17.
Coding-agent prompt:
```text
Fabula uses licensed synthetic-to-natural SFT data and frozen staged JSON contracts. Do not scrape or leak truth/other NPC data into NPC stage inputs. Use deterministic Python/pytest/Ruff.
Task: Implement audited SFT export. Acceptance: repeatable seed-based disjoint splits; provenance and rights required; counts reconcile; NPC inputs have no truth or other NPC content.
```
