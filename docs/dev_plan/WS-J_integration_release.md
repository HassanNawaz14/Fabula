# WS-J — Integration and Release

Prompts start with shared context block in `00_OVERVIEW.md` verbatim.

### J-01 Application integration and smoke flow
Goal: Wire generation, simulation, conversation and UI into playable application. Depends on E-02/F-04/G-04/H-03. Inputs: subsystem APIs and fixtures. Outputs: `src/fabula/app.py`, integration test, run docs. Steps: dependency injection; full mock flow settings→bundle→movement→clue/journal→chat→accusation; immutable bundle; truth absent UI/prompt; mock demo without local chat. Tests: offline full flow and spy proving no truth/other NPC prompt transmission. HUMAN GATE / HUMAN ACTION: HG-01/06/07/09.

### J-02 Package and model distribution
Goal: Provide clean installation and checksum-verified model acquisition. Depends on E-03/J-01. Inputs: HG-03/16/17 and supported OS. Outputs: packaging config, `docs/install.md`, model card. Steps: pin runtime; keep weights outside Git; checksum/license model; first-run config; audit no keys or local runtime chat model. Tests: clean mock install/demo and artifact hash checks. HUMAN GATE / HUMAN ACTION: HG-03/16/17, HA-03, HA-08 if hosted.

### J-03 Playtest, license audit and release checklist
Goal: Gather playtest findings and verify release evidence. Depends on J-01/J-02/I-03. Inputs: build, license inventory, evaluation report. Outputs: playtest/license/release checklists and release candidate report. Steps: record build/hardware; collect timing/fun/difficulty; clear code/assets/data/teacher/base/fine-tuned weights; state age rating; document limitations; obtain approvals. Tests: each checklist item links evidence or is explicitly blocked; no unapproved license/rating is claimed. HUMAN GATE / HUMAN ACTION: HG-13/14/16/17, HA-03/04/06/07/08.
