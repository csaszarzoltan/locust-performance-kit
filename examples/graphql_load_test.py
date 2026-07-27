"""GraphQL Load Test Example (TDD stub).

Placeholder for a production-ready Locust script demonstrating how to
use the GraphQLUser template for GraphQL API load testing.

Usage:
    locust -f examples/graphql_load_test.py --users 100 --spawn-rate 10 --run-time 5m
"""

import sys
from pathlib import Path

# Ensure src is on the path for template imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from locust import between, task

from locust_templates.graphql import GraphQLUser


class ExampleGraphQLUser(GraphQLUser):
    """Example GraphQL user extending the base template.

    Uses the inherited ``self.query()`` helper to send GraphQL
    queries and mutations.
    """

    wait_time = between(1, 5)

    @task(3)
    def list_items(self):
        """Sample query: fetch a list of items."""
        query = """
        query ListItems {
            items {
                id
                name
                price
            }
        }
        """
        response = self.query(query)
        if response.errors:
            self.environment.runner.quit()
        response.data  # noqa: B018 — consume data

    @task(1)
    def get_item_detail(self):
        """Sample query: fetch a single item by ID."""
        query = """
        query GetItem($id: ID!) {
            item(id: $id) {
                id
                name
                description
            }
        }
        """
        response = self.query(query, variables={"id": 1})
        if response.errors:
            self.environment.runner.quit()
        response.data  # noqa: B018 — consume data


if __name__ == "__main__":
    print("Run with: locust -f examples/graphql_load_test.py")
