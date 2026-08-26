"""
Unified CLI Entry Point for AURA (aura.exe / python -m aura).
"""

from __future__ import annotations

import argparse
import sys

from aura.cli.agent_cli import add_agent_subparsers
from aura.cli.doctor import main as doctor_main
from aura.core.version import __app_name__, __version__


def build_parser() -> argparse.ArgumentParser:
    """Construct top-level CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="aura",
        description=f"{__app_name__} — Production Endpoint Security & Privacy Platform",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{__app_name__} v{__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=False)

    # 1. aura doctor
    p_doc = subparsers.add_parser("doctor", help="Run system diagnostics and verify environment")
    p_doc.add_argument("-v", "--verbose", action="store_true", help="Detailed check output")
    p_doc.add_argument("--json", action="store_true", help="Output diagnostics as JSON")
    p_doc.set_defaults(func=lambda args: doctor_main((["-v"] if args.verbose else []) + (["--json"] if args.json else [])))

    # 2. aura agent ...
    add_agent_subparsers(subparsers)

    return parser


def main(args: list[str] | None = None) -> int:
    """Main CLI execution routine."""
    parser = build_parser()
    parsed = parser.parse_args(args)

    if not hasattr(parsed, "func") or parsed.command is None:
        # Default behavior when run with no arguments: Start AURA Runtime
        from aura.runtime import main as runtime_main
        return runtime_main()

    try:
        res = parsed.func(parsed)
        return int(res) if res is not None else 0
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
