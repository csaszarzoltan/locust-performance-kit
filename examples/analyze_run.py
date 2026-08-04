"""AI Performance Intelligence Example.

Runs the `locust-kit analyze` pipeline against the real Locust CSV fixtures
committed under tests/fixtures/intelligence/ (generated with locust 2.46.2,
headers byte-identical to Locust's schema) and prints the reports.

Usage:
    python examples/analyze_run.py

run_a is a healthy baseline (exit 0, no anomalies); run_b is a regressed run
whose p95 SLO is violated (exit 2 — the CI gate signal). See
tests/fixtures/intelligence/README.md for the scenario tables.
"""

import sys
from pathlib import Path

# Ensure src is on the path (examples run standalone, not installed)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from locust_templates.intelligence import analyze_run

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures" / "intelligence"
RUN_A = FIXTURES / "run_a" / "run_a"
RUN_B = FIXTURES / "run_b" / "run_b"


def main() -> None:
    # 1. Healthy run, advisory (no SLOs) -> exit code 0
    report_a = analyze_run(str(RUN_A))
    print(report_a.to_markdown())
    print(f"exit_code={report_a.exit_code}\n")

    # 2. Regressed run vs baseline with SLOs -> exit code 2 (gate signal)
    report_b = analyze_run(
        str(RUN_B),
        slos={"p95": 500, "error_rate": 0.01},
        baseline_prefix=str(RUN_A),
    )
    print(report_b.to_markdown())
    print(f"exit_code={report_b.exit_code}")


if __name__ == "__main__":
    main()
