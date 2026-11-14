"""Benchmark staged local generation with an offline fixture or the real GGUF.

Offline (default) uses MockModelRunner and requires no model, network, or GPU:

    python evaluation/generation_benchmark.py

Real mode is opt-in and requires the verified local artifact:

    $env:FABULA_MODEL_TESTS = "1"
    python evaluation/generation_benchmark.py --real --type theft --seed 1
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from fabula.generation import (
    GenerationConfig,
    GenerationError,
    GenerationSetupError,
    LocalModelRunner,
    MockModelRunner,
    RetryPolicy,
    config_from_env,
    generate_bundle,
    load_model_manifest,
    manifest_sha256,
    resolve_mystery_type,
    sha256_file,
)
from fabula.generation.bundle_io import publish_bundle
from fabula.generation.protocols import StageName
from fabula.schemas import GenerationSettings
from fabula.training_data import generate_skeleton

DEFAULT_REPORT_PATH = Path("evaluation") / "results" / "generation_benchmark.json"
REQUIRED_REPORT_KEYS = {
    "mode",
    "generated_at",
    "model",
    "hardware",
    "stages",
    "calls",
    "totals",
}


class TimedRunner:
    """Wrap a ModelRunner and record per-call timing and token statistics."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.calls: list[dict[str, object]] = []

    def generate(
        self,
        stage: StageName,
        stage_input: BaseModel,
        output_model: type[BaseModel],
        seed: int,
    ) -> str:
        start = time.perf_counter()
        try:
            text = self.inner.generate(stage, stage_input, output_model, seed)
        except Exception as exc:
            self.calls.append(
                {
                    "stage": stage,
                    "npc_id": getattr(stage_input, "npc_id", None),
                    "elapsed_seconds": round(time.perf_counter() - start, 4),
                    "error": str(exc),
                }
            )
            raise
        stats = getattr(self.inner, "last_stats", {})
        self.calls.append(
            {
                "stage": stage,
                "npc_id": getattr(stage_input, "npc_id", None),
                "elapsed_seconds": round(time.perf_counter() - start, 4),
                "prompt_tokens": stats.get("prompt_tokens"),
                "output_tokens": stats.get("output_tokens"),
            }
        )
        return text

    def close(self) -> None:
        close = getattr(self.inner, "close", None)
        if callable(close):
            close()


def _hardware(config: GenerationConfig) -> dict[str, object]:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "n_threads": config.n_threads,
        "n_ctx": config.n_ctx,
    }


def _model_section(mode: str, config: GenerationConfig) -> dict[str, object]:
    if mode != "real":
        return {
            "mode": "fixture",
            "path": None,
            "sha256": None,
            "size_bytes": None,
            "manifest": None,
        }
    manifest = load_model_manifest()
    return {
        "mode": "real",
        "path": str(config.model_path),
        "sha256": sha256_file(config.model_path),
        "size_bytes": config.model_path.stat().st_size,
        "manifest_sha256": manifest_sha256(manifest),
        "manifest": manifest,
    }


def _aggregate_stages(
    result_stages: tuple[Any, ...],
    calls: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str | None], dict[str, object]] = {}
    for call in calls:
        key = (str(call["stage"]), call.get("npc_id"))  # type: ignore[arg-type]
        entry = grouped.setdefault(
            key,
            {
                "stage": call["stage"],
                "npc_id": call.get("npc_id"),
                "calls": 0,
                "elapsed_seconds": 0.0,
                "prompt_tokens": 0,
                "output_tokens": 0,
                "failures": 0,
            },
        )
        entry["calls"] = int(entry["calls"]) + 1
        entry["elapsed_seconds"] = round(
            float(entry["elapsed_seconds"]) + float(call.get("elapsed_seconds", 0.0)), 4
        )
        entry["prompt_tokens"] = int(entry["prompt_tokens"]) + int(call.get("prompt_tokens") or 0)
        entry["output_tokens"] = int(entry["output_tokens"]) + int(call.get("output_tokens") or 0)
        if call.get("error"):
            entry["failures"] = int(entry["failures"]) + 1

    attempts = {
        (record.stage, getattr(record, "npc_id", None)): record.attempts for record in result_stages
    }
    for entry in grouped.values():
        key = (str(entry["stage"]), entry.get("npc_id"))  # type: ignore[arg-type]
        entry["attempts"] = attempts.get(key, entry["calls"])
        entry["retries"] = max(0, int(entry["attempts"]) - 1)
    return sorted(
        grouped.values(),
        key=lambda entry: (str(entry["stage"]), str(entry.get("npc_id") or "")),
    )


def validate_report(report: dict[str, object]) -> None:
    missing = REQUIRED_REPORT_KEYS - set(report)
    if missing:
        raise ValueError(f"benchmark report missing keys: {sorted(missing)}")
    if not isinstance(report["stages"], list):
        raise ValueError("benchmark report stages must be a list")
    if not isinstance(report["calls"], list):
        raise ValueError("benchmark report calls must be a list")
    for key in ("model", "hardware", "totals"):
        if not isinstance(report[key], dict):
            raise ValueError(f"benchmark report {key} must be an object")


def run_benchmark(
    *,
    real: bool,
    settings: GenerationSettings,
    seed: int,
    config: GenerationConfig,
    bundle_out: Path | None = None,
) -> dict[str, object]:
    mode = "real" if real else "fixture"
    if real:
        inner = LocalModelRunner(config.model_path, config)
    else:
        resolved = resolve_mystery_type(settings.mystery_type, seed)
        inner = MockModelRunner(
            generate_skeleton(
                resolved,
                seed,
                tone=settings.tone,
                difficulty=settings.difficulty,
            )
        )
    timed = TimedRunner(inner)

    with tempfile.TemporaryDirectory(prefix="fabula-benchmark-") as temp_dir:
        try:
            result = generate_bundle(
                settings,
                timed,
                Path(temp_dir) / "bundle",
                seed=seed,
                retry_policy=RetryPolicy(config.retry_attempts),
            )
        finally:
            timed.close()

        stages = _aggregate_stages(result.stage_attempts, timed.calls)
        failures = [call for call in timed.calls if call.get("error")]
        published = (
            publish_bundle(result.bundle, bundle_out) if bundle_out is not None else None
        )
        report: dict[str, object] = {
            "mode": mode,
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "bundle": str(published) if published is not None else None,
            "settings": {
                "mystery_type": settings.mystery_type.value,
                "tone": settings.tone.value,
                "difficulty": settings.difficulty.value,
                "seed": seed,
                "resolved_type": result.resolved_type.value,
            },
            "model": _model_section(mode, config),
            "hardware": _hardware(config),
            "stages": stages,
            "calls": timed.calls,
            "totals": {
                "elapsed_seconds": round(result.elapsed_seconds, 4),
                "calls": len(timed.calls),
                "stage_attempts": sum(record.attempts for record in result.stage_attempts),
                "retries": sum(record.attempts - 1 for record in result.stage_attempts),
                "failures": len(failures),
            },
        }
    validate_report(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real", action="store_true", help="use the local GGUF instead of the fixture"
    )
    parser.add_argument(
        "--type",
        dest="mystery_type",
        choices=("theft", "disappearance", "murder", "random"),
        default="theft",
    )
    parser.add_argument("--tone", choices=("cozy", "neutral", "dark"), default="cozy")
    parser.add_argument("--difficulty", choices=("easy", "normal", "hard"), default="easy")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument(
        "--bundle-out",
        type=Path,
        default=None,
        help="optional path to publish the generated bundle",
    )
    parser.add_argument("--model", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.real and os.environ.get("FABULA_MODEL_TESTS") != "1":
        print(
            "real benchmark requires FABULA_MODEL_TESTS=1 and a verified local GGUF",
            file=sys.stderr,
        )
        return 2

    config = config_from_env(model_path=args.model)
    settings = GenerationSettings(
        mystery_type=args.mystery_type,
        tone=args.tone,
        difficulty=args.difficulty,
    )
    try:
        report = run_benchmark(
            real=args.real,
            settings=settings,
            seed=args.seed,
            config=config,
            bundle_out=args.bundle_out,
        )
    except GenerationSetupError as exc:
        print(f"benchmark setup failed: {exc}", file=sys.stderr)
        return 2
    except GenerationError as exc:
        print(f"benchmark failed: {exc}", file=sys.stderr)
        return 3

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {args.out}")
    print(f"Mode: {report['mode']}")
    print(f"Elapsed: {report['totals']['elapsed_seconds']}s")
    print(f"Calls: {report['totals']['calls']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
