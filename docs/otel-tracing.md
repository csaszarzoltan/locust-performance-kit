# OpenTelemetry Tracing

Instrument your Locust load tests with OpenTelemetry (OTel) to capture
distributed traces — span tree, attributes, and timing — for every simulated
request. Trace data can be exported to any OTLP-compatible backend (Grafana
Tempo, Jaeger, Datadog, Honeycomb, etc.) or printed to stdout for local
development.

## Overview

The kit provides two modules:

- `examples/otel_config.py` — `setup_otel()` and `get_tracer()` for
  initialising and retrieving a global OTel tracer
- `examples/otel_load_test.py` — `OTelAPIUser` extension that creates a
  `user_session` span per simulated user and sub-spans per HTTP request

## Quick Start

```bash
# Install OTel dependencies
pip install locust-performance-kit[otel]
# Or manually: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

# Run with console output (no backend needed)
OTEL_TRACES_EXPORTER=console \
  locust -f examples/otel_load_test.py \
    --headless --users 5 --spawn-rate 1 --run-time 30s \
    --host https://api.example.com
```

Each simulated user creates a `user_session` span on start, sub-spans for
every HTTP request, and finalises the session on stop.

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP gRPC endpoint, e.g. `http://otel-collector:4317` |
| `OTEL_TRACES_EXPORTER` | `otlp` | Exporter: `otlp`, `console`, or `none` |
| `OTEL_SERVICE_NAME` | `locust-performance-test` | Service name for trace identification |

### Exporter behaviour

| `OTEL_TRACES_EXPORTER` | Behaviour |
|---|---|
| `otlp` | Export via OTLP gRPC. Falls back to console exporter when no endpoint is configured. |
| `console` | Print spans as JSON to stdout. Useful for local development and debugging. |
| `none` | Disable tracing entirely (no-op tracer). Zero-overhead mode. |

## Python API

### Initialising the tracer

```python
from examples.otel_config import get_tracer, setup_otel

# Configure once at startup
setup_otel(service_name="my-load-test")

# Get a tracer for creating spans
tracer = get_tracer()
```

The `setup_otel()` function accepts optional overrides:

```python
setup_otel(
    service_name="my-load-test",           # defaults to "locust-performance-test"
    otlp_endpoint="http://tempo:4317",     # overrides OTEL_EXPORTER_OTLP_ENDPOINT
    traces_exporter="otlp",                # "otlp" | "console" | "none"
)
```

### Creating custom spans

```python
tracer = get_tracer()
with tracer.start_as_current_span("my-operation") as span:
    span.set_attribute("key", "value")
    # ... your code ...
```

## Using OTelAPIUser

`OTelAPIUser` extends `APIUser` with automatic OpenTelemetry instrumentation.
It can be used as a drop-in replacement in any Locust test script.

```python
from examples.otel_load_test import OTelAPIUser
from locust import task

class MyUser(OTelAPIUser):
    wait_time = between(1, 3)
    auth_provider = "static"

    @task
    def my_endpoint(self):
        self.client.get("/api/v1/data")
```

The `on_start()` method creates a `user_session` span with:

- `user_id` — random identifier (`user_<id>`)
- `auth_provider` — the active auth provider name

Each `@task` method that wraps requests in a sub-span automatically records:

- `http.method` (e.g. `GET`, `POST`)
- `http.url` (the endpoint path)
- `http.status_code` (the HTTP response status)
- `response_time_ms` (wall-clock duration)

### Disabling instrumentation

```python
# Set before starting Locust
export OTEL_TRACES_EXPORTER=none
```

When tracing is disabled, `OTelAPIUser` still works but no spans are created.

## Span Lifecycle

1. **User start** — `on_start()` creates a `user_session` span with
   `user_id` and `auth_provider` attributes.
2. **Requests** — Each `@task` starts a child span under the active session.
   The span records HTTP method, URL, status code, and response time.
3. **User stop** — `on_stop()` ends the `user_session` span and calls
   `force_flush()` on the TracerProvider.
4. **Test exit** — The module-level `_on_quit` listener (registered on
   `events.quit`) calls `force_flush()` and `shutdown()` to ensure no spans
   are lost.

## Design Decisions

### No trace context propagation

Span context headers (`traceparent`, `tracestate`) are intentionally NOT
injected into target requests. Locust is a load generator, not a mesh proxy;
injecting trace context would pollute the target service's traces. The
`_build_headers()` method returns only the `Authorization` header.

### Lazy initialisation

The module-level tracer is initialised lazily on first use rather than at
import time, so the module can be safely imported without triggering OTel SDK
side effects.

## Backend Setup

### Grafana Tempo

```bash
# Run Tempo locally with Docker
docker run -d --name tempo \
  -p 4317:4317 -p 3200:3200 \
  grafana/tempo:latest

# Point Locust traces to Tempo
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

Then configure a Tempo data source in Grafana pointing to `http://tempo:3200`
and import the Grafana dashboards from `grafana/dashboards/`.

### Jaeger

```bash
docker run -d --name jaeger \
  -p 4317:4317 -p 16686:16686 \
  jaegertracing/all-in-one:latest

export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

Open Jaeger UI at `http://localhost:16686` to browse traces.

### OTel Collector

For production deployments, route traces through an OTel Collector for
batching, filtering, and multi-backend fan-out:

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
exporters:
  otlp:
    endpoint: tempo:4317
  logging:
    loglevel: debug
service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [otlp, logging]
```

## Example

See `examples/otel_load_test.py` for a complete runnable example with three
endpoint tasks (`get_items`, `get_item_detail`, `create_item`) and
error-handling per request.
