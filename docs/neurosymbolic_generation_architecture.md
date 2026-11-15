# Neurosymbolic Mystery Synthesis (NMS): Architecture & Performance Specification

**Document Version:** 1.0.0  
**Status:** Approved Architecture Specification  
**Target Gameplay:** Fabula — Single-player mystery game (~10-minute sessions)  
**Target Hardware:** Standard consumer laptop CPU (e.g. AMD Ryzen 5 / Intel Core i5, 4 physical cores, DDR4 RAM, 15W TDP, integrated graphics, CPU-only execution)  
**Performance Objective:** Full, verified, playable mystery case generated in **under 7 seconds** (hard ceiling: < 15 seconds), down from the 35–40+ minute baseline.

---

## 1. Problem Statement & Root Cause Analysis

### 1.1 The Baseline Problem
In the initial baseline implementation of Fabula, generating a single mystery case took **35 to 40+ minutes** on standard laptop hardware. Because Fabula is designed for a **10-minute gameplay session**, a 40-minute loading screen renders the game unplayable.

### 1.2 Quantitative Post-Mortem: Why the Previous System Failed
The failure was driven by three compounding architectural bottlenecks:

#### 1. The Physics of CPU Memory Bandwidth
Autoregressive token generation on a CPU is strictly memory-bandwidth bound. For every token generated, all active model weights must be streamed from main system RAM across the memory bus into CPU L3 cache and execution registers:
$$\text{Max Theoretical Decode Speed (tokens/s)} \approx \frac{\text{System Memory Bandwidth (GB/s)}}{\text{Model File Size (GB)}}$$
On typical dual-channel DDR4 laptop memory ($\sim 20\text{ GB/s}$ effective bandwidth):
* `Qwen2.5-3B-Instruct.Q4_K_M` occupies **$1.80\text{ GB}$**.
* The theoretical maximum decode throughput is:
  $$\frac{20\text{ GB/s}}{1.80\text{ GB}} \approx 11.1\text{ tokens/s}$$
* Under real-world mobile CPU constraints (15W power throttling, instruction overhead, cache contention), real throughput measures **$4.0\text{ to }5.2\text{ tokens/s}$**.

#### 2. The 152k Vocabulary Masking Penalty (GBNF on CPU)
In the initial implementation, `llama.cpp` context-free grammar (GBNF) enforcement was applied to ensure strict JSON Schema compliance.
* `Qwen2.5` has a massive vocabulary of **151,936 tokens**.
* Standard `llama.cpp` grammar engines evaluate the pushdown automaton (PDA) and compute a logit mask across the **entire 151,936-token array on a single CPU thread for every single token generated**.
* Across 8,000 generated tokens, the CPU performs over **1.2 billion logit checks**. This single-threaded mask generation stalls the execution pipeline, collapsing generation speed from $\sim 5\text{ tok/s}$ to **$\sim 1.0\text{--}1.5\text{ tok/s}$**. Stage 1 alone took over 4 minutes on an AMD Ryzen 5 quad-core CPU.

#### 3. The 9-Stage Sequential Cascade
The generation pipeline was divided into 9 sequential passes:
$$\text{Settings} \rightarrow \text{World} \rightarrow \text{Cast} \rightarrow \text{Truth/Clues} \rightarrow 6 \times \text{NPC Identity/Memory}$$
* Across all 9 stages, the model was forced to autoregressively generate **6,500 to 8,000 tokens** of boilerplate JSON syntax.
* At $4\text{ tok/s}$, 7,500 tokens requires $7,500 / 4 = 1,875\text{ seconds} \approx \mathbf{31.25\text{ minutes}}$ of raw decoding time alone.
* Adding prompt prefill ingestion (1,000+ tokens per stage), grammar compilation, and validation retries, total run time reliably reached **35 to 40+ minutes**.

---

## 2. The Solution: Neurosymbolic Mystery Synthesis (NMS)

### 2.1 The Core Architectural Principle
The fundamental design flaw was using an autoregressive neural network as a database serializer and JSON compiler. LLMs excel at **unstructured creative ideation** (motive, relationship twists, thematic atmosphere) but are computationally inefficient at generating repetitive syntax (braces, quotes, array indices, coordinate grids).

Fabula transitions to a **Neurosymbolic Architecture** separating **System 1 (Neural Story Planner)** from **System 2 (Symbolic World Engine)**:

```
+-----------------------------------------------------------------------------------+
|                        NEUROSYMBOLIC DUAL-AXIS ARCHITECTURE                       |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [SYSTEM 1: NEURAL STORY PLANNER] (Local Edge SLM: Llama-3.2-1B-Instruct)         |
|  - Generates high-level narrative intent, conspiracy, motive, and alibi links.    |
|  - Generates ONLY ~140-160 tokens of dense, token-optimized DSL.                  |
|  - Execution time: ~3.5 to 5.0 seconds on CPU.                                    |
|                                                                                   |
|                                 | (Compact Blueprint DSL)                         |
|                                 v                                                 |
|                                                                                   |
|  [SYSTEM 2: SYMBOLIC WORLD ENGINE] (Pure Python, Deterministic, 0.15 seconds)     |
|  - Causal Timeline Ordering (T_1 < T_2 < T_crime).                                |
|  - A* Spatial Topology Verification (Room connectivity & traversal constraints).  |
|  - Epistemic Knowledge Slicing (Assigns memory facts with strict provenance).     |
|  - Candidate-Elimination Solvability Proof (Proves |Candidates| == 1).             |
|  - Automatic Bundle Serialization (world.json, truth.json, clues.json, npcs/).    |
|                                                                                   |
|                                 | (Validated Pydantic Bundle)                     |
|                                 v                                                 |
|                                                                                   |
|  [GAMEPLAY: INTERACTIVE SIMULATION & DIALOGUE]                                    |
|  - Pure Python headless simulation core for movement, clues, accusation (<1 ms).  |
|  - Live Fast API (Gemini Flash / Grok) or Scripted Fallback for NPC conversation. |
|  - Total Pre-Game Generation Latency: ~5 to 7 SECONDS.                            |
+-----------------------------------------------------------------------------------+
```

---

## 3. Layer 1: The Compact Blueprint DSL

### 3.1 Eliminating the JSON Syntax Tax
Standard pretty-printed JSON wastes between 60% and 70% of its token budget on syntactic noise:
```json
{
  "observed_events": [
    {
      "event_id": "ev_01",
      "timestamp": "16:00",
      "location": "drawing_room"
    }
  ]
}
```
In the Compact Blueprint DSL, this exact information is encoded in a single line without quotes, brackets, or redundant keys:
```text
- 16:00 | npc_butler | drawing_room | retrieves duplicate key
```

### 3.2 Formal DSL Specification & Example
A complete mystery scenario is defined in under 150 tokens:

```text
[CASE:theft|cozy|seed_101]
PREMISE: A priceless antique music box vanishes from the manor drawing room during tea.
CAST: vict:lady_eleanor | culp:npc_butler | susp:npc_maid,npc_gardener,npc_nephew
CRIME: mot:gambling_debt | meth:skeleton_key | scene:drawing_room | time:16:30
TIMELINE:
- 16:00 | npc_butler | cellar | retrieves duplicate brass key
- 16:15 | npc_maid | hallway | delivers tea service to drawing room
- 16:30 | npc_butler | drawing_room | unlocks display cabinet, pockets music box
- 16:45 | npc_nephew | terrace | observes butler hurriedly crossing garden
CLUES:
- brass_shaving | drawing_room | physical | links:npc_butler | proves:meth
- debt_ledger | cellar | document | links:npc_butler | proves:mot
- muddy_glove | garden | trace | red_herring:npc_gardener
KNOWLEDGE:
- npc_maid | sees:butler_near_cabinet | alibi:in_kitchen_at_1630
- npc_nephew | sees:butler_on_terrace | alibi:on_terrace_with_gardener
- npc_gardener | sees:nephew_at_terrace | confirms:gardener_alibi
```

### 3.3 Token Comparison Matrix
| Representation | Token Count | Generation Time @ 30 tok/s | Generation Time @ 4 tok/s |
|---|---:|---:|---:|
| **Original 9-Stage JSONs** | **7,200** | *Not feasible on CPU* | **30.0 minutes** |
| **Single JSON Blueprint** | **520** | **17.3 seconds** | **130.0 seconds** |
| **Compact Blueprint DSL** | **145** | **4.8 seconds** | **36.2 seconds** |

---

## 4. Layer 2: Symbolic Compiler & Epistemic Engine

The Python Symbolic Compiler (`src/fabula/generation/compiler.py`) consumes the DSL string and builds the complete game world in memory.

### 4.1 Epistemic Knowledge Modeling ($K_i \phi$)
To prevent hallucinations and guarantee the **Spoiler Firewall**, characters do not receive general text summaries. Their `memory.json` files are constructed from strict epistemic provenance rules:

$$\text{Provenance}(\phi) \in \{\text{DirectObservation}, \text{CommunicationFrom}(j), \text{PublicAnnouncement}, \text{GuiltyKnowledge}\}$$

1. **Innocent NPCs:**
   * Knowledge is strictly bounded to events where `actor == npc_id` or events occurring in the same location at the same timestamp.
   * Alibis are verified against the spatial graph: an NPC cannot be in two locations simultaneously.
   * `disclosure` is set to `volunteer` for alibis and `if_asked` for observations of other suspects.
2. **The Culprit:**
   * Receives `truth.json` knowledge as a secret fact with `disclosure: hide`.
   * Receives an authored `cover_story` fact explaining their presence elsewhere during the crime.
3. **Spoiler Firewall Enforcement:**
   * `truth.json` is generated directly by Python and stored exclusively in the engine root. It is physically isolated and cannot be read by non-culprit NPC prompt builders.

### 4.2 Candidate-Elimination Solvability Proof
Before any case files are published, the compiler runs a deterministic constraint satisfaction check:
1. Construct the suspect set $S = \{s_1, s_2, \dots, s_n\}$.
2. For each discovered clue $c \in \text{Clues}$, compute the supported facts $F_c$ and implicated suspect $I_c$.
3. Evaluate the candidate culprit set $C \subseteq S$:
   $$C = \{s \in S \mid \exists c_1, c_2 \text{ s.t. } I_{c_1} = s \land \text{supports}(c_1, \text{method}) \land I_{c_2} = s \land \text{supports}(c_2, \text{motive}) \land \neg \text{AlibiValid}(s, T_{\text{crime}})\}$$
4. **Solvability Invariant:** A case is accepted if and only if:
   $$|C| = 1 \quad \text{and} \quad C = \{\text{bundle.truth.solution.culprit}\}$$
If $|C| \neq 1$, the compiler executes a deterministic auto-repair (e.g. adjusts a red herring clue or clarifies an alibi timestamp) in $< 5\text{ ms}$ without needing to re-run the LLM.

---

## 5. Model Selection & Runtime Optimization

### 5.1 Model Evaluation Matrix
To achieve the 7-second budget on a 4-core mobile CPU, parameter scale must be strictly optimized:

| Model Candidate | Parameter Scale | Memory Footprint (Q4) | CPU Throughput | Vocabulary Size | GBNF Overhead | Verdict |
|---|---|---|---|---|---|---|
| **Llama-3.2-1B-Instruct** | **1.23B** | **~750 MB** | **35 – 50 tok/s** | 128,256 | Minimal with DSL | **PRIMARY CHOICE (Speed & Native Support)** |
| **Qwen2.5-1.5B-Instruct** | 1.54B | ~980 MB | 22 – 32 tok/s | 151,936 | High if JSON | Secondary Choice |
| **SmolLM2-1.7B-Instruct** | 1.71B | ~1.05 GB | 18 – 26 tok/s | 49,152 | Lowest (49k vocab) | Strong Fallback |
| **Qwen2.5-3B-Instruct** | 3.09B | ~1.80 GB | 4 – 5 tok/s | 151,936 | Extreme | **Teacher Model Only (Kaggle)** |

### 5.2 Menu Pre-Warming Pattern
* When the Fabula game client launches, the main menu is displayed.
* While the player reads the menu (typically 3–5 seconds), a background thread loads `Llama(model_path, n_ctx=1024, n_threads=4)` into RAM.
* When the player clicks **"New Game"**, the model is already warm. Inference begins in **0 milliseconds**.

---

## 6. Training & Synthetic Distillation Plan

We preserve the work invested in WP-D (the Kaggle Qwen2.5-3B fine-tuning) by using the 3B model as a **Teacher Generator**:

1. **Step 1: Dataset Generation (Kaggle T4):**
   * Script generates 1,500 diverse mystery configurations (Seeds 0–1499).
   * Teacher model (`Qwen2.5-3B-Instruct`) expands configurations into validated Compact Blueprint DSL outputs.
   * Every sample is audited by `BlueprintCompiler.verify_solvability()`.
   * Result: `blueprint_train.jsonl` (1,200), `blueprint_val.jsonl` (150), `blueprint_test.jsonl` (150).
2. **Step 2: Student Fine-Tuning (Kaggle T4):**
   * Target model: `meta-llama/Llama-3.2-1B-Instruct`.
   * Method: Unsloth QLoRA, rank $r=16$, $\alpha=16$, cosine schedule, 2 full epochs.
   * Training time on 1,200 samples of 200 tokens: **~35 minutes**.
3. **Step 3: GGUF Export:**
   * Merge LoRA adapters into 16-bit base weights.
   * Quantize to `fabula-blueprint-1b.Q4_K_M.gguf` (750 MB).

---

## 7. Performance Budget & Latency Targets

### Measured Runtime Projection (AMD Ryzen 5 3500U, 4 Cores):

| Step | Operation | Execution Time | Cumulative Time |
|---|---|---:|---:|
| 1 | Model Ingestion (180 prompt tokens @ 450 tok/s) | 400 ms | 0.40 s |
| 2 | Neural Generation (145 DSL tokens @ 32 tok/s) | 4,530 ms | 4.93 s |
| 3 | Regex Parsing & Entity Extraction | 8 ms | 4.94 s |
| 4 | Spatial Topology & A* Navmesh Mapping | 15 ms | 4.95 s |
| 5 | Epistemic Memory Slicing (5 NPCs) | 35 ms | 4.99 s |
| 6 | Candidate-Elimination Solvability Check | 12 ms | 5.00 s |
| 7 | Atomic Temp-Directory Swap to `bundles/` | 30 ms | **5.03 s** |

**Total Player-Visible Latency:** **$\approx 5.03$ seconds** (down from 2,400 seconds).

---

## 8. Implementation Roadmap

```
+-----------------------------------------------------------------------------------+
|                           FIVE-PHASE IMPLEMENTATION PLAN                          |
+-----------------------------------------------------------------------------------+
|  Phase 1: Symbolic Compiler & Solvability Engine (Pure Python, local)             |
|           - src/fabula/generation/compiler.py                                     |
|           - src/fabula/generation/dsl.py                                          |
|           - tests/test_blueprint_compiler.py                                      |
|                                                                                   |
|  Phase 2: Teacher Synthetic Data Pipeline (Kaggle T4)                             |
|           - training/scripts/kaggle_blueprint_distillation.py                     |
|           - data/processed/blueprint_train.jsonl (1,500 validated samples)        |
|                                                                                   |
|  Phase 3: Student Edge Model Fine-Tuning (Kaggle T4)                              |
|           - training/scripts/kaggle_student_qlora.py (Llama-3.2-1B-Instruct)      |
|           - models/fabula-blueprint-1b.Q4_K_M.gguf (750 MB artifact)              |
|                                                                                   |
|  Phase 4: Runtime Orchestration & Menu Pre-Warming                                |
|           - src/fabula/generation/local_runner.py (1B GGUF adapter)               |
|           - src/fabula/ui/app.py (Background menu pre-warm thread)                |
|                                                                                   |
|  Phase 5: Benchmark & Solvability Suite                                           |
|           - evaluation/blueprint_benchmark.py                                     |
|           - End-to-end latency and 100-case solvability audit                     |
+-----------------------------------------------------------------------------------+
```
