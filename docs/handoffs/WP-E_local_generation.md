# WP-E Local Generation Runtime — Handoff Status

**Status date:** 2026-11-09
**Owner of continuation:** whoever resumes after the Kaggle fine-tune (WP-D) finishes.

## 1. Branch and PR state

| Item | Value |
|---|---|
| Continuation branch | `wp-e-local-generation` |
| Remote | `origin/wp-e-local-generation` (pushed, tracking) |
| Base | `origin/main` @ `4132036` (workflow policy sync merged from `1259b4a`) |
| E-01 commit | `2de6019` — `feat(generation): implement E-01 staged orchestrator with mock runner` |
| PR | **Not opened.** Do not merge WP-E until E-02 and E-03 are complete. |

Git workflow (mandatory): one work package per branch; branch from the latest `origin/main`; open a PR into `main` only when the whole WP is complete; never merge locally. The full policy is in `AGENTS.md` §4, merged into `main` via PR #2.

## 2. Done — E-01 staged orchestrator (complete)

Files:

```
src/fabula/generation/
  __init__.py
  errors.py          # typed GenerationError hierarchy
  protocols.py       # ModelRunner / CancellationToken / progress events / StageName
  retries.py         # RetryPolicy(max_attempts=3) + validation-only retry loop
  bundle_io.py       # canonical bundle files + atomic temp-dir swap publish
  mock_runner.py     # MockModelRunner + skeleton_runner fixtures
  orchestrator.py    # generate_bundle(): settings -> world -> cast -> truth+clues -> per-NPC
tests/test_orchestrator.py   # 10 tests
```

Behaviour implemented:

- Stage order follows the frozen contracts in `src/fabula/schemas/stages.py`.
- `random` mystery type resolves deterministically via `random.Random(f"fabula-generation-v1:{seed}")`.
- Every stage is parsed with Pydantic and validated before the next stage starts.
- Validation failures retry only the failing stage (default 3 attempts); cancellation is never retried.
- Final `Bundle` must pass both Pydantic cross-reference validation and `validate_bundle()` before anything is written.
- Publication is atomic: files are written to a sibling temp directory, then swapped; a previous bundle is restored/kept on failure.
- No network, GPU, UI, or model weights required; `MockModelRunner` replays a validated bundle.

Verification at handoff: `python -m pytest -q` -> **62 passed**; `ruff check src/fabula/generation tests/test_orchestrator.py` clean.

Progress entry also recorded in `docs/decisions.md` (2026-11-09 row).

## 3. Remaining work

### E-02 — Local constrained decoder and CLI

Deliverables:
- `src/fabula/generation/local_runner.py` — llama.cpp-compatible GGUF runner (HG-03), `Q4_K_M` artifact, four compact stage-specific GBNF grammars (or JSON-schema-constrained decoding) compiled from the frozen Pydantic models. **No API fallback.**
- `src/fabula/generation/config.py` — runtime/model paths, retry config, generation settings.
- `src/fabula/generation/cli.py` — CLI exposing `mystery_type` (including `random`), tone, difficulty, output path, seed, progress, retry config.
- `docs/local-generation.md` — how to obtain the artifact, run generation, and what failure means.
- Tests: mock-backed CLI creates a valid bundle; the local runtime path fails clearly if the binary/artifact is missing; tests assert no provider imports and no local chat path at runtime.

Acceptance (from `docs/dev_plan/WS-E_local_generation.md`): mock CLI creates a valid bundle; random resolves to a concrete v1 type; missing runtime/artifact fails clearly; no live-API imports in the generation path.

**Blocked on:** the D-03 GGUF artifact (WP-D / teammate), HG-03/HG-16 confirmation. The model-independent CLI/config/runner shell can be built and tested with `MockModelRunner` before the artifact arrives.

### E-03 — CPU benchmark and artifact distribution

Deliverables:
- `evaluation/generation_benchmark.py` — record hardware, model/runtime hashes, per-stage and total generation time, peak RAM, token counts, retries, failures; machine-readable JSON report.
- Benchmark report template and a retrieval section in `docs/local-generation.md` (checksum-verified artifact download per HG-16).
- Tests: fixture benchmark passes offline; real numbers require HA-03.

**Blocked on:** HA-03 (reference low-end laptop benchmark), HG-16/HA-08 if weights are hosted.

## 4. Handoff checklist from the fine-tuning teammate (WP-D)

Before E-02 can be finalized, obtain and record:

- Exact base model ID and revision actually trained (note: HG-02 approved Qwen3-4B primary / Gemma 4 E4B challenger, while the prepared script targets `unsloth/Qwen2.5-3B-Instruct-bnb-4bit`; record the deviation and rationale in `docs/decisions.md`).
- LoRA adapter directory and training run manifest / logs.
- `fabula_gguf/` Q4_K_M artifact path and SHA-256 checksum.
- `train.jsonl`, `val.jsonl`, `test.jsonl` paths for held-out evaluation.
- `data/reports/sft_audit_report.json` (already committed) plus the final run identifiers.
- Confirmation of the teacher model used for WS-C (`Qwen/Qwen2.5-7B-Instruct`) and any licence/NOTICE updates.

## 5. How to resume

```powershell
git fetch origin
git switch wp-e-local-generation
git pull --ff-only
git log --oneline -3
$env:PYTHONPATH="src"
python -m pytest -q
```

Then implement E-02 first (mock-first), bind the GGUF once available, then E-03.

## 6. Quality gates and PR instructions

- `python -m pytest`
- `ruff check .`
- `ruff format --check .`
- Known pre-existing Ruff debt lives in `data/scripts/audit_sft.py`, `training/scripts/*.py`, and the training notebook; do not silently delete it — fix it or record an explicit exclusion before opening the WP-E PR.
- When E-02 and E-03 are complete: push the branch and run `gh pr create --base main --title "[WP-E] Local generation runtime"`. The description must list completed tasks, tests run, and known gaps.

## 7. Boundaries

- Runtime conversation must remain live-API only; no local chat model, no Ollama, no API fallback inside the local generator.
- Use frozen schema v1.0 contracts; do not change bundle fields without a versioned migration.
- The canonical bundle layout is enforced by `src/fabula/generation/bundle_io.py` (E-01): `world.json`, `truth.json`, `clues.json`, `npcs/<id>/identity.json`, `npcs/<id>/memory.json`.
