"""Locust Performance Kit - Production-ready load testing templates.

Provides reusable Locust user classes, metrics collection, threshold
checking, custom load shapes, and configuration management for
enterprise-grade performance testing.

Quick start:
    from locust_templates import APIUser, MetricsCollector, ThresholdChecker
"""

from locust_templates.api_load import APIUser
from locust_templates.auth import (
    AuthConfigError,
    AuthenticationError,
    Authenticator,
    AuthError,
    AuthRegistry,
    EnvTokenAuthenticator,
    OAuth2ClientCredentialsAuthenticator,
    StaticTokenAuthenticator,
    create_authenticator,
    default_registry,
)
from locust_templates.baseline import PerformanceBaseline
from locust_templates.config import LoadTestConfig, load_config
from locust_templates.correlator import (
    CorrelatedEvent,
    CorrelationSummary,
    FailureChain,
    RequestCorrelator,
)
from locust_templates.metrics import MetricsCollector
from locust_templates.notifications import Notifier, SlackNotifier, TeamsNotifier
from locust_templates.report_data import (
    EndpointStats,
    ExceptionRecord,
    FailureRecord,
    ReportData,
    ReportMetadata,
    ReportSummary,
    ThresholdConfig,
)
from locust_templates.report_generator import HTMLReportGenerator
from locust_templates.runner import build_locust_command, generate_report
from locust_templates.shapes import SpikeLoadShape, StepLoadShape
from locust_templates.soak import SoakUser
from locust_templates.spike import SpikeUser
from locust_templates.stress import StressUser
from locust_templates.thresholds import ThresholdChecker, ThresholdResult
from locust_templates.web_ui import WebUIUser

__all__ = [
    "APIUser",
    "AuthConfigError",
    "AuthError",
    "AuthRegistry",
    "Authenticator",
    "AuthenticationError",
    "CorrelatedEvent",
    "CorrelationSummary",
    "EndpointStats",
    "EnvTokenAuthenticator",
    "ExceptionRecord",
    "FailureChain",
    "FailureRecord",
    "HTMLReportGenerator",
    "LoadTestConfig",
    "MetricsCollector",
    "Notifier",
    "OAuth2ClientCredentialsAuthenticator",
    "PerformanceBaseline",
    "ReportData",
    "ReportMetadata",
    "ReportSummary",
    "RequestCorrelator",
    "SlackNotifier",
    "SpikeLoadShape",
    "SpikeUser",
    "SoakUser",
    "StaticTokenAuthenticator",
    "StepLoadShape",
    "StressUser",
    "TeamsNotifier",
    "ThresholdChecker",
    "ThresholdConfig",
    "ThresholdResult",
    "WebUIUser",
    "build_locust_command",
    "create_authenticator",
    "default_registry",
    "generate_report",
    "load_config",
]
