"""CLI entry point for locust-kit analyze — AI performance intelligence.

Implements the ``locust-kit analyze`` contract from analysis/analysis-brief.md
§4.2 (flags, formats, exit codes 0/1/2). Mirrors the ``cli.py`` / ``cli_gen.py``
pattern: argparse, ``_build_parser()``, ``main(argv=None) -> int``.

Usage:
    locust-kit analyze --csv <prefix>
                      [--slo KEY=VALUE ...]
                      [--baseline <prior-prefix|baseline-name>]
                      [--format markdown|json]
                      [--output PATH|-]
                      [--llm]
                      [--version]

Exit codes: 0 = OK (or advisory, no SLOs), 1 = usage/IO/parse error,
2 = measured SLO violation (CI gate signal).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from locust_templates.intelligence import analyze_run

__version__ = "1.6.0"

_VALID_FORMATS = ("markdown", "json")
_VALID_SLO_KEYS = ("p95", "p99", "error_rate")


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
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1
    if args.command != "analyze":
        parser.print_help()
        return 1
    if not args.csv:
        print("error: --csv is required", file=sys.stderr)
        return 1
    if args.format not in _VALID_FORMATS:
        print(f"error: unsupported format '{args.format}' (choose markdown or json)", file=sys.stderr)
        return 1

    slos: dict[str, float] = {}
    for item in args.slo:
        try:
            key, value = item.split("=", 1)
            slos[key.strip()] = float(value)
        except ValueError:
            print(f"error: invalid --slo '{item}' (expected KEY=VALUE)", file=sys.stderr)
            return 1
    invalid = set(slos) - set(_VALID_SLO_KEYS)
    if invalid:
        print(
            f"error: invalid SLO key(s): {sorted(invalid)} (valid: {', '.join(_VALID_SLO_KEYS)})",
            file=sys.stderr,
        )
        return 1

    try:
        report = analyze_run(
            args.csv,
            slos=slos or None,
            baseline_prefix=args.baseline,
            use_llm=args.llm,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    content = (
        json.dumps(report.to_json(), indent=2)
        if args.format == "json"
        else report.to_markdown()
    )
    if args.output == "-":
        print(content)
    else:
        try:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content, encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot write output '{args.output}': {exc}", file=sys.stderr)
            return 1

    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
