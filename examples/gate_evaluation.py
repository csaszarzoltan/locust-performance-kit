"""
Runnable example: CI/CD quality gate evaluation using ThresholdChecker.

Simulates a passing and a failing quality gate, demonstrating how
thresholds are evaluated programmatically.

Usage:
    python examples/gate_evaluation.py
"""

from locust_templates.thresholds import ThresholdChecker


def simulate_pass():
    """Simulate a quality gate where all metrics are within thresholds."""
    checker = ThresholdChecker(p95_threshold=500, p99_threshold=1000)
    result = checker.check(p95=350, p99=820, error_rate=0.005)
    return result


def simulate_fail():
    """Simulate a quality gate where p95 exceeds the threshold."""
    checker = ThresholdChecker(p95_threshold=500, p99_threshold=1000)
    result = checker.check(p95=650, p99=1200, error_rate=0.02)
    return result


def simulate_custom_thresholds():
    """Simulate a quality gate with custom per-endpoint thresholds."""
    checker = ThresholdChecker(
        p95_threshold=200,  # stricter p95
        p99_threshold=500,  # stricter p99
        error_rate_threshold=0.001,  # 0.1% max error rate
    )
    result = checker.check(p95=180, p99=350, error_rate=0.0005)
    return result


def main():
    print("=" * 56)
    print("CI/CD Quality Gate Simulation")
    print("=" * 56)

    # Test 1: All metrics within thresholds
    print("\n[1] Gate — all metrics within thresholds")
    result = simulate_pass()
    print(f"    Passed: {result.passed}")
    for f in result.failures:
        print(f"    FAIL: {f}")
    print(f"    Metrics: {result.metrics}")
    assert result.passed is True, "Expected gate to pass"
    print("    ✓ PASS (expected)")

    # Test 2: p95 and p99 exceed thresholds
    print("\n[2] Gate — p95 and p99 exceed thresholds")
    result = simulate_fail()
    print(f"    Passed: {result.passed}")
    for f in result.failures:
        print(f"    FAIL: {f}")
    assert result.passed is False, "Expected gate to fail"
    assert len(result.failures) == 3, "Expected 3 failures"
    print("    ✓ FAIL (expected)")

    # Test 3: Custom stricter thresholds
    print("\n[3] Gate — custom stricter thresholds")
    result = simulate_custom_thresholds()
    print(f"    Passed: {result.passed}")
    for f in result.failures:
        print(f"    FAIL: {f}")
    print(f"    Metrics: {result.metrics}")
    assert result.passed is True, "Expected gate to pass with stricter thresholds"
    print("    ✓ PASS (expected)")

    print("\n" + "=" * 56)
    print("All gate scenarios verified.")
    print("=" * 56)


if __name__ == "__main__":
    main()
