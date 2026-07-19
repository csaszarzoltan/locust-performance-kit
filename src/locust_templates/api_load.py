"""API Load Test Template.

Production-ready Locust script for REST API load testing with
custom metrics collection and threshold validation.

Usage:
    locust -f src/locust_templates/api_load.py --users 100 --spawn-rate 10 --run-time 5m
"""

import random
import time

from locust import HttpUser, between, events, task


class APIUser(HttpUser):
    """Simulated user for API load testing.

    Adjust wait_time, host, and tasks based on your API.
    """

    wait_time = between(1, 3)

    def on_start(self):
        """Called when a simulated user starts."""
        pass

    @task(3)
    def get_items(self):
        """GET /items endpoint - weighted 3x more than other tasks."""
        with self.client.get(
            "/api/v1/items",
            headers={"Authorization": f"Bearer {self._get_token()}"},
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(2)
    def get_item_detail(self):
        """GET /items/{id} - detail page."""
        item_id = self._get_random_item_id()
        with self.client.get(
            f"/api/v1/items/{item_id}",
            headers={"Authorization": f"Bearer {self._get_token()}"},
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with {response.status_code}")

    @task(1)
    def create_item(self):
        """POST /items - create new item."""
        payload = {
            "name": f"Test Item {int(time.time())}",
            "description": "Load testing item",
        }
        with self.client.post(
            "/api/v1/items",
            json=payload,
            headers={"Authorization": f"Bearer {self._get_token()}"},
            catch_response=True,
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Create failed: {response.status_code}")

    def _get_token(self):
        """Generate or retrieve auth token."""
        return "test_token_123"

    def _get_random_item_id(self):
        """Return random item ID for testing."""
        return random.randint(1, 1000)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log slow requests for analysis."""
    if response_time > 1000:
        print(f"SLOW REQUEST: {name} took {response_time}ms")


@events.user_error.add_listener
def on_user_error(user_instance, exception, tb, **kwargs):
    """Log user errors."""
    print(f"User error: {exception}")


@events.quit.add_listener
def on_quit(**kwargs):
    """Called when load test ends."""
    print("Load test completed")
