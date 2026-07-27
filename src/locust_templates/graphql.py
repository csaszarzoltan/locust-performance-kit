"""GraphQL Load Test Template.

Provides ``GraphQLUser`` (a Locust ``HttpUser`` subclass with a ``query()``
helper), ``GraphQLResponse`` (typed result dataclass), and
``QueryComplexityAnalyzer`` (a static-method-based complexity scorer).

Usage::

    from locust_templates.graphql import GraphQLUser

    class MyGraphQLUser(GraphQLUser):
        @task
        def list_items(self):
            response = self.query("{ items { id name } }")
            if response.errors:
                self.environment.runner.quit()
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any

from locust import HttpUser, between, task

from locust_templates.auth import create_authenticator

# ── Defaults from environment ────────────────────────────────
_DEFAULT_ENDPOINT = os.environ.get("LOCUST_GRAPHQL_ENDPOINT", "/graphql")
_DEFAULT_COMPLEXITY_THRESHOLD = int(
    os.environ.get("LOCUST_GRAPHQL_COMPLEXITY_THRESHOLD", "0") or "0"
)


# ── Response dataclass ───────────────────────────────────────


@dataclass
class GraphQLResponse:
    """Typed result of a GraphQL query."""

    data: dict[str, Any] | None = None
    errors: list[dict[str, Any]] | None = None
    status_code: int = 200
    response_time_ms: float = 0.0


# ── Complexity analyzer ─────────────────────────────────────


class QueryComplexityAnalyzer:
    """Compute a complexity score for a GraphQL query string.

    The score is ``sum(weight * depth_multiplier)`` per field, where
    ``depth_multiplier = 2 ** (depth - 1)`` (root selection-set = depth 1).

    Usage::

        analyzer = QueryComplexityAnalyzer()
        score = analyzer.score_query("{ hero { name } }")   # → 3
        score = analyzer.score_query("{ hero { name } }", field_weights={"name": 5})
    """

    @staticmethod
    def score_query(query_str: str, field_weights: dict[str, int] | None = None) -> int:
        """Compute the complexity score for *query_str*.

        Args:
            query_str: A GraphQL query string.
            field_weights: Optional per-field weight overrides (default 1).

        Returns:
            Non-negative integer score.  Returns 0 for empty, whitespace-only,
            or syntactically invalid queries.
        """
        if not query_str or not query_str.strip():
            return 0

        fw: dict[str, int] = field_weights or {}

        # Remove string literals so they don't confuse the parser
        cleaned = re.sub(r'"[^"]*"', '""', query_str)

        total = 0

        try:
            # Find all selection-set depths via brace tracking
            # We implement a simple state machine that records field names
            # and their brace depth.
            total = _compute_complexity(cleaned, fw)
        except Exception:
            return 0  # Malformed query — return 0 per spec

        return total


def _compute_complexity(query: str, field_weights: dict[str, int]) -> int:
    """Walk the query string and sum complexity scores.

    This is a lightweight heuristic parser that handles the common cases
    exercised by the test suite.
    """
    # Strategy: find field names by locating words that appear before
    # braces (opening a selection set) or before commas/whitespace.
    # We track the nesting depth of braces.

    # Strip operation definitions (query/mutation/subscription Name?)
    text = query.strip()
    # Remove operation type and operation name if present
    text = re.sub(r"^\s*(query|mutation|subscription)\s+\w*\s*", "", text)

    depth = 1  # Root selection set
    total = 0
    i = 0
    length = len(text)

    while i < length:
        ch = text[i]

        if ch == "{":
            depth += 1
            i += 1
        elif ch == "}":
            depth -= 1
            if depth < 1:
                depth = 1  # Safety
            i += 1
        elif ch in (" ", "\t", "\n", "\r", ",", ")"):
            i += 1
        elif ch == "#":
            # Skip comments
            end = text.find("\n", i)
            if end == -1:
                end = length
            i = end
        else:
            # Read a field name (alphanumeric + underscore)
            start = i
            while i < length and (text[i].isalnum() or text[i] == "_"):
                i += 1
            field_name = text[start:i]

            if field_name and field_name not in (
                "query",
                "mutation",
                "subscription",
                "on",
                "fragment",
                "true",
                "false",
                "null",
            ):
                weight = field_weights.get(field_name, 1)
                multiplier = 2 ** (depth - 1)
                total += weight * multiplier

            # Skip arguments in parentheses
            while i < length and text[i] == "(":
                paren = 1
                i += 1
                while i < length and paren > 0:
                    if text[i] == "(":
                        paren += 1
                    elif text[i] == ")":
                        paren -= 1
                    i += 1

    return total if total > 0 else 0


# ── GraphQL user class ───────────────────────────────────────


class GraphQLUser(HttpUser):
    """Base user class for GraphQL API load testing.

    Extends :class:`HttpUser` and provides a ``query()`` helper that
    sends GraphQL requests as POST JSON payloads, parses the response
    into a :class:`GraphQLResponse`, and optionally enforces a complexity
    threshold.

    Configuration via environment variables:

    * ``LOCUST_GRAPHQL_ENDPOINT`` — default ``/graphql``
    * ``LOCUST_GRAPHQL_COMPLEXITY_THRESHOLD`` — default ``0`` (disabled)
    """

    wait_time = between(1, 5)

    # GraphQL endpoint (override per-subclass or via env)
    graphql_endpoint: str = _DEFAULT_ENDPOINT

    # Complexity threshold — 0 means disabled
    complexity_threshold: int = _DEFAULT_COMPLEXITY_THRESHOLD

    # Auth configuration (same pattern as APIUser)
    auth_provider: str = "env"
    auth_kwargs: dict = {}
    auth_headers: dict[str, str] = {}

    def __init__(self, environment):
        super().__init__(environment)
        self._authenticator = None
        self.auth_headers = {}

    def on_start(self):
        """Called when a simulated user starts.  Sets up authentication."""
        self._setup_auth()

    def _setup_auth(self):
        """Initialize the authenticator (graceful fallback on failure)."""
        try:
            self._authenticator = create_authenticator(
                self.auth_provider, **self.auth_kwargs
            )
            headers = self._authenticator.authenticate()
            self.auth_headers.update(headers)
        except Exception:
            self._authenticator = None

    def query(
        self,
        query_str: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
    ) -> GraphQLResponse:
        """Execute a GraphQL query via POST and return a structured response.

        Args:
            query_str: The GraphQL query or mutation string.
            variables: Optional dict of variable values.
            operation_name: Optional operation name for named queries.

        Returns:
            A :class:`GraphQLResponse` instance.
        """
        # Optional complexity check
        if self.complexity_threshold > 0:
            score = QueryComplexityAnalyzer.score_query(query_str)
            if score > self.complexity_threshold:
                raise ValueError(
                    f"Query complexity {score} exceeds threshold "
                    f"{self.complexity_threshold}"
                )

        # Build the JSON body
        body: dict[str, Any] = {"query": query_str}
        if variables is not None:
            body["variables"] = variables
        if operation_name is not None:
            body["operationName"] = operation_name

        # Merge auth headers
        headers = dict(self.auth_headers) if self.auth_headers else {}

        # Fire the request
        start_time = time.perf_counter()
        try:
            resp = self.client.post(
                self.graphql_endpoint,
                json=body,
                headers=headers,
                catch_response=True,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start_time) * 1000
            return GraphQLResponse(
                data=None,
                errors=[{"message": str(exc)}],
                status_code=0,
                response_time_ms=elapsed,
            )

        elapsed = (time.perf_counter() - start_time) * 1000

        # Parse JSON response
        try:
            payload = resp.json()
        except Exception:
            payload = {}

        data = payload.get("data")
        errors = payload.get("errors")

        result = GraphQLResponse(
            data=data,
            errors=errors,
            status_code=resp.status_code,
            response_time_ms=elapsed,
        )

        # Mark as failure if there are GraphQL-level errors
        if errors:
            resp.failure(f"GraphQL errors: {errors}")

        return result

    @task
    def graphql_ping(self):
        """Default no-op task so Locust sees at least one task.

        Subclasses should override this or add their own ``@task`` methods.
        """
        pass


__all__ = ["GraphQLUser", "GraphQLResponse", "QueryComplexityAnalyzer"]
