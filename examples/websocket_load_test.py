"""WebSocket Load Test Example — Chat System.

Demonstrates how to load-test a WebSocket-powered chat system using
the ``WebSocketUser`` template with connection lifecycle, send/receive
patterns, and heartbeat monitoring.

Usage:
    locust -f examples/websocket_load_test.py --users 50 --spawn-rate 5 --run-time 3m

Requires: pip install locust-performance-kit[websocket]
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is on the path for template imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import websocket  # noqa: F401
except ImportError:
    msg = (
        "WebSocket support requires extra dependencies.\n"
        "  pip install locust-performance-kit[websocket]\n"
        "or:\n"
        "  pip install websocket-client>=1.7.0"
    )
    print(msg)
    raise

from locust import between, task

from locust_templates.websocket import WebSocketUser


class ExampleWebSocketUser(WebSocketUser):
    """Example WebSocket user for load-testing a chat system.

    Opens a connection on start, then alternates between two tasks:

    1. **send_and_receive** — sends a chat message and receives an
       acknowledgment (the primary chat flow).
    2. **heartbeat_check** — sends a ping and expects a pong response
       (connection health monitoring).

    Closes the connection gracefully on stop.

    Run::

        locust -f examples/websocket_load_test.py \\
        --users 50 --spawn-rate 5 --run-time 3m
    """

    wait_time = between(1, 3)
    max_connections = 2

    def on_start(self) -> None:
        """Open a WebSocket connection when the simulated user starts.

        Stores the connection id so task methods can reference it.
        """
        self.conn_id = self.connect("wss://chat.example.com/ws")

    @task(3)
    def send_and_receive(self) -> None:
        """Send a chat message and verify acknowledgment.

        Weight: 3 — simulates the primary user action of sending a
        message and waiting for the server to acknowledge it.
        """
        self.send(self.conn_id, '{"type": "message", "text": "Hello!"}')
        response = self.receive(self.conn_id, timeout=5)
        if response:
            self.send(self.conn_id, f'{{"type": "ack", "for": "{response}"}}')

    @task(1)
    def heartbeat_check(self) -> None:
        """Send a ping and expect a pong response.

        Weight: 1 — simulates a keep-alive heartbeat to verify the
        connection is still healthy. Useful for long-running tests
        where idle connections may be dropped.
        """
        self.send(self.conn_id, '{"type": "ping"}')
        pong = self.receive(self.conn_id, timeout=5)
        if pong:
            # Connection is healthy — log the round-trip
            _ = pong  # ack consumed; Locust events record timing

    def on_stop(self) -> None:
        """Close the WebSocket connection when the simulated user stops.

        Ensures clean teardown for accurate per-user metrics.
        """
        import contextlib

        if hasattr(self, "conn_id"):
            with contextlib.suppress(Exception):
                self.close(self.conn_id)


if __name__ == "__main__":
    print("Run with: locust -f examples/websocket_load_test.py")
