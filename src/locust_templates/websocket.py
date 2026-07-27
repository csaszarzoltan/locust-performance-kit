"""WebSocket Load Test Template.

Provides ``WebSocketUser`` — a Locust user class for load-testing
WebSocket endpoints with connection pooling, message send/receive,
and Locust event integration.

Usage::

    from locust_templates.websocket import WebSocketUser

    class MyWSUser(WebSocketUser):
        def on_start(self):
            self.conn_id = self.connect("wss://example.com/ws")

        @task
        def ping_pong(self):
            self.send(self.conn_id, '{"type":"ping"}')
            resp = self.receive(self.conn_id, timeout=5)

        def on_stop(self):
            self.close(self.conn_id)

Requires: ``pip install locust-performance-kit[websocket]``
or ``pip install websocket-client>=1.7.0``
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

from locust import User, between, task

# ── Optional dependency guard ────────────────────────────────
try:
    import websocket
except ImportError:
    websocket = None  # type: ignore[assignment]


class WebSocketError(Exception):
    """Raised on WebSocket operation misuse."""


class WebSocketUser(User):
    """Base user class for WebSocket load testing.

    Manages a pool of WebSocket connections per user instance.
    Each connection is identified by a unique string id (UUID).

    Class attributes you can override:

    * ``max_connections`` — default 5 (also via ``LOCUST_WS_MAX_CONNECTIONS`` env)
    """

    wait_time = between(2, 8)

    max_connections: int = int(
        os.environ.get("LOCUST_WS_MAX_CONNECTIONS", "5") or "5"
    )

    # Class-level defaults so __new__-created instances (used in tests) work
    _connections: dict[str, Any] = {}
    _connection_states: dict[str, str] = {}

    def __init__(self, environment):
        super().__init__(environment)
        self._connections: dict[str, Any] = {}  # connection_id → WebSocket object
        self._connection_states: dict[str, str] = {}  # connection_id → open|closed

    def connect(
        self,
        url: str,
        subprotocols: list[str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Open a new WebSocket connection and register it in the pool.

        Args:
            url: The WebSocket endpoint URL (``ws://...`` or ``wss://...``).
            subprotocols: Optional list of subprotocols.
            headers: Optional custom HTTP headers for the opening handshake.

        Returns:
            A connection id (UUID string) that identifies this connection.

        Raises:
            WebSocketError: If ``max_connections`` would be exceeded.
        """
        from locust import events

        if len(self._connections) >= self.max_connections:
            raise WebSocketError(
                f"Max connections ({self.max_connections}) reached"
            )

        if websocket is None:
            raise ImportError(
                "WebSocket support requires extra dependencies.\n"
                "  pip install locust-performance-kit[websocket]\n"
                "or:\n  pip install websocket-client>=1.7.0"
            )

        start_time = time.perf_counter()
        exception = None
        ws = None

        try:
            ws = websocket.create_connection(
                url,
                subprotocols=subprotocols or [],
                header=headers or {},
                timeout=30,
            )
        except Exception as exc:
            exception = exc

        elapsed = (time.perf_counter() - start_time) * 1000

        events.request.fire(
            request_type="ws",
            name=f"connect {url}",
            response_time=elapsed,
            response_length=0,
            exception=exception,
        )

        if exception:
            raise exception

        connection_id = str(uuid.uuid4())
        self._connections[connection_id] = ws
        self._connection_states[connection_id] = "open"
        return connection_id

    def send(self, connection_id: str, message: str) -> None:
        """Send a text message over the identified WebSocket connection.

        Args:
            connection_id: The id returned by :meth:`connect`.
            message: Text payload to send.

        Raises:
            WebSocketError: If the connection is closed or unknown.
        """
        from locust import events

        ws = self._get_connection(connection_id)

        start_time = time.perf_counter()
        exception = None
        try:
            ws.send(message)
        except Exception as exc:
            exception = exc

        elapsed = (time.perf_counter() - start_time) * 1000

        events.request.fire(
            request_type="ws",
            name=f"send {connection_id[:8]}",
            response_time=elapsed,
            response_length=len(message),
            exception=exception,
        )

        if exception:
            raise exception

    def receive(self, connection_id: str, timeout: float = 5) -> str:
        """Receive a message from the identified WebSocket connection.

        Args:
            connection_id: The id returned by :meth:`connect`.
            timeout: Seconds to wait for a message (default 5).

        Returns:
            The received message text.

        Raises:
            Exception: On timeout or connection error.
        """
        from locust import events

        ws = self._get_connection(connection_id)

        start_time = time.perf_counter()
        exception = None
        msg = None
        try:
            ws.settimeout(timeout)
            msg = ws.recv()
        except Exception as exc:
            exception = exc

        elapsed = (time.perf_counter() - start_time) * 1000

        events.request.fire(
            request_type="ws",
            name=f"receive {connection_id[:8]}",
            response_time=elapsed,
            response_length=len(msg) if msg else 0,
            exception=exception,
        )

        if exception:
            raise exception
        return msg

    def close(self, connection_id: str) -> None:
        """Close the identified WebSocket connection and remove it from the pool.

        Args:
            connection_id: The id returned by :meth:`connect`.

        Raises:
            WebSocketError: If the connection is unknown.
        """
        from locust import events

        if connection_id not in self._connections:
            raise WebSocketError(f"Connection {connection_id} not found")

        ws = self._connections[connection_id]

        start_time = time.perf_counter()
        exception = None
        try:
            ws.close()
        except Exception as exc:
            exception = exc

        elapsed = (time.perf_counter() - start_time) * 1000

        self._connections.pop(connection_id, None)
        self._connection_states.pop(connection_id, None)

        events.request.fire(
            request_type="ws",
            name=f"close {connection_id[:8]}",
            response_time=elapsed,
            response_length=0,
            exception=exception,
        )

        if exception:
            raise exception

    def _get_connection(self, connection_id: str) -> Any:
        """Look up a connection by id or raise ``WebSocketError``."""
        if connection_id not in self._connections:
            raise WebSocketError(f"Connection {connection_id} not found")
        return self._connections[connection_id]

    def on_start(self):
        """Called when a simulated user starts."""
        pass

    def on_stop(self):
        """Called when a simulated user stops.

        Closes all tracked connections and clears the pool.
        """
        for cid in list(self._connections.keys()):
            try:
                ws = self._connections[cid]
                ws.close()
            except Exception:
                pass
        self._connections.clear()
        self._connection_states.clear()

    @task
    def ws_ping(self):
        """Default no-op task so Locust sees at least one task.

        Subclasses should override this or add their own ``@task`` methods.
        """
        pass


__all__ = ["WebSocketUser", "WebSocketError"]
