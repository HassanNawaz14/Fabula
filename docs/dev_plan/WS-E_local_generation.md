# WS-E — Local Generation Runtime

Every task is one session/one deliverable. Coding-agent prompts start with the shared context block in `00_OVERVIEW.md` verbatim, followed by the task-specific instructions and acceptance below.

### E-01 Staged orchestrator with mock runner
Goal: Execute world → cast → truth+clues → per-NPC stages with validation, retries and terminal failure. Depends on: A-02; HG-18. Inputs: frozen stage DTOs, validators, fixtures. Outputs: `src/fabula/generation/{protocols,orchestrator,retries,errors}.py`, tests. Steps: 1. Define `ModelRunner.generate(stage,input_json,schema,seed)->str` and fixture mock. 2. Validate each stage before proceeding; retry only failed stage up to configurable default 3. 3. Write to temporary bundle and atomically publish only after full validation. 4. Emit progress and typed user-safe errors. Tests/acceptance: offline success, per-stage retry, exhaustion, cancellation and atomicity tests pass. HUMAN GATE / HUMAN ACTION: HG-18 sign-off.

### E-02 Local constrained decoder and CLI
Goal: Bind approved local runtime and expose settings/output through CLI. Depends on: E-01, D-03. Inputs: GGUF, HG-03/16, frozen contracts. Outputs: `src/fabula/generation/{local_runner,cli,config}.py`, tests, `docs/local-generation.md`. Steps: 1. Implement selected runtime with constrained JSON, no API fallback. 2. Support type/random, tone, difficulty, output path, seed, progress and retry config. 3. Resolve random to concrete v1 type. 4. Fail clearly if runtime/artifact unavailable. Tests/acceptance: mock CLI creates valid bundle; assert no provider imports or runtime local chat path. HUMAN GATE / HUMAN ACTION: HG-03/HG-16, HA-01.

### E-03 CPU benchmark and artifact distribution
Goal: Measure speed/memory on selected minimum hardware and document artifact retrieval. Depends on: E-02. Inputs: model, scenarios, HG-16 hardware. Outputs: `evaluation/generation_benchmark.py`, report template and local-generation docs. Steps: record hardware, model/runtime hashes, stage/total time, peak RAM, tokens, retries and failures; provide reproducible JSON report and checksum-based retrieval. Tests/acceptance: fixture benchmark passes; real acceptance requires HA-03 numbers. HUMAN GATE / HUMAN ACTION: HG-16, HA-03, HA-08 if hosted.
