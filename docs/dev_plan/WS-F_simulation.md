# WS-F — Headless Simulation

Prompts start with the shared context block in `00_OVERVIEW.md` verbatim.

### F-01 Bundle loader and world state
Goal: Load validated read-only bundle into typed pure-Python state. Depends on: A-02/HG-18. Inputs: schema and fixtures. Outputs: `src/fabula/simulation/{loader,models,world}.py`, tests. Steps: validate before state build; reject missing/mismatched files, traversal and unknown versions; expose truth only to accusation service; no UI imports. Tests: invalid fixtures reject; UI-free import; source bundle unchanged. HUMAN GATE / HUMAN ACTION: HG-18.

### F-02 Clock, schedules, perception and A*
Goal: Advance simulation and move NPCs by deterministic scheduled destinations. Depends on: F-01. Inputs: frozen time/perception contracts. Outputs: `src/fabula/simulation/{clock,schedules,pathfinding}.py`, tests. Steps: implement Clock/FakeClock; deterministic A* tie-breaking; schedule minute boundaries; approved same/adjacent-location perception. Tests: deterministic paths/schedules, ten-minute timeout, no UI imports. HUMAN GATE / HUMAN ACTION: HG-05.

### F-03 Clues, journal and session facts
Goal: Track discoveries and scoped player-visible statements. Depends on: F-01/F-02. Inputs: clue contracts. Outputs: `src/fabula/simulation/{session,clues,journal}.py`, tests. Steps: implement examine/NPC-reveal requirements; idempotent journal entries with source/time; keep NPC-directed player statements only in that NPC's session facts; never mutate bundle. Tests: discovery gates, ordering, idempotence and NPC scoping. HUMAN GATE / HUMAN ACTION: HG-06.

### F-04 Accusation and terminal state
Goal: Check stable who/how/why option IDs against engine-only truth. Depends on: F-01/F-03. Inputs: accusation contracts. Outputs: `src/fabula/simulation/accusation.py`, tests. Steps: implement `submit(who_id,how_id,why_id)->AccusationResult`; apply attempt/partial-credit/hint/timeout choices; return only correctness flags and public result. Tests: all options, exhausted attempts, timeout; taint test proves truth absent from serialized events. HUMAN GATE / HUMAN ACTION: HG-06.
