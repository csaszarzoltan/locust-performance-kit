"""Unit tests for the real-time live metrics dashboard.

Tests LiveDashboard, TimeSeriesPoint, and the HTML dashboard rendering
with embedded JavaScript charts (Chart.js inline) and an alerts panel.
"""

from __future__ import annotations

import time
from pathlib import Path

from locust_templates.live_dashboard import (
    LiveDashboard,
    TimeSeriesPoint,
)

# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestInterfaceSmoke:
    """Verify that the live_dashboard module has the correct public API."""

    def test_live_dashboard_is_class(self):
        assert isinstance(LiveDashboard, type)

    def test_time_series_point_is_dataclass(self):
        import dataclasses

        assert dataclasses.is_dataclass(TimeSeriesPoint)

    def test_time_series_point_fields(self):
        now = time.time()
        pt = TimeSeriesPoint(
            timestamp=now,
            avg_response_time=150.0,
            p95_response_time=250.0,
            throughput=100.0,
            error_rate=0.01,
            active_users=50,
        )
        assert pt.timestamp == now
        assert pt.avg_response_time == 150.0
        assert pt.p95_response_time == 250.0
        assert pt.throughput == 100.0
        assert pt.error_rate == 0.01
        assert pt.active_users == 50

    def test_live_dashboard_init_defaults(self):
        dash = LiveDashboard()
        assert dash.get_history() == []

    def test_live_dashboard_init_with_max_points(self):
        dash = LiveDashboard(max_points=100)
        assert dash._max_points == 100

    def test_live_dashboard_has_record_method(self):
        assert hasattr(LiveDashboard, "record")

    def test_live_dashboard_has_render_method(self):
        assert hasattr(LiveDashboard, "render")


# ──────────────────────────────────────────────────────────────
# Behavioral tests — recording metrics
# ──────────────────────────────────────────────────────────────


class TestRecording:
    """Test LiveDashboard.record() and history management."""

    def test_record_single_point(self):
        dash = LiveDashboard()
        dash.record(
            avg_response_time=150.0,
            p95_response_time=250.0,
            throughput=100.0,
            error_rate=0.01,
            active_users=50,
        )
        history = dash.get_history()
        assert len(history) == 1
        assert history[0].avg_response_time == 150.0

    def test_record_multiple_points(self):
        dash = LiveDashboard()
        for i in range(5):
            dash.record(
                avg_response_time=100.0 + i,
                p95_response_time=200.0 + i,
                throughput=50.0,
                error_rate=0.01,
                active_users=10,
            )
        assert len(dash.get_history()) == 5

    def test_record_respects_max_points(self):
        dash = LiveDashboard(max_points=3)
        for i in range(5):
            dash.record(
                avg_response_time=float(i),
                p95_response_time=200.0,
                throughput=50.0,
                error_rate=0.0,
                active_users=10,
            )
        history = dash.get_history()
        assert len(history) == 3
        # Should keep the most recent 3
        assert history[0].avg_response_time == 2.0
        assert history[-1].avg_response_time == 4.0

    def test_record_uses_auto_timestamp(self):
        dash = LiveDashboard()
        before = time.time()
        dash.record(
            avg_response_time=100.0,
            p95_response_time=200.0,
            throughput=50.0,
            error_rate=0.0,
            active_users=10,
        )
        after = time.time()
        assert before <= dash.get_history()[0].timestamp <= after

    def test_record_uses_provided_timestamp(self):
        dash = LiveDashboard()
        ts = 1234567890.0
        dash.record(
            avg_response_time=100.0,
            p95_response_time=200.0,
            throughput=50.0,
            error_rate=0.0,
            active_users=10,
            timestamp=ts,
        )
        assert dash.get_history()[0].timestamp == ts

    def test_clear_history(self):
        dash = LiveDashboard()
        dash.record(
            avg_response_time=100.0,
            p95_response_time=200.0,
            throughput=50.0,
            error_rate=0.0,
            active_users=10,
        )
        dash.clear()
        assert dash.get_history() == []


# ──────────────────────────────────────────────────────────────
# Behavioral tests — snapshot from MetricsCollector
# ──────────────────────────────────────────────────────────────


class TestSnapshotFromCollector:
    """Test LiveDashboard.record_from_collector()."""

    def test_record_from_collector(self):
        from locust_templates.metrics import MetricsCollector

        collector = MetricsCollector()
        for i in range(100):
            collector.record_request(
                name="GET /api",
                response_time=100.0 + i,
                status_code=200,
                success=True,
            )
        for _i in range(5):
            collector.record_request(
                name="GET /api",
                response_time=500.0,
                status_code=500,
                success=False,
            )

        dash = LiveDashboard()
        dash.record_from_collector(collector, active_users=50)

        history = dash.get_history()
        assert len(history) == 1
        pt = history[0]
        assert pt.active_users == 50
        assert pt.p95_response_time > 0
        assert pt.throughput > 0
        assert pt.error_rate > 0  # 5 failures out of 105

    def test_record_from_collector_empty(self):
        from locust_templates.metrics import MetricsCollector

        collector = MetricsCollector()
        dash = LiveDashboard()
        dash.record_from_collector(collector, active_users=0)
        pt = dash.get_history()[0]
        assert pt.avg_response_time == 0.0
        assert pt.error_rate == 0.0


# ──────────────────────────────────────────────────────────────
# Behavioral tests — HTML rendering
# ──────────────────────────────────────────────────────────────


class TestHtmlRendering:
    """Test LiveDashboard.render() output."""

    def test_render_returns_html_string(self):
        dash = LiveDashboard()
        html = dash.render()
        assert isinstance(html, str)
        assert "<html" in html.lower()
        assert "</html>" in html.lower()

    def test_render_includes_chart_js(self):
        """The HTML should embed Chart.js for live charts."""
        dash = LiveDashboard()
        html = dash.render()
        # Should include a Chart.js CDN or inline script
        assert "chart" in html.lower() or "Chart" in html

    def test_render_includes_response_time_chart(self):
        dash = LiveDashboard()
        dash.record(
            avg_response_time=150.0,
            p95_response_time=250.0,
            throughput=100.0,
            error_rate=0.01,
            active_users=50,
        )
        html = dash.render()
        assert "response" in html.lower() or "Response" in html
        # Should reference the time series data
        assert "150" in html or "responseTime" in html

    def test_render_includes_throughput_chart(self):
        dash = LiveDashboard()
        dash.record(
            avg_response_time=150.0,
            p95_response_time=250.0,
            throughput=100.0,
            error_rate=0.01,
            active_users=50,
        )
        html = dash.render()
        assert "throughput" in html.lower() or "Throughput" in html

    def test_render_includes_alerts_panel(self):
        """The HTML should include a section for alerts."""
        dash = LiveDashboard()
        html = dash.render()
        assert "alert" in html.lower()

    def test_render_embeds_time_series_data_as_json(self):
        """The HTML should embed the time series data as a JSON blob."""
        dash = LiveDashboard()
        dash.record(
            avg_response_time=150.0,
            p95_response_time=250.0,
            throughput=100.0,
            error_rate=0.01,
            active_users=50,
        )
        html = dash.render()
        # Should contain a JSON data blob for Chart.js to consume
        assert "avg_response_time" in html or "avgResponseTime" in html

    def test_render_to_file(self, tmp_path):
        """render_to_file() should write HTML to disk."""
        dash = LiveDashboard()
        dash.record(
            avg_response_time=150.0,
            p95_response_time=250.0,
            throughput=100.0,
            error_rate=0.01,
            active_users=50,
        )
        out = tmp_path / "dashboard.html"
        result = dash.render_to_file(str(out))
        assert Path(result).exists()
        content = out.read_text()
        assert "<html" in content.lower()

    def test_render_auto_refresh_meta(self):
        """The HTML should auto-refresh or have a refresh mechanism."""
        dash = LiveDashboard()
        html = dash.render()
        # Should have either meta refresh or a JS setInterval for auto-update
        assert "refresh" in html.lower() or "setInterval" in html

    def test_render_with_alerts(self):
        """When alerts are present, they should appear in the HTML."""
        from locust_templates.alerts import AlertEngine, AlertRule

        rule = AlertRule(name="p95-high", metric="p95", operator=">", threshold=500.0)
        engine = AlertEngine(rules=[rule])
        engine.check({"p95": 600.0})
        alerts = engine.get_alerts()

        dash = LiveDashboard()
        html = dash.render(alerts=alerts)
        assert "p95-high" in html
        assert "600" in html

    def test_render_no_data(self):
        """Rendering with no recorded data should still produce valid HTML."""
        dash = LiveDashboard()
        html = dash.render()
        assert "<html" in html.lower()


# ──────────────────────────────────────────────────────────────
# Integration with AlertEngine
# ──────────────────────────────────────────────────────────────


class TestAlertIntegration:
    """Test LiveDashboard + AlertEngine integration."""

    def test_render_with_alert_engine(self):
        from locust_templates.alerts import AlertEngine, AlertRule

        rules = [
            AlertRule(
                name="p95-high", metric="p95", operator=">", threshold=500.0
            )
        ]
        engine = AlertEngine(rules=rules)

        dash = LiveDashboard()
        dash.record(
            avg_response_time=150.0,
            p95_response_time=600.0,
            throughput=100.0,
            error_rate=0.01,
            active_users=50,
        )

        # Check alerts against the latest snapshot
        latest = dash.get_history()[-1]
        metrics = {
            "p95": latest.p95_response_time,
            "throughput": latest.throughput,
            "error_rate": latest.error_rate,
        }
        alerts = engine.check(metrics)
        assert len(alerts) == 1
        assert alerts[0].rule_name == "p95-high"

    def test_get_latest_snapshot(self):
        dash = LiveDashboard()
        dash.record(
            avg_response_time=100.0,
            p95_response_time=200.0,
            throughput=50.0,
            error_rate=0.0,
            active_users=10,
        )
        dash.record(
            avg_response_time=150.0,
            p95_response_time=250.0,
            throughput=100.0,
            error_rate=0.01,
            active_users=50,
        )
        latest = dash.get_latest()
        assert latest is not None
        assert latest.avg_response_time == 150.0
        assert latest.active_users == 50

    def test_get_latest_empty(self):
        dash = LiveDashboard()
        assert dash.get_latest() is None
