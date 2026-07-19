"""Stress Test Template.

Locust template for stress testing with ramp-up patterns,
sustained load, and spike phases.

Usage:
    locust -f src/locust_templates/stress.py --users 500 --spawn-rate 50 --run-time 10m
"""


from locust import HttpUser, between, task


class StressUser(HttpUser):
    """Simulated user for stress testing.

    Tests system behavior under increasing load with ramp-up patterns.
    """

    wait_time = between(1, 5)

    def on_start(self):
        """Called when a simulated user starts."""
        pass

    def on_stop(self):
        """Called when a simulated user stops."""
        pass

    @task(3)
    def ramp_up_request(self):
        """Lightweight request for ramp-up phase."""
        with self.client.get(
            "/api/v1/health",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(2)
    def sustained_request(self):
        """Standard request for sustained load phase."""
        payload = {"query": "stress_test"}
        with self.client.post(
            "/api/v1/search",
            json=payload,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")

    @task(1)
    def spike_request(self):
        """Heavy request for spike phase."""
        with self.client.get(
            "/api/v1/reports/summary",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Report failed: {response.status_code}")
