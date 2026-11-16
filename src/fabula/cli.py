"""Root command line entry point for Fabula."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from fabula.generation.cli import (
    add_generation_arguments,
    add_kaggle_arguments,
    run_generate,
    run_kaggle_batch,
    run_model_check,
)
from fabula.generation.errors import GenerationError, GenerationSetupError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fabula",
        description="Fabula mystery game: local generation and play.",
    )
    subparsers = parser.add_subparsers(dest="command")

    generate = subparsers.add_parser("generate", help="generate a validated game bundle")
    add_generation_arguments(generate)

    kaggle = subparsers.add_parser("kaggle", help="generate one or more cases on your Kaggle GPU")
    add_kaggle_arguments(kaggle)

    model = subparsers.add_parser("model", help="model artifact utilities")
    model_subparsers = model.add_subparsers(dest="model_command", required=True)
    check = model_subparsers.add_parser("check", help="verify the local GGUF artifact")
    check.add_argument(
        "--model",
        type=Path,
        default=None,
        help="GGUF path (default: FABULA_MODEL_PATH or the bundled model path)",
    )
    check.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="model manifest path (default: models/model_manifest.json)",
    )

    play = subparsers.add_parser("play", help="launch the game or play a ready case")
    play.add_argument(
        "--bundle",
        type=Path,
        default=None,
        help="case directory to load directly (default: bundles/latest, else the start menu)",
    )
    return parser


def run_game() -> int:
    """Launch the game at its start menu, where every route is available."""
    from fabula.ui.app import FabulaApp

    FabulaApp(start_menu=True).run()
    return 0


def run_play(bundle: Path | None) -> int:
    from fabula.conversation import config_from_env, create_conversation_service
    from fabula.simulation import Session, load_bundle
    from fabula.ui.app import FabulaApp

    if bundle is None:
        latest = Path("bundles/latest")
        if not latest.exists():
            return run_game()
        bundle = latest
    if not bundle.exists():
        raise ValueError(f"case not found at {bundle}")

    loaded = load_bundle(bundle)
    session = Session(loaded)
    service = create_conversation_service(config_from_env())
    app = FabulaApp(session=session, conversation_service=service)
    app.run()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command is None:
            return run_game()
        if args.command == "generate":
            return run_generate(args)
        if args.command == "kaggle":
            return run_kaggle_batch(args)
        if args.command == "model" and args.model_command == "check":
            return run_model_check(args)
        if args.command == "play":
            return run_play(args.bundle)
        parser.error("unknown command")
    except GenerationSetupError as exc:
        print(f"setup error: {exc}", file=sys.stderr)
        return 2
    except GenerationError as exc:
        print(f"generation failed: {exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("cancelled", file=sys.stderr)
        return 130
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2
