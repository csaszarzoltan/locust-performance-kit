# GraphQL Benchmarking Guide

> Load-test GraphQL APIs using the `GraphQLUser` template, part of the
> [Multi-Protocol Templates](../README.md#multi-protocol-templates-v140) (v1.4.0+).

## Overview

GraphQL is a query language for APIs that lets clients request exactly the
fields they need. Performance testing GraphQL endpoints presents unique
challenges compared to REST:

- **Query complexity varies** — a single endpoint handles simple field fetches
  and deeply nested joins with very different server costs.
- **Over-fetching risk** — clients can request large nested responses that
  degrade performance.
- **No standard caching** — most GraphQL responses are POST-based and don't
  benefit from HTTP caching layers.

`GraphQLUser` extends Locust's `HttpUser` and provides:

- **`self.query()`** — a convenience method that sends POST requests with
  the correct JSON body and parses the response into a typed dataclass.
- **`GraphQLResponse`** — structured result with `data`, `errors`,
  `status_code`, and `response_time_ms`.
- **`QueryComplexityAnalyzer`** — a heuristic query-complexity scorer you can
  use to reject or warn on expensive queries before they run.
- **Auth integration** — plugs into the same authenticator system used by
  `APIUser`.

No extra dependencies are needed — `GraphQLUser` uses the existing `HttpUser`
infrastructure.

## Quick Start

Subclass `GraphQLUser`, set the `graphql_endpoint`, and write `@task`-decorated
methods that call `self.query()`.

```python
from locust import between, task
from locust_templates.graphql import GraphQLUser


class StorefrontUser(GraphQLUser):
    wait_time = between(1, 5)
    graphql_endpoint = "/graphql"

    @task(3)
    def list_products(self):
        """Fetch a list of products."""
        query = """
        query ListProducts {
            products {
                id
                name
                price
                inStock
            }
        }
        """
        response = self.query(query)
        if response.errors:
            self.environment.runner.quit()

    @task(1)
    def get_product(self):
        """Fetch a single product by ID using variables."""
        query = """
        query GetProduct($id: ID!) {
            product(id: $id) {
                id
                name
                description
                reviews { rating comment }
            }
        }
        """
        response = self.query(query, variables={"id": "prod-42"})
        if response.errors:
            self.environment.runner.quit()
```

Run it:

```bash
locust -f storefront_test.py --users 50 --spawn-rate 5 --run-time 5m \
  --host https://api.example.com
```

## API Reference

### `GraphQLUser`

Base class: `locust.HttpUser`

| Attribute / Method                                     | Description                                                              |
|--------------------------------------------------------|--------------------------------------------------------------------------|
| `graphql_endpoint`                                     | GraphQL endpoint path (default `/graphql` or `LOCUST_GRAPHQL_ENDPOINT`). |
| `complexity_threshold`                                 | Max query complexity before the request is rejected (default `0` = off). |
| `auth_provider`                                        | Authenticator provider name (default `"env"`).                           |
| `auth_kwargs`                                          | Keyword arguments passed to the authenticator.                           |
| `query(query_str, variables=None, operation_name=None)` | Execute a GraphQL query. Returns a `GraphQLResponse`.                    |

**`query(query_str, variables=None, operation_name=None)`** → `GraphQLResponse`

- `query_str` — the GraphQL query or mutation string.
- `variables` — optional dict of variable values (e.g. `{"id": "abc"}`).
- `operation_name` — optional name for named queries with multiple operations.
- Raises `ValueError` when `complexity_threshold > 0` and the computed
  complexity exceeds the threshold (pre-flight check).
- Fires a standard Locust HTTP request event through the `HttpUser.client`.
- If the response contains GraphQL-level `errors`, the request is marked as a
  failure in Locust stats (via `resp.failure()`).

### `GraphQLResponse`

```python
@dataclass
class GraphQLResponse:
    data: dict[str, Any] | None = None
    errors: list[dict[str, Any]] | None = None
    status_code: int = 200
    response_time_ms: float = 0.0
```

| Field              | Type                   | Description                                    |
|--------------------|------------------------|------------------------------------------------|
| `data`             | `dict \| None`         | The `"data"` key from the GraphQL response.    |
| `errors`           | `list[dict] \| None`   | The `"errors"` key from the GraphQL response.  |
| `status_code`      | `int`                  | HTTP status code (e.g. 200, 400).              |
| `response_time_ms` | `float`                | Elapsed wall-clock time in milliseconds.       |

### `QueryComplexityAnalyzer`

A static-method-based utility that computes a heuristic complexity score for a
GraphQL query string.

```python
from locust_templates.graphql import QueryComplexityAnalyzer

score = QueryComplexityAnalyzer.score_query(
    "{ hero { name friends { name } } }"
)
# → 5  (see scoring formula below)
```

| Method                                                                 | Description                                          |
|------------------------------------------------------------------------|------------------------------------------------------|
| `score_query(query_str, field_weights=None)`                            | Compute the complexity score for a query string.     |

#### How Complexity Scoring Works

The score is calculated as:

```
score = Σ (field_weight × depth_multiplier)
```

Where:

- **`field_weight`** defaults to **1** for every field, but can be overridden
  per field name via the `field_weights` dict.
- **`depth_multiplier`** = `2 ** (depth - 1)`, where the root selection set
  has `depth = 1`.

Example — query `{ hero { name friends { name } } }`:

```
hero    (depth 1)  → 1 × 2⁰ = 1
  name  (depth 2)  → 1 × 2¹ = 2
  friends (depth 2) → 1 × 2¹ = 2
    name (depth 3) → 1 × 2² = 4
                         Total = 9
```

With per-field weights:

```python
QueryComplexityAnalyzer.score_query(
    "{ hero { name friends { name } } }",
    field_weights={"name": 0, "friends": 5},
)
# → hero(1) + name(0) + friends(10) + name(0) = 11
```

The analyzer uses a lightweight heuristic parser (not a full GraphQL AST
parser), so it handles common patterns correctly but may not cover every edge
case — use it as a guard, not a security boundary.

## Configuration

### Environment Variables

| Variable                                | Default      | Description                                           |
|-----------------------------------------|--------------|-------------------------------------------------------|
| `LOCUST_GRAPHQL_ENDPOINT`               | `/graphql`   | Default `graphql_endpoint` for all `GraphQLUser` subclasses. |
| `LOCUST_GRAPHQL_COMPLEXITY_THRESHOLD`   | `0`          | Max allowed complexity score (`0` = no limit).        |

You can override the endpoint and threshold per subclass:

```python
class AdminUser(GraphQLUser):
    graphql_endpoint = "/admin/graphql"
    complexity_threshold = 50
```

## Full Working Example

A complete load test for a fictional e-commerce GraphQL API:

```python
"""GraphQL load test for an e-commerce storefront."""

from locust import between, task
from locust_templates.graphql import GraphQLUser, QueryComplexityAnalyzer


class EcommerceUser(GraphQLUser):
    wait_time = between(1, 4)
    graphql_endpoint = "/graphql"
    complexity_threshold = 100

    @task(5)
    def homepage_query(self):
        """Fetch the product catalogue (low complexity)."""
        query = """
        query Homepage {
            featuredProducts { id name price }
            categories { id name productCount }
        }
        """
        response = self.query(query)
        if response.errors:
            self.environment.runner.quit()

    @task(2)
    def product_detail(self):
        """Fetch a product with nested reviews (medium complexity)."""
        query = """
        query ProductDetail($id: ID!) {
            product(id: $id) {
                id name description price
                reviews(limit: 10) {
                    id rating
                    author { id displayName }
                    comment
                }
            }
        }
        """
        response = self.query(query, variables={"id": "prod-" + str(self._next_id())})
        data = response.data
        if data and data.get("product"):
            reviews = data["product"].get("reviews", [])
            print(f"Fetched {len(reviews)} reviews")  # noqa: T201

    @task(1)
    def complex_report(self):
        """Admin-style query that may hit the complexity threshold."""
        query = """
        query SalesReport($year: Int!) {
            sales(year: $year) {
                total
                byRegion { region total }
                byCategory {
                    category
                    products { id name unitsSold revenue }
                }
            }
        }
        """
        # Pre-flight complexity check (run-time, not just threshold guard)
        score = QueryComplexityAnalyzer.score_query(query)
        if score > self.complexity_threshold:
            print(f"Skipping complex report (score={score})")  # noqa: T201
            return

        response = self.query(query, variables={"year": 2026})
        if response.errors:
            self.environment.runner.quit()

    def _next_id(self):
        """Simple round-robin product id for demo purposes."""
        return hash(str(self)) % 1000 + 1
```

Run with:

```bash
locust -f ecommerce_test.py --users 30 --spawn-rate 3 --run-time 10m \
  --host https://shop.example.com
```

## Best Practices

1. **Use named queries.** Always give your queries an operation name (e.g.
   `query ListProducts`). It makes Locust stats easier to read and helps
   with debugging.
2. **Set a complexity threshold.** Start with `complexity_threshold=100` and
   adjust based on observed server performance. Queries that exceed the
   threshold are rejected before they reach the server, preventing cascading
   slowdowns.
3. **Weight tasks by query cost.** Give lightweight queries (simple field
   fetches) higher `@task` weights and expensive admin queries lower weights,
   matching realistic traffic patterns.
4. **Monitor `response.errors`.** GraphQL returns HTTP 200 even when the
   query fails semantically. Always check `response.errors` to catch resolver
   failures, rate-limiting, and validation errors in your test metrics.
5. **Vary variables.** Repeating the same `variables={"id": "abc"}` hits the
   dataloader cache. Rotate through a realistic set of IDs to measure
   uncached performance.
6. **Test mutations separately.** Mutations often have side effects (writes,
   billing). Use a dedicated `GraphQLUser` subclass or a separate test plan
   for write-heavy workloads.
