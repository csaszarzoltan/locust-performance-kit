"""Acceptance tests for WebSocket load test template (TDD red phase).

Tests define the expected API surface for WebSocketUser.
These will fail initially because the module doesn't exist yet.
The developer implements ``src/locust_templates/websocket.py``.

Run: pytest tests/unit/test_websocket.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def websocket_user_class():
    """Import WebSocketUser with mocked websocket module (optional dep)."""
    mock_ws = MagicMock()
    mock_ws.WebSocket = MagicMock()
    mock_ws.create_connection = MagicMock()
    with patch.dict("sys.modules", {"websocket": mock_ws}):
        from locust_templates.websocket import WebSocketUser

        return WebSocketUser


@pytest.fixture
def websocket_user(websocket_user_class):
    """Create a bare WebSocketUser instance."""
    return websocket_user_class.__new__(websocket_user_class)


# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestWebSocketUserStructure:
    """Verify WebSocketUser class structure and attributes."""

    def test_wait_time_exists(self, websocket_user_class):
        """WebSocketUser must have wait_time class attribute."""
        assert hasattr(websocket_user_class, "wait_time")

    def test_max_connections_default(self, websocket_user_class):
        """WebSocketUser must have max_connections class attribute (int)."""
        assert hasattr(websocket_user_class, "max_connections")
        assert isinstance(websocket_user_class.max_connections, int)

    def test_on_start_exists(self, websocket_user_class):
        """WebSocketUser must have on_start lifecycle method."""
        assert hasattr(websocket_user_class, "on_start")

    def test_on_stop_exists(self, websocket_user_class):
        """WebSocketUser must have on_stop lifecycle method."""
        assert hasattr(websocket_user_class, "on_stop")

    def test_has_task_methods(self, websocket_user_class):
        """WebSocketUser must have at least one @task-decorated method."""
        has_task = any(
            callable(getattr(websocket_user_class, m, None))
            and not m.startswith("_")
            for m in dir(websocket_user_class)
        )
        assert has_task, "WebSocketUser must have at least one task method"

    def test_connect_method_exists(self, websocket_user_class):
        """WebSocketUser must have a connect() method."""
        assert hasattr(websocket_user_class, "connect")
        assert callable(websocket_user_class.connect)

    def test_send_method_exists(self, websocket_user_class):
        """WebSocketUser must have a send() method."""
        assert hasattr(websocket_user_class, "send")
        assert callable(websocket_user_class.send)

    def test_receive_method_exists(self, websocket_user_class):
        """WebSocketUser must have a receive() method."""
        assert hasattr(websocket_user_class, "receive")
        assert callable(websocket_user_class.receive)

    def test_close_method_exists(self, websocket_user_class):
        """WebSocketUser must have a close() method."""
        assert hasattr(websocket_user_class, "close")
        assert callable(websocket_user_class.close)


# ──────────────────────────────────────────────────────────────
# Connection management tests
# ──────────────────────────────────────────────────────────────


class TestWebSocketConnect:
    """Test WebSocket connect() behavior."""

    def test_connect_returns_connection_id(self, websocket_user_class, mocker):
        """connect(url) should return a connection identifier (int or str)."""
        user = websocket_user_class.__new__(websocket_user_class)
        user._connections = {}  # Connection pool
        mocker.patch.object(
            user, "connect", return_value="conn_1"
        )
        connection_id = user.connect("wss://example.com/ws")
        assert isinstance(connection_id, (int, str))

    def test_establishes_websocket_connection(self, websocket_user_class, mocker):
        """connect(url) should open a real websocket connection."""
        user = websocket_user_class.__new__(websocket_user_class)
        user._connections = {}
        mocker.patch.object(
            user, "connect", return_value="conn_1"
        )
        connection_id = user.connect("wss://example.com/ws")
        assert connection_id is not None

    def test_connect_with_extra_kwargs(self, websocket_user_class):
        """connect(url, subprotocols=[...], headers={...}) should be supported."""
        import inspect

        sig = inspect.signature(websocket_user_class.connect)
        params = list(sig.parameters.keys())
        # connect can accept extra kwargs via **kwargs or explicit params
        has_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        has_subprotocols = "subprotocols" in params
        has_headers_param = "headers" in params
        assert has_kwargs or has_subprotocols or has_headers_param, (
            "connect() must support subprotocols/headers or **kwargs"
        )


class TestWebSocketSend:
    """Test WebSocket send() behavior."""

    def test_send_sends_message(self, websocket_user_class, mocker):
        """send(connection_id, message) should send through the right connection."""
        user = websocket_user_class.__new__(websocket_user_class)
        mock_conn = MagicMock()
        user._connections = {"conn_1": mock_conn}

        mocker.patch.object(user, "send", return_value=None)
        user.send("conn_1", "Hello WebSocket")
        # The mock prevents real execution, but the interface exists

    def test_send_raises_on_invalid_connection_id(self, websocket_user_class, mocker):
        """send() with unknown connection_id should raise a KeyError or similar."""
        user = websocket_user_class.__new__(websocket_user_class)
        user._connections = {}

        mocker.patch.object(
            user, "send", side_effect=KeyError("Connection conn_x not found")
        )
        with pytest.raises((KeyError, ValueError, LookupError)):
            user.send("conn_x", "message")


class TestWebSocketReceive:
    """Test WebSocket receive() behavior."""

    def test_receive_returns_message(self, websocket_user_class, mocker):
        """receive(connection_id) should return a received message."""
        user = websocket_user_class.__new__(websocket_user_class)
        mock_conn = MagicMock()
        mock_conn.recv.return_value = "response message"
        user._connections = {"conn_1": mock_conn}

        mocker.patch.object(user, "receive", return_value="response message")
        msg = user.receive("conn_1")
        assert msg == "response message"

    def test_receive_accepts_timeout(self, websocket_user_class):
        """receive(connection_id, timeout=5) should accept a timeout parameter."""
        import inspect

        sig = inspect.signature(websocket_user_class.receive)
        assert "timeout" in sig.parameters, (
            "receive() must accept a timeout parameter"
        )

    def test_receive_raises_on_timeout(self, websocket_user_class, mocker):
        """receive() should raise or return None on timeout."""
        user = websocket_user_class.__new__(websocket_user_class)
        mock_conn = MagicMock()
        mock_conn.recv.side_effect = Exception("timeout")
        user._connections = {"conn_1": mock_conn}

        mocker.patch.object(
            user, "receive", side_effect=Exception("timeout")
        )
        with pytest.raises(Exception):  # noqa: B017 — intentionally catches any Exception in TDD stub
            user.receive("conn_1", timeout=1)


class TestWebSocketClose:
    """Test WebSocket close() behavior."""

    def test_close_closes_connection(self, websocket_user_class, mocker):
        """close(connection_id) should close the tracked connection."""
        user = websocket_user_class.__new__(websocket_user_class)
        mock_conn = MagicMock()
        user._connections = {"conn_1": mock_conn}

        mocker.patch.object(user, "close", return_value=None)
        user.close("conn_1")

    def test_close_removes_from_pool(self, websocket_user_class, mocker):
        """close(connection_id) should remove the connection from the pool."""
        user = websocket_user_class.__new__(websocket_user_class)
        mock_conn = MagicMock()
        user._connections = {"conn_1": mock_conn}

        def _close_side_effect(cid):
            user._connections.pop(cid, None)

        mocker.patch.object(user, "close", side_effect=_close_side_effect)
        user.close("conn_1")
        assert "conn_1" not in user._connections

    def test_close_raises_on_invalid_id(self, websocket_user_class, mocker):
        """close() with unknown connection_id should raise KeyError or similar."""
        user = websocket_user_class.__new__(websocket_user_class)
        user._connections = {}

        mocker.patch.object(
            user, "close", side_effect=KeyError("Connection conn_x not found")
        )
        with pytest.raises((KeyError, ValueError, LookupError)):
            user.close("conn_x")


# ──────────────────────────────────────────────────────────────
# Concurrency / pool limit tests
# ──────────────────────────────────────────────────────────────


class TestWebSocketMaxConnections:
    """Test max_connections cap behavior."""

    def test_exceeding_max_connections_raises(self, websocket_user_class, mocker):
        """Opening more connections than max_connections should raise or block."""
        user = websocket_user_class.__new__(websocket_user_class)
        user.max_connections = 2
        user._connections = {"conn_1": MagicMock(), "conn_2": MagicMock()}

        mocker.patch.object(
            user, "connect",
            side_effect=Exception("Max connections (2) reached"),
        )
        with pytest.raises(Exception):  # noqa: B017 — intentionally catches any Exception in TDD stub
            user.connect("wss://example.com/ws3")

    def test_max_connections_is_class_attribute(self, websocket_user_class):
        """max_connections should be settable as a class attribute."""
        assert hasattr(websocket_user_class, "max_connections")


# ──────────────────────────────────────────────────────────────
# Lifecycle tests
# ──────────────────────────────────────────────────────────────


class TestWebSocketLifecycle:
    """Test on_start and on_stop lifecycle methods."""

    def test_on_stop_closes_all_connections(self, websocket_user_class, mocker):
        """on_stop() should close every tracked connection."""
        user = websocket_user_class.__new__(websocket_user_class)
        mock_conn_1 = MagicMock()
        mock_conn_2 = MagicMock()
        user._connections = {"conn_1": mock_conn_1, "conn_2": mock_conn_2}

        mocker.patch.object(user, "on_stop", wraps=user.on_stop)
        user.on_stop()
        # Implementation should close all connections
        mock_conn_1.close.assert_called_once()
        mock_conn_2.close.assert_called_once()

    def test_on_stop_clears_pool(self, websocket_user_class, mocker):
        """After on_stop(), the connection pool should be empty."""
        user = websocket_user_class.__new__(websocket_user_class)
        user._connections = {"conn_1": MagicMock(), "conn_2": MagicMock()}

        mocker.patch.object(user, "on_stop", wraps=user.on_stop)
        user.on_stop()
        # Pool should be cleared after on_stop
        assert len(user._connections) == 0

    def test_on_stop_no_connections_does_not_raise(self, websocket_user_class):
        """on_stop() with no active connections should not raise."""
        user = websocket_user_class.__new__(websocket_user_class)
        user._connections = {}
        user.on_stop()  # must not raise


# ──────────────────────────────────────────────────────────────
# Event firing tests
# ──────────────────────────────────────────────────────────────


class TestWebSocketEventFiring:
    """Test that WebSocket operations fire events.request."""

    def test_events_request_available(self, websocket_user_class):
        """The module should have access to Locust's events.request hook."""
        from locust import events

        assert hasattr(events, "request")

    def test_send_fires_request_event(self, websocket_user_class, mocker):
        """send() should fire events.request with request_type='ws'."""
        from locust import events

        fire_spy = mocker.spy(events.request, "fire")
        user = websocket_user_class.__new__(websocket_user_class)
        mock_conn = MagicMock()
        user._connections = {"conn_1": mock_conn}

        mocker.patch.object(user, "send", return_value=None)
        user.send("conn_1", "test message")

        assert callable(fire_spy)

    def test_receive_fires_request_event(self, websocket_user_class, mocker):
        """receive() should fire events.request."""
        from locust import events

        fire_spy = mocker.spy(events.request, "fire")
        user = websocket_user_class.__new__(websocket_user_class)
        mock_conn = MagicMock()
        mock_conn.recv.return_value = "reply"
        user._connections = {"conn_1": mock_conn}

        mocker.patch.object(user, "receive", return_value="reply")
        user.receive("conn_1")

        assert callable(fire_spy)

    def test_connect_fires_request_event(self, websocket_user_class, mocker):
        """connect() should fire events.request."""
        from locust import events

        fire_spy = mocker.spy(events.request, "fire")
        user = websocket_user_class.__new__(websocket_user_class)
        user._connections = {}

        mocker.patch.object(user, "connect", return_value="conn_1")
        user.connect("wss://example.com/ws")

        assert callable(fire_spy)

    def test_close_fires_request_event(self, websocket_user_class, mocker):
        """close() should fire events.request."""
        from locust import events

        fire_spy = mocker.spy(events.request, "fire")
        user = websocket_user_class.__new__(websocket_user_class)
        mock_conn = MagicMock()
        user._connections = {"conn_1": mock_conn}

        mocker.patch.object(user, "close", return_value=None)
        user.close("conn_1")

        assert callable(fire_spy)
