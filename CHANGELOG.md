# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **HTML report correlation section** (`report_generator.py`):
  - Optional `correlation_summary` parameter on `HTMLReportGenerator.__init__`
  - Renders cascade failure summary cards and top failure chains table
- **Baseline cascade rate** (`baseline.py`):
  - Optional `correlation_summary` parameter on `save_baseline()`
  - Stores `cascade_rate`, `cascade_failures`, `root_failures` in baseline JSON

### Changed

- Version bumped from 1.1.0 to 1.2.0
- Updated `src/locust_templates/__init__.py` to export `RequestCorrelator` and data classes

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
