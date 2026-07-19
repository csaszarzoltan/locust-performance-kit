"""Locust Performance Kit - Production-ready load testing templates.

Provides reusable Locust user classes, metrics collection, threshold
checking, custom load shapes, and configuration management for
enterprise-grade performance testing.

Quick start:
    from locust_templates import APIUser, MetricsCollector, ThresholdChecker
"""

from locust_templates.api_load import APIUser
from locust_templates.config import LoadTestConfig, load_config
from locust_templates.metrics import MetricsCollector
from locust_templates.shapes import SpikeLoadShape, StepLoadShape
from locust_templates.soak import SoakUser
from locust_templates.spike import SpikeUser
from locust_templates.stress import StressUser
from locust_templates.thresholds import ThresholdChecker, ThresholdResult
from locust_templates.web_ui import WebUIUser

__all__ = [
    "APIUser",
    "LoadTestConfig",
    "MetricsCollector",
    "SpikeLoadShape",
    "SpikeUser",
    "SoakUser",
    "StepLoadShape",
    "StressUser",
    "ThresholdChecker",
    "ThresholdResult",
    "WebUIUser",
    "load_config",
]
