"""Generate an HTML report from Locust CSV output.

Usage:
    # First run a load test with CSV output:
    locust -f examples/api_load_test.py --headless --users 50 --spawn-rate 5 \
        --run-time 2m --host http://localhost:8080 --csv results

    # Then generate the report:
    python examples/generate_report.py results

    # Or with test fixtures (no test run needed):
    python examples/generate_report.py tests/fixtures/sample_stats
"""

import sys
from pathlib import Path

# Ensure src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from locust_templates.report_generator import HTMLReportGenerator


def main():
    if len(sys.argv) < 2:
        print("Usage: python examples/generate_report.py <csv_prefix>")
        print("  csv_prefix: path prefix for Locust CSV files (e.g. 'results')")
        print()
        print("Example:")
        print("  locust -f examples/api_load_test.py --headless --csv results ...")
        print("  python examples/generate_report.py results")
        sys.exit(1)

    csv_prefix = sys.argv[1]

    # Check files exist
    stats_path = Path(f"{csv_prefix}_stats.csv")
    if not stats_path.exists():
        print(f"Error: {stats_path} not found")
        sys.exit(1)

    # Generate report with thresholds
    gen = HTMLReportGenerator.from_csv(
        csv_prefix,
        thresholds={"p95": 500, "p99": 1000},
    )
    output_path = gen.generate("report.html")

    print(f"Report generated: {output_path}")
    print(f"Open with: xdg-open {output_path}")


if __name__ == "__main__":
    main()
