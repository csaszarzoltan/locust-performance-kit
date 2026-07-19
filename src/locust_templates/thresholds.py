"""Threshold checking for performance test results.

Validates that performance metrics meet defined thresholds
and reports pass/fail status with detailed failure reasons.
"""

from dataclasses import dataclass, field


@dataclass
class ThresholdResult:
    """Result of a threshold check."""

    passed: bool
    failures: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


class ThresholdChecker:
    """Validates performance metrics against defined thresholds."""

    def __init__(
        self,
        p95_threshold: float = 500.0,
        p99_threshold: float = 1000.0,
        error_rate_threshold: float = 0.01,
    ):
        self.p95_threshold = p95_threshold
        self.p99_threshold = p99_threshold
        self.error_rate_threshold = error_rate_threshold

    def check(
        self,
        p95: float,
        p99: float,
        error_rate: float,
    ) -> ThresholdResult:
        """Check if metrics meet thresholds."""
        failures = []
        metrics = {"p95": p95, "p99": p99, "error_rate": error_rate}

        if p95 > self.p95_threshold:
            failures.append(
                f"p95 latency {p95:.1f}ms exceeds threshold {self.p95_threshold:.1f}ms"
            )

        if p99 > self.p99_threshold:
            failures.append(
                f"p99 latency {p99:.1f}ms exceeds threshold {self.p99_threshold:.1f}ms"
            )

        if error_rate > self.error_rate_threshold:
            failures.append(
                f"Error rate {error_rate:.2%} exceeds threshold {self.error_rate_threshold:.2%}"
            )

        return ThresholdResult(
            passed=len(failures) == 0,
            failures=failures,
            metrics=metrics,
        )
