"""Tests for __init__.py exports of new dashboard and alerts classes."""


class TestDashboardAlertsExports:
    """Test that dashboard and alerts classes are exported from __init__.py."""

    def test_live_dashboard_exported(self):
        from locust_templates import LiveDashboard
        assert LiveDashboard is not None

    def test_time_series_point_exported(self):
        from locust_templates import TimeSeriesPoint
        assert TimeSeriesPoint is not None

    def test_alert_rule_exported(self):
        from locust_templates import AlertRule
        assert AlertRule is not None

    def test_alert_exported(self):
        from locust_templates import Alert
        assert Alert is not None

    def test_alert_engine_exported(self):
        from locust_templates import AlertEngine
        assert AlertEngine is not None
