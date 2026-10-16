# WS-H — UI and Game Loop

Prompts start with shared context block in `00_OVERVIEW.md` verbatim.

### H-01 Map and movement UI
Goal: Render locations, placeholder tiles, NPC/player positions using chosen engine. Depends on F-01/F-02. Inputs: HG-01 and tile approval. Outputs: `src/fabula/ui/{app,map_view,input}.py`, tests. Steps: implement fixed enum tile placeholders; render names/positions; route movement only through simulation. Tests: fake renderer verifies position updates; simulation import has no UI dependency. HUMAN GATE / HUMAN ACTION: HG-01, HA-06.

### H-02 Dialogue, journal, timer and accusation UI
Goal: Expose free-text chat, clues, journal, timer and who/how/why selection. Depends on F-03/F-04/G-03/H-01. Inputs: service APIs and HG-06/08. Outputs: UI modules and tests. Steps: NPC selection/chat/loading; continuous timer and journal; approved option lists and attempts; show only result flags, never truth. Tests: fake service end-to-end; UI DTO contains no truth; outage fallback shown. HUMAN GATE / HUMAN ACTION: HG-01/06/08.

### H-03 Generation loading/error screens
Goal: Show staged progress and terminal failure before play. Depends on E-01/H-01. Inputs: generator events. Outputs: `src/fabula/ui/generation_screen.py`, tests. Steps: nonblocking progress; retry/exit actions; launch only after complete atomic validated bundle. Tests: failed generation cannot start partial bundle. HUMAN GATE / HUMAN ACTION: HG-01.
