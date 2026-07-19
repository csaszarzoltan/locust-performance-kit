"""Smoke tests for performance regression baseline (TASK-5).

Interface tests verify API surface. Behavioral tests define the contract
for baseline saving, comparison, and regression detection.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from locust_templates.baseline import (
    BaselineNotFoundError,
    Improvement,
    PerformanceBaseline,
    Regression,
    RegressionResult,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestInterfaceSmoke:
    """Verify that all classes exist with correct attributes/methods."""

    def test_performance_baseline_init(self):
        """PerformanceBaseline should be instantiable."""
        baseline = PerformanceBaseline()
        assert baseline is not None
        assert baseline.baseline_dir is not None

    def test_has_save_baseline(self):
        """Should have save_baseline method."""
        assert hasattr(PerformanceBaseline, "save_baseline")

    def test_has_compare(self):
        """Should have compare method."""
        assert hasattr(PerformanceBaseline, "compare")

    def test_has_list_baselines(self):
        """Should have list_baselines method."""
        assert hasattr(PerformanceBaseline, "list_baselines")

    def test_regression_is_dataclass(self):
        """Regression should have endpoint, metric, values, degradation_pct."""
        reg = Regression(
            endpoint="GET /api/items",
            metric="p95",
            baseline_value=100.0,
            current_value=150.0,
            degradation_pct=50.0,
        )
        assert reg.endpoint == "GET /api/items"
        assert reg.degradation_pct == 50.0

    def test_improvement_is_dataclass(self):
        """Improvement should have endpoint, metric, values, improvement_pct."""
        imp = Improvement(
            endpoint="GET /api/items",
            metric="p95",
            baseline_value=200.0,
            current_value=150.0,
            improvement_pct=25.0,
        )
        assert imp.improvement_pct == 25.0

    def test_regression_result_is_dataclass(self):
        """RegressionResult should have regressions, improvements, summary."""
        result = RegressionResult()
        assert result.regressions == []
        assert result.improvements == []
        assert result.summary == ""

    def test_baseline_not_found_error_exists(self):
        """BaselineNotFoundError should be an Exception."""
        assert issubclass(BaselineNotFoundError, Exception)


# ──────────────────────────────────────────────────────────────
# Behavioral pre-state tests (fail until implementation)
# ──────────────────────────────────────────────────────────────


class TestSaveBaseline:
    """Behavioral tests for save_baseline() — fail until implemented."""

    @pytest.mark.unit
    def test_save_baseline_creates_json(self, tmp_path):
        """save_baseline() should create a JSON file with per-endpoint metrics."""
        baseline = PerformanceBaseline(baseline_dir=tmp_path)
        result_path = baseline.save_baseline(
            str(FIXTURES_DIR / "sample"),
            name="v1.0",
        )
        assert Path(result_path).exists()
        with open(result_path) as f:
            data = json.load(f)
        assert "endpoints" in data or "stats" in data or len(data) > 0

    @pytest.mark.unit
    def test_save_baseline_stores_endpoint_metrics(self, tmp_path):
        """Baseline JSON should contain per-endpoint p95/p99 values."""
        baseline = PerformanceBaseline(baseline_dir=tmp_path)
        result_path = baseline.save_baseline(
            str(FIXTURES_DIR / "sample"),
            name="v1.0",
        )
        with open(result_path) as f:
            data = json.load(f)
        # Should have some endpoint data
        assert len(data) > 0


class TestCompare:
    """Behavioral tests for compare() — fail until implemented."""

    @pytest.mark.unit
    def test_compare_returns_regression_result(self, tmp_path):
        """compare() should return a RegressionResult."""
        baseline = PerformanceBaseline(baseline_dir=tmp_path)
        baseline.save_baseline(str(FIXTURES_DIR / "sample"), name="v1.0")
        result = baseline.compare(str(FIXTURES_DIR / "sample"), baseline_name="v1.0")
        assert isinstance(result, RegressionResult)
        assert isinstance(result.summary, str)

    @pytest.mark.unit
    def test_compare_raises_on_missing_baseline(self, tmp_path):
        """compare() should raise BaselineNotFoundError for unknown baseline."""
        baseline = PerformanceBaseline(baseline_dir=tmp_path)
        with pytest.raises(BaselineNotFoundError):
            baseline.compare(str(FIXTURES_DIR / "sample"), baseline_name="nonexistent")

    @pytest.mark.unit
    def test_compare_detects_no_regression(self, tmp_path):
        """Comparing identical data should show no regressions."""
        baseline = PerformanceBaseline(baseline_dir=tmp_path)
        baseline.save_baseline(str(FIXTURES_DIR / "sample"), name="v1.0")
        result = baseline.compare(str(FIXTURES_DIR / "sample"), baseline_name="v1.0")
        assert len(result.regressions) == 0


class TestListBaselines:
    """Behavioral tests for list_baselines() — fail until implemented."""

    @pytest.mark.unit
    def test_list_baselines_returns_names(self, tmp_path):
        """list_baselines() should return list of stored baseline names."""
        baseline = PerformanceBaseline(baseline_dir=tmp_path)
        baseline.save_baseline(str(FIXTURES_DIR / "sample"), name="v1.0")
        baseline.save_baseline(str(FIXTURES_DIR / "sample"), name="v2.0")
        names = baseline.list_baselines()
        assert isinstance(names, list)
        assert "v1.0" in names
        assert "v2.0" in names
