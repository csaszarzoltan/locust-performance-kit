"""Live Dashboard and Threshold Alerts Example.

Demonstrates the v1.3.0 real-time live metrics dashboard and configurable
threshold alerts that work during a running Locust load test.

Features shown:
  - LiveDashboard: time-series snapshots, Chart.js HTML output
  - AlertEngine: threshold rules with dedup, dashboard panel integration
  - MetricsCollector integration for automatic snapshot recording

Usage:
    # Run with web UI (dashboard generated on quit):
    locust -f examples/live_dashboard.py --users 50 --spawn-rate 5 --run-time 2m

    # Headless mode (CI/CD):
    locust -f examples/live_dashboard.py \\
        --headless --users 50 --spawn-rate 5 --run-time 2m \\
        --host http://localhost:8080

    # With environment variables:
    export LOCUST_HOST=http://localhost:8080
    export LOCUST_DASHBOARD_OUTPUT=dashboard.html
    locust -f examples/live_dashboard.py --headless --users 50 --run-time 1m
"""

import os
import sys
from pathlib import Path

# Ensure src is on the path for template imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from locust import between, events, task

from locust_templates.alerts import AlertEngine, AlertRule
from locust_templates.api_load import APIUser
from locust_templates.live_dashboard import LiveDashboard
from locust_templates.metrics import MetricsCollector

# Shared instances — dashboard and alerts persist across all Locust users
metrics = MetricsCollector()
dashboard = LiveDashboard(max_points=300)
alert_engine = AlertEngine(
    rules=[
        AlertRule("p95-high", "p95", ">", 500.0, severity="warning"),
        AlertRule("p95-critical", "p95", ">", 1000.0, severity="critical"),
        AlertRule("err-high", "error_rate", ">", 0.01, severity="warning"),
    ],
    dedup=True,
)


class DashboardUser(APIUser):
    """Example user that records metrics for the live dashboard.

    Each request records timing and success/failure into the shared
    MetricsCollector. On test quit, the dashboard renders an HTML file
    with Chart.js charts and the alert history.
    """

    wait_time = between(1, 3)

    @task(5)
    def get_products(self):
        """GET /api/v1/products — list endpoint."""
        with self.client.get(
            "/api/v1/products",
            catch_response=True,
        ) as response:
            rt = response.elapsed.total_seconds() * 1000
            success = response.status_code == 200
            metrics.record_request(
                "GET /api/v1/products", rt, response.status_code, success,
            )
            if success:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(3)
    def get_order(self):
        """GET /api/v1/orders/{id} — detail endpoint."""
        order_id = self._random_id()
        with self.client.get(
            f"/api/v1/orders/{order_id}",
            catch_response=True,
        ) as response:
            rt = response.elapsed.total_seconds() * 1000
            success = response.status_code == 200
            metrics.record_request(
                "GET /api/v1/orders/{id}", rt, response.status_code, success,
            )
            if success:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(1)
    def create_order(self):
        """POST /api/v1/orders — write endpoint."""
        with self.client.post(
            "/api/v1/orders",
            json={"product_id": self._random_id(), "quantity": 1},
            catch_response=True,
        ) as response:
            rt = response.elapsed.total_seconds() * 1000
            success = response.status_code in (200, 201)
            metrics.record_request(
                "POST /api/v1/orders", rt, response.status_code, success,
            )
            if success:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    def _random_id(self):
        """Return a fake random ID for demo purposes."""
        import random
        return str(random.randint(1, 1000))


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Generate the live dashboard HTML on test completion.

    This listener:
      1. Records a final snapshot from the MetricsCollector
      2. Checks alert rules against the latest metrics
      3. Renders the dashboard HTML with alerts to disk
    """
    summary = metrics.get_summary()
    if not summary:
        print("No metrics collected — skipping dashboard.")
        return

    # Compute current metrics from collector
    total_count = sum(s["count"] for s in summary.values())
    total_failures = sum(s["failures"] for s in summary.values())
    error_rate = total_failures / total_count if total_count > 0 else 0.0
    p95 = max(
        (metrics.get_percentile(name, 95) for name in summary),
        default=0.0,
    )
    throughput = float(total_count)

    # Record the final snapshot
    dashboard.record(
        avg_response_time=p95 / 2,  # approximate
        p95_response_time=p95,
        throughput=throughput,
        error_rate=error_rate,
        active_users=environment.runner.user_count,
    )

    # Check alerts against current metrics
    fired_alerts = alert_engine.check({
        "p95": p95,
        "error_rate": error_rate,
        "throughput": throughput,
    })
    if fired_alerts:
        print(f"\n  {len(fired_alerts)} alert(s) fired:")
        for a in fired_alerts:
            print(f"    [{a.severity.upper()}] {a.message}")

    # Determine output path
    output = os.environ.get("LOCUST_DASHBOARD_OUTPUT", "dashboard.html")

    # Render dashboard with all fired alerts
    path = dashboard.render_to_file(
        output, alerts=alert_engine.get_alerts(),
    )
    print(f"\n  Live dashboard written to: {path}")
    print("  Open in a browser to see charts and alert history.")
