"""Command-line entry point for Power Query Quack.

Phase 0 provides ``version`` and ``serve`` so the package is usable from the
shell immediately. Conversion subcommands arrive with the engine in later phases.
"""

from __future__ import annotations

import argparse
import sys

from pqquack import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pqquack",
        description="Power Query Quack — from M to DuckDB, one quack at a time.",
    )
    parser.add_argument("--version", action="version", version=f"pqquack {__version__}")

    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Run the beta web/API server.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "serve":
        import uvicorn

        uvicorn.run("pqquack.api.app:app", host=args.host, port=args.port)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
