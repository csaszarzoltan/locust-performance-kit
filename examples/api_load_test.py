"""
API Load Test Template
A production-ready Locust script for REST API load testing.

Usage:
    locust -f examples/api_load_test.py --users 100 --spawn-rate 10 --run-time 5m
    
    # Or with web UI:
    locust -f examples/api_load_test.py
"""

from locust import HttpUser, task, between, events
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIUser(HttpUser):
    """
    Simulated user for API load testing.
    Adjust wait_time, host, and tasks based on your API.
    """
    
    # Wait between 1-3 seconds between requests (realistic user behavior)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Called when a simulated user starts."""
        logger.info(f"User started - Host: {self.host}")
    
    @task(3)
    def get_items(self):
        """
        GET /items endpoint - weighted 3x more than other tasks.
        Adjust weight based on your traffic distribution.
        """
        with self.client.get(
            "/api/v1/items",
            headers={"Authorization": f"Bearer {self._get_token()}"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
                logger.warning("Rate limit hit")
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def get_item_detail(self):
        """GET /items/{id} - detail page."""
        item_id = self._get_random_item_id()
        with self.client.get(
            f"/api/v1/items/{item_id}",
            headers={"Authorization": f"Bearer {self._get_token()}"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with {response.status_code}")
    
    @task(1)
    def create_item(self):
        """POST /items - create new item."""
        import json
        payload = {
            "name": f"Test Item {int(time.time())}",
            "description": "Load testing item"
        }
        with self.client.post(
            "/api/v1/items",
            json=payload,
            headers={"Authorization": f"Bearer {self._get_token()}"},
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Create failed: {response.status_code}")
    
    def _get_token(self):
        """Generate or retrieve auth token."""
        # In production, use a token pool or OAuth flow
        return "test_token_123"
    
    def _get_random_item_id(self):
        """Return random item ID for testing."""
        import random
        return random.randint(1, 1000)


# Custom metrics collection
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log slow requests for analysis."""
    if response_time > 1000:  # 1 second threshold
        logger.warning(f"SLOW REQUEST: {name} took {response_time}ms")


@events.user_error.add_listener
def on_user_error(user_instance, exception, tb, **kwargs):
    """Log user errors."""
    logger.error(f"User error: {exception}")


@events.quit.add_listener
def on_quit(**kwargs):
    """Called when load test ends."""
    logger.info("Load test completed")
