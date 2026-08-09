"""Locust Performance Kit public API with lazy imports.

Lazy resolution keeps pure analysis, import, and workspace modules usable without
initializing Locust/gevent while preserving ``from locust_templates import X``.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "APIUser": ("api_load", "APIUser"),
    "Alert": ("alerts", "Alert"), "AlertEngine": ("alerts", "AlertEngine"), "AlertRule": ("alerts", "AlertRule"),
    "AuthConfigError": ("auth", "AuthConfigError"), "AuthenticationError": ("auth", "AuthenticationError"), "Authenticator": ("auth", "Authenticator"), "AuthError": ("auth", "AuthError"), "AuthRegistry": ("auth", "AuthRegistry"), "EnvTokenAuthenticator": ("auth", "EnvTokenAuthenticator"), "OAuth2ClientCredentialsAuthenticator": ("auth", "OAuth2ClientCredentialsAuthenticator"), "StaticTokenAuthenticator": ("auth", "StaticTokenAuthenticator"), "create_authenticator": ("auth", "create_authenticator"), "default_registry": ("auth", "default_registry"),
    "PerformanceBaseline": ("baseline", "PerformanceBaseline"),
    "LoadTestConfig": ("config", "LoadTestConfig"), "load_config": ("config", "load_config"),
    "CorrelatedEvent": ("correlator", "CorrelatedEvent"), "CorrelationSummary": ("correlator", "CorrelationSummary"), "FailureChain": ("correlator", "FailureChain"), "RequestCorrelator": ("correlator", "RequestCorrelator"),
    "GraphQLResponse": ("graphql", "GraphQLResponse"), "GraphQLUser": ("graphql", "GraphQLUser"), "QueryComplexityAnalyzer": ("graphql", "QueryComplexityAnalyzer"),
    "GrpcUser": ("grpc", "GrpcUser"),
    "AnalysisReport": ("intelligence", "AnalysisReport"), "Anomaly": ("intelligence", "Anomaly"), "AnomalyDetector": ("intelligence", "AnomalyDetector"), "Bottleneck": ("intelligence", "Bottleneck"), "BottleneckDetector": ("intelligence", "BottleneckDetector"), "CapacityProjection": ("intelligence", "CapacityProjection"), "CapacityProjector": ("intelligence", "CapacityProjector"), "EndpointProfile": ("intelligence", "EndpointProfile"), "HistoryPoint": ("intelligence", "HistoryPoint"), "Insight": ("intelligence", "Insight"), "InsightGenerator": ("intelligence", "InsightGenerator"), "KneePoint": ("intelligence", "KneePoint"), "LLMInsightProvider": ("intelligence", "LLMInsightProvider"), "RunProfile": ("intelligence", "RunProfile"), "SLOViolation": ("intelligence", "SLOViolation"), "analyze_run": ("intelligence", "analyze_run"), "check_slos": ("intelligence", "check_slos"),
    "LiveDashboard": ("live_dashboard", "LiveDashboard"), "TimeSeriesPoint": ("live_dashboard", "TimeSeriesPoint"),
    "MetricsCollector": ("metrics", "MetricsCollector"),
    "Notifier": ("notifications", "Notifier"), "SlackNotifier": ("notifications", "SlackNotifier"), "TeamsNotifier": ("notifications", "TeamsNotifier"),
    "EndpointStats": ("report_data", "EndpointStats"), "ExceptionRecord": ("report_data", "ExceptionRecord"), "FailureRecord": ("report_data", "FailureRecord"), "ReportData": ("report_data", "ReportData"), "ReportMetadata": ("report_data", "ReportMetadata"), "ReportSummary": ("report_data", "ReportSummary"), "ThresholdConfig": ("report_data", "ThresholdConfig"),
    "HTMLReportGenerator": ("report_generator", "HTMLReportGenerator"),
    "build_locust_command": ("runner", "build_locust_command"), "generate_report": ("runner", "generate_report"),
    "SpikeLoadShape": ("shapes", "SpikeLoadShape"), "StepLoadShape": ("shapes", "StepLoadShape"),
    "SoakUser": ("soak", "SoakUser"), "SpikeUser": ("spike", "SpikeUser"), "StressUser": ("stress", "StressUser"),
    "ThresholdChecker": ("thresholds", "ThresholdChecker"), "ThresholdResult": ("thresholds", "ThresholdResult"),
    "WebUIUser": ("web_ui", "WebUIUser"),
    "WebSocketError": ("websocket", "WebSocketError"), "WebSocketUser": ("websocket", "WebSocketUser"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve and cache a public symbol on first access."""
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(f"{__name__}.{module_name}"), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
