"""Save and compare performance baselines.

Usage:
    # Save a baseline:
    python examples/baseline_comparison.py save results v1.0

    # Compare against a baseline:
    python examples/baseline_comparison.py compare results_new v1.0

    # List all baselines:
    python examples/baseline_comparison.py list
"""

import sys
from pathlib import Path

# Ensure src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from locust_templates.baseline import (
    BaselineNotFoundError,
    PerformanceBaseline,
)


def cmd_save(csv_prefix: str, name: str):
    baseline = PerformanceBaseline()
    path = baseline.save_baseline(csv_prefix, name=name)
    print(f"Baseline '{name}' saved to {path}")


def cmd_compare(csv_prefix: str, name: str):
    baseline = PerformanceBaseline()
    try:
        result = baseline.compare(csv_prefix, baseline_name=name)
    except BaselineNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(result.summary)
    print()

    if result.regressions:
        print("REGRESSIONS:")
        for r in result.regressions:
            print(
                f"  {r.endpoint} [{r.metric}] "
                f"{r.baseline_value:.1f}ms -> {r.current_value:.1f}ms "
                f"({r.degradation_pct:.1f}% worse)"
            )

    if result.improvements:
        print("IMPROVEMENTS:")
        for imp in result.improvements:
            print(
                f"  {imp.endpoint} [{imp.metric}] "
                f"{imp.baseline_value:.1f}ms -> {imp.current_value:.1f}ms "
                f"({imp.improvement_pct:.1f}% better)"
            )

    if not result.regressions and not result.improvements:
        print("No significant changes detected.")

    # Exit with error code if regressions found (for CI/CD)
    if result.regressions:
        sys.exit(1)


def cmd_list():
    baseline = PerformanceBaseline()
    baselines = baseline.list_baselines()
    if baselines:
        print("Stored baselines:")
        for name in baselines:
            print(f"  {name}")
    else:
        print("No baselines found.")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python examples/baseline_comparison.py save <csv_prefix> <name>")
        print("  python examples/baseline_comparison.py compare <csv_prefix> <name>")
        print("  python examples/baseline_comparison.py list")
        sys.exit(1)

    command = sys.argv[1]

    if command == "save":
        if len(sys.argv) < 4:
            print("Usage: save <csv_prefix> <name>")
            sys.exit(1)
        cmd_save(sys.argv[2], sys.argv[3])

    elif command == "compare":
        if len(sys.argv) < 4:
            print("Usage: compare <csv_prefix> <name>")
            sys.exit(1)
        cmd_compare(sys.argv[2], sys.argv[3])

    elif command == "list":
        cmd_list()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
