"""Soak Test Template.

Locust template for endurance/soak testing to identify
memory leaks and performance degradation over time.

Usage:
    locust -f src/locust_templates/soak.py --users 50 --spawn-rate 5 --run-time 4h
"""

from locust import HttpUser, between, task


class SoakUser(HttpUser):
    """Simulated user for soak/endurance testing.

    Tests system stability over extended periods.
    """

    wait_time = between(2, 8)

    @task(4)
    def typical_user_flow(self):
        """Simulate a typical user interaction pattern."""
        with self.client.get(
            "/api/v1/dashboard",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Dashboard failed: {response.status_code}")

    @task(2)
    def data_creation(self):
        """Create data to test for memory leaks."""
        payload = {"content": "soak_test_data", "type": "endurance"}
        with self.client.post(
            "/api/v1/data",
            json=payload,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Data creation failed: {response.status_code}")

    @task(3)
    def read_heavy(self):
        """Read-heavy workload to test caching behavior."""
        with self.client.get(
            "/api/v1/data?limit=100",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Data read failed: {response.status_code}")

    @task(1)
    def background_cleanup(self):
        """Background task to test resource cleanup."""
        with self.client.delete(
            "/api/v1/data/cleanup",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 204]:
                response.success()
            else:
                response.failure(f"Cleanup failed: {response.status_code}")
