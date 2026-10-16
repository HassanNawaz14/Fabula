# Fabula Bundle & Stage Contracts — Schema v1.0 (A-01)

> **Status:** FROZEN — approved by owner 2026-10-17 (HG-18). Code of record: `src/fabula/schemas/` (Pydantic v2, `extra="forbid"`).
> Decisions encoded: HG-04 (location enum), HG-05 (schedule minutes), HG-06 (accusation options), HG-08 (reply shape), HG-15 (mystery types), plus checklist items of `docs/decisions.md`.
> Semantic validation: `src/fabula/schemas/validators.py` (`validate_bundle`, issue codes `E_*`). Deterministic training data: `src/fabula/training_data/` (300-scenario dataset, see `data/reports/dataset_manifest.json`).

## 1. Files in a game bundle

```
bundle/
├── world.json        WorldDocument
├── truth.json        TruthDocument        (engine-only, never in any prompt)
├── clues.json        CluesDocument
└── npcs/<npc_id>/
    ├── identity.json Identity
    └── memory.json   Memory
```

Every file carries `schema_version: "1.0"`.

## 2. Key constraints

| Rule | Where enforced |
|---|---|
| 3–4 locations, 5–6 NPCs | `WorldDocument` |
| 4–6 clues, unique clue ids | `CluesDocument` |
| `location.type` ∈ `location_types_v1`: market, library, cafe, park, parking, residence | `LocationType` (HG-04; docks→parking per owner 2026-10-17) |
| `schedule.at_minute` integer 0–10 (1 sim minute = 60 real s, 1 s ticks) | `ScheduleEntry` (HG-05) |
| `timeline.t`, `time_window.start/end` integer minutes 0–10; `time_window.start <= end`; `Fact.when` is a short prose string | `TimelineEntry`, `TimeWindow`, `Fact` |
| Exactly 4 method + 4 motive options, unique ids, no overlap | `AccusationOptions` (HG-06) |
| Answers live only in `truth.json`: `solution.correct_culprit_id / correct_method_id / correct_motive_id` | `Solution` (HG-06) |
| `mystery_type` ∈ theft / disappearance / murder; settings input also allows `random` | enums (HG-15) |
| NPC reply = `{reply, mood}` with `mood` ∈ neutral, friendly, nervous, angry, sad, amused | `NpcReply` (HG-08) |
| Facts carry `source` ∈ did/witnessed/heard/inferred and `disclosure` ∈ volunteer/if_asked/hide/lie | `Fact` |
| All cross-references resolve (locations, NPCs, clue ids, option ids, cover stories) | `Bundle` |
| NPC folder keys = world roster; identity.id = memory.npc_id = folder name | `Bundle` |

## 3. Stage contracts (staged generation)

| Stage | Input | Output |
|---|---|---|
| 1 `settings→world` | `GenerationSettings` | `WorldDocument` |
| 2 `world→cast` | `WorldDocument` | `CastDocument` (roster summary: id, name, role, traits, relationships, attitude) |
| 3 `world+cast→truth+clues` | `WorldDocument` + `CastDocument` | `TruthDocument` **and** `CluesDocument` (atomic pair) |
| 4 `…+npc_id→identity+memory` | world, cast, truth, clues, `npc_id` | that NPC's `Identity` + `Memory` only |

## 4. Spoiler firewall (type level)

- **Generation time:** stage 4 may read `truth` (it must author the culprit's true memory); its *output* is restricted to the single requested NPC.
- **Play time:** `NpcPromptInput` = own `identity` + own `memory` + own `chat_history` + `player_input` only. `extra="forbid"` means a `truth` field or another NPC's file **cannot even be passed** — enforced by test `test_prompt_input_rejects_truth_field`.
- `truth.json` stays engine-side; accusation checking happens in the engine.

## 5. Engine semantics frozen with this schema

- **Time:** fixed ticks, 1 simulation minute = 60 real seconds, tick step 1 s; clock pauses only while an API reply is in flight; opening dialogue freezes only the NPC being spoken to; pause menu pauses everything (HG-05).
- **Perception:** an NPC perceives events in its own location only (no adjacency in v1).
- **Accusation:** 3 attempts, no hints, no per-component feedback; wrong attempt shows only "not correct" (HG-06).
- **Cast stage:** a generation-time intermediate (not shipped in the bundle).
