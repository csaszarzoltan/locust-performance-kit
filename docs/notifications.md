# Notifications Guide

Send performance test results to Slack or Microsoft Teams via incoming webhooks.

## Overview

The notifications module provides:

- `Notifier` ABC with a `send()` interface
- `SlackNotifier` — posts formatted message blocks to Slack webhooks
- `TeamsNotifier` — posts Adaptive Cards to Teams webhooks
- `ConfigurationError` — raised when webhook URL is missing
- `NotificationError` — raised when the HTTP POST fails

## Setup

### Slack

1. Create a Slack app at https://api.slack.com/apps
2. Enable incoming webhooks and select a channel
3. Copy the webhook URL
4. Set environment variable:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T.../B.../..."
```

### Microsoft Teams

1. In Teams, go to the channel → Connectors → Incoming Webhook
2. Configure and copy the webhook URL
3. Set environment variable:

```bash
export TEAMS_WEBHOOK_URL="https://outlook.office.com/webhook/..."
```

## Quick Start

```python
from locust_templates.notifications import SlackNotifier, TeamsNotifier

results = {
    "p95_latency": "350ms",
    "p99_latency": "420ms",
    "error_rate": "0.1%",
    "total_requests": "12000",
    "status": "PASS",
}

# Slack
slack = SlackNotifier()  # reads SLACK_WEBHOOK_URL from env
slack.send("Performance test completed", results)

# Teams
teams = TeamsNotifier()  # reads TEAMS_WEBHOOK_URL from env
teams.send("Performance test completed", results)
```

## API Reference

### `Notifier` (ABC)

Abstract base class for notification providers.

#### `send(message, results) -> bool`

- **message**: Human-readable summary message
- **results**: Dict with test results (rendered as key-value pairs)
- **Returns**: `True` if sent successfully
- **Raises**: `ConfigurationError` if webhook URL is missing, `NotificationError` if HTTP fails

### `SlackNotifier`

```python
SlackNotifier(webhook_url: str | None = None, *, timeout: int = 10)
```

- **webhook_url**: Slack incoming webhook URL. If None, reads from `SLACK_WEBHOOK_URL` env var.
- **timeout**: HTTP request timeout in seconds.

Posts a Slack message with two sections:
1. The summary message (mrkdwn format)
2. The results dict as bullet points

### `TeamsNotifier`

```python
TeamsNotifier(webhook_url: str | None = None, *, timeout: int = 10)
```

- **webhook_url**: Teams incoming webhook URL. If None, reads from `TEAMS_WEBHOOK_URL` env var.
- **timeout**: HTTP request timeout in seconds.

Posts an Adaptive Card with:
1. A TextBlock with the summary message (Medium, Bold)
2. A FactSet with the results dict as key-value pairs

### Exceptions

- `ConfigurationError` — webhook URL not configured (missing env var and no constructor arg)
- `NotificationError` — HTTP POST failed (network error, non-2xx response)

## Error Handling

```python
from locust_templates.notifications import (
    SlackNotifier,
    ConfigurationError,
    NotificationError,
)

try:
    slack = SlackNotifier()
    slack.send("Test done", {"status": "PASS"})
except ConfigurationError as e:
    print(f"Not configured: {e}")
    # Set SLACK_WEBHOOK_URL env var
except NotificationError as e:
    print(f"Failed to send: {e}")
    # Check webhook URL, network connectivity
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run load test
  run: |
    locust -f examples/api_load_test.py \
      --headless --users 100 --spawn-rate 10 --run-time 2m \
      --host ${{ env.TARGET_HOST }} --csv results

- name: Notify Slack
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
  run: |
    python -c "
    from locust_templates.notifications import SlackNotifier
    
    slack = SlackNotifier()
    slack.send(
        'Performance test completed for ${{ github.ref }}',
        {
            'repository': '${{ github.repository }}',
            'commit': '${{ github.sha }}',
            'status': 'see attached report',
        },
    )
    "
```

### With Report and Thresholds

```python
from locust_templates.report_generator import HTMLReportGenerator
from locust_templates.baseline import PerformanceBaseline
from locust_templates.notifications import SlackNotifier

# Generate report
gen = HTMLReportGenerator.from_csv("results", thresholds={"p95": 500, "p99": 1000})
report_path = gen.generate("report.html")
summary = gen._compute_summary()

# Check for regressions
baseline = PerformanceBaseline()
try:
    reg_result = baseline.compare("results", "production")
    status = "FAIL" if reg_result.regressions else "PASS"
except Exception:
    status = "UNKNOWN"

# Notify
slack = SlackNotifier()
slack.send(
    f"Performance test {status}",
    {
        "total_requests": summary["total_requests"],
        "total_failures": summary["total_failures"],
        "overall_rps": f"{summary['total_rps']:.1f}",
        "status": status,
        "report": report_path,
    },
)
```

## Tips

- Store webhook URLs as GitHub Secrets, not in code
- Use different webhooks for different environments (staging vs production)
- Include a link to the HTML report in the results dict
- Send notifications only on failures to avoid alert fatigue
- Set a reasonable timeout (10s default) — don't let notifications block your pipeline
