"""CLI handlers for local generation and model artifact checks."""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
from pathlib import Path

from fabula.generation.config import (
    config_from_env,
    load_model_manifest,
    manifest_sha256,
    resolve_fast_model_path,
    resolve_model_path,
    verify_model_artifact,
)
from fabula.generation.errors import GenerationSetupError
from fabula.generation.local_runner import LocalModelRunner
from fabula.generation.orchestrator import generate_bundle, generate_neurosymbolic_bundle
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
    parser.add_argument(
        "--fast",
        dest="fast_mode",
        action="store_true",
        default=False,
        help="use fast Neurosymbolic generation pipeline (<7s)",
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
    elif event.kind == "bundle_notice":
        print(f"[bundle] notice: {event.detail}", flush=True)
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

    if getattr(args, "fast_mode", False):
        runner: LocalModelRunner | None = None
        model_to_use: Path | None = None
        if args.model is not None:
            model_to_use = resolve_model_path(args.model)
        elif not os.environ.get("PYTEST_CURRENT_TEST"):
            fast_model = resolve_fast_model_path()
            if fast_model.is_file():
                model_to_use = fast_model

        if model_to_use is not None and model_to_use.is_file():
            runner = LocalModelRunner(model_to_use, config)

        try:
            result = generate_neurosymbolic_bundle(
                settings,
                model_runner=runner,
                output_dir=config.output_dir,
                seed=seed,
                on_progress=_print_progress,
            )
        finally:
            if runner is not None:
                runner.close()
    else:
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
    print(f"Blueprint: {result.blueprint_source}")
    if result.fallback_reason:
        print(f"Fallback: {result.fallback_reason}")
    print(f"Bundle: {result.bundle_dir}")
    print(f"Elapsed: {result.elapsed_seconds:.1f}s")
    print(f"Stage attempts: {attempts}")
    return 0


def add_kaggle_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="number of cases to generate in this batch (default: 1)",
    )
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
        help="first seed; later cases use seed+1, seed+2, ... (default: random per case)",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="stop the batch after the first failed case",
    )


def run_kaggle_batch(args: argparse.Namespace) -> int:
    from fabula.case_library import library_root, unique_case_id
    from fabula.generation.kaggle_runner import kaggle_settings_from_env, run_kaggle_case

    if args.count < 1:
        raise ValueError("--count must be at least 1")
    settings = kaggle_settings_from_env()
    generation = GenerationSettings(
        mystery_type=args.mystery_type,
        tone=args.tone,
        difficulty=args.difficulty,
    )
    failures = 0
    for index in range(args.count):
        if args.seed is not None:
            seed = args.seed + index
        else:
            seed = random.SystemRandom().randrange(2**31)
        destination = library_root() / unique_case_id(f"kaggle_{time.strftime('%Y%m%d_%H%M%S')}")
        print(
            f"[{index + 1}/{args.count}] seed={seed} target={destination}",
            flush=True,
        )
        try:
            run_kaggle_case(
                settings,
                generation,
                seed=seed,
                destination=destination,
                emit=lambda message: print(f"    {message}", flush=True),
            )
        except Exception as exc:  # noqa: BLE001 - one bad case must not stop the batch
            failures += 1
            print(f"[{index + 1}/{args.count}] failed: {exc}", file=sys.stderr, flush=True)
            if args.stop_on_error:
                break
        else:
            print(f"[{index + 1}/{args.count}] ready: {destination}", flush=True)

    if failures:
        print(
            f"{failures} of {args.count} case(s) failed. Finished cases stay in {library_root()}.",
            file=sys.stderr,
        )
        return 3
    return 0


def run_model_check(args: argparse.Namespace) -> int:
    path = resolve_model_path(args.model)
    manifest = load_model_manifest(getattr(args, "manifest", None))
    expected = manifest_sha256(manifest, filename=path.name)
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
