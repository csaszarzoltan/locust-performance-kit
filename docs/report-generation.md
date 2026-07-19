# Report Generation Guide

Generate self-contained HTML reports from Locust CSV output. No external CSS/JS dependencies — works in CI artifacts, email attachments, and any browser.

## Overview

The `HTMLReportGenerator` class parses Locust's `--csv` output files and produces a single HTML file with:

- Summary cards: total requests, total failures, endpoint count, overall RPS
- Per-endpoint metrics table: requests, failures, avg, p50, p95, p99, RPS
- CSS-only bar charts for p95 and p99 per endpoint
- Threshold pass/fail indicators (green/red)
- Failures table (if any failures exist)

## Quick Start

### Step 1: Run Locust with CSV output

```bash
locust -f examples/api_load_test.py \
    --headless \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --host https://api.example.com \
    --csv results
```

This produces `results_stats.csv` and `results_failures.csv`.

### Step 2: Generate the HTML report

```python
from locust_templates.report_generator import HTMLReportGenerator

gen = HTMLReportGenerator.from_csv("results")
gen.generate("report.html")
```

Open `report.html` in any browser — no internet connection needed.

### Step 3: With thresholds

```python
from locust_templates.report_generator import HTMLReportGenerator

gen = HTMLReportGenerator.from_csv(
    "results",
    thresholds={"p95": 500, "p99": 1000},
)
gen.generate("report.html")
# Report now includes a threshold results section with PASS/FAIL indicators
```

## API Reference

### `HTMLReportGenerator`

#### Constructor

```python
HTMLReportGenerator(
    stats: list[dict],
    failures: list[dict] | None = None,
    thresholds: dict[str, float] | None = None,
)
```

- **stats**: List of stat dicts (one per endpoint, from CSV parsing)
- **failures**: List of failure dicts (from failures CSV)
- **thresholds**: Optional dict with `p95` and `p99` threshold values in milliseconds

#### `from_csv(csv_prefix, *, thresholds=None) -> HTMLReportGenerator` (classmethod)

Create a generator from Locust CSV files.

- **csv_prefix**: The prefix used with Locust's `--csv` flag (e.g. `"results"` for `results_stats.csv`)
- **thresholds**: Optional threshold dict

#### `generate(output_path) -> str`

Generate the HTML report and write it to `output_path`. Returns the resolved path.

## Integration with CI/CD

### GitHub Actions

```yaml
- name: Run load test
  run: |
    locust -f examples/api_load_test.py \
      --headless --users 100 --spawn-rate 10 --run-time 2m \
      --host ${{ env.TARGET_HOST }} --csv results

- name: Generate report
  run: |
    python -c "
    from locust_templates.report_generator import HTMLReportGenerator
    gen = HTMLReportGenerator.from_csv('results', thresholds={'p95': 500, 'p99': 1000})
    gen.generate('report.html')
    "

- name: Upload report artifact
  uses: actions/upload-artifact@v4
  with:
    name: performance-report
    path: report.html
```

### With Notifications

```python
from locust_templates.report_generator import HTMLReportGenerator
from locust_templates.notifications import SlackNotifier

# Generate report
gen = HTMLReportGenerator.from_csv("results", thresholds={"p95": 500, "p99": 1000})
report_path = gen.generate("report.html")

# Notify team
summary = gen._compute_summary()
slack = SlackNotifier()
slack.send(
    f"Performance test completed: {summary['total_requests']} requests",
    {
        "p95_threshold": "500ms",
        "total_failures": summary["total_failures"],
        "report": report_path,
    },
)
```

## Report Sections

### 1. Summary Cards

Top-level metrics at a glance:

- **Total Requests** — sum of all endpoint request counts
- **Total Failures** — sum of all endpoint failure counts
- **Endpoints** — number of unique endpoints tested
- **Overall RPS** — sum of per-endpoint requests per second

### 2. Threshold Results

If thresholds are provided, shows PASS/FAIL per endpoint:

| Endpoint | Metrics | Status |
|----------|---------|--------|
| GET /api/users | p95=350ms / p99=420ms | PASS |
| POST /api/orders | p95=620ms / p99=850ms | FAIL |

### 3. Per-Endpoint Metrics

Detailed table with one row per endpoint:

| Type | Name | Requests | Failures | Avg (ms) | p50 | p95 | p99 | RPS |
|------|------|----------|----------|----------|-----|-----|-----|-----|

### 4. p95 / p99 Bar Charts

CSS-only horizontal bar charts comparing p95 and p99 across endpoints. Red bars for p95, orange for p99. No JavaScript required.

### 5. Failures Table

If failures exist, shows method, endpoint name, error type, and error message.

## Tips

- Reports are self-contained — safe to email or attach in Jira tickets
- Typical report size is < 100KB for a 5-minute test with 10 endpoints
- The `Aggregated` row from Locust CSV is excluded from per-endpoint tables
- All user-provided content is HTML-escaped via Python's `html` module
