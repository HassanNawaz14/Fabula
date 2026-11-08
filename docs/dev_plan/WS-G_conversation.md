# WS-G — Runtime Conversation

Prompts start with the shared context block in `00_OVERVIEW.md` verbatim.

### G-01 Isolated prompt assembler
Goal: Build an NPC prompt from only that NPC files, own history/session facts and player input. Depends on: A-02/HG-18. Inputs: frozen NPC schema. Outputs: `src/fabula/conversation/{dto,prompt_builder}.py`, tests. Steps: define DTO that cannot accept root/truth/roster/other files; load exactly selected identity/memory; check embedded IDs; serialize rules and approved output schema. Tests: canary contents from truth and other NPC never occur in serialized prompt; traversal and ID mismatch reject. HUMAN GATE / HUMAN ACTION: HG-08.

### G-02 Provider interface and adapters
Goal: Support two selected live providers plus offline mock. Depends on: G-01. Inputs: HG-07, HA-02. Outputs: `src/fabula/conversation/{provider,mock,providers/*}.py`, tests. Steps: typed complete/stream interface; approved adapters; env/key store credentials, timeout, session token cap, redacted logs; no local model/Ollama. Tests: offline timeout/stream/cap/error and firewall tests; live tests opt-in. HUMAN GATE / HUMAN ACTION: HG-07, HA-02.

### G-03 Conversation service, input filter, fallback
Goal: Filter input and connect per-NPC chat to live provider. Depends on: F-03/G-01/G-02. Inputs: safety boundary and output shape. Outputs: `src/fabula/conversation/service.py`, tests. Steps: filter before API; scope history to addressed NPC; parse reply; enforce cap/timeout; canned in-character fallback on failure. Tests: blocked input makes zero calls; history isolation, malformed reply, cap and fallback cases. HUMAN GATE / HUMAN ACTION: HG-07/08/13, HA-02.

### G-04 Leak filter and gated reveal toggles
Goal: Implement optional safeguards as explicit ablations. Depends on: G-03. Inputs: disclosure/reveal contracts. Outputs: leak filter and gated reveal modules, tests. Steps: deterministic fact-match filter toggle; add own eligible fact only after required clue; preserve raw output when off; record toggle state. Tests: off preserves raw output; on blocks fixture leak; clue gate works; firewall holds. HUMAN GATE / HUMAN ACTION: HG-09.

### G-05 Scripted offline mode
Goal: Keep the full game playable with no API key using deterministic authored NPCs, without adding a local chat model. Depends on: G-03. Inputs: frozen NPC schema, clue contracts, HG-09/13. Outputs: `src/fabula/conversation/scripted.py`, mode resolution, tests, `docs/conversation.md`. Steps: persona-aware templates from the selected NPC's own identity, memory, traits, backstory, and public clue descriptions; stable-seed phrasing variation; cover greeting, identity, case, clue, pressure, farewell, unknown; reveal eligible `npc_reveal` clues honoring `requires` and return `revealed_clue_ids`; zero network calls. Modes: `auto` (live if key, else scripted), `live` (requires key, clear failure), `scripted` (kill switch). Tests: no-key auto mode; forced scripted makes zero provider calls; NPC-reveal clues collectible and accusation solvable across v1 mystery types; scripted output leaks no memory/truth; firewall holds. Excluded from live-provider metrics; docs state the limits. HUMAN GATE / HUMAN ACTION: HG-07/09/13.
