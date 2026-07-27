"""OpenTelemetry configuration for Locust performance tests.

Provides setup_otel() for initializing the OpenTelemetry TracerProvider
with configurable exporters (OTLP, console, or none), and get_tracer()
for retrieving a named tracer instance.

Usage:
    from examples.otel_config import get_tracer, setup_otel

    setup_otel(service_name="my-load-test")
    tracer = get_tracer()
    with tracer.start_as_current_span("my-span") as span:
        span.set_attribute("key", "value")
"""

from __future__ import annotations

import os
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_OTEL_RESOURCE_ATTRIBUTES: dict[str, str] = {}


def setup_otel(
    service_name: str = "locust-performance-test",
    otlp_endpoint: str | None = None,
    traces_exporter: str = "otlp",
) -> None:
    """Initialize OpenTelemetry tracing.

    Configures a global TracerProvider based on the given parameters and
    standard OTEL environment variables. If ``traces_exporter`` is
    ``"otlp"`` the function attempts to set up an OTLP gRPC exporter.
    When no OTLP endpoint is available it falls back to the console
    (stdout) exporter so local development does not require a backend.
    Pass ``traces_exporter="none"`` to disable tracing entirely.

    Args:
        service_name: Name of the service for trace identification.
            May be overridden by the ``OTEL_SERVICE_NAME`` env var.
        otlp_endpoint: OTLP gRPC endpoint URL (e.g.
            ``http://otel-collector:4317``). When ``None`` the value of
            the ``OTEL_EXPORTER_OTLP_ENDPOINT`` env var is used.
        traces_exporter: Trace exporter type. One of ``"otlp"``,
            ``"console"``, or ``"none"``.
    """
    global _OTEL_RESOURCE_ATTRIBUTES  # noqa: PLW0603

    # Resolve service name: param > env var > default
    resolved_service = os.environ.get("OTEL_SERVICE_NAME") or service_name

    # Build resource with service name
    resource = Resource.create(
        attributes={
            "service.name": resolved_service,
            **_OTEL_RESOURCE_ATTRIBUTES,
        }
    )

    provider: TracerProvider

    if traces_exporter == "none":
        # No-op provider – discard all spans
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        # Override: disable by using a simple no-op approach
        trace.set_tracer_provider(trace.NoOpTracerProvider())
        return

    provider = TracerProvider(resource=resource)

    # Resolve OTLP endpoint: param > env var > None (triggers console fallback)
    resolved_endpoint = otlp_endpoint or os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    )

    if traces_exporter == "otlp" and resolved_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        exporter = OTLPSpanExporter(endpoint=resolved_endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
    else:
        # Console exporter fallback (local dev or no endpoint configured)
        exporter = ConsoleSpanExporter()
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)


def get_tracer(service_name: str = "locust-performance-test") -> Any:
    """Return a tracer instance for creating custom spans.

    Args:
        service_name: Name of the service for trace identification.
            Used as the tracer's instrumentation scope name.

    Returns:
        A tracer instance with ``start_span()`` and
        ``start_as_current_span()`` methods.
    """
    resolved_service = os.environ.get("OTEL_SERVICE_NAME") or service_name
    return trace.get_tracer(resolved_service)
