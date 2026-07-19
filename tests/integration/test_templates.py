"""Integration tests for template modules."""

import importlib
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestModuleImports:
    """Test that all templates import correctly."""

    def test_api_load_imports(self):
        mod = importlib.import_module("locust_templates.api_load")
        assert hasattr(mod, "APIUser")

    def test_stress_imports(self):
        mod = importlib.import_module("locust_templates.stress")
        assert hasattr(mod, "StressUser")

    def test_spike_imports(self):
        mod = importlib.import_module("locust_templates.spike")
        assert hasattr(mod, "SpikeUser")

    def test_soak_imports(self):
        mod = importlib.import_module("locust_templates.soak")
        assert hasattr(mod, "SoakUser")

    def test_web_ui_imports(self):
        mod = importlib.import_module("locust_templates.web_ui")
        assert hasattr(mod, "WebUIUser")

    def test_metrics_imports(self):
        mod = importlib.import_module("locust_templates.metrics")
        assert hasattr(mod, "MetricsCollector")

    def test_thresholds_imports(self):
        mod = importlib.import_module("locust_templates.thresholds")
        assert hasattr(mod, "ThresholdChecker")
        assert hasattr(mod, "ThresholdResult")


class TestTemplateStructure:
    """Test that templates have correct Locust structure."""

    def test_all_users_inherit_from_http_user(self):
        from locust import HttpUser

        from locust_templates.api_load import APIUser
        from locust_templates.soak import SoakUser
        from locust_templates.spike import SpikeUser
        from locust_templates.stress import StressUser
        from locust_templates.web_ui import WebUIUser

        for user_cls in [APIUser, StressUser, SpikeUser, SoakUser, WebUIUser]:
            assert issubclass(user_cls, HttpUser), (
                f"{user_cls.__name__} must inherit from HttpUser"
            )

    def test_all_users_have_wait_time(self):
        from locust_templates.api_load import APIUser
        from locust_templates.soak import SoakUser
        from locust_templates.spike import SpikeUser
        from locust_templates.stress import StressUser
        from locust_templates.web_ui import WebUIUser

        for user_cls in [APIUser, StressUser, SpikeUser, SoakUser, WebUIUser]:
            assert hasattr(user_cls, "wait_time"), (
                f"{user_cls.__name__} must have wait_time"
            )

    def test_all_users_have_at_least_one_task(self):
        from locust_templates.api_load import APIUser
        from locust_templates.soak import SoakUser
        from locust_templates.spike import SpikeUser
        from locust_templates.stress import StressUser
        from locust_templates.web_ui import WebUIUser

        for user_cls in [APIUser, StressUser, SpikeUser, SoakUser, WebUIUser]:
            # Check for decorated methods (tasks)
            has_task = any(
                callable(getattr(user_cls, m, None))
                and not m.startswith("_")
                for m in dir(user_cls)
            )
            assert has_task, f"{user_cls.__name__} must have at least one task"


class TestMetricsIntegration:
    """Test metrics collector integration with templates."""

    def test_metrics_collector_singleton_behavior(self):
        from locust_templates.metrics import MetricsCollector
        c1 = MetricsCollector()
        c2 = MetricsCollector()
        # Each instance should be independent
        c1.record_request("test", 100.0, 200, True)
        assert c2.get_summary() == {}

    def test_metrics_thread_safety(self):
        import threading

        from locust_templates.metrics import MetricsCollector

        collector = MetricsCollector()
        errors = []

        def record_requests():
            try:
                for _ in range(100):
                    collector.record_request("test", 100.0, 200, True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_requests) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        summary = collector.get_summary()
        assert summary["test"]["count"] == 1000
