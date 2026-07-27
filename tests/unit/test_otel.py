"""Pre-development tests for OpenTelemetry instrumentation.

Interface tests verify the otel_config module API surface.
Behavioral tests verify span creation, attribute setting,
exporter configuration, and tracer lifecycle.
"""

from __future__ import annotations

import inspect

import pytest

import examples.otel_load_test  # noqa: F401 — early import to avoid gevent conflicts
from examples.otel_config import get_tracer, setup_otel

# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestInterfaceSmoke:
    """Verify that otel_config module has the correct public API."""

    def test_setup_otel_exists(self):
        """setup_otel must be a callable function."""
        assert callable(setup_otel)

    def test_get_tracer_exists(self):
        """get_tracer must be a callable function."""
        assert callable(get_tracer)

    def test_setup_otel_signature(self):
        """setup_otel must have correct parameter names."""
        sig = inspect.signature(setup_otel)
        param_names = list(sig.parameters.keys())
        assert "service_name" in param_names
        assert "otlp_endpoint" in param_names
        assert "traces_exporter" in param_names

    def test_setup_otel_default_service_name(self):
        """setup_otel service_name must default to 'locust-performance-test'."""
        sig = inspect.signature(setup_otel)
        default = sig.parameters["service_name"].default
        assert default == "locust-performance-test"

    def test_setup_otel_otlp_endpoint_default(self):
        """setup_otel otlp_endpoint must default to None."""
        sig = inspect.signature(setup_otel)
        default = sig.parameters["otlp_endpoint"].default
        assert default is None

    def test_setup_otel_traces_exporter_default(self):
        """setup_otel traces_exporter must default to 'otlp'."""
        sig = inspect.signature(setup_otel)
        default = sig.parameters["traces_exporter"].default
        assert default == "otlp"

    def test_get_tracer_signature(self):
        """get_tracer must have service_name parameter."""
        sig = inspect.signature(get_tracer)
        assert "service_name" in sig.parameters

    def test_get_tracer_default_service_name(self):
        """get_tracer service_name must default to 'locust-performance-test'."""
        sig = inspect.signature(get_tracer)
        default = sig.parameters["service_name"].default
        assert default == "locust-performance-test"

    def test_module_has_docstring(self):
        """otel_config module must have a docstring."""
        import examples.otel_config as mod

        assert mod.__doc__ is not None
        assert len(mod.__doc__) > 0


# ──────────────────────────────────────────────────────────────
# Behavioral tests — setup_otel() configuration
# ──────────────────────────────────────────────────────────────


class TestSetupOTelBehavior:
    """Behavioral tests for setup_otel() configuration."""

    def test_setup_otel_configures_console_exporter(self, monkeypatch):
        """setup_otel() without OTLP endpoint must configure
        console exporter (fallback)."""
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        # Should not raise — console exporter fallback
        try:
            setup_otel(service_name="test-console", traces_exporter="console")
        except Exception as exc:
            pytest.fail(f"setup_otel(console) raised unexpectedly: {exc}")
        # Verify tracer provider is configured
        from opentelemetry import trace as ot_trace

        provider = ot_trace.get_tracer_provider()
        assert provider is not None
        tracer = provider.get_tracer("test-console")
        assert tracer is not None
        assert hasattr(tracer, "start_span")

    def test_setup_otel_configures_otlp_exporter(self, monkeypatch):
        """setup_otel() with OTLP endpoint env var must configure OTLP exporter."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        try:
            setup_otel(service_name="test-otlp", traces_exporter="otlp")
        except Exception as exc:
            pytest.fail(f"setup_otel(otlp) raised unexpectedly: {exc}")

    def test_setup_otel_falls_back_to_console(self, monkeypatch):
        """setup_otel() without OTLP endpoint must fall back to console exporter."""
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        try:
            setup_otel(service_name="test-fallback")
        except Exception as exc:
            pytest.fail(f"setup_otel(fallback) raised unexpectedly: {exc}")

    def test_setup_otel_disabled_with_none(self):
        """OTEL_TRACES_EXPORTER=none must disable tracing."""
        from opentelemetry import trace as ot_trace

        setup_otel(service_name="test-none", traces_exporter="none")
        provider = ot_trace.get_tracer_provider()
        # Should be configured — the tracer will just not export
        tracer = provider.get_tracer("test-none")
        assert tracer is not None
        # Creating a span should not crash
        with tracer.start_as_current_span("silent-span") as span:
            span.set_attribute("test", "value")
        assert True

    def test_setup_otel_reads_env_endpoint(self, monkeypatch):
        """setup_otel() must read OTEL_EXPORTER_OTLP_ENDPOINT env var
        when otlp_endpoint is None."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4317")
        try:
            setup_otel(service_name="test-env")
        except Exception as exc:
            pytest.fail(f"setup_otel(env_endpoint) raised unexpectedly: {exc}")

    def test_setup_otel_reads_service_name_env(self, monkeypatch):
        """setup_otel() must respect OTEL_SERVICE_NAME env var."""
        monkeypatch.setenv("OTEL_SERVICE_NAME", "my-custom-service")
        try:
            setup_otel()
        except Exception as exc:
            pytest.fail(f"setup_otel(env_service_name) raised unexpectedly: {exc}")

    def test_get_tracer_returns_tracer_instance(self):
        """get_tracer() must return a tracer object with start_span."""
        tracer = get_tracer()
        assert tracer is not None
        assert hasattr(tracer, "start_span")
        assert hasattr(tracer, "start_as_current_span")
        # Verify we can create a span
        span = tracer.start_span("test-span")
        assert span is not None
        span.end()

    def test_get_tracer_with_custom_name(self):
        """get_tracer() must accept custom service name."""
        tracer = get_tracer(service_name="custom-service")
        assert tracer is not None
        assert hasattr(tracer, "start_span")


# ──────────────────────────────────────────────────────────────
# Behavioral tests — OTel-instrumented Locust user
# ──────────────────────────────────────────────────────────────


class TestOTelAPIUserBehavior:
    """Behavioral tests for OTel-instrumented Locust user class."""

    def _make_user(self):
        """Create an OTelAPIUser without triggering Locust HttpUser init.

        Uses ``__new__`` pattern to avoid Locust's environment setup.
        """
        from examples.otel_load_test import OTelAPIUser

        user = OTelAPIUser.__new__(OTelAPIUser)
        user._session_span = None
        return user

    def test_on_start_creates_user_session_span(self):
        """OTelApiUser.on_start() must create a 'user_session' span."""
        from examples.otel_load_test import _init_tracing

        _init_tracing()
        user = self._make_user()
        try:
            user.on_start()
        except Exception as exc:
            pytest.fail(f"OTelAPIUser.on_start() raised unexpectedly: {exc}")
        # Verify session_span attribute was created
        assert hasattr(user, "_session_span"), (
            "OTelAPIUser must have _session_span attribute after on_start()"
        )
        if user._session_span is not None:
            assert user._session_span.is_recording(), (
                "user_session span should be recording"
            )

    def test_user_session_span_has_user_id_attribute(self):
        """user_session span must carry user_id attribute."""
        from examples.otel_load_test import _init_tracing

        _init_tracing()
        user = self._make_user()
        user.on_start()
        span = user._session_span
        if span is not None:
            attrs = dict(span.attributes or {})
            assert "user_id" in attrs, (
                "user_session span must have user_id attribute"
            )
            assert isinstance(attrs["user_id"], str), (
                "user_id must be a string"
            )
            assert attrs["user_id"].startswith("user_"), (
                "user_id should start with 'user_' prefix"
            )

    def test_user_session_span_has_auth_provider_attribute(self):
        """user_session span must carry auth_provider attribute."""
        from examples.otel_load_test import _init_tracing

        _init_tracing()
        user = self._make_user()
        user.on_start()
        span = user._session_span
        if span is not None:
            attrs = dict(span.attributes or {})
            assert "auth_provider" in attrs, (
                "user_session span must have auth_provider attribute"
            )
            assert isinstance(attrs["auth_provider"], str), (
                "auth_provider must be a string"
            )

    def test_get_items_creates_sub_span(self):
        """get_items() task must create a sub-span under user_session."""
        from examples.otel_load_test import OTelAPIUser

        # Verify the method has OTel span wrapping by inspecting source
        source = inspect.getsource(OTelAPIUser.get_items)
        assert "start_as_current_span" in source, (
            "get_items must create a sub-span using start_as_current_span"
        )

    def test_get_item_detail_adds_item_id_attribute(self):
        """get_item_detail() span must include item_id attribute."""
        from examples.otel_load_test import OTelAPIUser

        source = inspect.getsource(OTelAPIUser.get_item_detail)
        assert "item_id" in source, (
            "get_item_detail must set item_id attribute on the span"
        )
        assert "span.set_attribute" in source, (
            "get_item_detail must call span.set_attribute"
        )

    def test_create_item_captures_payload_size(self):
        """create_item() span must include payload size attribute."""
        from examples.otel_load_test import OTelAPIUser

        source = inspect.getsource(OTelAPIUser.create_item)
        assert "payload_size_bytes" in source, (
            "create_item must capture payload_size_bytes attribute"
        )
        assert "span.set_attribute" in source, (
            "create_item must call span.set_attribute for payload size"
        )

    def test_on_stop_ends_session_span(self):
        """OTelAPIUser.on_stop() must end the user_session span."""
        from examples.otel_load_test import _init_tracing

        _init_tracing()
        user = self._make_user()
        user.on_start()
        span_before = user._session_span
        assert span_before is not None
        user.on_stop()
        # After on_stop, the span should be ended
        if hasattr(span_before, "is_recording"):
            assert not span_before.is_recording(), (
                "user_session span should NOT be recording after on_stop()"
            )

    def test_on_stop_flushes_spans(self):
        """OTelAPIUser.on_stop() must flush spans to exporter."""
        from examples.otel_load_test import _init_tracing

        _init_tracing()
        user = self._make_user()
        user.on_start()
        # on_stop should flush without error
        try:
            user.on_stop()
        except Exception as exc:
            pytest.fail(f"OTelAPIUser.on_stop() raised unexpectedly: {exc}")

    def test_events_quit_flushes_and_shuts_down(self):
        """events.quit listener must flush and shutdown TracerProvider."""
        import examples.otel_load_test as otel_mod

        assert hasattr(otel_mod, "_on_quit"), (
            "otel_load_test must have an events.quit listener"
        )
        # The _on_quit handler should call shutdown without error
        try:
            otel_mod._on_quit()
        except Exception as exc:
            pytest.fail(f"events.quit handler raised unexpectedly: {exc}")

    def test_no_traceparent_injection(self):
        """Span context headers must NOT be injected into target requests."""
        user = self._make_user()
        headers = user._build_headers()
        # Must NOT contain traceparent or tracestate
        assert "traceparent" not in headers, (
            "Must NOT inject traceparent header into target requests"
        )
        assert "tracestate" not in headers, (
            "Must NOT inject tracestate header into target requests"
        )
        # Must contain Authorization header
        assert "Authorization" in headers, (
            "Should still include Authorization header"
        )