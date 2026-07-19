"""Tests for config and runner integration with dashboard and alerts."""

from __future__ import annotations

import os
from unittest.mock import patch

from locust_templates.config import LoadTestConfig


class TestDashboardConfig:
    """Test dashboard-related config fields."""

    def test_dashboard_enabled_default(self):
        config = LoadTestConfig()
        assert config.dashboard_enabled is True

    def test_dashboard_refresh_interval_default(self):
        config = LoadTestConfig()
        assert config.dashboard_refresh_interval == 5

    def test_dashboard_max_points_default(self):
        config = LoadTestConfig()
        assert config.dashboard_max_points == 300

    def test_dashboard_output_path_default(self):
        config = LoadTestConfig()
        assert config.dashboard_output == ""

    def test_dashboard_enabled_from_env(self):
        env = {"LOCUST_DASHBOARD_ENABLED": "false"}
        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env()
            assert config.dashboard_enabled is False

    def test_dashboard_refresh_from_env(self):
        env = {"LOCUST_DASHBOARD_REFRESH": "10"}
        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env()
            assert config.dashboard_refresh_interval == 10

    def test_dashboard_max_points_from_env(self):
        env = {"LOCUST_DASHBOARD_MAX_POINTS": "600"}
        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env()
            assert config.dashboard_max_points == 600

    def test_dashboard_output_from_env(self):
        env = {"LOCUST_DASHBOARD_OUTPUT": "/tmp/dash.html"}
        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env()
            assert config.dashboard_output == "/tmp/dash.html"


class TestAlertsConfig:
    """Test alert-related config fields."""

    def test_alerts_enabled_default(self):
        config = LoadTestConfig()
        assert config.alerts_enabled is True

    def test_alerts_config_default_empty(self):
        config = LoadTestConfig()
        assert config.alert_rules == []

    def test_alerts_enabled_from_env(self):
        env = {"LOCUST_ALERTS_ENABLED": "false"}
        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env()
            assert config.alerts_enabled is False

    def test_alert_rules_from_env_json(self):
        import json

        rules = [
            {
                "name": "p95-high",
                "metric": "p95",
                "operator": ">",
                "threshold": 500.0,
            },
            {
                "name": "err-high",
                "metric": "error_rate",
                "operator": ">",
                "threshold": 0.01,
            },
        ]
        env = {"LOCUST_ALERT_RULES": json.dumps(rules)}
        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env()
            assert len(config.alert_rules) == 2
            assert config.alert_rules[0]["name"] == "p95-high"


class TestRunnerDashboardHelper:
    """Test runner.build_dashboard_command() helper."""

    def test_build_dashboard_command_exists(self):
        from locust_templates.runner import build_dashboard_command
        assert callable(build_dashboard_command)

    def test_build_dashboard_command_basic(self):
        from locust_templates.runner import build_dashboard_command
        cmd = build_dashboard_command(
            csv_prefix="results",
            output="dashboard.html",
        )
        assert "locust-report" in cmd
        assert "dashboard" in cmd.lower()
        assert "dashboard.html" in cmd

    def test_build_dashboard_command_with_format(self):
        from locust_templates.runner import build_dashboard_command
        cmd = build_dashboard_command(
            csv_prefix="results",
            output="dashboard.html",
            fmt="html",
        )
        assert "--format" in cmd
        assert "html" in cmd
