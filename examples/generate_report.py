"""Generate performance reports from Locust CSV output in all formats.

Demonstrates the v1.2.0 cross-platform report export system:
  - HTML (self-contained, browser-viewable)
  - JSON (machine-parseable, API/dashboards)
  - Markdown (GitHub PR comments)
  - JUnit XML (CI test runner integration)

Usage:
    # After running a load test with CSV output:
    locust -f examples/api_load_test.py --headless --users 50 --spawn-rate 5 \\
        --run-time 2m --host http://localhost:8080 --csv results

    # Generate all report formats:
    python examples/generate_report.py results

    # Use test fixtures (no test run needed):
    python examples/generate_report.py tests/fixtures/sample

    # Generate a single format:
    python examples/generate_report.py results --format json

    # With custom output directory:
    python examples/generate_report.py results --output-dir reports/2026-07
"""

import argparse
import sys
from pathlib import Path

# Ensure src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from locust_templates.exporters import (
    HTMLExporter,
    JSONExporter,
    JUnitXMLExporter,
    MarkdownExporter,
)
from locust_templates.report_data import ReportData
from locust_templates.runner import generate_report

# Format -> (exporter class, file extension, description)
FORMATS = [
    ("html", HTMLExporter, ".html", "Self-contained HTML report"),
    ("json", JSONExporter, ".json",
     "Structured JSON for APIs and dashboards"),
    ("markdown", MarkdownExporter, ".md",
     "GitHub-flavored Markdown for PR comments"),
    ("junit", JUnitXMLExporter, ".xml", "JUnit XML for CI test runners"),
]


def generate_all_formats(
    csv_prefix: str,
    output_dir: str,
    thresholds: dict[str, float] | None = None,
) -> None:
    """Generate reports in all four formats using the Python API.

    Shows two approaches:
      1. High-level: runner.generate_report() -- one-call convenience
      2. Low-level: ReportData + exporter.export() -- full control
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if thresholds is None:
        _thresholds: dict[str, float] = {"p95": 500, "p99": 1000}
    else:
        _thresholds = thresholds

    print(f"Generating reports from: {csv_prefix}")
    print(f"Output directory: {output_path.resolve()}")
    p95 = _thresholds.get("p95", "none")
    p99 = _thresholds.get("p99", "none")
    print(f"Thresholds: p95={p95}ms, p99={p99}ms")
    print()

    # -- Approach 1: High-level generate_report() for HTML ---------------
    html_path = generate_report(
        csv_prefix,
        output_path / "report.html",
        fmt="html",
        thresholds=_thresholds,
    )
    print(f"  HTML:      {html_path}")

    # -- Approach 2: Low-level ReportData + exporters for other formats --
    # Parse once, render multiple formats from the same ReportData
    data = ReportData.from_csv(csv_prefix, thresholds=_thresholds)

    json_exporter = JSONExporter()
    json_path = json_exporter.export(data, output_path / "report.json")
    print(f"  JSON:      {json_path}")

    md_exporter = MarkdownExporter()
    md_path = md_exporter.export(data, output_path / "report.md")
    print(f"  Markdown:  {md_path}")

    junit_exporter = JUnitXMLExporter()
    junit_path = junit_exporter.export(
        data, output_path / "junit-results.xml",
    )
    print(f"  JUnit XML: {junit_path}")

    print()
    print("All formats generated successfully.")

    # Show threshold summary if thresholds were provided
    if _thresholds:
        failed = [
            ep for ep in data.endpoints
            if ep.threshold_status == "FAIL"
        ]
        passed = [
            ep for ep in data.endpoints
            if ep.threshold_status == "PASS"
        ]
        print()
        print(
            f"Threshold results: {len(passed)} passed,"
            f" {len(failed)} failed",
        )
        if failed:
            print("  Failed endpoints:")
            for ep in failed:
                print(
                    f"    {ep.name}:"
                    f" p95={ep.percentile_95:.0f}ms,"
                    f" p99={ep.percentile_99:.0f}ms",
                )


def generate_single_format(
    csv_prefix: str,
    fmt: str,
    output_dir: str,
    thresholds: dict[str, float] | None = None,
) -> None:
    """Generate a single report format using the runner helper."""
    extensions = {
        "html": ".html", "json": ".json",
        "markdown": ".md", "junit": ".xml",
    }
    ext = extensions.get(fmt, ".txt")
    filename = f"report{ext}"
    output_path = Path(output_dir) / filename

    path = generate_report(
        csv_prefix, output_path, fmt=fmt, thresholds=thresholds,
    )
    print(f"Generated {fmt.upper()} report: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate performance reports from Locust CSV output.",
    )
    parser.add_argument(
        "csv_prefix",
        help="Prefix path for Locust CSV files"
             " (e.g. 'results' for results_stats.csv)",
    )
    parser.add_argument(
        "--format",
        default="all",
        help="Output format: html, json, markdown, junit,"
             " or all (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Output directory (default: reports/)",
    )
    parser.add_argument(
        "--p95-threshold",
        type=float,
        default=500,
        help="p95 threshold in ms (default: 500)",
    )
    parser.add_argument(
        "--p99-threshold",
        type=float,
        default=1000,
        help="p99 threshold in ms (default: 1000)",
    )
    args = parser.parse_args()

    # Check CSV exists
    stats_path = Path(f"{args.csv_prefix}_stats.csv")
    if not stats_path.exists():
        print(f"Error: {stats_path} not found", file=sys.stderr)
        print()
        print("Tip: Run a load test first with --csv flag:")
        print("  locust -f examples/api_load_test.py"
              " --headless --csv results ...")
        print()
        print("Or use the bundled test fixtures:")
        print("  python examples/generate_report.py"
              " tests/fixtures/sample")
        sys.exit(1)

    thresholds = {
        "p95": args.p95_threshold,
        "p99": args.p99_threshold,
    }

    if args.format == "all":
        generate_all_formats(
            args.csv_prefix, args.output_dir, thresholds,
        )
    else:
        generate_single_format(
            args.csv_prefix, args.format,
            args.output_dir, thresholds,
        )


if __name__ == "__main__":
    main()
