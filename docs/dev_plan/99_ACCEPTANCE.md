# Acceptance and Definition of Done

A release decision requires evidence for each mandatory item and recorded human decisions/actions. Passing checks does not itself authorize release.

## Product acceptance
- Local pre-play generation produces an atomic validated bundle for theft, disappearance or murder from type/random, tone and difficulty settings.
- Stages are world → cast → truth+clues → per-NPC identity/memory. Each is constrained JSON, separately validated, retried up to three times by default, with loading progress and terminal error.
- Bundle has 3–4 connected named locations using approved fixed types, 5–6 NPCs, 4–6 clues, engine-only truth and isolated NPC files.
- Fine-tuned small model has documented Kaggle T4 Unsloth QLoRA SFT and held-out comparison; CPU quantized artifact retrieval and license documented.
- No fine-tuned model or local chat model runs during play. At least two approved live API providers are supported; mock is test/demo only.
- Headless Python simulation loads bundle, schedules NPC movement with A*, handles perception, clues, journal, visible ~10-minute timer and deterministic who/how/why accusations.
- Thin selected-engine UI supports movement, examine, free-text chat, journal, timer and accusation.
- Input filter runs before each API call; token/latency limits and canned failure fallback work.
- NPC behavior probe suite and report include required metrics and ablations; generator checks are secondary.

## Mandatory engineering checks
Run at repository root:
```
python -m pytest
ruff check .
ruff format --check .
```
All pass without credentials, GPU or downloaded weights. Mock integration game and clean mock install/demo pass.

## Spoiler firewall release blockers
- Canary tests prove no outbound NPC request contains truth.json or any other NPC identity/memory content.
- Prompt-builder DTO cannot accept bundle root, truth, roster-wide map or arbitrary path; selected IDs match file IDs; path traversal rejects.
- UI/provider events contain no truth payload; accusation service returns only correctness/result flags.
- Bundle is read-only; session additions stay scoped to each NPC.
- Tests prove runtime never invokes fine-tuned generator or local chat model; no Ollama/local fallback exists.

## Playtest checklist (HA-04)
Record build hash, hardware/OS, type, seed and player experience; generation time/peak memory; map and NPC schedule clarity; conversation latency/fallback/persona; clue/journal accuracy; elapsed play time and whether who/how/why was understandable; difficulty/fun/confusion with reproducible examples. Do not change probe expectations based on a single session without documenting the change.

## Release checklist
- HG-01 through HG-18 and applicable HA-01 through HA-08 recorded in `docs/decisions.md` or evidence log.
- Baseline, first fine-tune and evaluation results reviewed.
- Minimum hardware and HA-03 benchmark published.
- Code, dependencies, assets, training data, teacher outputs, base/fine-tuned weights and reference materials have documented license disposition; nothing uncleared distributed.
- Age rating/content boundary approved and accurate.
- Weight distribution/checksum/install path approved; HA-08 complete if hosted.
- HA-06 tile kit approved or primitive placeholders explicitly retained.
- Key setup, spend controls, privacy/logging, outage fallback and limitations documented.
- Owner explicitly approves release readiness (HA-07).
