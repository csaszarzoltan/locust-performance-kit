"""OTel-instrumented Locust load test script.

Extends ``APIUser`` from the core templates with OpenTelemetry tracing.
Each simulated user gets a ``user_session`` span, and every HTTP request
creates a sub-span carrying endpoint-specific attributes.

Usage:
    locust -f examples/otel_load_test.py \\
        --headless --users 5 --spawn-rate 1 --run-time 30s

To export traces to an OTLP-compatible backend:
    export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    locust -f examples/otel_load_test.py ...

To disable tracing (zero-overhead mode):
    export OTEL_TRACES_EXPORTER=none
    locust -f examples/otel_load_test.py ...
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Any

from locust import task
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from examples.otel_config import get_tracer, setup_otel
from src.locust_templates.api_load import APIUser

# Module-level tracer — initialised lazily on first use.
_tracer: Any = None
_tracer_initialized: bool = False


def _init_tracing() -> None:
    """Initialise the global tracer from environment defaults."""
    global _tracer, _tracer_initialized  # noqa: PLW0603
    if _tracer_initialized:
        return
    exporter = os.environ.get("OTEL_TRACES_EXPORTER", "otlp")
    setup_otel(traces_exporter=exporter)
    _tracer = get_tracer()
    _tracer_initialized = True


def _get_tracer() -> Any:
    """Return the module-level tracer, initialising lazily if needed."""
    _init_tracing()
    return _tracer


class OTelAPIUser(APIUser):
    """Locust user with OpenTelemetry instrumentation.

    Every user session creates a ``user_session`` span on ``on_start()``
    and ends it on ``on_stop()``.  Each HTTP request creates a sub-span
    that records endpoint, response time, and status code.

    Span context headers (``traceparent``) are intentionally NOT injected
    into target requests — Locust is a load generator, not a mesh proxy,
    and injecting trace context would pollute the target's traces.
    """

    _session_span: Any = None

    def on_start(self) -> None:
        """Start a ``user_session`` span for this simulated user."""
        super().on_start()
        tracer = _tracer or get_tracer()
        self._session_span = tracer.start_span(
            "user_session",
            attributes={
                "user_id": f"user_{random.randint(1, 10000)}",
                "auth_provider": self.auth_provider,
            },
        )

    @task(3)
    def get_items(self) -> None:
        """GET /items with a sub-span under the user session."""
        tracer = _tracer or get_tracer()
        with tracer.start_as_current_span(
            "get_items",
            context=trace.set_span_in_context(self._session_span)
            if self._session_span
            else None,
        ) as span:
            start = time.monotonic()
            try:
                response = self.client.get(
                    "/api/v1/items",
                    headers=self._build_headers(),
                    catch_response=True,
                )
                duration_ms = (time.monotonic() - start) * 1000
                span.set_attribute("http.method", "GET")
                span.set_attribute("http.url", "/api/v1/items")
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("response_time_ms", duration_ms)
                if response.status_code == 200:
                    response.success()
                elif response.status_code == 429:
                    response.failure("Rate limited")
                else:
                    response.failure(
                        f"Unexpected status: {response.status_code}"
                    )
            except Exception as exc:
                span.set_attribute("error", str(exc))
                raise

    @task(2)
    def get_item_detail(self) -> None:
        """GET /items/{id} with item_id set on the span."""
        tracer = _tracer or get_tracer()
        item_id = self._get_random_item_id()
        with tracer.start_as_current_span(
            "get_item_detail",
            context=trace.set_span_in_context(self._session_span)
            if self._session_span
            else None,
        ) as span:
            span.set_attribute("item_id", item_id)
            start = time.monotonic()
            try:
                response = self.client.get(
                    f"/api/v1/items/{item_id}",
                    headers=self._build_headers(),
                    catch_response=True,
                )
                duration_ms = (time.monotonic() - start) * 1000
                span.set_attribute("http.method", "GET")
                span.set_attribute("http.url", f"/api/v1/items/{item_id}")
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("response_time_ms", duration_ms)
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(
                        f"Failed with {response.status_code}"
                    )
            except Exception as exc:
                span.set_attribute("error", str(exc))
                raise

    @task(1)
    def create_item(self) -> None:
        """POST /items capturing payload size in span attributes."""
        tracer = _tracer or get_tracer()
        payload: dict[str, Any] = {
            "name": f"Test Item {int(time.time())}",
            "description": "Load testing item",
        }
        with tracer.start_as_current_span(
            "create_item",
            context=trace.set_span_in_context(self._session_span)
            if self._session_span
            else None,
        ) as span:
            payload_bytes = len(json.dumps(payload).encode("utf-8"))
            span.set_attribute("payload_size_bytes", payload_bytes)
            span.set_attribute("http.method", "POST")
            span.set_attribute("http.url", "/api/v1/items")
            start = time.monotonic()
            try:
                response = self.client.post(
                    "/api/v1/items",
                    json=payload,
                    headers=self._build_headers(),
                    catch_response=True,
                )
                duration_ms = (time.monotonic() - start) * 1000
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("response_time_ms", duration_ms)
                if response.status_code in (200, 201):
                    response.success()
                else:
                    response.failure(
                        f"Create failed: {response.status_code}"
                    )
            except Exception as exc:
                span.set_attribute("error", str(exc))
                raise

    def on_stop(self) -> None:
        """End the user session span and force a flush."""
        if self._session_span is not None:
            self._session_span.end()
            self._session_span = None
        # Force-flush spans so nothing is lost when Locust stops users
        provider = trace.get_tracer_provider()
        if isinstance(provider, TracerProvider):
            provider.force_flush()

    def _build_headers(self) -> dict[str, str]:
        """Build auth headers WITHOUT injecting traceparent.

        Returns only the Authorization header.  No trace context
        propagation headers are added so that target services are
        not contaminated with load-generator trace context.
        """
        token = self._get_token()
        return {"Authorization": f"Bearer {token}"}


def _on_quit(**kwargs: Any) -> None:
    '''Flush and shut down the TracerProvider on test exit.'''
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.force_flush()
        provider.shutdown()


def _register_quit_listener() -> None:
    '''Register the OTel shutdown handler on Locust's quit event.'''
    from locust import events as locust_events

    locust_events.quit.add_listener(_on_quit)


_register_quit_listener()
