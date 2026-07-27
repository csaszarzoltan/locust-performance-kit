# Grafana Dashboards

Three pre-built Grafana dashboards for visualising Locust performance test
results, traces, and system resources in real time.

## Dashboard Overview

| Dashboard | UID | Data source | Focus |
|---|---|---|---|
| **Locust Overview** | `locust-overview` | Prometheus | Load test metrics — users, RPS, latency, errors |
| **Locust Traces** | `locust-traces` | Tempo | Distributed traces — service graph, spans, heatmaps |
| **Locust Combined** | `locust-combined` | Prometheus + Tempo | Unified view — metrics + traces + system resources |

All three dashboards share:

- **Tags**: `locust`, `performance-testing`, `observability`
- **Template variables**: `$datasource` (data source selector), `$environment`
  (defaults to `production`)
- **Timezone**: Browser-local
- **Grafana schemaVersion**: 30+ (Grafana v8+ compatible)

## Importing Dashboards

### Via Grafana Web UI

1. Open Grafana → **Dashboards** → **New** → **Import**
2. Upload the JSON file or paste its contents
3. Select the corresponding data source for `$datasource`
4. Click **Import**

### Via Grafana API

```bash
# Set your Grafana API key and URL
GRAFANA_URL=http://localhost:3000
API_KEY=your_api_key

for dashboard in grafana/dashboards/*.json; do
  payload=$(python3 -c "
import json
with open('$dashboard') as f:
    d = json.load(f)
print(json.dumps({'dashboard': d, 'overwrite': True}))
  ")
  curl -s -X POST "$GRAFANA_URL/api/dashboards/db" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload"
done
```

### Via Terraform / Grafana Provider

```hcl
resource "grafana_dashboard" "locust_overview" {
  config_json = file("${path.module}/grafana/dashboards/locust-overview.json")
}
```

## Locust Overview Dashboard

**Data source**: Prometheus (`$datasource`)

### Panels

| Panel | Type | PromQL / Description |
|---|---|---|
| Active Users | Stat | `sum(locust_users_swarm)` |
| Total RPS | Stat | `sum(rate(locust_requests_total[5m]))` |
| Avg Response Time | Stat | `avg(locust_request_duration_seconds_sum / locust_request_duration_seconds_count)` |
| p95 Latency | Stat | `histogram_quantile(0.95, sum(rate(locust_request_duration_seconds_bucket[5m])) by (le))` |
| p99 Latency | Stat | `histogram_quantile(0.99, sum(rate(locust_request_duration_seconds_bucket[5m])) by (le))` |
| Error Rate | Stat | `(sum(rate(locust_requests_total{status!~"2.."}[5m])) / sum(rate(locust_requests_total[5m]))) * 100` |
| Top Slow Endpoints | Table | Longest avg response time by endpoint |
| Failure Hotspots | Table | Endpoints sorted by failure rate |

The p95 Latency and p99 Latency panels include colour thresholds:
- **Green** (≤500ms) / **Orange** (500–1000ms) / **Red** (>1000ms)

## Locust Traces Dashboard

**Data source**: Tempo (`$datasource`)

### Panels

| Panel | Type | Query |
|---|---|---|
| Service Graph | Node Graph | `{service.name="locust-performance-test"}` |
| Trace List | Trace List | `{service.name="locust-performance-test"}` |
| Span Duration Heatmap | Heatmap | `rate(span_duration_seconds_bucket[5m])` |
| Error Spans | Table | Span attributes query for error status |
| Span Attributes | Table | Span attributes query for endpoint details |

The Service Graph and Trace List panels filter by
`service.name="locust-performance-test"`, matching the default `OTEL_SERVICE_NAME`.
Override via the [OpenTelemetry Tracing](otel-tracing.md) configuration.

## Locust Combined Dashboard

**Data source**: Prometheus + Tempo

### Panels

| Panel | Type | Data Source |
|---|---|---|
| Active Users | Stat | Prometheus |
| Total RPS | Stat | Prometheus |
| Service Graph | Node Graph | Tempo |
| Trace List | Trace List | Tempo |
| CPU Usage | Time Series | Prometheus (`100 - avg(rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100`) |
| Memory Usage | Time Series | Prometheus (`(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100`) |
| Network | Time Series | Prometheus |

This dashboard is designed for a single-pane-of-glass view during load tests,
combining application-level metrics, distributed traces, and system resources.

## Template Variables

All three dashboards include two template variables:

| Variable | Name | Default | Description |
|---|---|---|---|
| Data Source | `datasource` | — | Select the Prometheus or Tempo data source at import time |
| Environment | `environment` | `production` | Filter by deployment environment; change to `staging` or `development` as needed |

To change the default environment:

```json
{
  "templating": {
    "list": [
      {
        "name": "environment",
        "query": "staging"
      }
    ]
  }
}
```

## Prerequisites

### Prometheus

The Locust Prometheus exporter must be running and exposing metrics. The
dashboard expects the following metric names from the
[locust-exporter](https://github.com/ContainerSolutions/locust_exporter):

- `locust_users_swarm`
- `locust_requests_total`
- `locust_request_duration_seconds_*`
- `locust_errors_total`

### Tempo / Jaeger

Traces must be exported from Locust via OTLP to a Tempo or Jaeger backend.
See [OpenTelemetry Tracing](otel-tracing.md) for setup instructions.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Panels show "No data" | Data source not selected in the `$datasource` template variable, or data source is unreachable |
| Active Users shows 0 | Locust not running, or Prometheus not scraping Locust metrics |
| Trace List is empty | Locust not exporting traces, or OTel endpoint not configured |
| p95 Latency shows N/A | No histogram buckets configured in Locust metrics exporter |
| CPU/Memory panels show N/A | Node exporter not running on the target host |
