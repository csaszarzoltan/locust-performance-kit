"""WebSocket Load Test Example (TDD stub).

Placeholder for a production-ready Locust script demonstrating how to
use the WebSocketUser template for WebSocket stress testing.

Usage:
    locust -f examples/websocket_load_test.py --users 50 --spawn-rate 5 --run-time 3m

Requires: pip install locust-performance-kit[websocket]
"""

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
    """Example WebSocket user extending the base template.

    Connects to a WebSocket endpoint, sends messages, and receives
    responses for each simulated user.
    """

    wait_time = between(1, 3)
    max_connections = 2

    def on_start(self):
        """Open a connection when the user starts."""
        self.conn_id = self.connect("wss://example.com/ws")

    @task
    def send_and_receive(self):
        """Send a message and wait for a response."""
        self.send(self.conn_id, '{"type": "ping"}')
        response = self.receive(self.conn_id, timeout=5)
        if response:
            self.send(self.conn_id, f'{{"ack": "{response}"}}')

    def on_stop(self):
        """Close connection when the user stops."""
        self.close(self.conn_id)


if __name__ == "__main__":
    print("Run with: locust -f examples/websocket_load_test.py")
