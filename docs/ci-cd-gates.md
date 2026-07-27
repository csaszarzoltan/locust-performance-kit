# CI/CD Performance Gates

A reusable GitHub Actions workflow that automates Locust-based performance
testing in CI/CD pipelines. It runs a load test, generates multi-format
reports, evaluates quality thresholds, and sends notifications — all as a
single reusable pipeline.

## Quick Start

```bash
# Run manually via gh CLI
gh workflow run perf-test.yml \
  -f locust-script=examples/api_load_test.py \
  -f target-host=http://staging.example.com \
  -f users=100 \
  -f run-time=5m
```

The pipeline runs four sequential jobs:

1. **load-test** — Executes the Locust script in headless mode, saves CSV
2. **generate-reports** — Produces HTML, JSON, Markdown, and JUnit XML reports
3. **quality-gate** — Evaluates metrics against configured thresholds
4. **notify** — Sends Slack/Teams notification with pass/fail result

## Pipeline Architecture

```
workflow_dispatch / workflow_call
         │
         ▼
    ┌─────────────┐
    │  load-test   │  locust -f <script> --headless --csv results
    └──────┬──────┘
           │ CSV artifacts
           ▼
    ┌──────────────────┐
    │ generate-reports  │  locust-report (HTML, JSON, Markdown, JUnit)
    └──────┬───────────┘
           │ report artifacts
           ▼
    ┌────────────────┐
    │  quality-gate   │  Evaluate p95, p99, error rate, RPS
    │                 │  Exit code 2 on failure
    └──────┬─────────┘
           │ gate-passed / metrics-json outputs
           ▼
    ┌──────────┐
    │  notify   │  Slack + Teams webhooks
    └──────────┘
```

## Usage

### From another workflow (reusable workflow)

```yaml
# .github/workflows/deploy-and-perf.yml
jobs:
  perf-gate:
    uses: your-org/your-repo/.github/workflows/perf-test.yml@main
    with:
      locust-script: examples/api_load_test.py
      target-host: https://staging.example.com
      users: 100
      run-time: 5m
      p95-threshold: 500
      p99-threshold: 1000
      error-rate-threshold: 0.01
      rps-threshold: 500
    secrets:
      SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
      TEAMS_WEBHOOK_URL: ${{ secrets.TEAMS_WEBHOOK_URL }}
```

### Consuming quality-gate outputs

```yaml
jobs:
  perf-gate:
    uses: ./.github/workflows/perf-test.yml
    with:
      target-host: https://staging.example.com
    secrets:
      SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}

  deploy-to-prod:
    needs: [perf-gate]
    if: needs.perf-gate.outputs.gate-passed == 'true'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Performance gate passed — deploying to production"
```

## Input Reference

| Input | Required | Default | Description |
|---|---|---|---|
| `locust-script` | No | `examples/api_load_test.py` | Path to the Locust test script |
| `target-host` | No | `http://localhost:8080` | Target host URL for load test |
| `users` | No | `50` | Number of concurrent users |
| `spawn-rate` | No | `5` | Users spawned per second |
| `run-time` | No | `2m` | Test duration |
| `p95-threshold` | No | `500` | p95 latency threshold (ms) |
| `p99-threshold` | No | `1000` | p99 latency threshold (ms) |
| `error-rate-threshold` | No | `0.01` | Maximum error rate (0.0–1.0) |
| `rps-threshold` | No | `0` | Minimum RPS (0 = disabled) |

## Output Reference

| Output | Type | Description |
|---|---|---|
| `gate-passed` | string | `"true"` or `"false"` |
| `p95-max` | string | Maximum p95 latency observed (ms) |
| `p99-max` | string | Maximum p99 latency observed (ms) |
| `error-rate` | string | Overall error rate |
| `metrics-json` | string | Full metrics as JSON blob |

## Quality Gate Thresholds

The quality-gate job evaluates four metrics:

| Metric | Sources from | Pass condition |
|---|---|---|
| **p95 latency** | `report.json -> p95_response_time` | ≤ `p95-threshold` |
| **p99 latency** | `report.json -> p99_response_time` | ≤ `p99-threshold` |
| **Error rate** | `report.json -> error_rate` | ≤ `error-rate-threshold` |
| **RPS** | `report.json -> total_rps` | ≥ `rps-threshold` (skipped when 0) |

When any threshold is breached, the job:
- Sets `gate-passed=false` in the step outputs
- Exits with code 2 (failure)
- Includes failure details in the step summary

## Notifications

Notifications are sent on every run (pass or fail). The `notify` job runs
with `if: always()` so failure notifications are always delivered.

### Slack

The workflow sends a formatted message to Slack when `SLACK_WEBHOOK_URL` is
supplied as a secret. The message includes the pass/fail status and target
host.

```yaml
secrets:
  SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Microsoft Teams

Similarly, `TEAMS_WEBHOOK_URL` sends an Adaptive Card to a Teams channel:

```yaml
secrets:
  TEAMS_WEBHOOK_URL: ${{ secrets.TEAMS_WEBHOOK_URL }}
```

Both notifications are optional — the workflow runs without them.

## Example: Python Threshold Check

For programmatic evaluation outside GitHub Actions, use the
`ThresholdChecker` from the core templates:

```python
from locust_templates.thresholds import ThresholdChecker

checker = ThresholdChecker(p95_threshold=500, p99_threshold=1000)
result = checker.check(p95=350, p99=820, error_rate=0.005)

print(f"Gate passed: {result.passed}")
if result.failures:
    for f in result.failures:
        print(f"  FAIL: {f}")
```

Output:

```
Gate passed: True
```

```python
# With a breach
result = checker.check(p95=650, p99=1200, error_rate=0.02)
print(f"Gate passed: {result.passed}")
for f in result.failures:
    print(f"  FAIL: {f}")
```

Output:

```
Gate passed: False
  FAIL: p95 latency 650.0ms exceeds threshold 500.0ms
  FAIL: p99 latency 1200.0ms exceeds threshold 1000.0ms
  FAIL: Error rate 2.00% exceeds threshold 1.00%
```

## Example: Using Thresholds in a CI Script

See `examples/gate_evaluation.py` for a complete runnable example that
simulates both a passing and a failing quality gate.
