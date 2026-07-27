# Analysis Brief: Observable Performance Pipeline

## Overview

Transform the Locust Performance Kit from a collection of templates into a complete,
production-ready observable performance testing pipeline with three integrated components:

1. **CI/CD Performance Gates** — GitHub Actions workflow template with configurable pass/fail thresholds
2. **OpenTelemetry Instrumentation** — Locust test scripts instrumented with OpenTelemetry for end-to-end tracing
3. **Grafana Dashboard Templates** — Pre-built JSON dashboards for visualizing OTel traces, Locust metrics, and system performance

---

## 1. CI/CD Performance Gates

### Current State Assessment

- **Existing CI file**: `.github/workflows/performance-ci.yml` runs Locust tests on push/PR (ubuntu/windows/macos matrix).
- **Current workflow**: Runs a 2-minute API load test, then generates reports (HTML, JSON, Markdown, JUnit) via the `locust-report` CLI. Thresholds are passed as CLI arguments (p95: 500ms, p99: 1000ms) but the workflow doesn't enforce gates — it always exits 0 regardless of metric violations.
- **Threshold module**: `src/locust_templates/thresholds.py` contains `ThresholdChecker` that validates p95/p99/error_rate, and `src/locust_templates/alerts.py` provides real-time alerting during test runs.
- **Gap**: No structured gate step that inspects metrics after the test and fails the pipeline on threshold breach. No support for matrix-free configurable thresholds. No integration with GitHub Actions status checks or deployment gating.

### Chosen Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| CI platform | GitHub Actions | Existing CI already uses it; zero migration cost |
| Threshold config | YAML workflow inputs + env vars | Git-versioned, auditable, re-usable across branches |
| Metric source | Locust CSV output + `locust-report` exit code | Already implemented; exit code 2 means threshold breach |
| Notification | Slack/Teams webhooks via existing `notifications.py` | Reuse existing `SlackNotifier`/`TeamsNotifier` |
| Gate logic | Composite job with `needs` + `if: failure()` | Standard GitHub Actions pattern; transparent in workflow graph |

### Interface Descriptions

**New file**: `.github/workflows/perf-test.yml`
**Location**: `locust-performance-kit/.github/workflows/perf-test.yml`
**Inputs** (workflow_dispatch and workflow_call):

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `locust-script` | string | `examples/api_load_test.py` | Path to Locust test script |
| `target-host` | string | `http://localhost:8080` | Target host URL for load test |
| `users` | number | `50` | Number of concurrent users |
| `spawn-rate` | number | `5` | Users spawned per second |
| `run-time` | string | `2m` | Test duration |
| `p95-threshold` | number | `500` | p95 latency threshold in ms |
| `p99-threshold` | number | `1000` | p99 latency threshold in ms |
| `error-rate-threshold` | number | `0.01` | Maximum error rate (0.0–1.0) |
| `rps-threshold` | number | `0` | Minimum RPS (0 = disabled) |

**Required environment variables** (set via repo secrets):

| Variable | Description |
|----------|-------------|
| `SLACK_WEBHOOK_URL` | Optional — Slack webhook for notifications |
| `TEAMS_WEBHOOK_URL` | Optional — Teams webhook for notifications |

**Outputs** (from the gate job):

| Output | Type | Description |
|--------|------|-------------|
| `gate-passed` | string | `true` or `false` |
| `p95-max` | string | Maximum p95 latency observed (ms) |
| `p99-max` | string | Maximum p99 latency observed (ms) |
| `error-rate` | string | Overall error rate |
| `metrics-json` | string | Full metrics as JSON (for downstream jobs) |

**Jobs**:

1. `load-test` — Runs the Locust test, generates CSV output
2. `generate-reports` (needs: load-test) — Produces HTML/JSON/Markdown reports
3. `quality-gate` (needs: generate-reports) — Evaluates thresholds, exits non-zero on breach
4. `notify` (needs: quality-gate, if: always()) — Sends pass/fail notification via Slack/Teams
5. The `quality-gate` job sets the workflow conclusion — downstream deploy jobs can `needs: [load-test, generate-reports, quality-gate]` and use `if: success()` to gate deployments

### Acceptance Criteria

- [ ] `perf-test.yml` accepts all listed inputs via `workflow_dispatch` and `workflow_call`
- [ ] The `quality-gate` job exits with non-zero code when any threshold is breached
- [ ] The `quality-gate` job exits 0 when all metrics are within thresholds
- [ ] All four reports (HTML, JSON, Markdown, JUnit) are uploaded as workflow artifacts
- [ ] Slack/Teams notification fires on both pass and fail (configurable via env vars)
- [ ] The workflow can be triggered manually (workflow_dispatch) and from other workflows (workflow_call) — e.g., after a staging deployment
- [ ] RPS threshold of 0 means "don't check RPS" (backward compatible)
- [ ] All existing `.github/workflows/performance-ci.yml` functionality is preserved (matrix, nightly schedule)

---

## 2. OpenTelemetry Instrumentation

### Current State Assessment

- **No OTel integration exists** in the kit. No OTel dependencies in `pyproject.toml` or `requirements.txt`.
- **Existing dependency**: Locust >= 2.20.0 (currently Locust 2.43+ ships **native** OTel support via env vars — `OTEL_TRACES_EXPORTER`, `OTEL_EXPORTER_OTLP_*`, etc.).
- **Existing `api_load.py`**: Uses `HttpUser` with `client.get/post` calls, has `events.request` and `events.user_error` listeners for basic logging.
- **Existing `MetricsCollector`**: Thread-safe in-process metrics recording, no span/trace context.
- **Gap**: No example scripts show how to configure Locust's built-in OTel export, add custom span attributes (user_id, endpoint, correlation_id), or push custom metrics to OTel backends.

### Chosen Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| OTel Python SDK | `opentelemetry-api>=1.30`, `opentelemetry-sdk>=1.30` | Latest stable; required for custom span creation |
| OTLP exporter | `opentelemetry-exporter-otlp>=1.30` | Sends traces to any OTel-compatible backend (Jaeger, Tempo, Grafana) |
| Locust integration | Built-in (env-var driven) | Locust 2.43+ supports natively; zero code needed for basic traces |
| Custom instrumentation | Manual via Python SDK | Locust's built-in OTel covers HTTP requests; custom spans for user journeys, correlation IDs, business context |
| Instrumentation libraries | `opentelemetry-instrumentation-requests` | Auto-instrument `requests` calls inside Locust `HttpUser` |
| Backend | OTLP gRPC endpoint | Self-hosted OTel Collector or Grafana Cloud Tempo |

### Interface Descriptions

**New files**:

| File | Purpose |
|------|---------|
| `examples/otel_load_test.py` | Runnable Locust script with full OTel instrumentation |
| `examples/otel_config.py` | Standalone helper module for OTel setup (TracerProvider, span processors, exporters) |

**`otel_config.py` — Public API**:

```python
def setup_otel(
    service_name: str = "locust-performance-test",
    otlp_endpoint: str | None = None,
    traces_exporter: str = "otlp",
) -> None:
    """
    Initialize OpenTelemetry tracing.

    If otlp_endpoint is None, reads OTEL_EXPORTER_OTLP_ENDPOINT env var.
    Falls back to stdout export (console exporter) for local debugging
    when no OTLP endpoint is configured.
    """

def get_tracer(service_name: str = "locust-performance-test") -> Tracer:
    """Return a tracer instance for creating custom spans."""
```

**`otel_load_test.py` — Structure**:

```
class OTelAPIUser(APIUser):        # Extends existing APIUser
    - on_start():                  # Sets up OTel context, starts root span per user session
      - Creates custom span "user_session" with attributes: user_id, auth_provider
    - @task get_items():            # Wraps request in span with endpoint-specific attributes
    - @task get_item_detail():      # Adds item_id to span attributes
    - @task create_item():          # Captures payload size in span attributes
    - on_stop():                    # Ends user session span, forces span flush
```

**Required environment variables** (all standard OTel env vars, documented at opentelemetry.io):

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_TRACES_EXPORTER` | `otlp` | Trace exporter type |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP gRPC endpoint |
| `OTEL_EXPORTER_OTLP_HEADERS` | (empty) | OTLP auth headers (e.g., for Grafana Cloud) |
| `OTEL_SERVICE_NAME` | `locust-performance-test` | Service name in traces |
| `OTEL_RESOURCE_ATTRIBUTES` | (empty) | Additional resource attributes (e.g., `environment=staging`) |

**New optional dependencies** (extras in pyproject.toml):

```toml
[project.optional-dependencies]
otel = [
    "opentelemetry-api>=1.30.0",
    "opentelemetry-sdk>=1.30.0",
    "opentelemetry-exporter-otlp>=1.30.0",
    "opentelemetry-instrumentation-requests>=0.50b0",
]
```

### Acceptance Criteria

- [ ] `otel_config.py` is importable and sets up a valid TracerProvider without side effects on import
- [ ] `setup_otel()` reads `OTEL_EXPORTER_OTLP_ENDPOINT` env var and configures OTLP exporter
- [ ] `setup_otel()` falls back to console exporter when no OTLP endpoint is configured (local dev)
- [ ] `otel_load_test.py` runs with `locust -f examples/otel_load_test.py --headless --users 5 --run-time 30s` without errors
- [ ] Custom spans (`user_session`) carry correct attributes (user_id, auth_provider)
- [ ] Each HTTP request inside `get_items()`, `get_item_detail()`, `create_item()` creates attributes for endpoint name, response time, status code
- [ ] Traces include both Locust's built-in spans (from native OTel) AND custom user_journey spans
- [ ] Span context propagation headers (traceparent) are NOT set on target requests (Locust is load generator, not service mesh — we observe, not inject)
- [ ] Running with `OTEL_TRACES_EXPORTER=none` disables tracing (zero overhead mode)
- [ ] Flush/shutdown on test end via `events.quit` listener to ensure spans are exported before process exits

---

## 3. Grafana Dashboard Templates

### Current State Assessment

- **No Grafana dashboards exist** in the repository.
- **No Prometheus metrics endpoint** is configured for Locust (Locust has a built-in `/export/prometheus` endpoint when running with web UI).
- **Existing reporting**: HTML reports, JSON, Markdown, and JUnit XML via the report generator and exporters.
- **Existing live dashboard**: `LiveDashboard` in `live_dashboard.py` renders self-contained HTML with Chart.js but is not a Grafana dashboard.
- **Gap**: Users have no way to visualize performance test results over time (trend across test runs) or correlate Locust metrics with OTel traces in a unified dashboard.

### Chosen Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Dashboard format | Grafana JSON model (v8+) | Industry standard; importable via UI, API, or ConfigMap |
| Data source | Prometheus / Tempo / Jaeger | Prometheus for Locust metrics; Tempo/Jaeger for OTel traces |
| Locust metrics source | Locust built-in Prometheus endpoint (`/export/prometheus`) | No extra exporter needed; Prometheus can scrape it directly |
| Dashboard IDs | Three JSON files | Separation of concerns: metrics, traces, combined |
| Variables | Templated with `$datasource`, `$environment` | Reusable across environments (dev/staging/prod) |

### Interface Descriptions

**New directory and files**:

```
grafana/dashboards/
    locust-overview.json       — Real-time test metrics (RPS, response times, error rate, users)
    locust-traces.json         — Trace exploration (service graph, span stats, trace list)
    locust-combined.json       — Combined view: metrics + traces + system performance
```

**Dashboard 1: `locust-overview.json`** — Quick-reference metrics dashboard

| Panel | Type | Target / Query | Description |
|-------|------|---------------|-------------|
| Active Users | Stat / Time series | `sum(locust_users_swarm)` | Current active users |
| Total RPS | Stat / Time series | `sum(rate(locust_requests_total[5m]))` | Requests per second |
| Avg Response Time | Stat / Time series | `avg(locust_request_duration_seconds_sum / locust_request_duration_seconds_count)` | Average response time |
| p95 Latency | Stat / Time series | `histogram_quantile(0.95, sum(rate(locust_request_duration_seconds_bucket[5m])) by (le))` | p95 latency |
| p99 Latency | Stat / Time series | `histogram_quantile(0.99, sum(rate(locust_request_duration_seconds_bucket[5m])) by (le))` | p99 latency |
| Error Rate | Stat / Time series | `sum(rate(locust_requests_total{state="FAILED"}[5m])) / sum(rate(locust_requests_total[5m]))` | Error percentage |
| Top Slow Endpoints | Table | `topk(10, ...)` p95 by endpoint name | Slowest endpoints |
| Failure Hotspots | Table | `topk(10, ...)` failure count by endpoint | Most failing endpoints |

**Dashboard 2: `locust-traces.json`** — Trace exploration (for Tempo/Jaeger data sources)

| Panel | Type | Target / Query | Description |
|-------|------|---------------|-------------|
| Service Graph | Node Graph | Tempo service graph | Service topology from traces |
| Trace List | Trace List | `{service.name="locust-performance-test"}` | Recent traces from Locust |
| Span Duration Heatmap | Heatmap | Span duration distribution | Latency distribution across spans |
| Span Attributes | Table | Per-span attributes | User ID, endpoint, status code from custom spans |
| Error Spans | List | `{status="error"}` | Failed spans for debugging |

**Dashboard 3: `locust-combined.json`** — Combined observability view

Reuses panels from the above two plus:
- **Trace/metric correlation** — Click on a time-series spike to see related traces
- **System resource panels** — CPU, memory, network during load test (if node_exporter available)
- **Timeline sync** — All panels share the same time range for correlation

**Dashboard JSON requirements**:
- Format: Grafana dashboard JSON model v8.5+
- Data source references: templated `"datasource": {"type": "$datasource_type", "uid": "$datasource_uid"}` or `"datasource": {"type": "prometheus", "uid": "Prometheus"}` as fallback
- Variables: `datasource` (type: datasource), `environment` (type: constant, default: `production`), `endpoint` (type: query, sourced from Prometheus metric labels)
- Tags: `["locust", "performance-testing", "observability"]`
- Editable: `true` so users can customize after import
- Timezone: `"browser"` for multi-team usability

### Acceptance Criteria

- [ ] `locust-overview.json` imports into Grafana v8+ without errors and shows data when Prometheus is scraping Locust
- [ ] `locust-traces.json` imports without errors and connects to Tempo/Jaeger data sources
- [ ] `locust-combined.json` imports without errors and shows both metrics and traces
- [ ] All three dashboards have valid JSON syntax (validated by `python -c "import json; json.load(open(...))"`)
- [ ] All dashboard UIDs are unique within the kit namespace (prefix: `locust-`)
- [ ] Template variables work: changing `$environment` from `production` to `staging` updates all panels
- [ ] Tags are set on all dashboards so they group together in Grafana
- [ ] Dashboard panels use null-handling defaults (no broken panels when no data exists yet)
- [ ] README section documents how to import dashboards (Grafana UI: + → Import → paste JSON or upload file; or Grafana API: `POST /api/dashboards/db`)

---

## 4. Dependencies Between Components

```
analysis-brief.md  ─────────► pre-tester ────────► developer ──────► tester ───────► documenter
(THIS FILE)        spec       (writes tests)       (implements)       (validates)    (writes docs)
                              │                     │                                    │
                              │ depends on          │ depends on                         │ depends on
                              │ spec from analyst   │ passing tests                      │ implemented code
                              ▼                     ▼                                    ▼
                      t_e6a18f71              t_c4607c66                          t_41d2db5a
                                                                                        │
                                                                                        │ depends on
                                                                                        │ green tests
                                                                                        ▼
                                                                                t_1d25683d
                                                                                (tester validates all)
```

**Explicit cross-component dependencies**:

| Component A | Depends on | Why |
|-------------|-----------|-----|
| CI/CD Gates | — | Standalone; only needs existing Locust + locust-report CLI |
| OTel Instrumentation | — | Standalone; new package dependencies, new example scripts |
| Grafana Dashboards | — | Standalone; JSON files with queries for Prometheus/Tempo |
| Documentation | CI/CD Gates, OTel Instrumentation, Grafana Dashboards | Must document implemented features, not planned ones |
| CI/CD Gates notification step | (existing) `notifications.py` | Reuses `SlackNotifier`/`TeamsNotifier` from v1.1.0 |
| OTel example script | (existing) `APIUser` in `api_load.py` | Extends `APIUser` with OTel spans |

---

## 5. Prioritized Task List

### P0 — Core pipeline functionality (must ship)

| ID | Task | Component | Est. effort | Notes |
|----|------|-----------|-------------|-------|
| 1 | Create `.github/workflows/perf-test.yml` with inputs + quality gate job | CI/CD Gates | 1h | Standalone workflow; reusable via `workflow_call` |
| 2 | Create `otel_config.py` with `setup_otel()` and `get_tracer()` | OTel | 1h | Reads standard OTel env vars; console fallback |
| 3 | Create `examples/otel_load_test.py` with OTelAPIUser | OTel | 1.5h | Extends APIUser; custom spans on user_session + per-request |
| 4 | Create `grafana/dashboards/locust-overview.json` | Grafana | 1h | Prometheus data source; standard Locust metric panels |
| 5 | Create `grafana/dashboards/locust-traces.json` | Grafana | 1h | Tempo/Jaeger data source; trace exploration |
| 6 | Create `grafana/dashboards/locust-combined.json` | Grafana | 1.5h | Mixed data sources; trace/metric correlation |
| 7 | Update `pyproject.toml` with OTel optional deps | OTel | 15min | `[project.optional-dependencies] otel = [...]` |

### P1 — Pipeline completeness

| ID | Task | Component | Est. effort | Notes |
|----|------|-----------|-------------|-------|
| 8 | Add `perf-test.yml` notification step to Slack/Teams | CI/CD Gates | 30min | Reuse `notifications.py` after quality gate |
| 9 | Add `locust-report` exit-code handling in `quality-gate` job | CI/CD Gates | 30min | Parse `--format json --output /dev/null` exit code 2 |
| 10 | Add `setup_otel()` console exporter fallback and test it | OTel | 30min | Console exporter for local dev without OTel backend |
| 11 | Add `events.quit` flush/shutdown to `otel_load_test.py` | OTel | 15min | Ensure spans export before `locust` process exits |
| 12 | Ensure RPS threshold = 0 means "skip RPS check" | CI/CD Gates | 15min | Backward compat |
| 13 | Add Grafana import instructions to README | Grafana | 30min | UI + API methods |

### P2 — Polish and hardening

| ID | Task | Component | Est. effort | Notes |
|----|------|-----------|-------------|-------|
| 14 | Add matrix support to `perf-test.yml` (opt-in) | CI/CD Gates | 30min | For multi-region or multi-target testing |
| 15 | Add breakdown panels to `locust-overview.json` per endpoint | Grafana | 30min | Table with per-endpoint p95, RPS, failure count |
| 16 | Add `OTEL_EXPORTER_OTLP_HEADERS` support for Grafana Cloud | OTel | 15min | Standard env var, just need to document |
| 17 | Validate all three dashboard JSONs pass `pytest` fixture import test | Grafana | 15min | Test reads JSON validates structure |

### Implementation Order

```
Week 1: Task IDs 1, 2, 3, 4, 7  (P0 — core)
Week 1-2: Task IDs 5, 6, 8, 9, 10, 11, 12  (P0+P1 — completeness)
Week 2: Task IDs 13, 14, 15, 16, 17  (P2 — polish)
```

---

## 6. New Test Spec for Pre-Tester

### Test files to create

| Test file | Tests for | Pattern |
|-----------|-----------|---------|
| `tests/unit/test_perf_gate.py` | CI/CD Gates workflow | Interface: import checks + YAML parsing. Behavioral: threshold logic, env var parsing |
| `tests/unit/test_otel.py` | OTel instrumentation | Interface: `setup_otel` import + signature. Behavioral: span creation, attribute setting, console exporter |
| `tests/unit/test_grafana_dashboards.py` | Grafana dashboard JSONs | Interface: file existence + valid JSON. Behavioral: required panel titles, data source references, variables |

### Test conventions (match existing patterns)

- Interface smoke tests (pass immediately) in `TestInterfaceSmoke` class
- Behavioral tests raise `NotImplementedError` until developer implements
- All behavioral tests must have at least one assertion so they're real contracts
- Use `pytest.raises(NotImplementedError)` pattern or direct `raise NotImplementedError` inside test body
- Run `pytest tests/ -v` to confirm interface tests pass and behavioral tests fail as expected

### Key test scenarios for CI/CD Gates

1. Interface: `yaml.safe_load(open(...))` on workflow file — must parse without error
2. Interface: workflow has `on.workflow_dispatch.inputs` with all required inputs
3. Interface: workflow has `on.workflow_call.inputs` (reusable)
4. Behavioral: `quality-gate` job exits non-zero when p95 > threshold
5. Behavioral: `quality-gate` job exits non-zero when error rate > threshold
6. Behavioral: `quality-gate` job exits 0 when all metrics within thresholds
7. Behavioral: RPS threshold = 0 disables RPS check
8. Behavioral: notification fires on both pass and fail

### Key test scenarios for OTel

1. Interface: `otel_config.setup_otel` is callable with correct signature
2. Interface: `otel_config.get_tracer` returns a `Tracer` instance
3. Behavioral: `setup_otel()` with OTLP endpoint env var configures OTLP exporter
4. Behavioral: `setup_otel()` without endpoint configures console exporter
5. Behavioral: in `otel_load_test.py`, `OTelAPIUser.on_start()` creates "user_session" span
6. Behavioral: custom span has attributes `user_id` and `auth_provider`
7. Behavioral: each HTTP request creates a sub-span under user_session
8. Behavioral: `OTEL_TRACES_EXPORTER=none` disables tracing

### Key test scenarios for Grafana Dashboards

1. Interface: `grafana/dashboards/locust-overview.json` exists and is valid JSON
2. Interface: `grafana/dashboards/locust-traces.json` exists and is valid JSON
3. Interface: `grafana/dashboards/locust-combined.json` exists and is valid JSON
4. Behavioral: each dashboard has required `title` field (non-empty string)
5. Behavioral: each dashboard has `panels` array with at least 3 panels
6. Behavioral: `locust-overview.json` has Prometheus-based panels with query expressions
7. Behavioral: `locust-traces.json` has Tempo/Jaeger based panels
8. Behavioral: all dashboards have `tags` containing `"locust"`

---

## Summary

This spec defines three self-contained but complementary components that together transform
the Locust Performance Kit into an observable, production-ready CI/CD pipeline.

- **CI/CD Gates** add structured threshold enforcement to the existing GitHub Actions workflow
- **OTel Instrumentation** adds end-to-end tracing to Locust test scripts using Locust's built-in OTel support plus custom spans
- **Grafana Dashboards** provide reusable visualization templates for Prometheus and Tempo/Jaeger

All three components are deployable independently and work with self-hosted/OSS infrastructure
(no external service dependencies). Total estimated implementation effort: ~11 hours P0, ~3 hours P1, ~2 hours P2.
