"""Web UI Test Template.

Locust template for browser-based user journey testing
simulating realistic web application interactions.

Usage:
    locust -f src/locust_templates/web_ui.py --users 100 --spawn-rate 10 --run-time 10m
"""

from locust import HttpUser, between, task


class WebUIUser(HttpUser):
    """Simulated user for web UI testing.

    Tests typical browser-based user journeys through a web application.
    """

    wait_time = between(2, 10)

    @task(5)
    def browse_homepage(self):
        """Browse the main page."""
        with self.client.get(
            "/",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Homepage failed: {response.status_code}")

    @task(3)
    def search_items(self):
        """Search for items."""
        with self.client.get(
            "/search?q=test&limit=20",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")

    @task(2)
    def view_detail_page(self):
        """View a detail page."""
        with self.client.get(
            "/items/1",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Detail page failed: {response.status_code}")

    @task(2)
    def add_to_cart(self):
        """Add an item to cart."""
        with self.client.post(
            "/cart/add",
            json={"item_id": 1, "quantity": 1},
            catch_response=True,
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Add to cart failed: {response.status_code}")

    @task(1)
    def checkout_flow(self):
        """Complete checkout flow."""
        with self.client.post(
            "/checkout",
            json={"payment_method": "credit_card"},
            catch_response=True,
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Checkout failed: {response.status_code}")
