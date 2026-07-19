"""CLI entry point for locust-report.

Generates performance reports from Locust CSV output in various formats:
HTML (default), JSON, Markdown, JUnit XML.

Usage:
    locust-report <csv_prefix> [--format html|json|markdown|junit] [--output PATH]
                 [--p95-threshold MS] [--p99-threshold MS] [--version]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from locust_templates.exporters import (
    HTMLExporter,
    JSONExporter,
    JUnitXMLExporter,
    MarkdownExporter,
)
from locust_templates.report_data import ReportData

__version__ = "1.2.0"

_EXPORTERS = {
    "html": HTMLExporter,
    "json": JSONExporter,
    "markdown": MarkdownExporter,
    "junit": JUnitXMLExporter,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="locust-report",
        description="Generate performance reports from Locust CSV output.",
    )
    parser.add_argument(
        "csv_prefix",
        nargs="?",
        help="Prefix path for Locust CSV files (e.g. 'results' for results_stats.csv)",
    )
    parser.add_argument(
        "--format",
        default="html",
        help="Output format: html, json, markdown, junit (default: html)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path. Use '-' for stdout. Default: stdout for json/markdown",
    )
    parser.add_argument(
        "--p95-threshold",
        type=float,
        default=None,
        help="p95 response time threshold in ms (exceed → FAIL)",
    )
    parser.add_argument(
        "--p99-threshold",
        type=float,
        default=None,
        help="p99 response time threshold in ms (exceed → FAIL)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"locust-report {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Argument list (None → sys.argv[1:]).

    Returns:
        Exit code: 0 success, 1 error, 2 threshold violation.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # csv_prefix is required for actual report generation
    if args.csv_prefix is None:
        print(
            "error: the following arguments are required: csv_prefix",
            file=sys.stderr,
        )
        return 1

    # Validate format
    if args.format not in _EXPORTERS:
        print(f"error: unsupported format '{args.format}'", file=sys.stderr)
        return 1

    # Build thresholds dict
    thresholds: dict[str, float] | None = None
    if args.p95_threshold is not None or args.p99_threshold is not None:
        thresholds = {}
        if args.p95_threshold is not None:
            thresholds["p95"] = args.p95_threshold
        if args.p99_threshold is not None:
            thresholds["p99"] = args.p99_threshold

    # Load data
    try:
        data = ReportData.from_csv(args.csv_prefix, thresholds=thresholds)
    except FileNotFoundError:
        print(
            f"error: CSV file not found for prefix '{args.csv_prefix}'",
            file=sys.stderr,
        )
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Render
    exporter_cls = _EXPORTERS[args.format]
    exporter = exporter_cls()
    content = exporter.render(data)

    # Output
    output = args.output
    if output is None or output == "-":
        print(content)
    else:
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")

    # Check threshold violations → exit code 2
    if thresholds is not None:
        for ep in data.endpoints:
            if ep.threshold_status == "FAIL":
                return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
