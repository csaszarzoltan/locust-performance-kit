"""Unit tests for metrics collection."""

import pytest

from locust_templates.metrics import MetricsCollector


class TestMetricsCollector:
    """Test the MetricsCollector class."""

    def test_init_creates_empty_metrics(self):
        collector = MetricsCollector()
        assert collector.get_summary() == {}

    def test_record_request(self):
        collector = MetricsCollector()
        collector.record_request(
            name="GET /api/items",
            response_time=150.5,
            status_code=200,
            success=True,
        )
        summary = collector.get_summary()
        assert "GET /api/items" in summary
        assert summary["GET /api/items"]["count"] == 1

    def test_record_multiple_requests(self):
        collector = MetricsCollector()
        for _ in range(5):
            collector.record_request(
                name="GET /api/items",
                response_time=100.0,
                status_code=200,
                success=True,
            )
        summary = collector.get_summary()
        assert summary["GET /api/items"]["count"] == 5

    def test_record_failed_request(self):
        collector = MetricsCollector()
        collector.record_request(
            name="POST /api/items",
            response_time=500.0,
            status_code=500,
            success=False,
        )
        summary = collector.get_summary()
        assert summary["POST /api/items"]["failures"] == 1

    def test_percentile_calculation(self):
        collector = MetricsCollector()
        for i in range(100):
            collector.record_request(
                name="GET /api/items",
                response_time=float(i + 1),
                status_code=200,
                success=True,
            )
        p50 = collector.get_percentile("GET /api/items", 50)
        p95 = collector.get_percentile("GET /api/items", 95)
        p99 = collector.get_percentile("GET /api/items", 99)
        assert p50 == pytest.approx(50.5, abs=1.0)
        assert p95 == pytest.approx(95.5, abs=1.0)
        assert p99 == pytest.approx(99.5, abs=1.0)

    def test_error_rate_calculation(self):
        collector = MetricsCollector()
        for _ in range(90):
            collector.record_request(
                name="GET /api/items",
                response_time=100.0,
                status_code=200,
                success=True,
            )
        for _ in range(10):
            collector.record_request(
                name="GET /api/items",
                response_time=500.0,
                status_code=500,
                success=False,
            )
        error_rate = collector.get_error_rate("GET /api/items")
        assert error_rate == pytest.approx(0.1, rel=1e-2)

    def test_reset_metrics(self):
        collector = MetricsCollector()
        collector.record_request(
            name="GET /api/items",
            response_time=100.0,
            status_code=200,
            success=True,
        )
        collector.reset()
        assert collector.get_summary() == {}
