# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
