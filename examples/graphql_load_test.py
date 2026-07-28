"""GraphQL Load Test Example — E-Commerce Storefront.

Demonstrates how to load-test a GraphQL e-commerce API using the
``GraphQLUser`` template with parameterized queries, mutations, and
complexity analysis.

Usage:
    locust -f examples/graphql_load_test.py --users 100 --spawn-rate 10 --run-time 5m
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is on the path for template imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from locust import between, task

from locust_templates.graphql import GraphQLUser


class ExampleGraphQLUser(GraphQLUser):
    """Example GraphQL user simulating an e-commerce storefront.

    Demonstrates three realistic load patterns:

    1. **Product search** — parameterised query with search variables
    2. **Product detail** — fetching a single item by ID
    3. **Place order** — a mutation that creates a new order

    Run::

        locust -f examples/graphql_load_test.py \\
        --users 100 --spawn-rate 10 --run-time 5m
    """

    wait_time = between(1, 5)

    @task(3)
    def search_products(self) -> None:
        """Search for products by category and price range.

        Uses ``self.query()`` with a variables dict to parameterise
        the GraphQL query. Checks for GraphQL errors and logs them
        via ``self.environment.runner.quit()`` if critical.
        """
        query = """
        query SearchProducts($category: String, $maxPrice: Float) {
            products(category: $category, maxPrice: $maxPrice) {
                id
                name
                price
                inStock
            }
        }
        """
        response = self.query(
            query,
            variables={"category": "electronics", "maxPrice": 999.99},
        )
        if response.errors:
            self.environment.runner.quit()

    @task(2)
    def get_product_detail(self) -> None:
        """Fetch full product details by ID.

        Demonstrates a parameterised single-item query with multiple
        nested fields and error checking via ``GraphQLResponse.errors``.
        """
        query = """
        query GetProduct($id: ID!) {
            product(id: $id) {
                id
                name
                description
                price
                category
                reviews {
                    rating
                    comment
                }
            }
        }
        """
        response = self.query(query, variables={"id": "prod-42"})
        if response.errors:
            self.environment.runner.quit()

    @task(1)
    def place_order(self) -> None:
        """Place a new order via a GraphQL mutation.

        Demonstrates mutation operations with input types and returns
        the order confirmation. Complexity can be checked via the
        ``QueryComplexityAnalyzer`` if desired.
        """
        mutation = """
        mutation PlaceOrder($items: [OrderItemInput!]!) {
            createOrder(items: $items) {
                orderId
                status
                total
            }
        }
        """
        response = self.query(
            mutation,
            variables={
                "items": [
                    {"productId": "prod-42", "quantity": 2},
                    {"productId": "prod-99", "quantity": 1},
                ]
            },
        )
        if response.errors:
            self.environment.runner.quit()

    def on_start(self) -> None:
        """Initialise auth headers when the user starts.

        Inherits from ``GraphQLUser`` which handles authenticator setup.
        """
        super().on_start()


if __name__ == "__main__":
    print("Run with: locust -f examples/graphql_load_test.py")
