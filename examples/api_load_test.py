"""API Load Test Example.

Production-ready Locust script demonstrating how to use the
locust_templates package for REST API load testing.

Usage:
    locust -f examples/api_load_test.py --users 100 --spawn-rate 10 --run-time 5m

    # Headless mode (CI/CD):
    locust -f examples/api_load_test.py \\
        --headless --users 50 --spawn-rate 5 --run-time 2m \\
        --host http://localhost:8080
"""

import os
import sys
from pathlib import Path

# Ensure src is on the path for template imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from locust import between, events, task
from locust_templates.api_load import APIUser
from locust_templates.metrics import MetricsCollector
from locust_templates.thresholds import ThresholdChecker

# Shared metrics collector for post-test analysis
metrics = MetricsCollector()


class ExampleAPIUser(APIUser):
    """Example API user extending the base template.

    Customizes the base APIUser for a specific API by overriding
    the authentication token and adding project-specific tasks.
    """

    wait_time = between(1, 3)

    def on_start(self):
        self.api_token = os.environ.get("API_TOKEN", "example_token")

    @task(5)
    def list_products(self):
        """GET /api/v1/products - high-frequency list endpoint."""
        with self.client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {self._get_token()}"},
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                metrics.record_request(
                    "GET /api/v1/products",
                    response.elapsed.total_seconds() * 1000,
                    response.status_code,
                    True,
                )
                response.success()
            elif response.status_code == 429:
                metrics.record_request(
                    "GET /api/v1/products",
                    response.elapsed.total_seconds() * 1000,
                    response.status_code,
                    False,
                )
                response.failure("Rate limited")
            else:
                metrics.record_request(
                    "GET /api/v1/products",
                    response.elapsed.total_seconds() * 1000,
                    response.status_code,
                    False,
                )
                response.failure(f"Unexpected status: {response.status_code}")

    @task(3)
    def get_product_detail(self):
        """GET /api/v1/products/{id} - detail page."""
        product_id = self._get_random_item_id()
        with self.client.get(
            f"/api/v1/products/{product_id}",
            headers={"Authorization": f"Bearer {self._get_token()}"},
            catch_response=True,
        ) as response:
            success = response.status_code == 200
            metrics.record_request(
                "GET /api/v1/products/{id}",
                response.elapsed.total_seconds() * 1000,
                response.status_code,
                success,
            )
            if success:
                response.success()
            else:
                response.failure(f"Failed with {response.status_code}")

    @task(1)
    def create_order(self):
        """POST /api/v1/orders - create a new order."""
        payload = {
            "product_id": self._get_random_item_id(),
            "quantity": 1,
        }
        with self.client.post(
            "/api/v1/orders",
            json=payload,
            headers={"Authorization": f"Bearer {self._get_token()}"},
            catch_response=True,
        ) as response:
            success = response.status_code in [200, 201]
            metrics.record_request(
                "POST /api/v1/orders",
                response.elapsed.total_seconds() * 1000,
                response.status_code,
                success,
            )
            if success:
                response.success()
            else:
                response.failure(f"Order failed: {response.status_code}")

    def _get_token(self):
        """Override to use environment-based token."""
        return getattr(self, "api_token", "example_token")


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Print threshold results when test ends."""
    summary = metrics.get_summary()
    if not summary:
        return

    checker = ThresholdChecker(
        p95_threshold=float(os.environ.get("P95_THRESHOLD", "500")),
        p99_threshold=float(os.environ.get("P99_THRESHOLD", "1000")),
        error_rate_threshold=float(os.environ.get("ERROR_RATE_THRESHOLD", "0.01")),
    )

    # Calculate overall p95/p99 from all endpoints
    all_p95 = []
    all_p99 = []
    total_errors = 0
    total_requests = 0

    for name in summary:
        p95 = metrics.get_percentile(name, 95)
        p99 = metrics.get_percentile(name, 99)
        all_p95.append(p95)
        all_p99.append(p99)
        total_errors += summary[name]["failures"]
        total_requests += summary[name]["count"]

    overall_p95 = max(all_p95) if all_p95 else 0
    overall_p99 = max(all_p99) if all_p99 else 0
    error_rate = total_errors / total_requests if total_requests > 0 else 0

    result = checker.check(
        p95=overall_p95,
        p99=overall_p99,
        error_rate=error_rate,
    )

    print("\n" + "=" * 60)
    print("PERFORMANCE THRESHOLD RESULTS")
    print("=" * 60)
    print(f"  p95 latency:   {overall_p95:.1f}ms")
    print(f"  p99 latency:   {overall_p99:.1f}ms")
    print(f"  Error rate:    {error_rate:.2%}")
    print(f"  Status:        {'PASS' if result.passed else 'FAIL'}")

    if result.failures:
        print("\n  Failures:")
        for f in result.failures:
            print(f"    - {f}")
    print("=" * 60)


if __name__ == "__main__":
    print("Run with: locust -f examples/api_load_test.py")
