# Local Generation

Fabula generates a complete mystery bundle on the player's machine **before play**. The generator is the fine-tuned Qwen2.5-3B-Instruct GGUF; it is never loaded during the play phase, and the runtime never performs local chat inference.

## Artifact

| Item | Value |
|---|---|
| Model | `models/Qwen2.5-3B-Instruct.Q4_K_M.gguf` |
| Size | `1,929,902,688` bytes (1.80 GiB) |
| SHA-256 | `7EDCCECCF2201E6859520209F9BA578B350F52C6CEB29826E3E0C8D042C067DC` |
| Manifest | `models/model_manifest.json` (lowercase hash) |
| Runtime | `llama-cpp-python 0.3.36`, CPU wheel |
| Context | `4096` tokens (override with `FABULA_MODEL_CTX`) |

The GGUF weights are intentionally gitignored. Only the manifest is committed; place the artifact at the path above or set `FABULA_MODEL_PATH`. Keep the manifest hash in sync with the distributed file.

## Install

```powershell
python -m pip install -e .
python -m pip install llama-cpp-python --prefer-binary --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
python -m fabula model check
```

`model check` prints the resolved path, size, computed SHA-256 and manifest comparison. A mismatch is a hard failure (`exit 2`).

## Generate

```powershell
python -m fabula generate --type theft --seed 1 --out bundles/my-case
```

Options:

| Option | Values / default |
|---|---|
| `--type` | `theft`, `disappearance`, `murder`, `random` (default) |
| `--tone` | `cozy` (default), `neutral`, `dark` |
| `--difficulty` | `easy`, `normal` (default), `hard` |
| `--seed` | integer; generated and printed when omitted |
| `--out` | `bundles/latest` by default, or `FABULA_GENERATION_OUT` |
| `--retries` | per-stage attempts (default `3`) |
| `--model` | GGUF path override |

`random` is resolved deterministically from the seed, so the same seed and settings reproduce the same requested type.

Environment overrides:

| Variable | Purpose |
|---|---|
| `FABULA_MODEL_PATH` | GGUF path |
| `FABULA_MODEL_CTX` | context size, default `4096` |
| `FABULA_MODEL_THREADS` | CPU threads, default `cpu_count - 1` |
| `FABULA_GENERATION_OUT` | default output directory |
| `FABULA_GENERATION_RETRIES` | default per-stage attempts |

## Pipeline

Generation is staged, and every stage is parsed and validated before the next one starts:

1. `settings -> world`
2. `world -> cast`
3. `world + cast -> truth + clues`
4. `world + cast + clues + npc_id -> identity + memory`, once per NPC

The culprit stage also receives `truth`; every other NPC prompt excludes it. The bundle is written to a temporary sibling directory and atomically swapped into place only after the complete bundle passes Pydantic and `validate_bundle()` checks. A failed run leaves any previous bundle untouched.

Each stage retries only on validation failure, up to the configured attempt count. Model/setup failures are terminal and are reported with a user-safe error.

## Constrained decoding and repair

The local backend compiles one JSON-schema grammar per stage from the frozen Pydantic models. Two llama.cpp-specific safeguards are applied before compilation:

- `pattern`, `minLength` and schema metadata are removed from the grammar. `maxLength` is capped at 300 characters instead of being dropped: llama.cpp expands `maxLength` into nested optional groups, and the original 400/4000-character limits caused a grammar-compiler stack overflow. The cap keeps outputs bounded and the grammar small; Pydantic still enforces the original limits. Array cardinality (`minItems`/`maxItems`) is retained so the model cannot emit too few locations, NPCs, clues or accusation options.
- For NPC stages, `identity.id`, `memory.npc_id` and every `fact.who` are pinned to the requested NPC id with an enum. This prevents cross-NPC ownership and keeps memory files isolated.

Two final-validation repairs are applied after all stages, because a small model occasionally omits a structurally required culprit detail:

- If the culprit memory has no secret `did` fact, a truth-backed account fact is added. Its content comes from `truth.json` (crime type/target/location and the solution's "how"), and it is marked `secret` with `hide` disclosure.
- If no clue implies a culprit-owned fact, the crime-scene clue (preferring an `examine` clue) is linked to the culprit's account fact.

These repairs run only in the engine, never in a prompt, and only after the model has produced the rest of the bundle. They guarantee that a generated case is solvable and never make `truth.json` visible to the player or to any NPC prompt.

## Output

```text
<out>/
  world.json
  truth.json          # engine-only
  clues.json
  npcs/<npc_id>/identity.json
  npcs/<npc_id>/memory.json
```

`truth.json` is engine-only. It is used to validate the bundle and for the accusation check; it is never passed to a non-culprit prompt and is not read by the play-phase conversation prompt assembler.

## Benchmark

The fixture benchmark needs no model:

```powershell
python evaluation/generation_benchmark.py --out evaluation/results/generation_fixture.json
```

Real mode is opt-in and requires the verified GGUF:

```powershell
$env:FABULA_MODEL_TESTS = "1"
python evaluation/generation_benchmark.py --real --type theft --seed 1 --out evaluation/results/generation_real.json
```

The report records hardware, model path/hash/manifest, per-stage elapsed time, prompt/output tokens, attempts, retries and failures. `evaluation/results/` is gitignored; attach the report to the WP-E PR or the evaluation deliverable rather than committing it.

Generation is CPU-heavy. On a 4-vCPU reference machine a full six-NPC run can take tens of minutes, longer than the HG-16 target; reduce `FABULA_MODEL_CTX` only if prompts still fit, and keep the loading screen free of time promises until HA-03 numbers are final.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `model artifact not found` | Place the GGUF at `models/...` or set `FABULA_MODEL_PATH`. |
| `llama-cpp-python is not installed` | Run the CPU-wheel install command above. |
| `SHA-256 mismatch` | Replace or re-download the artifact; update the manifest only for an intentional new build. |
| `prompt uses N tokens but n_ctx is M` | Raise `FABULA_MODEL_CTX` or shorten the stage input; do not silently truncate. |
| `cannot compile a JSON-schema grammar` | The schema contains a construct llama.cpp cannot compile; simplify the schema before changing the prompt or model. |
| Stage exhausted after retries | Inspect the reported validation detail. A malformed stage is retried; a setup or context failure is not. |
| Final bundle validation fails | The run publishes nothing. Repairable culprit-account/evidence issues are handled automatically; other cross-stage inconsistencies mean the model output is unusable and generation must be retried. |

## Tests

Offline coverage:

```powershell
python -m pytest -q tests/test_local_runner.py tests/test_generation_cli.py tests/test_generation_config.py tests/test_generation_prompts.py tests/test_generation_benchmark.py tests/test_orchestrator.py
python -m ruff check .
python -m ruff format --check .
```

The real artifact is never required by the normal test suite.
