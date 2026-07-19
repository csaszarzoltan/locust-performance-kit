"""Spike Test Template.

Locust template for spike testing with sudden load bursts
to test system recovery behavior.

Usage:
    locust -f src/locust_templates/spike.py --users 1000 --spawn-rate 100 --run-time 5m
"""

from locust import HttpUser, between, task


class SpikeUser(HttpUser):
    """Simulated user for spike testing.

    Tests system behavior under sudden load spikes and recovery.
    """

    wait_time = between(1, 2)

    @task(2)
    def normal_request(self):
        """Normal baseline request."""
        with self.client.get(
            "/api/v1/status",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status check failed: {response.status_code}")

    @task(5)
    def burst_request(self):
        """High-frequency burst request."""
        with self.client.post(
            "/api/v1/events",
            json={"type": "spike_test", "timestamp": "now"},
            catch_response=True,
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Event creation failed: {response.status_code}")

    @task(1)
    def recovery_request(self):
        """Request to verify system recovery after spike."""
        with self.client.get(
            "/api/v1/health/detailed",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Recovery check failed: {response.status_code}")
