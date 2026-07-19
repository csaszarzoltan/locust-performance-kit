# Live Dashboard & Threshold Alerts Guide

## Overview

The Locust Performance Kit provides a real-time live metrics dashboard
and configurable threshold alerts that work during a running load test.

**Features:**
- Live response-time and throughput charts (Chart.js, auto-refresh)
- Configurable threshold alerts (p95, p99, error rate, throughput)
- Failure hotspots in HTML/Markdown reports
- Integration with existing runner/config

## Live Dashboard

### Quick Start

```python
from locust_templates import LiveDashboard, MetricsCollector

dash = LiveDashboard(max_points=300)
collector = MetricsCollector()

# During the test, record snapshots periodically:
dash.record_from_collector(collector, active_users=100)

# Render the HTML dashboard:
html = dash.render()
# Or write to file:
dash.render_to_file("dashboard.html")
```

### TimeSeriesPoint

Each snapshot is a `TimeSeriesPoint` with:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | float | Unix timestamp |
| `avg_response_time` | float | Average response time (ms) |
| `p95_response_time` | float | 95th percentile response time (ms) |
| `throughput` | float | Requests per second |
| `error_rate` | float | Error rate (0.0–1.0) |
| `active_users` | int | Active simulated users |

### Manual Recording

```python
dash = LiveDashboard()

dash.record(
    avg_response_time=150.0,
    p95_response_time=250.0,
    throughput=100.0,
    error_rate=0.01,
    active_users=50,
)
```

### Rolling Window

The dashboard keeps a rolling window of the most recent `max_points`
(default 300). Older points are automatically discarded.

```python
dash = LiveDashboard(max_points=600)  # keep last 600 snapshots
```

### HTML Output

The rendered HTML is self-contained:
- Embedded Chart.js from CDN
- Time-series data as JSON
- Auto-refresh meta tag (default 5s)
- Summary cards (avg RT, p95, throughput, error rate, users)
- Response time chart (avg + p95)
- Throughput chart
- Alerts panel (when alerts are passed)

## Threshold Alerts

### AlertRule

An `AlertRule` defines a threshold breach condition:

```python
from locust_templates import AlertRule

rule = AlertRule(
    name="p95-high",
    metric="p95",
    operator=">",      # >, >=, <, <=, ==
    threshold=500.0,
    severity="warning",  # "warning" (default) or "critical"
)
```

### AlertEngine

The `AlertEngine` evaluates rules against live metrics:

```python
from locust_templates import AlertEngine, AlertRule

rules = [
    AlertRule("p95-high", "p95", ">", 500.0),
    AlertRule("err-high", "error_rate", ">", 0.01),
    AlertRule("rps-low", "throughput", "<", 100.0),
]

engine = AlertEngine(rules=rules, dedup=True)

# Check metrics during the test:
alerts = engine.check({
    "p95": 600.0,
    "error_rate": 0.05,
    "throughput": 150.0,
})
# Returns list of newly fired Alerts

# Get all fired alerts:
all_alerts = engine.get_alerts()
```

### Dedup Mode

With `dedup=True`, repeated breaches of the same rule are suppressed
while the metric remains in breach. A new alert fires only after the
metric returns below threshold and then breaches again.

### From Config

```python
config = [
    {"name": "p95-high", "metric": "p95", "operator": ">", "threshold": 500.0},
    {"name": "err-high", "metric": "error_rate", "operator": ">", "threshold": 0.01},
]
engine = AlertEngine.from_config(config)
```

### Environment Variable Configuration

```bash
# Enable/disable alerts
export LOCUST_ALERTS_ENABLED=true

# Alert rules as JSON array
export LOCUST_ALERT_RULES='[
  {"name": "p95-high", "metric": "p95", "operator": ">", "threshold": 500.0},
  {"name": "err-high", "metric": "error_rate", "operator": ">", "threshold": 0.01}
]'
```

## Dashboard + Alerts Integration

```python
from locust_templates import (
    LiveDashboard, AlertEngine, AlertRule, MetricsCollector
)

dash = LiveDashboard(max_points=300)
collector = MetricsCollector()

rules = [
    AlertRule("p95-high", "p95", ">", 500.0, severity="critical"),
    AlertRule("err-high", "error_rate", ">", 0.01),
]
engine = AlertEngine(rules=rules, dedup=True)

# During the test loop:
dash.record_from_collector(collector, active_users=100)
latest = dash.get_latest()

metrics = {
    "p95": latest.p95_response_time,
    "throughput": latest.throughput,
    "error_rate": latest.error_rate,
}
alerts = engine.check(metrics)

# Render dashboard with alerts:
dash.render_to_file("dashboard.html", alerts=engine.get_alerts())
```

## Failure Hotspots in Reports

The HTML and Markdown exporters now include a "Failure Hotspots" section
that shows endpoints sorted by failure rate (descending), so you can
quickly identify the worst offenders for triage.

```python
from locust_templates.report_data import ReportData

data = ReportData.from_csv("results")
hotspots = data.get_failure_hotspots()
# [{"name": "/api/orders", "failure_count": 10, "request_count": 500, "failure_rate": 0.02}, ...]
```

This section appears automatically in HTML and Markdown reports when
failures exist. Endpoints with 0 failures are excluded.

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `LOCUST_DASHBOARD_ENABLED` | `true` | Enable/disable dashboard |
| `LOCUST_DASHBOARD_REFRESH` | `5` | Auto-refresh interval (seconds) |
| `LOCUST_DASHBOARD_MAX_POINTS` | `300` | Max time-series points to retain |
| `LOCUST_DASHBOARD_OUTPUT` | (empty) | Dashboard output file path |
| `LOCUST_ALERTS_ENABLED` | `true` | Enable/disable threshold alerts |
| `LOCUST_ALERT_RULES` | (empty) | JSON array of alert rule dicts |

## CI/CD Integration

```python
from locust_templates.runner import build_dashboard_command

cmd = build_dashboard_command(
    csv_prefix="results",
    output="dashboard.html",
    fmt="html",
    refresh=10,
    max_points=600,
)
# "locust-report results --format html --output dashboard.html
#  --dashboard --refresh 10 --max-points 600"
```
