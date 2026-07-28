"""Pre-development tests for multi-protocol example files (TDD red phase).

Interface tests verify the example files exist, compile, and have
correct class inheritance (must pass immediately).
Behavioral tests define the expected structure of rewritten examples
and raise NotImplementedError until those behaviors are implemented.

Run: pytest tests/unit/test_examples.py -v
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


#

# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestInterfaceSmoke:
    """Verify example files exist, compile, and have correct inheritance."""

    # ── Compile checks ────────────────────────────────────────

    def test_grpc_example_compiles(self):
        """examples/grpc_load_test.py must parse as valid Python."""
        path = REPO_ROOT / "examples" / "grpc_load_test.py"
        assert path.exists(), f"File not found: {path}"
        source = path.read_bytes()
        compile(source, str(path), "exec")  # raises SyntaxError if invalid

    def test_graphql_example_compiles(self):
        """examples/graphql_load_test.py must parse as valid Python."""
        path = REPO_ROOT / "examples" / "graphql_load_test.py"
        assert path.exists(), f"File not found: {path}"
        source = path.read_bytes()
        compile(source, str(path), "exec")

    def test_websocket_example_compiles(self):
        """examples/websocket_load_test.py must parse as valid Python."""
        path = REPO_ROOT / "examples" / "websocket_load_test.py"
        assert path.exists(), f"File not found: {path}"
        source = path.read_bytes()
        compile(source, str(path), "exec")

    # ── Inheritance checks ────────────────────────────────────

    def test_grpc_example_inherits_grpc_user(self):
        """ExampleGrpcUser must inherit from GrpcUser."""
        from examples.grpc_load_test import (
            ExampleGrpcUser,  # type: ignore[import-untyped]
        )
        from locust_templates.grpc import GrpcUser

        assert issubclass(ExampleGrpcUser, GrpcUser), (
            "ExampleGrpcUser must inherit from GrpcUser"
        )

    def test_graphql_example_inherits_graphql_user(self):
        """ExampleGraphQLUser must inherit from GraphQLUser."""
        from examples.graphql_load_test import (
            ExampleGraphQLUser,  # type: ignore[import-untyped]
        )
        from locust_templates.graphql import GraphQLUser

        assert issubclass(ExampleGraphQLUser, GraphQLUser), (
            "ExampleGraphQLUser must inherit from GraphQLUser"
        )

    def test_websocket_example_inherits_websocket_user(self):
        """ExampleWebSocketUser must inherit from WebSocketUser."""
        from examples.websocket_load_test import (
            ExampleWebSocketUser,  # type: ignore[import-untyped]
        )
        from locust_templates.websocket import WebSocketUser

        assert issubclass(ExampleWebSocketUser, WebSocketUser), (
            "ExampleWebSocketUser must inherit from WebSocketUser"
        )


# ──────────────────────────────────────────────────────────────
# Behavioral tests — example class structure & capabilities
# ──────────────────────────────────────────────────────────────


class TestExampleGrpcBehavior:
    """Behavioral tests for the gRPC example (GREEN phase).

    Verifies that the rewritten example has the required task methods,
    lifecycle hooks, and importability.
    """

    def test_has_at_least_2_task_methods(self):
        """ExampleGrpcUser must have at least 2 @task-decorated methods."""
        from examples.grpc_load_test import ExampleGrpcUser

        task_methods = [
            m
            for m in dir(ExampleGrpcUser)
            if callable(getattr(ExampleGrpcUser, m, None))
            and not m.startswith("_")
        ]
        assert len(task_methods) >= 2, (
            f"Found {len(task_methods)} callable methods, expected >= 2"
        )

    def test_on_start_defined_or_inherited(self):
        """ExampleGrpcUser must have an on_start method (own or inherited)."""
        from examples.grpc_load_test import ExampleGrpcUser

        assert hasattr(ExampleGrpcUser, "on_start"), (
            "ExampleGrpcUser must have on_start method"
        )
        assert callable(ExampleGrpcUser.on_start), (
            "ExampleGrpcUser.on_start must be callable"
        )

    def test_import_does_not_raise_not_implemented(self):
        """Importing grpc_load_test must NOT raise NotImplementedError."""
        from examples.grpc_load_test import ExampleGrpcUser  # noqa: F811

        assert ExampleGrpcUser is not None, (
            "ExampleGrpcUser must be importable without raising NotImplementedError"
        )


class TestExampleGraphQLBehavior:
    """Behavioral tests for the GraphQL example (GREEN phase)."""

    def test_has_at_least_2_task_methods(self):
        """ExampleGraphQLUser must have at least 2 @task-decorated methods."""
        from examples.graphql_load_test import ExampleGraphQLUser

        task_methods = [
            m
            for m in dir(ExampleGraphQLUser)
            if callable(getattr(ExampleGraphQLUser, m, None))
            and not m.startswith("_")
        ]
        assert len(task_methods) >= 2, (
            f"Found {len(task_methods)} callable methods, expected >= 2"
        )

    def test_on_start_inherited(self):
        """ExampleGraphQLUser must inherit on_start from GraphQLUser/HttpUser."""
        from examples.graphql_load_test import ExampleGraphQLUser

        assert hasattr(ExampleGraphQLUser, "on_start"), (
            "ExampleGraphQLUser must have on_start (inherited from HttpUser)"
        )
        assert callable(ExampleGraphQLUser.on_start), (
            "ExampleGraphQLUser.on_start must be callable"
        )

    def test_uses_query_with_variables(self):
        """ExampleGraphQLUser must use self.query() helper with variables."""
        from examples.graphql_load_test import ExampleGraphQLUser

        assert hasattr(ExampleGraphQLUser, "query"), (
            "ExampleGraphQLUser must have access to query() method"
        )
        import inspect

        found_variables = False
        for name in dir(ExampleGraphQLUser):
            if name.startswith("_"):
                continue
            method = getattr(ExampleGraphQLUser, name)
            if callable(method):
                try:
                    source = inspect.getsource(method)
                    if "self.query(" in source and ("variables" in source):
                        found_variables = True
                        break
                except (OSError, TypeError):
                    pass
        assert found_variables, (
            "No task method found that calls self.query() with a variables argument"
        )


class TestExampleWebSocketBehavior:
    """Behavioral tests for the WebSocket example (GREEN phase)."""

    def test_has_at_least_2_task_methods(self):
        """ExampleWebSocketUser must have at least 2 @task-decorated methods."""
        from examples.websocket_load_test import ExampleWebSocketUser

        task_methods = [
            m
            for m in dir(ExampleWebSocketUser)
            if callable(getattr(ExampleWebSocketUser, m, None))
            and not m.startswith("_")
        ]
        assert len(task_methods) >= 2, (
            f"Found {len(task_methods)} callable methods, expected >= 2"
        )

    def test_on_start_defined(self):
        """ExampleWebSocketUser must define an on_start method."""
        from examples.websocket_load_test import ExampleWebSocketUser

        assert hasattr(ExampleWebSocketUser, "on_start"), (
            "ExampleWebSocketUser must have on_start method"
        )
        assert callable(ExampleWebSocketUser.on_start), (
            "ExampleWebSocketUser.on_start must be callable"
        )
        import inspect

        source = inspect.getsource(ExampleWebSocketUser.on_start)
        assert "self.connect(" in source or "self.conn_id" in source, (
            "ExampleWebSocketUser.on_start must open a WebSocket connection"
        )

    def test_demonstrates_connect_send_receive_lifecycle(self):
        """ExampleWebSocketUser must demonstrate connect/send/receive lifecycle."""
        from examples.websocket_load_test import ExampleWebSocketUser

        assert hasattr(ExampleWebSocketUser, "connect"), (
            "WebSocket example must reference connect"
        )
        assert hasattr(ExampleWebSocketUser, "send"), (
            "WebSocket example must reference send"
        )
        assert hasattr(ExampleWebSocketUser, "receive"), (
            "WebSocket example must reference receive"
        )
        import inspect

        for name in dir(ExampleWebSocketUser):
            if name.startswith("_"):
                continue
            method = getattr(ExampleWebSocketUser, name)
            if callable(method):
                try:
                    source = inspect.getsource(method)
                    if "self.send(" in source or "self.receive(" in source:
                        assert "self.send(" in source or "self.receive(" in source
                except (OSError, TypeError):
                    pass
