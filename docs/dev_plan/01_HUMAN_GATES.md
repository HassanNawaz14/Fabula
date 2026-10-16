# Human Gates and Human Actions

Record resolved choices in `docs/decisions.md` using: `ID | decision | date | rationale | affected schema/API version | approver`. Agents must stop before dependent work, ask the listed question with options, and continue independent tasks. Defaults are provisional only.

## Human Gates

### ⛔ HUMAN GATE HG-01 — Game engine
Question: Pygame or Arcade? Options: A Pygame / B Arcade · Default if no answer: Pygame · Blocks: H-01, J-01. Ask before UI implementation. Consequence: selected engine is the only UI dependency; simulation remains headless. Record in decisions.md.

### ⛔ HUMAN GATE HG-02 — Fine-tuning base model
Question: Which exact ~3–4B instruct base? Options: Qwen 3.x ~4B / Gemma 3 ~4B / Llama 3.2 3B, after benchmark/licence bake-off · Default if no answer: run bake-off and defer final choice to owner · Blocks: D-02, D-03, E-02 final model binding. Ask after D-01 baseline harness defines comparable candidates and before training. Consequence: model determines license, memory, schema performance, export compatibility. Record exact model ID/revision.

### ⛔ HUMAN GATE HG-03 — Local generation runtime
Question: Which local inference runtime? Options: A llama.cpp-compatible GGUF runner / B another documented local runtime supporting constrained JSON and CPU · Default: A · Blocks: E-02, J-02. Ask before packaging adapter is finalized. Consequence: affects model artifact format, grammar support, installation.

### ⛔ HUMAN GATE HG-04 — Location type enum
Question: Which fixed location types ship? Options: A market, library, café, park, parking, residence (chosen; see decisions.md) / B reduced/expanded owner-provided list · Default: A · Blocks: A-01, A-02 and all downstream schema/tile work. Ask at schema freeze. Consequence: changes accepted bundle values and tile mapping.

### ⛔ HUMAN GATE HG-05 — Simulation clock
Question: Real-time or tick-based simulation? Options: A real-time monotonic clock with minute schedule boundaries / B fixed simulation ticks mapped to real time · Default: B, one simulation minute per 60 real seconds, tick step 1 second; rationale: deterministic tests and schedule reproducibility while retaining the ten-minute session · Blocks: A-01, F-02, F-03, H-01. Ask before schema freeze. Consequence: changes schedule/time APIs and pause behavior.

### ⛔ HUMAN GATE HG-06 — Accusation rules
Question: How many accusations, partial credit, hints, and how/why matching? Options: A one final attempt, no hints, exact selection from generated option IDs, report who/how/why correctness internally / B three attempts, no hints, same option IDs / C owner-defined counts/hints · Default: none; recommendation B to support a short mystery while keeping deterministic truth checks · Blocks: A-01, A-02, F-04, H-02, B-02. Ask before schema freeze. Consequence: modifies option schema, UI, session terminal states, test fixtures. No free-text judge: player selects culprit and generator-provided method/motive options; engine compares stable IDs to truth IDs.

### ⛔ HUMAN GATE HG-07 — Runtime providers and key model
Question: Which two live providers and credentials model? Options: A Gemini + Grok-class, BYO keys / B owner-selected two live providers with capped managed key · Default: A is provisional (provider names and exact model IDs must be checked at implementation); BYO preferred · Blocks: G-02, G-03, I live runs, J-02. Ask before adapters/credential UI. Consequence: provider SDKs, cost, region, terms, key storage. Never block mock-provider work.

### ⛔ HUMAN GATE HG-08 — NPC reply shape
Question: Which reply schema? Options: A `{reply: string, mood: string}` / B `{reply: string}` · Default: A · Blocks: G-01, G-03, H-01. Ask before prompt/adapter implementation. Consequence: impacts parser and dialogue UI; mood is presentation metadata only.

### ⛔ HUMAN GATE HG-09 — Leak filter and gated reveal product behavior
Question: Ship either safeguard enabled by default or evaluation-only toggles? Options: A ablation-only toggles, off in baseline / B leak filter on in product, gated reveal off / C enable both · Default: A · Blocks: G-04, I-03, J-01. Ask before final runtime config. Consequence: alters measured raw secret-keeping and reveal behavior. Implement toggles regardless; evaluation baseline disables them.

### ⛔ HUMAN GATE HG-10 — Legacy GA/MLP/K-Means
Question: Any course requirement for these algorithms? Options: A no, exclude from MVP / B specify required algorithm and rubric · Default: A · Blocks: none; scope confirmation before plan approval. Consequence: B requires a separately approved scope change and schedule update; do not build absent that decision.

### ⛔ HUMAN GATE HG-11 — Teacher model and output-use license
Question: Which teacher model/provider is approved, and do its terms allow training on outputs? Options: A approved hosted teacher after written terms review / B approved locally hosted teacher / C no teacher pipeline until cleared · Default: none; recommendation C until terms are verified, then A for quality · Blocks: C-02, C-03. Ask before any teacher request or data creation. Consequence: cost, privacy, permissible data use, reproducibility.

### ⛔ HUMAN GATE HG-12 — Judge and human sample protocol
Question: Which judge model and human rating sample? Options: A owner-approved live judge + blinded 10% sample stratified by provider/type/policy / B rubric-only human scoring / C judge plus owner-defined sampling · Default: none; recommend A, with fixed probe set and adjudication sheet · Blocks: I-02, I-03. Ask before live evaluation. Consequence: metric validity, API spend, human time.

### ⛔ HUMAN GATE HG-13 — Age rating and content boundary
Question: Intended age rating and allowed violence/gore boundary? Options: A owner specifies rating and concrete prohibited/allowed examples / B conservative teen rating and non-graphic violence pending approval · Default: none; recommendation B only as provisional test configuration, not release claim · Blocks: C-01, G-02, J-03. Ask before teacher prompts, input filter rules, or release metadata. Consequence: generation prompts, input filtering, public rating.

### ⛔ HUMAN GATE HG-14 — Roles and timeline
Question: Who owns each human action and what availability/timeline? Options: A adopt proposed 8 weeks with named owners per action / B provide revised roles and dates · Default: none; eight weeks is planning estimate only · Blocks: approved schedule in 00_OVERVIEW and J-01. Ask at kickoff. Consequence: sequencing, parallelism, attainable completion date.

### ⛔ HUMAN GATE HG-15 — Mystery types beyond v1
Question: Add sabotage or blackmail/fraud to v1? Options: A defer both (v1 theft/disappearance/murder) / B name one type and approve scope/data/test changes · Default: A, post-MVP · Blocks: none for v1; B blocks schema freeze and B/C/D scope. Ask only if owner requests expanded scope.

### ⛔ HUMAN GATE HG-16 — Weight distribution and minimum hardware
Question: How will weights be distributed and what minimum player CPU/RAM/OS is supported? Options: A downloadable owner-hosted artifact with documented checksum and CPU/RAM minimum / B bundle weights with installer after size/license review / C private distribution · Default: none; recommend A to avoid shipping large weights with app · Blocks: E-03, J-02, J-03. Ask before packaging/release. Consequence: installer, bandwidth, license, benchmark target. HA-08 required if hosting.

### ⛔ HUMAN GATE HG-17 — Licences and language
Question: Approve licenses for code, base weights, fine-tuned weights, training data, teacher outputs, and reference material; confirm language? Options: A English and only explicitly cleared assets/data/weights / B owner-approved alternative language/licensing matrix · Default: none; recommend A as a provisional implementation assumption, not legal approval · Blocks: C-01/C-03, D-02, J-03. Ask before using reference data or release. Consequence: permissible training, attribution, redistribution, language support.

### ⛔ HUMAN GATE HG-18 — Schema freeze sign-off
Question: Approve versioned schemas and stage input/output contracts from A-01? Options: A approve as written / B return changes with field-level comments · Default: no default; sign-off is required · Blocks: A-02 and every downstream task. Ask after A-01 and before dependent implementation. Consequence: freezes interface contract; changes later require versioned migration. HA-07 records approval.

## Additional required owner sign-offs
Record explicit approval after D-01 baseline comparison (whether fine-tune remains justified), first D-03 fine-tune review, I-04 results review, and J-03 release readiness. These are approval checkpoints rather than new product-design gates; stop the corresponding next commitment until answered.

## Human-only actions
- **HA-01** Run Kaggle T4 training notebook, monitor quota, download adapters/GGUF. Blocks D-03/E-02 final-model verification; coding agents provide reproducible notebook/run instructions and wait.
- **HA-02** Provide runtime, teacher and judge API keys; set spend limits. Blocks live-provider/data/evaluation calls; agents continue mock tests without keys.
- **HA-03** Run CPU generation benchmark on representative low-end hardware and report model, OS, elapsed time, peak memory. Blocks performance acceptance in J-02; agents prepare benchmark command.
- **HA-04** Playtest sessions and report timing, difficulty, fun, confusion. Blocks final gameplay sign-off; agents prepare checklist/build.
- **HA-05** Rate the sample of NPC outputs according to HG-12 rubric. Blocks final persona metric/report.
- **HA-06** Approve placeholder tile kit/assets and verify asset licenses. Blocks H-01/J-03; agents use generated primitive placeholders meanwhile.
- **HA-07** Approve schema freeze, evaluation results, and release. Blocks A-02, J-03 as applicable.
- **HA-08** Host/publish model weights per HG-16. Blocks public model download/release; agents can test local artifact paths.
