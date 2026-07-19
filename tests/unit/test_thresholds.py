"""Unit tests for threshold checking."""

import pytest
from locust_templates.thresholds import ThresholdChecker


class TestThresholdChecker:
    """Test the ThresholdChecker class."""

    def test_init_with_defaults(self):
        checker = ThresholdChecker()
        assert checker.p95_threshold == 500.0
        assert checker.p99_threshold == 1000.0
        assert checker.error_rate_threshold == 0.01

    def test_init_with_custom_thresholds(self):
        checker = ThresholdChecker(
            p95_threshold=200.0,
            p99_threshold=500.0,
            error_rate_threshold=0.05,
        )
        assert checker.p95_threshold == 200.0
        assert checker.p99_threshold == 500.0
        assert checker.error_rate_threshold == 0.05

    def test_check_passes_when_below_thresholds(self):
        checker = ThresholdChecker(p95_threshold=500.0, p99_threshold=1000.0)
        result = checker.check(p95=200.0, p99=400.0, error_rate=0.005)
        assert result.passed is True
        assert len(result.failures) == 0

    def test_check_fails_when_p95_exceeds(self):
        checker = ThresholdChecker(p95_threshold=500.0)
        result = checker.check(p95=600.0, p99=800.0, error_rate=0.005)
        assert result.passed is False
        assert any("p95" in f.lower() for f in result.failures)

    def test_check_fails_when_p99_exceeds(self):
        checker = ThresholdChecker(p99_threshold=1000.0)
        result = checker.check(p95=400.0, p99=1200.0, error_rate=0.005)
        assert result.passed is False
        assert any("p99" in f.lower() for f in result.failures)

    def test_check_fails_when_error_rate_exceeds(self):
        checker = ThresholdChecker(error_rate_threshold=0.01)
        result = checker.check(p95=200.0, p99=400.0, error_rate=0.05)
        assert result.passed is False
        assert any("error" in f.lower() for f in result.failures)

    def test_check_multiple_failures(self):
        checker = ThresholdChecker(
            p95_threshold=100.0,
            p99_threshold=200.0,
            error_rate_threshold=0.01,
        )
        result = checker.check(p95=500.0, p99=800.0, error_rate=0.1)
        assert result.passed is False
        assert len(result.failures) >= 2


class TestThresholdResult:
    """Test ThresholdResult data class."""

    def test_passed_result_has_no_failures(self):
        from locust_templates.thresholds import ThresholdResult
        result = ThresholdResult(passed=True, failures=[], metrics={})
        assert result.passed is True
        assert result.failures == []
        assert result.metrics == {}
