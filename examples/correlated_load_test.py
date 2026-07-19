"""Example: Request correlation and cascade failure detection.

This example shows how to use RequestCorrelator to track request chains
and identify cascade failures — when a failed request causes downstream
requests from the same user to also fail within a time window.

Run:
    locust -f examples/correlated_load_test.py --headless \
        --users 10 --spawn-rate 2 --run-time 1m \
        --host https://api.example.com

After the test, the following files are written:
    results/correlated_events.csv   — all events with correlation metadata
    results/failure_chains.json     — failure chains (cascades only)
    A summary is printed to stdout.
"""

from __future__ import annotations

from pathlib import Path

from locust import HttpUser, between, events, task

from locust_templates import RequestCorrelator

# Create the correlator with a 5-second cascade window
correlator = RequestCorrelator(cascade_window_s=5.0)


@events.init.add_listener
def _on_init(environment, **kwargs):
    """Register the correlator when Locust initializes."""
    correlator.register(environment)


@events.quitting.add_listener
def _on_quitting(environment, **kwargs):
    """Export correlated data and print summary when the test ends."""
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)

    # Export all events to CSV
    csv_path = correlator.export_csv(output_dir / "correlated_events.csv")
    print(f"\n[correlator] CSV written to {csv_path}")

    # Export failure chains to JSON (cascades only by default)
    json_path = correlator.export_json(output_dir / "failure_chains.json")
    print(f"[correlator] JSON written to {json_path}")

    # Print summary
    summary = correlator.get_summary()
    print("\n" + "=" * 60)
    print("Request Correlation Summary")
    print("=" * 60)
    print(f"  Total requests:     {summary.total_requests}")
    print(f"  Total failures:     {summary.total_failures}")
    print(f"  Cascade failures:   {summary.cascade_failures}")
    print(f"  Root failures:      {summary.root_failures}")
    print(f"  Avg chain depth:    {summary.avg_chain_depth:.2f}")

    if summary.top_failure_chains:
        print(f"\n  Top {len(summary.top_failure_chains)} failure chains:")
        for i, chain in enumerate(summary.top_failure_chains, 1):
            root = chain.root_request
            print(f"    {i}. {root.name} (user={root.user_id})")
            print(f"       cascade_count={chain.cascade_count}, "
                  f"total_length={chain.total_chain_length}")
            for dep in chain.failed_dependents:
                print(f"       -> {dep.name} (status={dep.status_code}, "
                      f"depth={dep.chain_depth})")
    else:
        print("\n  No failure chains detected.")
    print("=" * 60)

    # Also export all events (not just chains) for debugging
    all_events_path = correlator.export_json(
        output_dir / "all_events.json", chains_only=False
    )
    print(f"[correlator] All events JSON written to {all_events_path}")


class CorrelatedAPIUser(HttpUser):
    """Simulated user with a login -> profile -> orders journey.

    Each request includes a user_id in the context so the correlator
    can track request chains per user and detect cascade failures.
    """

    wait_time = between(1, 3)

    def on_start(self):
        """Login and store token — if this fails, downstream requests
        will likely fail too (cascade)."""
        with self.client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpass"},
            context={"user_id": f"user-{self.environment.runner.user_count}"},
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure("Login failed")
            else:
                self.token = response.json().get("token", "")

    @task(3)
    def view_profile(self):
        """View user profile — depends on auth token from login."""
        with self.client.get(
            "/api/v1/profile",
            headers={"Authorization": f"Bearer {getattr(self, 'token', '')}"},
            context={"user_id": f"user-{self.environment.runner.user_count}"},
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Profile failed: {response.status_code}")

    @task(2)
    def list_orders(self):
        """List user orders — depends on auth token from login."""
        with self.client.get(
            "/api/v1/orders",
            headers={"Authorization": f"Bearer {getattr(self, 'token', '')}"},
            context={"user_id": f"user-{self.environment.runner.user_count}"},
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Orders failed: {response.status_code}")

    @task(1)
    def view_order_detail(self):
        """View a specific order — depends on orders list succeeding."""
        with self.client.get(
            "/api/v1/orders/12345",
            headers={"Authorization": f"Bearer {getattr(self, 'token', '')}"},
            context={
                "user_id": f"user-{self.environment.runner.user_count}",
                "correlation_id": "order-detail-view",
            },
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Order detail failed: {response.status_code}")
