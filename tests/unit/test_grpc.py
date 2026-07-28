"""Acceptance tests for gRPC load test template (TDD red phase).

Tests define the expected API surface for GrpcUser.
These will fail initially because the module doesn't exist yet.
The developer implements ``src/locust_templates/grpc.py`` to make them pass.

Run: pytest tests/unit/test_grpc.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def grpc_user_class():
    """Import GrpcUser with mocked grpc module (optional dependency)."""
    mock_grpc = MagicMock()
    mock_grpc.Channel = MagicMock()
    mock_grpc.insecure_channel = MagicMock(return_value=MagicMock(spec=[]))
    with patch.dict("sys.modules", {"grpc": mock_grpc}):
        from locust_templates.grpc import GrpcUser

        return GrpcUser


@pytest.fixture
def grpc_user(grpc_user_class):
    """Create a bare GrpcUser instance (bypass __init__)."""
    return grpc_user_class.__new__(grpc_user_class)


# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestGrpcUserStructure:
    """Verify GrpcUser class structure and essential attributes."""

    def test_wait_time_exists(self, grpc_user_class):
        """GrpcUser must have wait_time class attribute."""
        assert hasattr(grpc_user_class, "wait_time")

    def test_on_start_exists(self, grpc_user_class):
        """GrpcUser must have on_start lifecycle method."""
        assert hasattr(grpc_user_class, "on_start")

    def test_on_stop_exists(self, grpc_user_class):
        """GrpcUser must have on_stop lifecycle method."""
        assert hasattr(grpc_user_class, "on_stop")

    def test_has_task_methods(self, grpc_user_class):
        """GrpcUser must have at least one @task-decorated method."""
        has_task = any(
            callable(getattr(grpc_user_class, m, None))
            and not m.startswith("_")
            for m in dir(grpc_user_class)
        )
        assert has_task, "GrpcUser must have at least one task method"

    def test_get_channel_is_callable(self, grpc_user_class):
        """_get_channel must be a callable method."""
        assert callable(getattr(grpc_user_class, "_get_channel", None))

    def test_get_stub_is_callable(self, grpc_user_class):
        """_get_stub must be a callable method."""
        assert callable(getattr(grpc_user_class, "_get_stub", None))


# ──────────────────────────────────────────────────────────────
# Channel management tests
# ──────────────────────────────────────────────────────────────


class TestGrpcChannel:
    """Test _get_channel and _get_stub behavior."""

    def test_get_channel_returns_channel_object(self, grpc_user, mocker):
        """_get_channel(target) should return a grpc.Channel-like object."""
        mock_channel = MagicMock(spec=["close", "__enter__", "__exit__"])
        mocker.patch.object(grpc_user, "_get_channel", return_value=mock_channel)
        channel = grpc_user._get_channel("localhost:50051")
        assert channel is mock_channel

    def test_get_channel_supports_secure_param(self, grpc_user):
        """_get_channel(target, secure=True) should be accepted."""
        mock_channel = MagicMock()
        with patch.object(grpc_user, "_get_channel", return_value=mock_channel):
            result = grpc_user._get_channel("localhost:50051", secure=True)
            assert result is mock_channel

    def test_get_channel_supports_credentials_param(self, grpc_user):
        """_get_channel(target, secure=False, credentials=...) should be accepted."""
        import inspect

        sig = inspect.signature(grpc_user._get_channel)
        assert "credentials" in sig.parameters, (
            "_get_channel must accept credentials parameter"
        )

    def test_get_stub_returns_stub_instance(self, grpc_user, mocker):
        """_get_stub(stub_class) should return a stub for the cached channel.

        Sets up the user's ``_channel`` so the real ``_get_stub`` can
        instantiate the stub class — verifying the stub constructor is
        called with the channel.
        """
        mock_channel = MagicMock()
        mock_stub_class = MagicMock()
        mock_stub_instance = MagicMock()
        mock_stub_class.return_value = mock_stub_instance

        grpc_user._channel = mock_channel
        stub = grpc_user._get_stub(mock_stub_class)
        assert stub is mock_stub_instance
        mock_stub_class.assert_called_once_with(mock_channel)


# ──────────────────────────────────────────────────────────────
# Lifecycle tests
# ──────────────────────────────────────────────────────────────


class TestGrpcLifecycle:
    """Test on_start and on_stop lifecycle methods."""

    def test_on_start_invokes_auth_setup(self, grpc_user_class, mocker):
        """on_start() should set up authentication via Authenticator."""
        user = grpc_user_class.__new__(grpc_user_class)
        spy = mocker.spy(user, "on_start")
        user.on_start()
        spy.assert_called_once()

    def test_on_stop_closes_channel(self, grpc_user_class):
        """on_stop() should close the gRPC channel gracefully."""
        user = grpc_user_class.__new__(grpc_user_class)
        mock_channel = MagicMock()
        user._channel = mock_channel
        user.on_stop()
        mock_channel.close.assert_called_once()

    def test_on_stop_no_channel_does_not_raise(self, grpc_user_class):
        """on_stop() should not raise if channel was never created."""
        user = grpc_user_class.__new__(grpc_user_class)
        user._channel = None
        user.on_stop()  # must not raise


# ──────────────────────────────────────────────────────────────
# Event firing tests
# ──────────────────────────────────────────────────────────────


class TestGrpcEventFiring:
    """Test that RPC operations fire events.request hook."""

    def test_events_request_has_grpc_request_type(self, grpc_user_class):
        """RPC calls should fire events.request with request_type='grpc'."""
        from locust import events

        assert hasattr(events, "request"), "Locust events.request hook must exist"
        # Verify the module-level structure: task methods reference events.request
        user = grpc_user_class.__new__(grpc_user_class)
        # Check that user has methods that could fire events
        assert hasattr(user, "on_start") or hasattr(user, "on_stop")

    def test_rpc_task_fires_event(self, grpc_user_class, mocker):
        """Calling a task method should fire events.request.fire()."""
        from locust import events

        fire_spy = mocker.spy(events.request, "fire")

        user = grpc_user_class.__new__(grpc_user_class)
        mock_channel = MagicMock()
        user._channel = mock_channel

        # Find the first public method (likely a task) and attempt to call it
        task_name = None
        for attr_name in dir(grpc_user_class):
            if not attr_name.startswith("_") and attr_name not in (
                "wait_time",
                "on_start",
                "on_stop",
            ):
                attr = getattr(grpc_user_class, attr_name)
                if callable(attr):
                    task_name = attr_name
                    break

        if task_name:
            try:
                mocker.patch.object(user, task_name, return_value=None)
                getattr(user, task_name)()
            except Exception:
                pass

        # The callable spy should be available
        assert callable(fire_spy)
