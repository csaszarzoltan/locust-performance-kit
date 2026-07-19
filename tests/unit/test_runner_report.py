"""Tests for runner.py report integration (TDD).

These tests define the contract for the new report_format, report_output,
p95_threshold, and p99_threshold parameters in build_locust_command().
They will FAIL until runner.py is updated.
"""

from __future__ import annotations

import pytest

from locust_templates.runner import build_locust_command

# ──────────────────────────────────────────────────────────────
# Backward compatibility tests
# ──────────────────────────────────────────────────────────────


class TestRunnerBackwardCompat:
    """Verify existing build_locust_command() behavior is unchanged."""

    @pytest.mark.unit
    def test_runner_backward_compat_existing_params(self):
        """Existing parameters should produce same output as v1.1.0."""
        cmd = build_locust_command(
            script="examples/api_load_test.py",
            headless=True,
            users=100,
            spawn_rate=10,
            host="https://api.example.com",
            csv_prefix="results",
        )
        assert "locust -f examples/api_load_test.py" in cmd
        assert "--headless" in cmd
        assert "--users 100" in cmd
        assert "--spawn-rate 10" in cmd
        assert "--host https://api.example.com" in cmd
        assert "--csv results" in cmd

    @pytest.mark.unit
    def test_runner_without_report_format(self):
        """No report_format → no locust-report appended (backward compat)."""
        cmd = build_locust_command(
            script="test.py",
            csv_prefix="results",
        )
        assert "locust-report" not in cmd


# ──────────────────────────────────────────────────────────────
# New report integration tests
# ──────────────────────────────────────────────────────────────


class TestRunnerReportIntegration:
    """Tests for new report_format, report_output, threshold parameters."""

    @pytest.mark.unit
    def test_runner_with_report_format(self):
        """report_format='json' → command includes 'locust-report ... --format json'."""
        cmd = build_locust_command(
            script="test.py",
            csv_prefix="results",
            report_format="json",
        )
        assert "locust-report" in cmd
        assert "--format json" in cmd
        assert "results" in cmd

    @pytest.mark.unit
    def test_runner_with_report_output(self):
        """report_output='report.json' → command includes '--output report.json'."""
        cmd = build_locust_command(
            script="test.py",
            csv_prefix="results",
            report_format="json",
            report_output="report.json",
        )
        assert "--output report.json" in cmd

    @pytest.mark.unit
    def test_runner_with_thresholds(self):
        """p95_threshold=500 → command includes '--p95-threshold 500'."""
        cmd = build_locust_command(
            script="test.py",
            csv_prefix="results",
            report_format="html",
            p95_threshold=500.0,
            p99_threshold=1000.0,
        )
        assert "--p95-threshold 500" in cmd
        assert "--p99-threshold 1000" in cmd

    @pytest.mark.unit
    def test_runner_report_format_appended_after_locust(self):
        """locust-report command should be appended with && after locust."""
        cmd = build_locust_command(
            script="test.py",
            csv_prefix="results",
            report_format="json",
        )
        # The locust command should come first, then && locust-report
        assert "&&" in cmd
        locust_part, report_part = cmd.split("&&", 1)
        assert "locust -f test.py" in locust_part
        assert "locust-report" in report_part
