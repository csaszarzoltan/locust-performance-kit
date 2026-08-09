"""Shared fixtures for locust-performance-kit tests."""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("LOCUST_SKIP_MONKEY_PATCH", "1")

# Add src to path so templates can be imported
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def api_user_class():
    """Import and return the API user class."""
    from locust_templates.api_load import APIUser

    return APIUser


@pytest.fixture
def stress_user_class():
    """Import and return the Stress user class."""
    from locust_templates.stress import StressUser

    return StressUser


@pytest.fixture
def spike_user_class():
    """Import and return the Spike user class."""
    from locust_templates.spike import SpikeUser

    return SpikeUser


@pytest.fixture
def soak_user_class():
    """Import and return the Soak user class."""
    from locust_templates.soak import SoakUser

    return SoakUser


@pytest.fixture
def web_ui_user_class():
    """Import and return the WebUI user class."""
    from locust_templates.web_ui import WebUIUser

    return WebUIUser


@pytest.fixture
def metrics_collector():
    """Import and return the MetricsCollector."""
    from locust_templates.metrics import MetricsCollector

    return MetricsCollector


@pytest.fixture
def threshold_checker():
    """Import and return the ThresholdChecker."""
    from locust_templates.thresholds import ThresholdChecker

    return ThresholdChecker


# ── New protocol template fixtures (TDD red phase) ──────────


@pytest.fixture
def grpc_user_class():
    """Import and return the GrpcUser class (optional dep)."""
    from locust_templates.grpc import GrpcUser

    return GrpcUser


@pytest.fixture
def graphql_user_class():
    """Import and return the GraphQLUser class."""
    from locust_templates.graphql import GraphQLUser

    return GraphQLUser


@pytest.fixture
def websocket_user_class():
    """Import and return the WebSocketUser class (optional dep)."""
    from locust_templates.websocket import WebSocketUser

    return WebSocketUser
