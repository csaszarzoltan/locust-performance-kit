# Report Export Guide

Export Locust performance test results in **four formats**: HTML, JSON, Markdown,
and JUnit XML — from a single CLI command or Python API call.

## Overview

The report export system (v1.2.0+) decouples CSV parsing from report rendering
using a Strategy pattern:

```
Locust CSV → ReportData (model) → Exporter (Strategy) → Output file
```

- **`ReportData`** (`report_data.py`) — Dataclass model parsed from Locust's
  `--csv` output. Holds per-endpoint stats, failures, exceptions, summary
  metrics, and optional threshold config.
- **Exporters** (`exporters.py`) — `HTMLExporter`, `JSONExporter`,
  `MarkdownExporter`, `JUnitXMLExporter`. Each implements `render(data) -> str`
  and `export(data, path) -> str`.
- **CLI** (`cli.py`) — `locust-report` command-line tool wrapping the above.
- **`runner.generate_report()`** — Programmatic helper for CI/CD scripts.

## Quick Start

### 1. Run Locust with CSV output

```bash
locust -f examples/api_load_test.py \
    --headless --users 100 --spawn-rate 10 --run-time 5m \
    --host https://api.example.com --csv results
```

This produces `results_stats.csv`, `results_failures.csv`, and
`results_exceptions.csv`.

### 2. Generate a report

**CLI:**

```bash
locust-report results --output report.html
```

**Python:**

```python
from locust_templates.runner import generate_report

generate_report("results", "report.html", fmt="html")
```

## CLI Reference

```
locust-report <csv_prefix> [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|---|---|---|
| `csv_prefix` | Yes | Prefix path for Locust CSV files (e.g. `results` for `results_stats.csv`) |

### Options

| Option | Default | Description |
|---|---|---|
| `--format` | `html` | Output format: `html`, `json`, `markdown`, `junit` |
| `--output PATH` | stdout | Output file path. Use `-` for stdout. Default: stdout for json/markdown/junit |
| `--p95-threshold MS` | None | p95 response time threshold in ms (exceed → FAIL) |
| `--p99-threshold MS` | None | p99 response time threshold in ms (exceed → FAIL) |
| `--version` | — | Print version and exit |

### Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success — report generated, no threshold violations |
| 1 | Error — missing CSV file, invalid format, or parse error |
| 2 | Threshold violation — at least one endpoint exceeded p95/p99 threshold |

### Examples

```bash
# HTML report to file (default format)
locust-report results --output report.html

# JSON to stdout (pipe to jq or redirect)
locust-report results --format json > report.json

# Markdown for PR comments
locust-report results --format markdown --output report.md

# JUnit XML for CI test runners (Jenkins, GitLab CI)
locust-report results --format junit --output junit-results.xml

# With thresholds — exit code 2 if any endpoint exceeds
locust-report results \
    --format html \
    --output report.html \
    --p95-threshold 500 \
    --p99-threshold 1000

# Version check
locust-report --version
# locust-report 1.2.0
```

## Python API Reference

### `ReportData.from_csv(csv_prefix, *, thresholds=None) -> ReportData`

Parse Locust CSV files into a `ReportData` model.

```python
from locust_templates.report_data import ReportData

data = ReportData.from_csv("results")
data = ReportData.from_csv("results", thresholds={"p95": 500, "p99": 1000})
```

**Parameters:**
- `csv_prefix` (`str | Path`): Prefix path. `{prefix}_stats.csv` is required;
  `{prefix}_failures.csv` and `{prefix}_exceptions.csv` are optional.
- `thresholds` (`dict[str, float] | None`): Optional dict with keys `"p95"`
  and/or `"p99"` (values in milliseconds).

**Raises:**
- `FileNotFoundError`: If `{prefix}_stats.csv` does not exist.
- `ValueError`: If `thresholds` contains invalid keys (only `"p95"`, `"p99"`
  are valid).

### `runner.generate_report(csv_prefix, output_path, fmt, thresholds) -> str`

High-level helper — parse CSV, render, and write to file in one call.

```python
from locust_templates.runner import generate_report

path = generate_report("results", "report.html", fmt="html")
path = generate_report("results", "report.json", fmt="json",
                       thresholds={"p95": 500})
```

**Parameters:**
- `csv_prefix` (`str | Path`): Prefix for Locust CSV files.
- `output_path` (`str | Path`): Where to write the report.
- `fmt` (`str`): `html`, `json`, `markdown`, or `junit` (default: `html`).
- `thresholds` (`dict[str, float] | None`): Optional p95/p99 thresholds.

**Returns:** Absolute path of the generated report file (str).

### Exporter Classes (Strategy Pattern)

For advanced use cases where you need fine-grained control:

```python
from locust_templates.exporters import (
    HTMLExporter, JSONExporter, MarkdownExporter, JUnitXMLExporter,
    ReportExporter,
)
from locust_templates.report_data import ReportData

data = ReportData.from_csv("results", thresholds={"p95": 500, "p99": 1000})

# Each exporter has:
#   render(data: ReportData) -> str   — produce content string
#   export(data: ReportData, path) -> str  — render + write to file

HTMLExporter().export(data, "report.html")     # self-contained HTML
JSONExporter().export(data, "report.json")     # structured JSON
MarkdownExporter().export(data, "report.md")   # GitHub-flavored Markdown
JUnitXMLExporter().export(data, "junit.xml")   # JUnit XML for CI

# Or render to string without writing:
content = JSONExporter().render(data)
print(content)
```

**`ReportExporter` (ABC)** — Abstract base class:
- `render(data: ReportData) -> str` (abstract) — format-specific rendering.
- `export(data: ReportData, output_path: str | Path) -> str` — renders and
  writes to disk. Creates parent directories if needed. Returns absolute path.

### Backward Compatibility: `HTMLReportGenerator`

The v1.1.0 `HTMLReportGenerator` class remains fully supported with
backward-compatible shims that delegate to the new exporters:

```python
from locust_templates.report_generator import HTMLReportGenerator

gen = HTMLReportGenerator.from_csv("results", thresholds={"p95": 500})
gen.generate("report.html")     # HTML (v1.1.0 API)
gen.to_json("report.json")      # JSON (v1.2.0 shim → JSONExporter)
gen.to_markdown("report.md")    # Markdown (v1.2.0 shim → MarkdownExporter)
gen.to_junit("junit.xml")       # JUnit XML (v1.2.0 shim → JUnitXMLExporter)
```

## Format Comparison

| Feature | HTML | JSON | Markdown | JUnit XML |
|---|---|---|---|---|
| Human-readable report | Yes (styled) | No | Yes (plain text) | No |
| Machine-parseable | No | Yes | Limited | Yes |
| CI artifact (browser viewable) | Best | Good (raw) | Good (rendered) | No |
| PR/MR comment | No | No | Best | No |
| CI test runner integration | No | No | No | Best (Jenkins, GitLab CI) |
| Threshold pass/fail display | Visual (green/red) | `threshold_status` field | Emoji table | `<failure>` elements |
| Self-contained (no deps) | Yes | Yes | Yes | Yes |
| Typical use case | Email, Jira, artifact | API, dashboards, archival | GitHub PR comments | CI pipeline gates |

## Cross-Platform Path Handling

All file operations use `pathlib.Path` for cross-platform compatibility:

- **Windows**: `locust-report C:\tests\results --output C:\reports\report.html`
- **Linux/macOS**: `locust-report /home/user/results --output ./report.html`
- **Relative paths**: Resolved against the current working directory
- **Parent directories**: Created automatically if they don't exist
  (`output.parent.mkdir(parents=True, exist_ok=True)`)
- **Path separators**: `pathlib.Path` normalizes `/` and `\` automatically

```python
# Works identically on all platforms
from locust_templates.runner import generate_report

generate_report("results", "reports/2026-07/report.html", fmt="html")
# Creates reports/2026-07/ directory if needed
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Performance Test

on: [push, pull_request]

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run load test
        run: |
          locust -f examples/api_load_test.py \
            --headless --users 100 --spawn-rate 10 --run-time 2m \
            --host ${{ vars.TARGET_HOST }} --csv results

      - name: Generate HTML report
        run: |
          locust-report results \
            --format html --output report.html \
            --p95-threshold 500 --p99-threshold 1000

      - name: Generate JUnit XML for test gate
        run: |
          locust-report results --format junit --output junit-results.xml

      - name: Publish JUnit results
        if: always()
        uses: dorny/test-reporter@v1
        with:
          name: Performance Test Results
          path: junit-results.xml
          reporter: java-junit

      - name: Upload HTML report artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: performance-report
          path: report.html

      - name: Post Markdown summary to PR
        if: github.event_name == 'pull_request'
        run: |
          locust-report results --format markdown > performance-summary.md
          gh pr comment ${{ github.event.number }} --body-file performance-summary.md
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    stages {
        stage('Load Test') {
            steps {
                sh '''
                    locust -f examples/api_load_test.py \
                      --headless --users 100 --spawn-rate 10 \
                      --run-time 5m --host https://api.example.com \
                      --csv results
                '''
            }
        }
        stage('Generate Reports') {
            steps {
                sh 'locust-report results --format html --output report.html'
                sh 'locust-report results --format junit --output junit-results.xml'
            }
        }
        stage('Performance Gate') {
            steps {
                sh '''
                    locust-report results --format json --output /dev/null \
                      --p95-threshold 500 --p99-threshold 1000
                '''
            }
        }
    }
    post {
        always {
            junit 'junit-results.xml'
            publishHTML([
                reportDir: '.',
                reportFiles: 'report.html',
                reportName: 'Performance Report',
                allowMissing: false,
            ])
        }
    }
}
```

### GitLab CI

```yaml
performance_test:
  stage: test
  script:
    - locust -f examples/api_load_test.py --headless --users 100
        --spawn-rate 10 --run-time 2m --host $TARGET_HOST --csv results
    - locust-report results --format junit --output junit-results.xml
        --p95-threshold 500 --p99-threshold 1000
  artifacts:
    when: always
    paths:
      - junit-results.xml
    reports:
      junit: junit-results.xml
```

## Example Outputs

### HTML (excerpt)

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Locust Performance Report</title>
<style>/* embedded CSS */</style>
</head>
<body>
<h1>Locust Performance Report</h1>
<div class="summary">
  <div class="card"><div class="label">Total Requests</div>
    <div class="value">5,000</div></div>
  <!-- ... -->
</div>
<table>
  <thead><tr><th>Type</th><th>Name</th><th>Requests</th>...</tr></thead>
  <tbody>
    <tr><td>GET</td><td>/api/items</td><td>1,500</td>...</tr>
  </tbody>
</table>
</body>
</html>
```

### JSON (excerpt)

```json
{
  "metadata": {
    "generated_at": "2026-07-19T14:30:00Z",
    "tool": "locust-performance-kit",
    "version": "1.2.0",
    "csv_prefix": "results"
  },
  "summary": {
    "total_requests": 5000,
    "total_failures": 30,
    "endpoint_count": 4,
    "total_rps": 83.6,
    "failure_rate": 0.006
  },
  "endpoints": [
    {
      "name": "/api/items",
      "type": "GET",
      "request_count": 1500,
      "failure_count": 15,
      "avg_response_time_ms": 135.0,
      "p95": 250.0,
      "p99": 450.0,
      "rps": 25.3,
      "threshold_status": "PASS"
    }
  ],
  "failures": [],
  "exceptions": []
}
```

### Markdown (excerpt)

```markdown
# Locust Performance Report

Generated: 2026-07-19T14:30:00Z | Tool: locust-performance-kit v1.2.0

## Summary

| Metric | Value |
|--------|-------|
| Total Requests | 5,000 |
| Total Failures | 30 |
| Endpoints | 4 |
| Overall RPS | 83.6 |
| Failure Rate | 0.0060 |

## Per-Endpoint Metrics

| Type | Name | Requests | Failures | Avg (ms) | p50 | p95 | p99 | RPS |
|------|------|----------|----------|----------|-----|-----|-----|-----|
| GET | /api/items | 1,500 | 15 | 135.0 | 120.0 | 250.0 | 450.0 | 25.3 |

## Threshold Results

| Endpoint | p95 (ms) | p99 (ms) | Status |
|----------|----------|----------|--------|
| /api/items | 250.0 | 450.0 | ✅ PASS |
| /api/orders | 420.0 | 800.0 | ❌ FAIL |
```

### JUnit XML (excerpt)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="Locust Performance Test" tests="4" failures="1">
    <properties>
      <property name="total_requests" value="5000"/>
      <property name="total_failures" value="30"/>
      <property name="endpoint_count" value="4"/>
      <property name="total_rps" value="83.6"/>
    </properties>
    <testcase classname="locust.endpoints" name="/api/items" time="0.1350">
      <system-out>requests=1500 failures=15 p95=250.0ms p99=450.0ms rps=25.3</system-out>
    </testcase>
    <testcase classname="locust.endpoints" name="/api/orders" time="0.2200">
      <failure type="ThresholdExceeded" message="p95=420.0ms p99=800.0ms exceeds threshold">
        Endpoint /api/orders exceeded threshold: p95=420.0ms, p99=800.0ms
      </failure>
      <system-out>requests=500 failures=10 p95=420.0ms p99=800.0ms rps=8.3</system-out>
    </testcase>
  </testsuite>
</testsuites>
```

## Data Model

The `ReportData` model decouples CSV parsing from rendering:

| Field | Type | Description |
|---|---|---|
| `endpoints` | `list[EndpointStats]` | Per-endpoint metrics (excludes `Aggregated` row) |
| `failures` | `list[FailureRecord]` | Failure entries from `_failures.csv` |
| `exceptions` | `list[ExceptionRecord]` | Exception entries from `_exceptions.csv` |
| `summary` | `ReportSummary` | Aggregated totals (requests, failures, RPS, failure rate) |
| `metadata` | `ReportMetadata` | Generation timestamp, tool name, version, csv_prefix |
| `thresholds` | `ThresholdConfig \| None` | Optional p95/p99 threshold config |

Each `EndpointStats` includes: name, request_type, request_count,
failure_count, average/min/max response time, average content size, RPS,
percentiles (p50, p66, p75, p80, p90, p95, p98, p99), and threshold_status
(`PASS`, `FAIL`, or `SKIP`).

## Tips

- **Threshold exit codes**: Use exit code 2 in CI to gate deployments —
  `locust-report results --p95-threshold 500` fails the CI step if any
  endpoint exceeds 500ms p95.
- **Multiple formats**: Generate all formats in one CI step for maximum
  flexibility:
  ```bash
  locust-report results --format html --output report.html
  locust-report results --format json --output report.json
  locust-report results --format markdown --output report.md
  locust-report results --format junit --output junit.xml
  ```
- **Stdout output**: Use `--output -` or omit `--output` for JSON/Markdown/JUnit
  to write to stdout (useful for piping).
- **Self-contained HTML**: The HTML report has no external CSS/JS dependencies —
  safe for email attachments and Jira tickets.
- **Aggregated row**: The `Aggregated` row from Locust CSV is automatically
  excluded from per-endpoint tables.
