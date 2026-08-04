"""CLI entry point for locust-kit analyze (pre-development TDD stub, v1.6.0).

Mirrors the ``cli.py`` / ``cli_gen.py`` pattern: argparse, ``_build_parser()``,
``main(argv=None) -> int``. The parser (interface) is fully defined so
interface tests pass immediately; ``main`` raises ``NotImplementedError`` until
the developer implements the analysis pipeline per ``analysis/analysis-brief.md``
§4.2 (flags, formats, exit codes 0/1/2).

Usage:
    locust-kit analyze --csv <prefix>
                      [--slo KEY=VALUE ...]
                      [--baseline <prior-prefix|baseline-name>]
                      [--format markdown|json]
                      [--output PATH|-]
                      [--llm]
                      [--version]
"""

from __future__ import annotations

import argparse
import sys

__version__ = "1.6.0"


def _build_parser() -> argparse.ArgumentParser:
    """Build the locust-kit argument parser with the analyze subcommand."""
    parser = argparse.ArgumentParser(
        prog="locust-kit",
        description="AI performance intelligence for Locust CSV runs",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    analyze = sub.add_parser("analyze", help="Analyze a Locust CSV run and produce insights")
    analyze.add_argument(
        "--csv", default=None,
        help="Locust CSV prefix (requires {prefix}_stats.csv)",
    )
    analyze.add_argument(
        "--slo", action="append", default=[], metavar="KEY=VALUE",
        help="SLO as KEY=VALUE (p95/p99 in ms, error_rate as ratio); repeatable",
    )
    analyze.add_argument(
        "--baseline", default=None,
        help="Prior-run CSV prefix or stored baseline name (.baselines/<name>.json)",
    )
    analyze.add_argument(
        "--format", default="markdown",
        help="Report format: markdown|json (default: markdown)",
    )
    analyze.add_argument(
        "--output", default="-",
        help="Output file path, or '-' for stdout (default: -)",
    )
    analyze.add_argument(
        "--llm", action="store_true", default=False,
        help="Enable OpenAI-compatible LLM enrichment (opt-in; clean statistical fallback)",
    )
    analyze.add_argument(
        "--version", action="version", version=f"locust-kit {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: exit 0 = OK, 1 = usage/IO/parse error, 2 = SLO violated."""
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
