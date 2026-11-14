"""CLI handlers for local generation and model artifact checks."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from fabula.generation.config import (
    config_from_env,
    load_model_manifest,
    manifest_sha256,
    resolve_model_path,
    verify_model_artifact,
)
from fabula.generation.errors import GenerationSetupError
from fabula.generation.local_runner import LocalModelRunner
from fabula.generation.orchestrator import generate_bundle
from fabula.generation.protocols import ProgressEvent
from fabula.generation.retries import RetryPolicy
from fabula.schemas import GenerationSettings


def add_generation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--type",
        dest="mystery_type",
        choices=("theft", "disappearance", "murder", "random"),
        default="random",
        help="mystery type (default: random, resolved deterministically by seed)",
    )
    parser.add_argument(
        "--tone",
        choices=("cozy", "neutral", "dark"),
        default="cozy",
        help="tone (default: cozy)",
    )
    parser.add_argument(
        "--difficulty",
        choices=("easy", "normal", "hard"),
        default="normal",
        help="difficulty (default: normal)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="deterministic generation seed (default: random 31-bit seed, printed)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="bundle output directory (default: bundles/latest or FABULA_GENERATION_OUT)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=None,
        help="per-stage retry attempts (default: 3 or FABULA_GENERATION_RETRIES)",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=None,
        help="GGUF path (default: FABULA_MODEL_PATH or models/Qwen2.5-3B-Instruct.Q4_K_M.gguf)",
    )


def _print_progress(event: ProgressEvent) -> None:
    stage = event.stage or "bundle"
    suffix = f" {event.detail}" if event.detail else ""
    if event.kind == "stage_started":
        print(f"[{stage}] started{suffix}", flush=True)
    elif event.kind == "stage_attempt":
        print(f"[{stage}] attempt {event.attempt}{suffix}", flush=True)
    elif event.kind == "stage_succeeded":
        print(f"[{stage}] ok after {event.attempt} attempt(s){suffix}", flush=True)
    elif event.kind == "bundle_published":
        print(f"[bundle] published to {event.detail}", flush=True)


def run_generate(args: argparse.Namespace) -> int:
    config = config_from_env(
        model_path=args.model,
        output_dir=args.out,
        retry_attempts=args.retries,
    )
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(2**31)
    print(f"Seed: {seed}", flush=True)

    settings = GenerationSettings(
        mystery_type=args.mystery_type,
        tone=args.tone,
        difficulty=args.difficulty,
    )
    runner = LocalModelRunner(config.model_path, config)
    try:
        result = generate_bundle(
            settings,
            runner,
            config.output_dir,
            seed=seed,
            retry_policy=RetryPolicy(config.retry_attempts),
            on_progress=_print_progress,
        )
    finally:
        runner.close()

    attempts = sum(record.attempts for record in result.stage_attempts)
    print(f"Resolved type: {result.resolved_type.value}")
    print(f"Bundle: {result.bundle_dir}")
    print(f"Elapsed: {result.elapsed_seconds:.1f}s")
    print(f"Stage attempts: {attempts}")
    return 0


def run_model_check(args: argparse.Namespace) -> int:
    path = resolve_model_path(args.model)
    manifest = load_model_manifest(getattr(args, "manifest", None))
    expected = manifest_sha256(manifest)
    try:
        computed = verify_model_artifact(path, expected_sha256=expected)
    except GenerationSetupError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    size = path.stat().st_size
    print(f"Model: {path}")
    print(f"Size: {size:,} bytes ({size / (1024**3):.2f} GiB)")
    print(f"SHA-256: {computed}")
    if expected is None:
        print("Expected: unknown (model manifest not found)")
        print("PASS (no expected checksum to compare)")
    else:
        print(f"Expected: {expected}")
        print("PASS")
    return 0
