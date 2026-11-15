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
    subparsers = parser.add_subparsers(dest="command", required=True)

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

    play = subparsers.add_parser("play", help="launch and play a generated mystery case")
    play.add_argument(
        "--bundle",
        type=Path,
        default=Path("bundles/latest"),
        help="bundle directory to play (default: bundles/latest)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            return run_generate(args)
        if args.command == "kaggle":
            return run_kaggle_batch(args)
        if args.command == "model" and args.model_command == "check":
            return run_model_check(args)
        if args.command == "play":
            from fabula.conversation import ConversationConfig, create_conversation_service
            from fabula.simulation import Session, load_bundle
            from fabula.ui.app import FabulaApp

            loaded = load_bundle(args.bundle)
            session = Session(loaded)
            service = create_conversation_service(ConversationConfig(mode="scripted"))
            app = FabulaApp(session=session, conversation_service=service)
            app.run()
            return 0
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
