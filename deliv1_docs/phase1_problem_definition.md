# Deliverable 1 — Phase 1: Problem Definition

**Project:** Fabula — AI-Generated Mystery Game (Fine-tuned LLM + Live-API NPCs)
**Deliverable:** 1 — Phase 1: Problem Definition (applies to Tracks A & B)
**Status:** Draft v0.1 — complete for review; derived from the sources of truth `docs/features.md` and `docs/md/DOCUMENTATION.md`. Owner review required before submission into the final report.

---

## 1. Problem Statement

### The pain point: AI-driven story games face a content bottleneck

Mystery and adventure games depend entirely on the coherence of their authored content: one consistent crime, a cast of characters who each *know different things*, and dialogue that never contradicts the solution. Today, studios and developers face a three-way bind:

1. **Hand-authored content is expensive, finite, and non-replayable.** A well-crafted mystery (case, suspects, alibis, clue chain) takes professional writers weeks to produce. The result is one static mystery per title: once solved, the experience is over, and generating a fresh case requires repeating the entire authoring cost.
2. **Runtime delegation to large cloud LLMs is costly, slow, and unreliable.** Wiring NPCs directly to a large model introduces per-session cost, multi-second latency, and — fatally for a mystery — no guarantee of consistency: an NPC may contradict earlier statements, claim knowledge it should not have, or simply announce the solution, destroying the game in one reply.
3. **Procedural generation historically produces broken mysteries.** Generators that shuffle templates yield contradictory timelines, unsolvable or trivially solvable cases, and characters who know things they should not know. The output is varied but not *coherent*.

What is missing is a way to produce a **fresh, coherent, solvable mystery on every run — on consumer hardware — with NPCs that stay in character, know only what they should know, and never leak the solution.**

### The proposed solution (Fabula)

Fabula moves content generation **before play** and bounds it with engineering guarantees:

- A **fine-tuned ~3–4B parameter LLM runs locally once per game**, generating the complete case — mystery, town, cast, and every NPC's private knowledge — as a set of validated JSON files (schema checks, cross-reference checks, solvability and unique-culprit checks, with automatic retries).
- A **headless Python engine owns the ground truth** (`truth.json` never leaves the engine). NPCs move via classical AI (schedules + A* pathfinding), and the ~10-minute session is bounded by a visible timer, a clue journal, and a who/how/why accusation.
- **NPC conversation runs through live APIs only**, with each NPC's prompt assembled *exclusively* from that NPC's own `identity.json` + `memory.json` (the "spoiler firewall"): only the culprit holds the true account; everyone else holds partial observations and their own red-herring secrets.

The outcome: a self-contained, replayable, spoiler-free mystery game in which the AI is the content author and the voice — while the engine keeps the rules deterministic.

---

## 2. Target Audience

### Primary users (application track)
- **Players of short mystery/puzzle games** who want a complete, fresh case in a ~10-minute session — casual mystery fans and AI-gaming enthusiasts. The barrier to play is deliberately low: a CPU-class machine for local generation plus a live-API key for conversation; no gaming rig and no prior knowledge required (each game is self-contained).
- **Indie developers and students** as a reference architecture for "pre-play generation + deterministic runtime + isolated grounding" — a reproducible pattern for building AI-driven games that are testable and spoiler-safe.

### Research gap addressed (R&D track)
While LLM-driven game agents and role-play characters are widely demonstrated, there is **no standard, machine-checkable evaluation of knowledge-isolated NPC behaviour**. Existing work rarely measures whether a character:

- **keeps secrets** it is authored to hide or lie about (secret-keeping),
- **never claims knowledge absent from its own state** (knowledge boundary),
- **stays consistent** with its structured memory and an authored cover story across turns,
- **follows disclosure policies** (volunteer / if-asked / hide / lie), and
- behaves the **same way across different live-API providers** (robustness).

Fabula fills this gap: its NPC memories are *structured facts* with explicit `source` and `disclosure` fields, making these behaviours measurable by scripted probe suites and fact-matching — and enabling a direct **base-model vs fine-tuned-model** comparison of how much fine-tuning improves them.

---

## 3. AI Justification

*Why machine learning / deep learning is necessary here — and where classical programming deliberately remains.*

### 3.1 Free-text conversation cannot be solved by rule-based parsing
The player types arbitrary natural-language questions ("Where were you when the locket disappeared?", "Why is your sleeve muddy?"). A rule-based solution requires an intent taxonomy and template responses covering every paraphrase; it breaks on open vocabulary, ambiguity, and multi-turn context. Producing fluent, in-character, context-sensitive replies for unlimited input space is exactly the problem learned language models exist for — hence a **live LLM per reply** (the project's "Voice"), with prompt grounding and disclosure policies supplied by the engine.

### 3.2 Content diversity and narrative coherence require a generative model
The pitch is that the game *feels* AI-generated: a fresh town, cast, motives, secrets, and clue chain each run. A rule-based generator can shuffle predefined templates, but it cannot author rich identities, natural backstories, or a coherent mystery narrative whose timeline, alibis, and clue graph all line up — variety of that quality requires a **generative model**. This is the project's most crucial component: the fine-tuned LLM that writes the entire game before play.

### 3.3 Small local models need fine-tuning to be reliable at structured output
Generation must run on the player's machine, so the model must be small (~3–4B parameters). Small instruct models, prompted zero-shot, routinely emit malformed or inconsistent multi-stage JSON. **QLoRA supervised fine-tuning** (on free Kaggle T4 GPUs) teaches a small model format reliability, schema adherence, and the scenario/NPC writing style — capabilities the project *measures* against the base model (base-vs-fine-tune experiment), i.e. the benefit of ML is an empirical result, not an assumption. Grammar/JSON-schema-constrained decoding plus validators-and-retries provide the ML-side safety net that pure rule systems would provide for free — this is why learning-based generation is paired with deterministic validation.

### 3.4 Classical ML/heuristics remain where guarantees are required (the hybrid argument)
Using ML does not mean using it everywhere — the architecture applies each technique only where its failure mode is acceptable:

| Concern | Technique | Why not the alternative |
|---|---|---|
| Movement, schedules, pathfinding | **A\*** + classical simulation (rule-based) | Needs *guarantees* (shortest path, no teleporting); ML offers none and adds hallucination risk |
| Ground truth, accusation verdict | **Deterministic engine code** | Win/lose must be provably correct against `truth.json` |
| Content authoring (mystery, cast, secrets) | **Fine-tuned LLM (deep learning)** | Rule systems cannot produce the diversity + naturalness the product promises |
| Player-facing dialogue | **Live API LLM (deep learning)** | Rule-based parsers cannot handle open-ended free text |

In short: **ML is necessary precisely where the problem is language and unbounded variety** (generation, conversation), and deliberately excluded where the problem demands determinism (simulation, judging). A purely rule-based build cannot deliver the product; a purely neural build cannot be trusted as a game.

### 3.5 Secret-keeping is a learned behaviour, so it must be evaluated empirically
Whether an LLM withholds an authored secret cannot be guaranteed by prompt wording alone (per project decision, a leak is an *LLM accuracy fault*, not an engine bug). This makes behavioural evaluation — probe suites, secret-keeping rates, LLM-judge rubrics, cross-provider comparisons — a core ML-evaluation component of the project, further grounding the choice of a data-centric, model-based approach over fixed rule-based dialogue trees.

---

## Sources
- `docs/features.md` — product specification (§1 overview, §2 non-negotiables, §4 features, §5 fine-tuning plan, §11 evaluation) — *source of truth*.
- `docs/md/DOCUMENTATION.md` — architecture documentation (§1.5 academic relevance, §3 two-phase design, §4 body/voice split, §5 spoiler firewall, §6 pipeline, §8 evaluation).
