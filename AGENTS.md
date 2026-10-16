# Project Memory & Agent Operational Rules

## 1. Documentation Architecture & Sources of Truth
- **Sole sources of truth**: `docs/features.md` (product & feature specification) and `docs/FABULA_DEVPLAN_SOURCE.md` (dev-plan source brief). The development plan in `docs/dev_plan/` is generated from them and is up to date.
- **Synced documents** (derived, never authoritative): `README.md`, `docs/md/DOCUMENTATION.md`, and the diagrams in `assets/`. When a product question arises, consult the truth files first; on conflict, **the truth files win**.
- `docs/md/`: Markdown documentation (`DOCUMENTATION.md`) — designed for AI models, IDE previews, and fast contextual reading.
- `docs/latex/`: Academic LaTeX source and deliverables (`main.tex`, `main.pdf`, `.aux`, `.toc`) — designed strictly for the human user and academic submission.

---

## 2. STRICT PROHIBITION: Never Open or Read the `docs/latex/` Folder
- **RULE**: The AI assistant must **NEVER** open, view, grep, or inspect files inside `docs/latex/` (`docs/latex/main.tex`, etc.).
- **RATIONALE**: The LaTeX report currently reflects the **previous (pre-sync) edition** of the project description until the user explicitly regenerates it; opening it anyway would only waste context tokens on LaTeX boilerplate.
- **WORKING DOCUMENT**: For architecture and documentation, read `docs/md/DOCUMENTATION.md`; for product decisions (scope, features, architecture choices), read `docs/features.md` / `docs/FABULA_DEVPLAN_SOURCE.md`.
- **LATEX COMPILATION**: Files in `docs/latex/` are strictly for the user's formal submission and should only be updated or compiled if the user explicitly gives a direct instruction to modify or recompile the LaTeX files. Build logs (`*.log`) are always removed after compiling.

---

## 3. General Project Context
- **System**: **Fabula** — a small, single-player Python mystery game (kind-of-open world): **5–6 NPCs**, **3–4 named locations**, ~**4–6 clues**, **~10-minute** session; v1 mystery types **theft, disappearance, murder** (solution shape: who / how / why).
- **Two phases [DECIDED]**:
  - *Generation (before play, local)*: a **fine-tuned ~3–4B LLM** (QLoRA SFT, Unsloth, Kaggle T4) staged-generates a validated JSON bundle (`world.json`, `truth.json`, `clues.json`, `npcs/<id>/identity.json` + `memory.json`) with constrained decoding and per-stage validators.
  - *Play (~10 min)*: the Python engine builds the world from JSON; the fine-tuned model **never** runs at runtime, and NPC conversation uses **live APIs only** (no Ollama/local chat model).
- **Hybrid AI Architecture**:
  - *The Body (classical AI)*: simplified NPC schedules + $A^*$ pathfinding, perception, engine rules, journal/timer/accusation — a headless pure-Python core with **zero UI imports** (thin Pygame/Arcade UI on top, engine choice open).
  - *The Voice (live API)*: prompt assembler builds each NPC's prompt **only** from that NPC's `identity.json`, `memory.json`, and chat history; provider abstraction (≥2 providers), ≈2–3 s latency, per-session token cap, canned fallback lines.
- **Spoiler firewall [DECIDED]**: `truth.json` is engine-only and must never enter any prompt or API call; per-NPC isolation is **enforced by tests**, not prompt wording. Only culprit(s) hold the true account; lies are authored `cover_story`s.
- **Evaluation [DECIDED]**: targets **NPC behaviour** (secret-keeping, knowledge boundary, persona adherence, consistency, culprit-lie consistency, disclosure adherence, provider robustness) via probe suites and a base-vs-fine-tune experiment — **not** mystery quality.
- **Explicitly not in MVP**: GA planner, MLP action classifier, K-Means clustering (HG-10 default: skip), generated art, scraping, runtime local chat.
- **Repository Cleanliness**:
  - Root contains `README.md`, `AGENTS.md`, `.gitignore`, `.agents/`, `assets/`, and `docs/`.
  - `assets/` holds the three current diagram pairs (`system_architecture`, `decision_engine_dispatch`, `town_knowledge_diffusion`) in SVG + 2× PNG; PNGs are regenerated from the SVGs (headless Chrome at 2× scale).
  - LaTeX build logs (`*.log`) must always be removed after compiling.
