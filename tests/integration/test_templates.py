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

    def test_grpc_imports(self):
        mod = importlib.import_module("locust_templates.grpc")
        assert hasattr(mod, "GrpcUser")

    def test_graphql_imports(self):
        mod = importlib.import_module("locust_templates.graphql")
        assert hasattr(mod, "GraphQLUser")
        assert hasattr(mod, "GraphQLResponse")
        assert hasattr(mod, "QueryComplexityAnalyzer")

    def test_websocket_imports(self):
        mod = importlib.import_module("locust_templates.websocket")
        assert hasattr(mod, "WebSocketUser")


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

    # ── New protocol template structural tests ──

    def test_grpc_user_has_wait_time(self):
        from locust_templates.grpc import GrpcUser

        assert hasattr(GrpcUser, "wait_time")

    def test_grpc_user_has_on_start_on_stop(self):
        from locust_templates.grpc import GrpcUser

        assert hasattr(GrpcUser, "on_start")
        assert hasattr(GrpcUser, "on_stop")

    def test_graphql_user_inherits_from_http_user(self):
        from locust import HttpUser

        from locust_templates.graphql import GraphQLUser

        assert issubclass(GraphQLUser, HttpUser)

    def test_graphql_user_has_wait_time(self):
        from locust_templates.graphql import GraphQLUser

        assert hasattr(GraphQLUser, "wait_time")

    def test_graphql_user_has_query_method(self):
        from locust_templates.graphql import GraphQLUser

        assert callable(GraphQLUser.query)

    def test_websocket_user_has_wait_time(self):
        from locust_templates.websocket import WebSocketUser

        assert hasattr(WebSocketUser, "wait_time")

    def test_websocket_user_has_max_connections(self):
        from locust_templates.websocket import WebSocketUser

        assert hasattr(WebSocketUser, "max_connections")

    def test_websocket_user_has_connect_send_receive_close(self):
        from locust_templates.websocket import WebSocketUser

        assert callable(WebSocketUser.connect)
        assert callable(WebSocketUser.send)
        assert callable(WebSocketUser.receive)
        assert callable(WebSocketUser.close)


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
