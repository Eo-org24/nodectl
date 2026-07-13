"""Minimal fixture-runner scaffold for Phase 0.

Implements the W-001 repo scaffold needed before D5/D13 harness behavior exists.
The only supported path in this scaffold is `--harness-only`, which allows the
builder protocol check to pass without inventing W-002 functionality early.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Create the scaffold CLI surface reserved for W-002."""

    parser = argparse.ArgumentParser(description="sx fixture runner scaffold")
    parser.add_argument("fixture_path", nargs="?")
    parser.add_argument("--repeat", type=int)
    parser.add_argument(
        "--harness-only",
        action="store_true",
        help="Validate that the harness entrypoint exists without calling a model.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the scaffold entrypoint.

    Implements D2's judgment/execution boundary conservatively by refusing every
    non-harness path until W-002 adds the real fixture harness.
    """

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.harness_only:
        return 0
    parser.error("W-002 fixture harness not implemented; use --harness-only")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
