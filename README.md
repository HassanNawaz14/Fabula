# Fabula: AI-Generated Mystery Game (Fine-tuned LLM + Live-API NPCs)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Fine-tuned Generator](https://img.shields.io/badge/LLM-QLoRA%20Fine--tuned%20Generator-orange.svg)]()
[![Live API Voice](https://img.shields.io/badge/Runtime-Live%20APIs%20Only-pink.svg)]()
[![Session Scale](https://img.shields.io/badge/Scale-5%E2%80%936%20NPCs%20%C2%B7%20~10%20min-green.svg)]()

> A small, single-player **Python mystery game** where every NPC is AI-controlled: a **fine-tuned small LLM generates the entire game before play** (mystery, town, cast, and each NPC's private knowledge and identity), a headless Python engine brings it to life, and **live APIs** give each NPC its voice — grounded strictly in that NPC's own JSON files.

---

## 📖 Full Technical Documentation
For the complete technical breakdown including architecture, schemas, prompts, evaluation metrics, and the implementation plan:

- 📄 **Markdown Technical Docs (for AI / Reading)**: **[docs/md/DOCUMENTATION.md](docs/md/DOCUMENTATION.md)**
- 📕 **Academic PDF Report**: **[docs/latex/main.pdf](docs/latex/main.pdf)**
- 📐 **LaTeX Source (for User / TeX Compilation)**: **[docs/latex/main.tex](docs/latex/main.tex)**
- 🧭 **Product Specification (single source of truth)**: **[docs/features.md](docs/features.md)** · **[docs/FABULA_DEVPLAN_SOURCE.md](docs/FABULA_DEVPLAN_SOURCE.md)**
- 🗂️ **Development Plan (generated)**: **[docs/dev_plan/](docs/dev_plan/)**

> **Documentation status:** `docs/features.md` and `docs/FABULA_DEVPLAN_SOURCE.md` are the sole sources of truth; everything else is synced to them. The LaTeX report still reflects the previous (pre-sync) edition and is regenerated only on explicit request.

---

## 🏛️ System Architecture
The game runs in two phases — **generation** (local, before play) and **play** (~10 minutes):

- **Phase 1**: player settings (`mystery_type`, `tone`, `difficulty`) → the fine-tuned ~3–4B LLM generates the bundle in stages (`world → cast → truth → per-NPC files`) with constrained JSON decoding → validators + retries → a JSON game bundle on disk.
- **Phase 2**: the engine builds the world from `world.json`; NPCs move via **schedules + A\***; NPC conversation goes through **live APIs only**, with prompts assembled from that NPC's own `identity.json` + `memory.json`; `truth.json` stays engine-only.

![System Architecture: Generation & Play](assets/system_architecture.png)

- **Vector SVG**: [assets/system_architecture.svg](assets/system_architecture.svg)
- **High-Res PNG (2x)**: [assets/system_architecture.png](assets/system_architecture.png)

---

## 🎨 Clean Engineering Diagrams

All diagrams are designed with a minimalist light theme (simple boxes, clear arrows, zero clutter) and available in PNG and SVG formats:

| # | Diagram Title | Where Used | Formats |
|---|---|---|---|
| **01** | **[System Architecture: Generation & Play](assets/system_architecture.png)** | Section 3: Phase 1 staged generation + Phase 2 play loop | [PNG](assets/system_architecture.png) • [SVG](assets/system_architecture.svg) |
| **02** | **[Runtime Dispatch: Body & Voice](assets/decision_engine_dispatch.png)** | Section 4: How an NPC turn routes to schedule + $A^*$ or prompt assembler + live API | [PNG](assets/decision_engine_dispatch.png) • [SVG](assets/decision_engine_dispatch.svg) |
| **03** | **[Knowledge Isolation & Spoiler Firewall](assets/town_knowledge_diffusion.png)** | Section 5: Per-NPC knowledge and the engine-only `truth.json` boundary | [PNG](assets/town_knowledge_diffusion.png) • [SVG](assets/town_knowledge_diffusion.svg) |

---

## ⚙️ How It Works

### Phase 1 — Generation (local, before play)
1. **Player settings**: `mystery_type` (theft / disappearance / murder / random), `tone` (cozy ↔ dark), `difficulty`.
2. **Staged generation**: the fine-tuned ~3–4B LLM emits `world → cast → truth (+clues) → per-NPC files` with grammar / JSON-schema-constrained decoding.
3. **Validation**: every stage is checked (schema, cross-references, graph connectivity, timeline, solvability, unique culprit) and retried up to 3 times; persistent failure shows a clear error screen.
4. **Bundle on disk**: `world.json`, `truth.json` (engine-only), `clues.json`, and `npcs/<id>/identity.json` + `memory.json`.
5. Everything runs on the player's machine — **the fine-tuned model never runs during play**.

### Phase 2 — Play (~10 minutes)
1. **World**: the engine loads the bundle read-only and builds the town (3–4 locations from a fixed type enum → placeholder tiles).
2. **Body**: NPCs follow simplified schedules using $A^*$ pathfinding and perceive events only in their own location.
3. **Player loop**: walk, examine ~4–6 clues, type free-text questions to 5–6 NPCs, watch the visible timer.
4. **Voice**: each reply comes from a live API whose prompt contains only that NPC's `identity.json`, `memory.json`, and chat history — `truth.json` never leaves the engine (enforced by tests).
5. **Verdict**: the journal records clues; the player accuses **who / how / why**; the engine checks the accusation against `truth.json` → win or lose.

---

## 🚀 8-Week Implementation Roadmap

```text
Week 1: Decisions, frozen schemas, project setup (schema-freeze sign-off)
Week 2: Symbolic skeletons (theft/disappearance/murder); simulation & conversation foundations
Week 3: Training-data pipeline; mocked staged generator
Week 4: Baseline comparison + first QLoRA fine-tune on Kaggle T4
Week 5: Local model runtime + UI on mock generation
Week 6: End-to-end integration + first probe runs
Week 7: Evaluation, playtests
Week 8: Fixes, report, licence review, release decision
```

> **Compute requirements**: generation runs on the player's CPU (with a loading screen); fine-tuning runs on free Kaggle T4 GPUs (QLoRA + Unsloth); play needs only live-API keys — no local model at runtime.
