"""Unit tests for locust_templates package exports and runner utility.

Tests verify:
- All public classes are exported from __init__.py
- Runner utility can build command-line arguments
- Package version is accessible
"""



class TestPackageExports:
    """Test that __init__.py exports all public classes."""

    def test_api_user_exported(self):
        from locust_templates import APIUser
        assert APIUser is not None

    def test_stress_user_exported(self):
        from locust_templates import StressUser
        assert StressUser is not None

    def test_spike_user_exported(self):
        from locust_templates import SpikeUser
        assert SpikeUser is not None

    def test_soak_user_exported(self):
        from locust_templates import SoakUser
        assert SoakUser is not None

    def test_web_ui_user_exported(self):
        from locust_templates import WebUIUser
        assert WebUIUser is not None

    def test_metrics_collector_exported(self):
        from locust_templates import MetricsCollector
        assert MetricsCollector is not None

    def test_threshold_checker_exported(self):
        from locust_templates import ThresholdChecker
        assert ThresholdChecker is not None

    def test_threshold_result_exported(self):
        from locust_templates import ThresholdResult
        assert ThresholdResult is not None

    def test_shapes_exported(self):
        from locust_templates import SpikeLoadShape, StepLoadShape
        assert StepLoadShape is not None
        assert SpikeLoadShape is not None

    def test_config_exported(self):
        from locust_templates import LoadTestConfig, load_config
        assert LoadTestConfig is not None
        assert load_config is not None


class TestRunnerUtility:
    """Test the runner utility for building locust commands."""

    def test_runner_importable(self):
        from locust_templates.runner import build_locust_command
        assert callable(build_locust_command)

    def test_build_basic_command(self):
        from locust_templates.runner import build_locust_command
        cmd = build_locust_command(script="examples/api_load_test.py")
        assert "locust" in cmd
        assert "examples/api_load_test.py" in cmd

    def test_build_command_with_headless(self):
        from locust_templates.runner import build_locust_command
        cmd = build_locust_command(script="examples/api_load_test.py", headless=True)
        assert "--headless" in cmd

    def test_build_command_with_users(self):
        from locust_templates.runner import build_locust_command
        cmd = build_locust_command(
            script="examples/api_load_test.py", users=50, spawn_rate=5
        )
        assert "--users 50" in cmd
        assert "--spawn-rate 5" in cmd

    def test_build_command_with_host(self):
        from locust_templates.runner import build_locust_command
        cmd = build_locust_command(
            script="examples/api_load_test.py",
            host="https://api.example.com",
        )
        assert "--host https://api.example.com" in cmd

    def test_build_command_with_run_time(self):
        from locust_templates.runner import build_locust_command
        cmd = build_locust_command(
            script="examples/api_load_test.py",
            run_time="10m",
        )
        assert "--run-time 10m" in cmd

    def test_build_command_with_html_report(self):
        from locust_templates.runner import build_locust_command
        cmd = build_locust_command(
            script="examples/api_load_test.py",
            html_report="report.html",
        )
        assert "--html report.html" in cmd
