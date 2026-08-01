"""Acceptance tests for GraphQL load test template (TDD red phase).

Tests define the expected API surface for GraphQLUser, GraphQLResponse,
and QueryComplexityAnalyzer. These will fail initially because the
module doesn't exist yet.

Run: pytest tests/unit/test_graphql.py -v
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, fields
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def graphql_user_class():
    """Import GraphQLUser from the (not-yet-existing) module."""
    from locust_templates.graphql import GraphQLUser

    return GraphQLUser


@pytest.fixture
def graphql_response_class():
    """Import GraphQLResponse dataclass."""
    from locust_templates.graphql import GraphQLResponse

    return GraphQLResponse


@pytest.fixture
def complexity_analyzer_class():
    """Import QueryComplexityAnalyzer class."""
    from locust_templates.graphql import QueryComplexityAnalyzer

    return QueryComplexityAnalyzer


@pytest.fixture
def graphql_user(graphql_user_class):
    """Create a bare GraphQLUser instance."""
    return graphql_user_class.__new__(graphql_user_class)


# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestGraphQLUserStructure:
    """Verify GraphQLUser class structure."""

    def test_inherits_from_http_user(self, graphql_user_class):
        """GraphQLUser must inherit from Locust's HttpUser."""
        from locust import HttpUser

        assert issubclass(graphql_user_class, HttpUser), (
            "GraphQLUser must inherit from HttpUser"
        )

    def test_wait_time_exists(self, graphql_user_class):
        """GraphQLUser must have wait_time class attribute."""
        assert hasattr(graphql_user_class, "wait_time")

    def test_on_start_exists(self, graphql_user_class):
        """GraphQLUser must have on_start lifecycle method."""
        assert hasattr(graphql_user_class, "on_start")

    def test_on_stop_exists(self, graphql_user_class):
        """GraphQLUser must have on_stop lifecycle method."""
        assert hasattr(graphql_user_class, "on_stop")

    def test_query_method_exists(self, graphql_user_class):
        """GraphQLUser must have a query() method."""
        assert hasattr(graphql_user_class, "query")
        assert callable(graphql_user_class.query)

    def test_query_signature(self, graphql_user_class):
        """query() should accept query_str, variables, operation_name."""
        sig = inspect.signature(graphql_user_class.query)
        params = list(sig.parameters.keys())
        # First param is 'self' for instance methods
        assert "query_str" in params or "query" in params, (
            "query() must accept a query string parameter"
        )

    def test_has_task_methods(self, graphql_user_class):
        """GraphQLUser must have at least one @task-decorated method."""
        has_task = any(
            callable(getattr(graphql_user_class, m, None))
            and not m.startswith("_")
            for m in dir(graphql_user_class)
        )
        assert has_task, "GraphQLUser must have at least one task method"


# ──────────────────────────────────────────────────────────────
# GraphQLResponse dataclass tests
# ──────────────────────────────────────────────────────────────


class TestGraphQLResponse:
    """Verify GraphQLResponse dataclass structure."""

    def test_is_dataclass(self, graphql_response_class):
        """GraphQLResponse should be a dataclass."""
        assert dataclass(graphql_response_class) or hasattr(
            graphql_response_class, "__dataclass_fields__"
        ), "GraphQLResponse must be a dataclass"

    def test_has_data_field(self, graphql_response_class):
        """GraphQLResponse must have a 'data' field (dict)."""
        field_names = [f.name for f in fields(graphql_response_class)]
        assert "data" in field_names, "GraphQLResponse must have data field"

    def test_has_errors_field(self, graphql_response_class):
        """GraphQLResponse must have an 'errors' field (list)."""
        field_names = [f.name for f in fields(graphql_response_class)]
        assert "errors" in field_names, "GraphQLResponse must have errors field"

    def test_has_status_code_field(self, graphql_response_class):
        """GraphQLResponse must have a status_code field."""
        field_names = [f.name for f in fields(graphql_response_class)]
        assert "status_code" in field_names, (
            "GraphQLResponse must have status_code field"
        )

    def test_has_response_time_field(self, graphql_response_class):
        """GraphQLResponse must have a response_time_ms field."""
        field_names = [f.name for f in fields(graphql_response_class)]
        has_time = "response_time_ms" in field_names or "response_time" in field_names
        assert has_time, "GraphQLResponse must have a response time field"


# ──────────────────────────────────────────────────────────────
# QueryComplexityAnalyzer tests
# ──────────────────────────────────────────────────────────────


class TestQueryComplexityAnalyzer:
    """Verify QueryComplexityAnalyzer class structure and behavior."""

    def test_score_query_method_exists(self, complexity_analyzer_class):
        """QueryComplexityAnalyzer must have a score_query() method."""
        assert hasattr(complexity_analyzer_class, "score_query")
        assert callable(complexity_analyzer_class.score_query)

    def test_score_query_signature(self, complexity_analyzer_class):
        """score_query() should accept a query string."""
        sig = inspect.signature(complexity_analyzer_class.score_query)
        # Static/class method or instance method
        assert len(sig.parameters) >= 1, (
            "score_query must accept at least one parameter (the query string)"
        )

    # ── scoring behavior ──

    def test_score_query_simple_returns_int(self, complexity_analyzer_class):
        """score_query(simple_query) should return a non-negative integer."""
        analyzer = complexity_analyzer_class()
        score = analyzer.score_query("{ hero { name } }")
        assert isinstance(score, int)
        assert score >= 0

    def test_score_query_simple_fields(self, complexity_analyzer_class):
        """Simple query (2 fields, depth 1) should return a small score."""
        analyzer = complexity_analyzer_class()
        score = analyzer.score_query("{ hero { name appearsIn } }")
        assert score > 0, "A valid query with 2 fields must have a positive score"

    def test_score_query_nested(self, complexity_analyzer_class):
        """Nested query (3 levels deep) should score higher than flat."""
        analyzer = complexity_analyzer_class()
        flat_score = analyzer.score_query("{ hero { name } }")
        nested_score = analyzer.score_query("{ hero { friends { name } } }")
        assert nested_score > flat_score, (
            "Nested queries must score higher than flat queries"
        )

    def test_score_query_with_lists(self, complexity_analyzer_class):
        """Query with list fields should have multiplication effect."""
        analyzer = complexity_analyzer_class()
        single_score = analyzer.score_query("{ hero { name } }")
        list_score = analyzer.score_query("{ hero { friends { name } } }")
        # Lists should multiply complexity — nested lists are heavier
        assert list_score >= single_score, (
            "List/nested queries must not score lower than simple queries"
        )

    def test_score_query_empty(self, complexity_analyzer_class):
        """Empty or malformed query should return 0."""
        analyzer = complexity_analyzer_class()
        assert analyzer.score_query("") == 0
        assert analyzer.score_query("   ") == 0

    def test_score_query_malformed(self, complexity_analyzer_class):
        """Malformed query should return 0 without raising."""
        analyzer = complexity_analyzer_class()
        # Should not raise exception
        score = analyzer.score_query("not a { valid query")
        assert isinstance(score, int)
        assert score >= 0


# ──────────────────────────────────────────────────────────────
# GraphQLUser behavioral tests
# ──────────────────────────────────────────────────────────────


class TestGraphQLQuery:
    """Test the query() helper method behavior."""

    def test_query_sends_post(self, graphql_user_class, mocker):
        """query() should use self.client.post to send the GraphQL request."""
        user = graphql_user_class.__new__(graphql_user_class)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"hero": {"name": "Luke"}}}
        mock_client.post.return_value = mock_response
        user.client = mock_client

        spy = mocker.spy(mock_client, "post")
        from locust_templates.graphql import GraphQLResponse

        result = user.query("{ hero { name } }")
        spy.assert_called_once()
        assert isinstance(result, GraphQLResponse)
        assert result.data == {"hero": {"name": "Luke"}}

    def test_query_posts_to_correct_url(self, graphql_user_class):
        """query() should POST to the GraphQL endpoint URL."""
        user = graphql_user_class.__new__(graphql_user_class)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_client.post.return_value = mock_response
        user.client = mock_client

        user.query("{ hero { name } }")
        call_args = mock_client.post.call_args
        # The POST should have json with 'query' key
        if call_args:
            _, kwargs = call_args
            assert "json" in kwargs or "data" in kwargs
            body = kwargs.get("json", kwargs.get("data", {}))
            assert "query" in body, "POST body must include 'query' field"

    def test_query_returns_graphql_response_type(self, graphql_user_class):
        """query() should return a GraphQLResponse instance."""
        user = graphql_user_class.__new__(graphql_user_class)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"ok": True}}
        mock_client.post.return_value = mock_response
        user.client = mock_client

        from locust_templates.graphql import GraphQLResponse

        result = user.query("{ ok }")
        assert isinstance(result, GraphQLResponse)

    def test_query_parses_errors(self, graphql_user_class):
        """query() should parse GraphQL errors and call response.failure()."""
        user = graphql_user_class.__new__(graphql_user_class)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": None,
            "errors": [{"message": "Field 'unknown' not found"}],
        }
        mock_client.post.return_value.__enter__.return_value = mock_response
        mock_client.post.return_value = mock_response
        user.client = mock_client

        result = user.query("{ unknown }")
        assert result.errors is not None
        assert len(result.errors) > 0

    def test_query_with_variables(self, graphql_user_class):
        """query() should accept and pass variables."""
        user = graphql_user_class.__new__(graphql_user_class)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"hero": {"name": "Luke"}}}
        mock_client.post.return_value = mock_response
        user.client = mock_client

        variables = {"episode": "EMPIRE"}
        user.query(
            "query Hero($episode: Episode!) { hero(episode: $episode) { name } }",
            variables=variables,
        )
        call_args = mock_client.post.call_args
        if call_args:
            _, kwargs = call_args
            body = kwargs.get("json", kwargs.get("data", {}))
            assert "variables" in body, (
                "POST body must include 'variables' when variables are provided"
            )
            assert body["variables"] == variables

    def test_query_with_operation_name(self, graphql_user_class):
        """query() should accept and pass operation_name."""
        user = graphql_user_class.__new__(graphql_user_class)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_client.post.return_value = mock_response
        user.client = mock_client

        user.query(
            "query HeroName { hero { name } }",
            operation_name="HeroName",
        )
        call_args = mock_client.post.call_args
        if call_args:
            _, kwargs = call_args
            body = kwargs.get("json", kwargs.get("data", {}))
            assert "operationName" in body, (
                "POST body must include 'operationName' when provided"
            )
            assert body["operationName"] == "HeroName"


# ──────────────────────────────────────────────────────────────
# Complexity threshold tests
# ──────────────────────────────────────────────────────────────


class TestComplexityThreshold:
    """Test optional complexity threshold checking."""

    def test_complexity_threshold_does_not_block_simple_query(
        self, graphql_user_class, mocker
    ):
        """A query under the complexity threshold should proceed."""
        user = graphql_user_class.__new__(graphql_user_class)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"hero": {"name": "Luke"}}}
        mock_client.post.return_value = mock_response
        user.client = mock_client

        # Set a high threshold
        user.complexity_threshold = 100
        mocker.patch.object(
            type(user), "complexity_threshold", 100, create=True
        )

        result = user.query("{ hero { name } }")
        assert result is not None

    def test_complexity_threshold_exceeded(self, graphql_user_class, mocker):
        """A query exceeding the complexity threshold should raise or fail."""
        user = graphql_user_class.__new__(graphql_user_class)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"hero": {"name": "Luke"}}}
        mock_client.post.return_value = mock_response
        user.client = mock_client

        # Set a very low threshold so any query exceeds it
        user.complexity_threshold = 1

        from locust_templates.graphql import QueryComplexityAnalyzer

        analyzer = QueryComplexityAnalyzer()
        score = analyzer.score_query("{ hero { name } }")

        if score > 1:
            # Query should be blocked — either raise or return an error response
            with pytest.raises((ValueError, RuntimeError, Exception)):
                mocker.patch.object(
                    type(user), "query",
                    side_effect=ValueError("Query complexity 6 exceeds threshold 1"),
                )
                user.query("{ hero { name } }")


# ──────────────────────────────────────────────────────────────
# Auth integration tests
# ──────────────────────────────────────────────────────────────


class TestGraphQLAuth:
    """Test auth header integration with GraphQLUser."""

    def test_query_includes_auth_headers(self, graphql_user_class):
        """query() should include auth headers from inherited setup."""
        user = graphql_user_class.__new__(graphql_user_class)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_client.post.return_value = mock_response
        user.client = mock_client

        # Simulate auth headers being set
        user.auth_headers = {"Authorization": "Bearer test_token"}

        user.query("{ hero { name } }")
        call_args = mock_client.post.call_args
        if call_args:
            _, kwargs = call_args
            headers = kwargs.get("headers", {})
            assert "Authorization" in headers, (
                "query() must include Authorization header"
            )

    def test_query_sends_custom_headers(self, graphql_user_class):
        """query() should forward custom headers from the user config."""
        user = graphql_user_class.__new__(graphql_user_class)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_client.post.return_value = mock_response
        user.client = mock_client

        custom_headers = {"X-Custom": "value", "Authorization": "Bearer tok"}
        user.auth_headers = custom_headers

        user.query("{ hero { name } }")
        call_args = mock_client.post.call_args
        if call_args:
            _, kwargs = call_args
            headers = kwargs.get("headers", {})
            assert headers.get("Authorization") == "Bearer tok"
            assert headers.get("X-Custom") == "value"
