# Locust Performance Kit

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 398](https://img.shields.io/badge/tests-398%20passed-brightgreen.svg)]()
[![Version: 1.2.0](https://img.shields.io/badge/version-1.2.0-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Production-ready Locust load testing templates, CI/CD pipelines, and monitoring integrations for enterprise-grade performance testing.

Built by a performance engineer with 6+ years at a major Swiss bank. These templates have been battle-tested on real banking applications handling millions of transactions.

## What's Inside

### Core Templates
- `src/locust_templates/api_load.py` — REST API load testing with custom metrics
- `src/locust_templates/stress.py` — Stress testing with ramp-up patterns
- `src/locust_templates/spike.py` — Spike testing for sudden load bursts
- `src/locust_templates/soak.py` — Endurance testing for stability
- `src/locust_templates/web_ui.py` — Browser-based user journey testing

### Utility Modules
- `src/locust_templates/metrics.py` — Thread-safe metrics collection with percentile calculations
- `src/locust_templates/thresholds.py` — Performance threshold validation (p95, p99, error rate)
- `src/locust_templates/shapes.py` — Custom Locust shapes (StepLoadShape, SpikeLoadShape)
- `src/locust_templates/config.py` — Environment-based configuration with .env support
- `src/locust_templates/runner.py` — CLI command builder for CI/CD pipelines

### Request Correlation (v1.2.0+)
- `src/locust_templates/correlator.py` — Request correlation and cascade failure detection
  - `RequestCorrelator` tracks per-user request chains via Locust `events.request`
  - Cascade detection: failed request → downstream failures from same user within time window
  - CSV/JSON export of correlated events and failure chains
  - See [Request Correlation Guide](docs/request-correlation.md) for details

### Report Export (v1.2.0+)

Generate performance reports in **four formats** from Locust CSV output —
HTML, JSON, Markdown, and JUnit XML — with a unified CLI and Python API.

**CLI:**

```bash
# Default HTML report
locust-report results --output report.html

# JSON for CI pipelines, Markdown for PR comments, JUnit XML for test runners
locust-report results --format json --output report.json
locust-report results --format markdown --output report.md
locust-report results --format junit --output junit-results.xml

# With p95/p99 thresholds (exit code 2 on violation → CI gate)
locust-report results --p95-threshold 500 --p99-threshold 1000 --output report.html
```

**Python API:**

```python
from locust_templates.runner import generate_report

# Any format via a single function call
generate_report("results", "report.html", fmt="html")
generate_report("results", "report.json", fmt="json", thresholds={"p95": 500})
generate_report("results", "report.md", fmt="markdown")
generate_report("results", "junit.xml", fmt="junit")
```

**Strategy-pattern exporters** (for advanced use):

```python
from locust_templates.exporters import HTMLExporter, JSONExporter, MarkdownExporter, JUnitXMLExporter
from locust_templates.report_data import ReportData

data = ReportData.from_csv("results", thresholds={"p95": 500, "p99": 1000})
HTMLExporter().export(data, "report.html")
JSONExporter().export(data, "report.json")
```

All four formats are cross-platform (paths resolved via `pathlib.Path`),
self-contained, and work in CI artifacts, email attachments, and PR comments.

See [Report Export Guide](docs/report-export.md) for the full CLI reference,
format comparison table, and CI/CD integration examples.

### Reporting & Analysis (v1.1.0+)
- `src/locust_templates/report_generator.py` — HTML report generator from Locust CSV output
  - Self-contained HTML with CSS-only bar charts (no JS dependencies)
  - Summary stats table, per-endpoint p95/p99 metrics, threshold pass/fail indicators
  - Optional correlation section with cascade failure summary and top failure chains
  - Backward-compatible shims: `to_json()`, `to_markdown()`, `to_junit()` delegate to exporters
- `src/locust_templates/baseline.py` — Performance regression baseline comparison
  - Save and compare baselines to detect p95 degradations > 10%
  - `RegressionResult` with regressions, improvements, and human-readable summary
  - Optional cascade rate storage in baseline JSON
- `src/locust_templates/notifications.py` — Slack/Teams webhook notifications
  - `SlackNotifier` posts formatted message blocks to Slack webhooks
  - `TeamsNotifier` posts Adaptive Cards to Teams webhooks

### CI/CD Integration
- `.github/workflows/performance-ci.yml` — GitHub Actions pipeline for automated performance gates
- Pre-configured thresholds and pass/fail criteria
- Automatic reporting to Slack/Teams

## Quick Start

```bash
git clone https://github.com/csaszarzoltan/locust-performance-kit.git
cd locust-performance-kit
pip install -r requirements.txt

# Run a basic load test with web UI
locust -f examples/api_load_test.py --users 100 --spawn-rate 10 --run-time 5m
# Open http://localhost:8089
```

### Headless Mode (CI/CD)

```bash
locust -f examples/api_load_test.py \
    --headless \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --host https://api.example.com \
    --csv results
```

## Configuration

Configuration is managed via environment variables with sensible defaults:

```bash
export LOCUST_HOST=https://api.example.com
export LOCUST_USERS=100
export LOCUST_SPAWN_RATE=10
export LOCUST_RUN_TIME=5m

# Performance thresholds
export LOCUST_P95_THRESHOLD=500
export LOCUST_P99_THRESHOLD=1000
export LOCUST_ERROR_RATE_THRESHOLD=0.01

# Notifications (optional)
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
export TEAMS_WEBHOOK_URL=https://outlook.office.com/...
```

Or use a `.env` file:

```bash
LOCUST_HOST=https://api.example.com
LOCUST_USERS=100
LOCUST_AUTH_TOKEN=your_token_here
```

## Authentication (v1.2.0+)

The kit provides a pluggable authentication system so load tests can obtain
credentials from different sources without modifying test code.

### Available Providers

| Provider | Registry name | Description |
|---|---|---|
| `StaticTokenAuthenticator` | `static` | Fixed token from constructor or `LOCUST_AUTH_TOKEN` env var |
| `EnvTokenAuthenticator` | `env` | Token read from a configurable environment variable |
| `OAuth2ClientCredentialsAuthenticator` | `oauth2-client-credentials` | OAuth2 client_credentials flow with token caching and thread-safe refresh |

### Configuration via Environment Variables

```bash
# Select the provider (static | env | oauth2-client-credentials)
export LOCUST_AUTH_PROVIDER=oauth2-client-credentials

# Static / Env provider
export LOCUST_AUTH_TOKEN=your_bearer_token

# OAuth2 client_credentials provider
export LOCUST_AUTH_CLIENT_ID=my-client-id
export LOCUST_AUTH_CLIENT_SECRET=my-client-secret
export LOCUST_AUTH_TOKEN_URL=https://auth.example.com/oauth/token
export LOCUST_AUTH_SCOPES="read write"
```

### Usage in Locust Scripts

`APIUser` integrates auth automatically — set the provider name and any
constructor kwargs as class attributes:

```python
from locust_templates.api_load import APIUser
from locust import between, task

class MyAPIUser(APIUser):
    wait_time = between(1, 3)
    auth_provider = "oauth2-client-credentials"
    auth_kwargs = {
        "token_url": "https://auth.example.com/oauth/token",
        "client_id": "my-client-id",
        "client_secret": "my-client-secret",
        "scope": "read write",
    }

    @task
    def get_data(self):
        self.client.get("/api/v1/data")
```

### Registering a Custom Provider

```python
from locust_templates.auth import Authenticator, default_registry, create_authenticator

class MyAuthenticator(Authenticator):
    def authenticate(self) -> dict[str, str]:
        return {"X-API-Key": "my-secret-key"}

default_registry.register("my-custom", MyAuthenticator)
auth = create_authenticator("my-custom")
headers = auth.get_headers()  # {"X-API-Key": "my-secret-key"}
```

See [Authentication Providers Guide](docs/auth-providers.md) for the full
architecture, custom provider walkthrough, and migration guide.

## Using Custom Shapes

```python
from locust_templates.shapes import StepLoadShape, SpikeLoadShape

# Step-load: increase users by 10 every 30 seconds up to 100
shape = StepLoadShape(step_duration=30, step_users=10, max_users=100)

# Spike: alternate between 10 baseline and 100 spike users
shape = SpikeLoadShape(
    baseline_users=10,
    spike_users=100,
    baseline_duration=30,
    spike_duration=5,
    recovery_duration=30,
)
```

## Programmatic Command Building

```python
from locust_templates.runner import build_locust_command

cmd = build_locust_command(
    script="examples/api_load_test.py",
    headless=True,
    users=100,
    spawn_rate=10,
    host="https://api.example.com",
    run_time="5m",
)
# Returns: "locust -f examples/api_load_test.py --headless --users 100 --spawn-rate 10 ..."
```

## HTML Report Generation (v1.1.0+)

Generate self-contained HTML reports from Locust CSV output:

```python
from locust_templates.report_generator import HTMLReportGenerator

# Parse Locust CSV output and generate HTML report
gen = HTMLReportGenerator.from_csv("results", thresholds={"p95": 500, "p99": 1000})
gen.generate("report.html")
# report.html is self-contained — no external CSS/JS dependencies

# Also export to JSON, Markdown, and JUnit XML (v1.2.0+)
gen.to_json("report.json")
gen.to_markdown("report.md")
gen.to_junit("junit.xml")
```

**CLI (v1.2.0+):**

```bash
locust-report results --format html --output report.html --p95-threshold 500
```

See [Report Generation Guide](docs/report-generation.md) and
[Report Export Guide](docs/report-export.md) for details.

## Performance Regression Baselines (v1.1.0+)

Save baselines and compare new runs to detect regressions:

```python
from locust_templates.baseline import PerformanceBaseline

baseline = PerformanceBaseline()

# Save current run as a named baseline
baseline.save_baseline("results", name="v1.0")

# Compare a new run against the baseline
result = baseline.compare("results_new", baseline_name="v1.0")
if result.regressions:
    print(result.summary)
    for r in result.regressions:
        print(f"  {r.endpoint} {r.metric}: {r.degradation_pct}% degradation")
```

See [Baseline Comparison Guide](docs/baseline-comparison.md) for details.

## Notifications (v1.1.0+)

Send test results to Slack or Teams:

```python
from locust_templates.notifications import SlackNotifier, TeamsNotifier

# Slack
slack = SlackNotifier()  # reads SLACK_WEBHOOK_URL from env
slack.send("Performance test completed", {"p95": "350ms", "status": "PASS"})

# Teams
teams = TeamsNotifier()  # reads TEAMS_WEBHOOK_URL from env
teams.send("Performance test completed", {"p95": "350ms", "status": "PASS"})
```

See [Notifications Guide](docs/notifications.md) for details.

## Testing

```bash
# All tests (no real API calls needed)
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Visual regression tests
pytest tests/visual/ -v

# Lint
ruff check src/ tests/
```

All 398 tests pass (134 pre-existing + 38 for v1.1.0 + 116 for v1.2.0 + 110 for cross-platform report export).

## Tech Stack

- **Load Testing:** Locust, k6, JMeter (migrations)
- **CI/CD:** GitHub Actions, GitLab CI
- **APM:** AppDynamics, Dynatrace, CA Wily, Prometheus + Grafana
- **Notifications:** Slack, Microsoft Teams (webhooks)
- **Languages:** Python, Bash, YAML
- **Cloud:** AWS, Azure, GCP load testing patterns

## Performance Thresholds (Typical)

```yaml
# Example thresholds for banking applications
p95_latency: 500ms
p99_latency: 1000ms
error_rate: 0.1%
throughput: 1000 RPS
```

## Use Cases

- **Regression testing** — Verify performance after deployments
- **Capacity planning** — Find breaking points before production
- **SLA validation** — Ensure contractual performance metrics
- **Bottleneck detection** — Identify slow endpoints early
- **Baseline establishment** — Create performance benchmarks
- **CI/CD gates** — Block deployments on performance regressions
- **Automated reporting** — Generate HTML reports and notify teams

## Project Structure

```
src/locust_templates/
    __init__.py            — package exports
    api_load.py            — REST API load testing base
    auth.py                — pluggable authentication providers (v1.2.0)
    baseline.py            — regression baseline comparison (v1.1.0)
    cli.py                 — locust-report CLI entry point (v1.2.0)
    config.py              — environment-based configuration
    correlator.py          — request correlation & cascade detection (v1.2.0)
    exporters.py           — HTML/JSON/Markdown/JUnit exporters (v1.2.0)
    metrics.py             — thread-safe metrics collection
    notifications.py       — Slack/Teams webhook notifications (v1.1.0)
    report_data.py         — ReportData model + from_csv (v1.2.0)
    report_generator.py    — HTML report from CSV (v1.1.0)
    runner.py              — CLI command builder + generate_report
    shapes.py              — custom load shapes
    soak.py                — endurance testing
    spike.py               — spike testing
    stress.py              — stress testing
    thresholds.py          — threshold validation
    web_ui.py              — browser user journeys
tests/
    unit/                  — unit tests (mocked)
    integration/           — integration tests
    visual/                — visual regression tests
    fixtures/              — test fixture CSVs
docs/                      — documentation
examples/                  — runnable example scripts
.github/workflows/         — CI/CD pipeline
```

## Documentation

- [Authentication Providers Guide](docs/auth-providers.md)
- [Getting Started Guide](docs/getting-started.md)
- [Writing Custom Locust Scripts](docs/custom-scripts.md)
- [Report Generation Guide](docs/report-generation.md)
- [Report Export Guide](docs/report-export.md)
- [Baseline Comparison Guide](docs/baseline-comparison.md)
- [Request Correlation Guide](docs/request-correlation.md)
- [Notifications Guide](docs/notifications.md)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Contributing

Contributions are welcome! Please:

1. Fork the repo and create a feature branch
2. Write tests for new features (TDD)
3. Ensure `ruff check src/ tests/` passes
4. Ensure `pytest tests/` passes
5. Submit a pull request

## License

MIT License — feel free to use these templates in your projects.

## Author

**Zoltan Csaszar**
- GitHub: [@csaszarzoltan](https://github.com/csaszarzoltan)
- Upwork: [Profile](https://www.upwork.com/freelancers/~010b8149572fd46b3d)
- Location: Zurich, Switzerland

---

Star this repo if you find it useful! It helps others discover it.
