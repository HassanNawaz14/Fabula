"""Direct entrypoint for python -m fabula.server."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fabula.server.app import run_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Fabula 3D Noir web server.")
    parser.add_argument(
        "--bundle",
        type=Path,
        default=Path("bundles/latest"),
        help="Path to mystery bundle directory (default: bundles/latest)",
    )
    parser.add_argument(
        "--web-dir",
        type=Path,
        default=Path("web"),
        help="Path to web directory (default: web)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port number (default: 8000)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the browser",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="auto",
        choices=["auto", "live", "scripted"],
        help="Conversation mode (default: auto)",
    )

    parser.add_argument(
        "--gemini-key",
        "--api-key",
        dest="api_key",
        type=str,
        default=None,
        help="Gemini API key for live conversation (e.g. AIzaSy...)",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.api_key:
        import os

        os.environ["GEMINI_API_KEY"] = args.api_key

    bundle_path = args.bundle
    if not bundle_path.exists():
        fallback = Path("tests/fixtures/valid_bundle")
        if fallback.exists():
            bundle_path = fallback

    run_server(
        bundle_path=bundle_path,
        web_dir=args.web_dir,
        host=args.host,
        port=args.port,
        auto_open=not args.no_browser,
        conversation_mode=args.mode,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
