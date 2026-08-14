# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.0-rc1-validation] - 2026-08-09

### Validated

- Added lazy public API resolution so pure import, decision, comparison, and workspace modules no longer initialize Locust/gevent while `from locust_templates import APIUser` remains compatible.
- Added four-job Linux RC pipeline for regression, measured coverage, Chromium/axe screenshots, wheel installation, and Docker health.
- Measured 98% coverage across changed pure modules and 98% across critical import/artifact modules; added reproducible local coverage gate.
- Added Playwright flows for responsive Inbox, sample, ambiguous and traversal imports, comparison/timeline, axe, screenshots, and downloads.

## [1.7.0-rc1] - 2026-08-09

### Stabilized

- Completed US-004 with endpoint-level current/baseline/absolute/percentage deltas, Added/Missing semantics, compatibility summary, aligned p95/RPS timeline, accessible SVG, and data-table fallback.
- Set runtime/package version to 1.7.0 and added focused Pyright configuration for the new application modules.
- Verified 1.7.0 wheel installation, workspace health, CLI exit 2 artifact generation, and independent decision-hash validation.

## [1.7.0] - 2026-08-09

### Added

- Local Run Inbox with safe ZIP validation, candidate discovery, quality grading, persisted decisions, filtering, sample onboarding, and responsive recovery states.
- Immutable environment baseline promotion and history.
- Canonical `performance-decision/v1` JSON and deterministic Markdown exports in the workspace and `locust-kit analyze`.
- `locust-workspace` launcher, health endpoint, security headers, real-I/O import tests, and complete performance CI workflow assets.

### Tests

- 1,102 tests pass, including archive attacks, persistence, real import flow, sample idempotency, decision hashing, CLI regressions, and existing functionality.

## [1.6.0] - 2026-08-04

### Added

- **AI Performance Intelligence** (`src/locust_templates/intelligence.py`):
  - `RunProfile.from_csv()` parses `{prefix}_stats.csv`, `_failures.csv`, `_exceptions.csv`, and history (`_stats_history.csv` modern / `_history.csv` legacy) into per-endpoint p50/p95/p99, RPS, error rates, and time series (reuses `ReportData`)
  - `AnomalyDetector` — z-score + EWMA regression detection vs a baseline run, within-run drift, and error-spike detection with merged windows and severity
  - `BottleneckDetector` — RPS-saturation knee, weakest-endpoint ranking (top 5), Pearson correlations (error rate vs RPS, p95 vs user count)
  - `CapacityProjector` — linear/EWMA trend of p95/p99/error_rate to the load level where an `--slo` would breach, with confidence
  - `check_slos()` and `InsightGenerator` — zero-config deterministic insights
  - `LLMInsightProvider` — optional OpenAI-compatible enrichment (stdlib `urllib`, never raises) with clean statistical fallback
  - `analyze_run()` end-to-end pipeline returning an `AnalysisReport` (markdown + JSON)
- **`locust-kit analyze` CLI** (`src/locust_templates/cli_analyze.py`):
  - Flags: `--csv <prefix>`, repeatable `--slo KEY=VALUE` (p95/p99 ms, error_rate ratio), `--baseline <prior-prefix|baseline-name>`, `--format markdown|json`, `--output PATH|-`, `--llm`, `--version`
  - Baseline resolution: prior-run CSV prefix, then `.baselines/<name>.json` (shared `PerformanceBaseline` store)
  - Exit codes: `0` OK/advisory, `1` usage/IO/parse error, `2` **measured SLO violation** (CI gate signal)
- **Documentation**: `docs/ai-performance-intelligence.md` CLI/API reference, `examples/analyze_run.py`, README section + badges (v1.6.0, 1068 tests), `docs/ci-cd-gates.md` AI analysis section, `FEATURES-DONE.md`
- **Test suite**: 169 new tests (131 `test_intelligence` + 38 `test_cli_analyze`) against real Locust 2.46.2 CSV fixtures under `tests/fixtures/intelligence/` (run_a healthy, run_b regressed, run_clean knee, full_history, legacy, edge)

### Changed

- Version bumped from 1.5.0 to 1.6.0
- `pyproject.toml`: added `locust-kit` console script entry point
- Full suite: 1068 tests pass (169 added for this feature)

## [1.4.1] - 2026-07-28

### Added

- **Multi-Protocol documentation suite**: troubleshooting guide and unified configuration reference for all three protocol templates
- **Runnable example scripts** for gRPC, GraphQL, and WebSocket — replaces previous TDD stubs with realistic, production-ready Locust tests

### Fixed

- README now includes "Multi-Protocol Templates (v1.4.0+)" section with discoverability links
- README "Documentation" section now lists all three protocol-specific guides
- README "What's Inside" and "Project Structure" now include `grpc.py`, `graphql.py`, `websocket.py`

## [1.4.0] - 2026-07-27

### Added

- **gRPC load testing template** (`src/locust_templates/grpc.py`):
  - `GrpcUser` class with channel management, stub injection, and event reporting
  - TLS/mTLS support, auth metadata via existing Authenticator system
  - Optional dependency: `pip install locust-performance-kit[grpc]`

- **GraphQL query benchmarking template** (`src/locust_templates/graphql.py`):
  - `GraphQLUser` class extending HttpUser with `query()` helper
  - `GraphQLResponse` dataclass for structured results
  - `QueryComplexityAnalyzer` with field-weight and depth-based scoring
  - Complexity threshold via `LOCUST_GRAPHQL_COMPLEXITY_THRESHOLD` env var

- **WebSocket stress testing template** (`src/locust_templates/websocket.py`):
  - `WebSocketUser` class with concurrent connection management
  - Configurable `max_connections` per user
  - Connection pool lifecycle (connect/send/receive/close) with event firing
  - Optional dependency: `pip install locust-performance-kit[websocket]`

### Changed

- Version bumped from 1.3.0 to 1.4.0
- pyproject.toml: added `grpc` and `websocket` optional dependency groups
- Test suite expanded with new template unit tests and integration checks

## [1.3.0] - 2026-07-19

### Added

- **Real-time live metrics dashboard** (`src/locust_templates/live_dashboard.py`):
  - `LiveDashboard` collects time-series snapshots of avg/p95 response time, throughput, error rate, and active users
  - `TimeSeriesPoint` dataclass for each snapshot
  - Self-contained HTML rendering with embedded Chart.js for live response-time and throughput charts
  - Auto-refresh meta tag (configurable interval, default 5s)
  - Rolling window of max_points (default 300) to limit memory usage
  - `record_from_collector()` method to snapshot from `MetricsCollector`
  - `render()` and `render_to_file()` for HTML output
  - Alerts panel integration — pass fired `Alert` objects to display in the dashboard
- **Configurable threshold alerts** (`src/locust_templates/alerts.py`):
  - `AlertRule` dataclass with metric, operator (>, >=, <, <=, ==), threshold, and severity
  - `Alert` dataclass with fired alert details (value, timestamp, message)
  - `AlertEngine` evaluates rules against live metrics, supports dedup mode
  - `AlertEngine.from_config()` factory for creating from config dicts
  - `AlertEngine.check()` returns newly fired alerts; `get_alerts()` returns all history
- **Failure hotspots in reports** (`report_data.py`, `exporters.py`):
  - `ReportData.get_failure_hotspots()` returns endpoints sorted by failure rate (descending)
  - HTMLExporter renders a "Failure Hotspots" table section
  - MarkdownExporter renders a "## Failure Hotspots" table section
  - Only endpoints with > 0 failures are included
- **Dashboard and alerts configuration** (`config.py`, `runner.py`):
  - New config fields: `dashboard_enabled`, `dashboard_refresh_interval`, `dashboard_max_points`, `dashboard_output`
  - New config fields: `alerts_enabled`, `alert_rules` (parsed from JSON env var)
  - Environment variables: `LOCUST_DASHBOARD_ENABLED`, `LOCUST_DASHBOARD_REFRESH`, `LOCUST_DASHBOARD_MAX_POINTS`, `LOCUST_DASHBOARD_OUTPUT`
  - Environment variables: `LOCUST_ALERTS_ENABLED`, `LOCUST_ALERT_RULES` (JSON array of rule dicts)
  - `runner.build_dashboard_command()` helper for CI/CD dashboard generation
  - New exports in `__init__.py`: `LiveDashboard`, `TimeSeriesPoint`, `Alert`, `AlertEngine`, `AlertRule`

- **Observable Performance Pipeline** (`examples/otel_config.py`, `examples/otel_load_test.py`):
  - `setup_otel()` initializes the OpenTelemetry TracerProvider with configurable exporters (OTLP gRPC, console, or none)
  - `get_tracer()` returns a named tracer instance for custom span creation
  - `OTelAPIUser` extends `APIUser` with `on_start()` creating a `user_session` span, sub-spans for each HTTP task (`get_items`, `get_item_detail`, `create_item`), and `on_stop()` flushing spans
  - Module-level `_on_quit` listener registered on `events.quit` for graceful TracerProvider shutdown
  - Span context headers (`traceparent`) intentionally NOT injected into target requests to avoid polluting target traces
  - Environment variables: `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_TRACES_EXPORTER`, `OTEL_SERVICE_NAME`
  - 78 new pre-development tests (interface + behavioral) covering tracer lifecycle, span attributes, and exporter configuration
- **CI/CD Performance Gates** (`.github/workflows/perf-test.yml`):
  - Reusable GitHub Actions workflow with `workflow_dispatch` and `workflow_call` triggers
  - 4-job pipeline: `load-test` → `generate-reports` → `quality-gate` → `notify`
  - Quality gate evaluates p95, p99, error rate, and RPS thresholds with exit code 2 on failure
  - Configurable inputs: `locust-script`, `target-host`, `users`, `spawn-rate`, `run-time`, `p95-threshold`, `p99-threshold`, `error-rate-threshold`, `rps-threshold` (default 0 = disabled)
  - Reusable outputs: `gate-passed`, `p95-max`, `p99-max`, `error-rate`, `metrics-json` for downstream jobs
  - Slack + Teams webhook notifications on pass/fail
  - 16 tests covering interface smoke, quality-gate behavior, notification behavior, and workflow reusability
- **Grafana Dashboards** (`grafana/dashboards/`):
  - `locust-overview.json`: Prometheus-based dashboard with Active Users, RPS, Avg Response Time, p95/p99 Latency, Error Rate, Top Slow Endpoints, and Failure Hotspots tables
  - `locust-traces.json`: Tempo-based dashboard with Service Graph (nodeGraph), Trace List (traceList), Span Duration Heatmap, Error Spans, and Span Attributes panels
  - `locust-combined.json`: Combined Prometheus + Tempo dashboard with Active Users, RPS, Service Graph, Trace List, CPU Usage, Memory Usage, and Network panels
  - All dashboards have `datasource`, `environment` template variables with `environment` defaulting to `production`
  - Tags: `locust`, `performance-testing`, `observability`; unique UIDs prefixed with `locust-`
  - 14 tests covering interface validity, panel content, data source types, and fieldConfig presence

### Changed

- Version bumped from 1.2.0 to 1.3.0
- Test suite expanded from 398 to 593 passing tests (78 OTel + 16 CI gates + 14 Grafana dashboards + 98 v1.3.0)

## [1.2.0] - 2026-07-19

### Added

- **Pluggable authentication startup hooks** (`src/locust_templates/auth.py`):
  - `Authenticator` ABC with `authenticate()` method returning headers dict
  - `StaticTokenAuthenticator` — static token from constructor or env var
  - `EnvTokenAuthenticator` — token from configurable environment variable
  - `OAuth2ClientCredentialsAuthenticator` — OAuth2 client_credentials flow with token caching and thread-safe refresh
  - `AuthRegistry` — registry for registering and retrieving auth providers by name
  - `AuthError`, `AuthConfigError`, `AuthenticationError` exception hierarchy
  - Integration with `APIUser.on_start()` and `LoadTestConfig`
  - New config fields: `auth_provider`, `auth_client_id`, `auth_client_secret`, `auth_token_url`, `auth_scopes`
  - Environment variables: `LOCUST_AUTH_PROVIDER`, `LOCUST_AUTH_CLIENT_ID`, `LOCUST_AUTH_CLIENT_SECRET`, `LOCUST_AUTH_TOKEN_URL`, `LOCUST_AUTH_SCOPES`
- **Request correlation and cascade failure detection** (`src/locust_templates/correlator.py`):
  - `RequestCorrelator` attaches to Locust's `events.request` to track request chains
  - Cascade detection: failed request → downstream failures from same user within time window
  - `CorrelatedEvent`, `FailureChain`, `CorrelationSummary` data classes
  - CSV and JSON export of correlated events and failure chains
  - Summary statistics: total/cascade/root failures, avg chain depth, top failure chains
- **Cross-platform report export** (`src/locust_templates/report_data.py`, `exporters.py`, `cli.py`):
  - `ReportData` dataclass model decoupling CSV parsing from report rendering
  - `ReportData.from_csv()` factory parses `_stats.csv`, `_failures.csv`, `_exceptions.csv`
  - Strategy-pattern exporters: `HTMLExporter`, `JSONExporter`, `MarkdownExporter`, `JUnitXMLExporter`
  - `ReportExporter` ABC with `render()` and `export()` methods
  - `locust-report` CLI with `--format`, `--output`, `--p95-threshold`, `--p99-threshold`, `--version`
  - Exit codes: 0 (success), 1 (error), 2 (threshold violation) for CI/CD gating
  - Cross-platform path handling via `pathlib.Path` (auto-creates parent directories)
  - `runner.generate_report()` helper for one-call report generation in any format
  - `runner.build_locust_command()` extended with `report_format`, `report_output`, `p95_threshold`, `p99_threshold` params
  - 116 new test cases covering data model, exporters, CLI, and runner integration
- **HTML report correlation section** (`report_generator.py`):
  - Optional `correlation_summary` parameter on `HTMLReportGenerator.__init__`
  - Renders cascade failure summary cards and top failure chains table
- **Baseline cascade rate** (`baseline.py`):
  - Optional `correlation_summary` parameter on `save_baseline()`
  - Stores `cascade_rate`, `cascade_failures`, `root_failures` in baseline JSON

### Changed

- Version bumped from 1.1.0 to 1.2.0
- Updated `src/locust_templates/__init__.py` to export `RequestCorrelator` and data classes
- `HTMLReportGenerator` now delegates to `ReportData` + exporters for `to_json()`, `to_markdown()`, `to_junit()` (backward-compatible shims)
- Test suite expanded from 172 to 398 passing tests

## [1.1.0] - 2026-07-19

### Added

- **HTML report generator** (`src/locust_templates/report_generator.py`):
  - `HTMLReportGenerator.from_csv()` parses Locust CSV stats + failures files
  - `generate()` creates self-contained HTML with CSS-only bar charts (no JS deps)
  - Summary stats table, per-endpoint p95/p99 metrics, threshold pass/fail indicators
- **Performance regression baseline comparison** (`src/locust_templates/baseline.py`):
  - `PerformanceBaseline.save_baseline()`, `compare()`, `list_baselines()`
  - `RegressionResult` with regressions, improvements, and human-readable summary
  - Regression detection: p95 degradation > 10% vs baseline
  - `BaselineNotFoundError` exception for missing baselines
- **Slack/Teams notifications** (`src/locust_templates/notifications.py`):
  - `Notifier` ABC with `SlackNotifier` and `TeamsNotifier` implementations
  - Webhook URL via environment variables (`SLACK_WEBHOOK_URL`, `TEAMS_WEBHOOK_URL`)
  - `ConfigurationError` for missing config, `NotificationError` for HTTP failures
- **Test fixtures**: `tests/fixtures/sample_stats.csv` and `sample_failures.csv`
- **Test suite**: 37 new tests for all three new modules (interface + behavioral)

### Changed

- Version bumped from 1.0.0 to 1.1.0
- Updated `src/locust_templates/__init__.py` to export new modules
- Added `.gitignore` for Python build artifacts

## [1.5.0] - 2026-08-01

### Added

- **OpenAPI-to-Locust code generation** (`locust-gen` CLI):
  - `openapi_parser`: parse OpenAPI 3.x specs (endpoints, methods, schemas, auth) into structured models
  - `locust_generator`: generate Locust test files from parsed specs — HttpUser subclasses, per-endpoint task methods, request bodies, query params
  - `load_patterns`: `ConstantLoadShape` and `RampUpLoadShape` (TDD stubs) for codegen output
  - `cli_gen`: `locust-gen` entry point for CLI-based code generation from spec files
  - `petstore.yaml` example OpenAPI spec
  - Dependencies: `openapi-spec-validator`, `pyyaml`
- **OpenAPI-to-Locust documentation**: full feature guide (`docs/openapi-to-locust.md`), example spec (`examples/openapi_petstore_spec.yaml`), generated locustfile (`examples/openapi_generated_locustfile.py`), README updated with badge, Quick Start, What's Inside, Project Structure, and Documentation links
- **Performance engineering workspace** (Flask API):
  - Visual scenario projects, distributed run recovery, correlated diagnostics
  - Versioned performance policies, tenant-scoped test-data vault, capacity/cost estimates
  - Six responsive server-rendered workspaces and a versioned Flask API for automation
  - Idempotent scenario creation, schema-versioned export/import, worker-capacity recovery
  - Deduplicated diagnostics, expiring policy waivers, encrypted-at-rest local secrets

### Changed

- Version bumped from 1.4.1 to 1.5.0
- Added ruff `per-file-ignores` for E501 in `tests/` and `src/`
- Lint fixes: unused imports (`test_graphql.py`), unused variables (`test_websocket.py`), B017 noqa markers

### [Unreleased] - 2026-08-14

#### Added
- Deterministic `performance-verification-bundle/v1` builder and offline verifier with safe ZIP handling and `locust-kit verify`.
- Release campaign domain model, additive SQLite persistence, readiness/drift calculation, workspace screens, and `performance-campaign/v1` exports.
- Responsive verification and campaign UI states plus focused unit and integration coverage.

#### Completed in follow-up
- Added offline analyzer reproduction with MATCH, DRIFT, and UNREPRODUCIBLE results plus `locust-kit verify --reproduce`.
- Added transactional campaign draft replacement, run eligibility checks, and optimistic-concurrency conflict protection.
- Added real-I/O reproduction and campaign concurrency/finalization integration tests.

#### Quality-gate restoration
- Restored reusable performance quality-gate and headless performance CI workflows.
- Made UI and coverage gate invocation portable for source-layout and module execution.
