"""Real-time live metrics dashboard for Locust performance tests.

Records time-series snapshots of response times, throughput, and error
rate during a running test and renders a self-contained HTML dashboard
with inline Chart.js for live response-time/throughput charts, an alerts
panel, and auto-refresh.

Public API:
    TimeSeriesPoint — a single time-series snapshot
    LiveDashboard   — collects snapshots and renders HTML
"""

from __future__ import annotations

import html as html_module
import json
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from locust_templates.alerts import Alert
    from locust_templates.metrics import MetricsCollector


@dataclass
class TimeSeriesPoint:
    """A single time-series snapshot of live metrics.

    Attributes:
        timestamp: Unix timestamp of the snapshot.
        avg_response_time: Average response time in ms.
        p95_response_time: 95th percentile response time in ms.
        throughput: Requests per second.
        error_rate: Error rate (0.0–1.0).
        active_users: Number of active simulated users.
    """

    timestamp: float
    avg_response_time: float
    p95_response_time: float
    throughput: float
    error_rate: float
    active_users: int


class LiveDashboard:
    """Collect time-series metrics and render a live HTML dashboard.

    The dashboard is self-contained — it embeds Chart.js from a CDN
    and the time-series data as a JSON blob. When served by Locust's
    built-in web server (or any HTTP server), the page auto-refreshes
    to show the latest data.

    Example:
        dash = LiveDashboard(max_points=300)

        # During the test, record snapshots periodically:
        dash.record_from_collector(collector, active_users=100)

        # Render the HTML dashboard:
        html = dash.render()
        # or write to file:
        dash.render_to_file("dashboard.html")
    """

    def __init__(self, max_points: int = 300) -> None:
        """Initialize the dashboard.

        Args:
            max_points: Maximum number of time-series points to retain.
                Older points are discarded (rolling window).
        """
        self._max_points = max_points
        self._history: deque[TimeSeriesPoint] = deque(maxlen=max_points)

    def record(
        self,
        avg_response_time: float,
        p95_response_time: float,
        throughput: float,
        error_rate: float,
        active_users: int,
        *,
        timestamp: float | None = None,
    ) -> TimeSeriesPoint:
        """Record a single time-series snapshot.

        Args:
            avg_response_time: Average response time in ms.
            p95_response_time: 95th percentile response time in ms.
            throughput: Requests per second.
            error_rate: Error rate (0.0–1.0).
            active_users: Number of active users.
            timestamp: Optional explicit timestamp. Defaults to now.

        Returns:
            The recorded TimeSeriesPoint.
        """
        pt = TimeSeriesPoint(
            timestamp=timestamp if timestamp is not None else time.time(),
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            throughput=throughput,
            error_rate=error_rate,
            active_users=active_users,
        )
        self._history.append(pt)
        return pt

    def record_from_collector(
        self,
        collector: MetricsCollector,
        active_users: int,
        *,
        timestamp: float | None = None,
    ) -> TimeSeriesPoint:
        """Record a snapshot from a MetricsCollector.

        Computes avg/p95/throughput/error_rate across all endpoints
        recorded in the collector.

        Args:
            collector: A MetricsCollector with recorded requests.
            active_users: Current number of active simulated users.
            timestamp: Optional explicit timestamp.

        Returns:
            The recorded TimeSeriesPoint.
        """
        summary = collector.get_summary()
        if not summary:
            return self.record(
                avg_response_time=0.0,
                p95_response_time=0.0,
                throughput=0.0,
                error_rate=0.0,
                active_users=active_users,
                timestamp=timestamp,
            )

        total_count = sum(s["count"] for s in summary.values())
        total_failures = sum(s["failures"] for s in summary.values())

        # Weighted average response time
        avg_rt = (
            sum(s["avg"] * s["count"] for s in summary.values()) / total_count
            if total_count > 0
            else 0.0
        )

        # Overall p95: take max p95 across endpoints (conservative)
        p95 = 0.0
        for name in summary:
            p = collector.get_percentile(name, 95)
            if p > p95:
                p95 = p

        error_rate = total_failures / total_count if total_count > 0 else 0.0

        # Throughput: sum of RPS across endpoints
        # MetricsCollector doesn't track RPS directly; approximate
        # from the count and the time span. For simplicity, use total count
        # as a rough proxy — the caller can override with a direct record().
        throughput = float(total_count)

        return self.record(
            avg_response_time=avg_rt,
            p95_response_time=p95,
            throughput=throughput,
            error_rate=error_rate,
            active_users=active_users,
            timestamp=timestamp,
        )

    def get_history(self) -> list[TimeSeriesPoint]:
        """Return all recorded time-series points."""
        return list(self._history)

    def get_latest(self) -> TimeSeriesPoint | None:
        """Return the most recent point, or None if empty."""
        if not self._history:
            return None
        return self._history[-1]

    def clear(self) -> None:
        """Clear all recorded history."""
        self._history.clear()

    def render(self, *, alerts: list[Alert] | None = None) -> str:
        """Render the dashboard as a self-contained HTML string.

        Args:
            alerts: Optional list of fired Alerts to display in the
                alerts panel.

        Returns:
            Complete HTML document string with embedded Chart.js and
            time-series data.
        """
        history = self.get_history()
        data_json = json.dumps(
            [asdict(pt) for pt in history], default=str
        )

        alerts_html = self._build_alerts_panel(alerts or [])

        latest = history[-1] if history else None
        latest_cards = self._build_summary_cards(latest)

        return _HTML_TEMPLATE.format(
            data_json=data_json,
            alerts_html=alerts_html,
            summary_cards=latest_cards,
        )

    def render_to_file(
        self,
        output_path: str | Path,
        *,
        alerts: list[Alert] | None = None,
    ) -> str:
        """Render the dashboard and write it to a file.

        Args:
            output_path: Where to write the HTML file.
            alerts: Optional list of fired Alerts.

        Returns:
            Absolute path of the written file.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.render(alerts=alerts), encoding="utf-8")
        return str(out.resolve())

    def _build_summary_cards(self, latest: TimeSeriesPoint | None) -> str:
        """Build the summary cards from the latest snapshot."""
        if latest is None:
            return """
  <div class="card"><div class="label">Avg RT</div><div class="value">—</div></div>
  <div class="card"><div class="label">p95 RT</div><div class="value">—</div></div>
  <div class="card"><div class="label">Throughput</div><div class="value">—</div></div>
  <div class="card"><div class="label">Error Rate</div><div class="value">—</div></div>
  <div class="card"><div class="label">Active Users</div><div class="value">—</div></div>"""  # noqa: E501
        return f"""
  <div class="card"><div class="label">Avg RT</div>
    <div class="value">{latest.avg_response_time:.1f}ms</div></div>
  <div class="card"><div class="label">p95 RT</div>
    <div class="value">{latest.p95_response_time:.1f}ms</div></div>
  <div class="card"><div class="label">Throughput</div>
    <div class="value">{latest.throughput:.1f}</div></div>
  <div class="card"><div class="label">Error Rate</div>
    <div class="value">{latest.error_rate:.4f}</div></div>
  <div class="card"><div class="label">Active Users</div>
    <div class="value">{latest.active_users}</div></div>"""

    def _build_alerts_panel(self, alerts: list[Alert]) -> str:
        """Build the alerts panel HTML."""
        if not alerts:
            return '<div id="alerts"><h2>Alerts</h2><p>No active alerts.</p></div>'

        rows = []
        for a in alerts:
            esc_name = html_module.escape(a.rule_name)
            esc_msg = html_module.escape(a.message)
            css_class = (
                "alert-critical"
                if a.severity == "critical"
                else "alert-warning"
            )
            rows.append(
                f'<div class="alert {css_class}">'
                f"<strong>{esc_name}</strong> — {esc_msg}"
                f"</div>"
            )
        return (
            '<div id="alerts"><h2>Alerts</h2>'
            f'{"".join(rows)}</div>'
        )


# ──────────────────────────────────────────────────────────────
# HTML template
# ──────────────────────────────────────────────────────────────

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="5">
<title>Locust Live Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  body {{ font-family: Arial, sans-serif; margin: 1.5rem;
    background: #f5f5f5; color: #333; }}
  h1 {{ color: #2c3e50; }}
  h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 0.3rem; }}
  .summary {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; }}
  .card {{ background: #fff; border-radius: 8px; padding: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1); min-width: 140px; }}
  .card .label {{ font-size: 0.75rem; color: #7f8c8d; text-transform: uppercase; }}
  .card .value {{ font-size: 1.4rem; font-weight: bold; color: #2c3e50; }}
  .chart-container {{ background: #fff; border-radius: 8px; padding: 1rem;
    margin: 1rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
  canvas {{ max-height: 300px; }}
  .alert {{ padding: 0.75rem 1rem; border-radius: 4px; margin: 0.5rem 0; }}
  .alert-warning {{ background: #fff3cd; border: 1px solid #ffe08a; color: #856404; }}
  .alert-critical {{ background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }}
  .footer {{ margin-top: 2rem; color: #95a5a6; font-size: 0.8rem; }}
</style>
</head>
<body>
<h1>Locust Live Dashboard</h1>
<div class="summary">{summary_cards}
</div>
{alerts_html}
<div class="chart-container">
  <h2>Response Time (ms)</h2>
  <canvas id="responseTimeChart"></canvas>
</div>
<div class="chart-container">
  <h2>Throughput (req/s)</h2>
  <canvas id="throughputChart"></canvas>
</div>
<div class="footer">Auto-refresh: 5s |
  Generated by locust-performance-kit LiveDashboard</div>
<script>
const rawData = {data_json};
const labels = rawData.map(p => new Date(p.timestamp * 1000).toLocaleTimeString());
const avgRT = rawData.map(p => p.avg_response_time);
const p95RT = rawData.map(p => p.p95_response_time);
const throughput = rawData.map(p => p.throughput);
const errorRate = rawData.map(p => p.error_rate);

// Response time chart
new Chart(document.getElementById('responseTimeChart'), {{
  type: 'line',
  data: {{
    labels: labels,
    datasets: [
      {{ label: 'Avg Response Time (ms)', data: avgRT,
         borderColor: '#3498db', fill: false, tension: 0.1 }},
      {{ label: 'p95 Response Time (ms)', data: p95RT,
         borderColor: '#e74c3c', fill: false, tension: 0.1 }}
    ]
  }},
  options: {{
    responsive: true,
    scales: {{ x: {{ display: true }},
              y: {{ display: true, beginAtZero: true }} }}
  }}
}});

// Throughput chart
new Chart(document.getElementById('throughputChart'), {{
  type: 'line',
  data: {{
    labels: labels,
    datasets: [
      {{ label: 'Throughput (req/s)', data: throughput,
         borderColor: '#27ae60', fill: false, tension: 0.1 }}
    ]
  }},
  options: {{
    responsive: true,
    scales: {{ x: {{ display: true }},
              y: {{ display: true, beginAtZero: true }} }}
  }}
}});
</script>
</body>
</html>"""


__all__ = [
    "LiveDashboard",
    "TimeSeriesPoint",
]
