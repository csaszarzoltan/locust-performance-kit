# WebSocket Stress Testing Guide

> Stress-test WebSocket services using the `WebSocketUser` template, part of the
> [Multi-Protocol Templates](../README.md#multi-protocol-templates-v140) (v1.4.0+).

## Overview

WebSocket provides a full-duplex communication channel over a single TCP
connection, commonly used for:

- Real-time chat and messaging
- Live data feeds (market data, sports scores, IoT telemetry)
- Collaborative editing and gaming
- Push notifications and streaming dashboards

Load-testing WebSocket services is fundamentally different from HTTP testing
because connections are long-lived and stateful — each simulated user must
connect once, then maintain the connection while sending and receiving messages.

`WebSocketUser` extends Locust's `User` with:

- **Connection pooling** — each user instance manages up to `max_connections`
  simultaneous WebSocket connections, each identified by a unique UUID.
- **Full lifecycle** — `connect()`, `send()`, `receive()`, and `close()`
  methods, each firing Locust events for metrics.
- **Automatic cleanup** — `on_stop()` closes all tracked connections when a
  user stops.
- **Heartbeat-compatible** — design send/receive patterns that mirror your
  production keep-alive logic.

## Installation

```bash
pip install locust-performance-kit[websocket]
```

This installs `websocket-client>=1.7.0` alongside the kit. Alternatively add
it manually:

```bash
pip install locust-performance-kit websocket-client>=1.7.0
```

## Quick Start

Subclass `WebSocketUser`, override `on_start` to open a connection, then
write `@task`-decorated methods that call `send()` and `receive()`.

```python
from locust import between, task
from locust_templates.websocket import WebSocketUser


class ChatUser(WebSocketUser):
    wait_time = between(2, 5)
    max_connections = 2

    def on_start(self):
        """Open a WebSocket connection when the simulated user starts."""
        self.conn_id = self.connect("wss://chat.example.com/ws")

    @task
    def ping_pong(self):
        """Send a ping and wait for the pong."""
        self.send(self.conn_id, '{"type": "ping"}')
        response = self.receive(self.conn_id, timeout=5)
        if response:
            self.send(self.conn_id, f'{{"ack": "{response}"}}')

    def on_stop(self):
        """Close the connection when the simulated user stops."""
        self.close(self.conn_id)
```

Run it:

```bash
locust -f chat_test.py --users 30 --spawn-rate 3 --run-time 5m
```

## API Reference

### `WebSocketUser`

Base class: `locust.User`

| Attribute / Method                                               | Description                                                             |
|------------------------------------------------------------------|-------------------------------------------------------------------------|
| `max_connections`                                                | Max concurrent WebSocket connections per user (default `5`).            |
| `connect(url, subprotocols=None, headers=None)` → `str`          | Open a new WebSocket connection, return a connection id (UUID str).     |
| `send(connection_id, message)`                                   | Send a text message over the identified connection.                     |
| `receive(connection_id, timeout=5)` → `str`                      | Wait for a message (up to `timeout` seconds) and return it as a string. |
| `close(connection_id)`                                           | Close the identified connection and remove it from the pool.            |

### Exceptions

| Exception        | Description                                            |
|------------------|--------------------------------------------------------|
| `WebSocketError` | Raised on misuse — connection not found, pool full, etc. Import from `locust_templates.websocket`. |

### Method Details

**`connect(url, subprotocols=None, headers=None)`** → `str`

- `url` — WebSocket endpoint URL (`ws://...` or `wss://...`).
- `subprotocols` — optional list of subprotocol strings.
- `headers` — optional dict of HTTP headers for the opening handshake.
- Returns a UUID string (the connection id).
- Raises `WebSocketError` if `max_connections` is reached.
- Fires a Locust event with `request_type="ws"` and `name="connect <url>"`.

**`send(connection_id, message)`**

- `connection_id` — the id returned by `connect()`.
- `message` — text payload to send (strings only; for binary, encode first).
- Raises `WebSocketError` if the connection id is unknown or closed.
- Fires a Locust event with `request_type="ws"` and `name="send <id_prefix>"`.

**`receive(connection_id, timeout=5)`** → `str`

- `connection_id` — the id returned by `connect()`.
- `timeout` — seconds to wait for a message (default 5).
- Returns the received text message.
- Raises on timeout or connection error (after firing the event).
- Fires a Locust event with `request_type="ws"` and `name="receive <id_prefix>"`.

**`close(connection_id)`**

- `connection_id` — the id returned by `connect()`.
- Raises `WebSocketError` if the connection id is unknown.
- Fires a Locust event with `request_type="ws"` and `name="close <id_prefix>"`.

### Event Lifecycle

Every WebSocket operation fires a Locust `events.request` with:

| Operation | `request_type` | `name` example            |
|-----------|----------------|---------------------------|
| Connect   | `ws`           | `connect ws://example...` |
| Send      | `ws`           | `send a1b2c3d4`           |
| Receive   | `ws`           | `receive a1b2c3d4`        |
| Close     | `ws`           | `close a1b2c3d4`          |

This means all WebSocket operations are visible in the Locust web UI under
the **ws** tab, with separate statistics per operation type.

## Connection Management

### `max_connections`

Controls how many simultaneous WebSocket connections a single simulated user
can hold. Default is `5`. You can set it per subclass:

```python
class MarketDataUser(WebSocketUser):
    max_connections = 3  # Subscribe to 3 different feeds
```

Or via the environment variable:

```bash
export LOCUST_WS_MAX_CONNECTIONS=10
```

### Connection Pool Lifecycle

```
┌──────────┐   connect()   ┌──────────────┐
│  User    │ ────────────→ │  Pool (max)  │
│  starts  │               │  conn_1  ✓   │
│          │               │  conn_2  ✓   │
│          │               │  conn_3  ✓   │
│          │   close()     │              │
│  User    │ ←──────────── │  (removed)   │
│  stops   │               └──────────────┘
│          │   on_stop()   │  all closed   │
└──────────┘               └──────────────┘
```

When `on_stop` is called (user finishes), all tracked connections are closed
automatically and the pool is cleared.

### Heartbeat Pattern

If your WebSocket server expects periodic keep-alive pings, add a dedicated
task:

```python
from locust import task
from locust_templates.websocket import WebSocketUser


class HeartbeatUser(WebSocketUser):
    def on_start(self):
        self.conn_id = self.connect("wss://example.com/ws")

    @task
    def heartbeat(self):
        """Send a heartbeat every few seconds."""
        self.send(self.conn_id, '{"type": "heartbeat"}')
        # Don't wait for a response — fire-and-forget
```

Use `wait_time` to control the heartbeat interval:

```python
wait_time = between(10, 15)  # heartbeat every 10-15 seconds
```

## Configuration

### Environment Variables

| Variable                  | Default | Description                                          |
|---------------------------|---------|------------------------------------------------------|
| `LOCUST_WS_MAX_CONNECTIONS` | `5`   | Default `max_connections` for all `WebSocketUser` subclasses. |

Set it before running Locust:

```bash
export LOCUST_WS_MAX_CONNECTIONS=20
locust -f feed_test.py --users 100 --spawn-rate 10
```

## Full Working Example

A complete load test for a fictional real-time market data feed:

```python
"""WebSocket load test for a market data feed."""

import json
import time
from locust import between, task
from locust_templates.websocket import WebSocketUser


class MarketFeedUser(WebSocketUser):
    wait_time = between(1, 3)
    max_connections = 3

    subscriptions = ["BTC/USD", "ETH/USD", "SOL/USD"]

    def on_start(self):
        """Subscribe to multiple feeds on separate connections."""
        self.conn_ids = {}
        for symbol in self.subscriptions:
            conn_id = self.connect(
                "wss://feed.example.com/market",
                headers={"Origin": "https://trader.example.com"},
            )
            self.conn_ids[symbol] = conn_id
            # Subscribe to the symbol
            self.send(
                conn_id,
                json.dumps({"type": "subscribe", "symbol": symbol}),
            )

    @task
    def receive_tick(self):
        """Read a real-time price tick from any connection."""
        for symbol, conn_id in self.conn_ids.items():
            try:
                msg = self.receive(conn_id, timeout=2)
                data = json.loads(msg)
                if data.get("type") == "trade":
                    self.send(
                        conn_id,
                        json.dumps({"type": "ack", "seq": data.get("seq", 0)}),
                    )
            except Exception:
                pass  # timeout is expected when no data

    @task
    def ping_feed(self):
        """Send a heartbeat on the first connection."""
        first_id = list(self.conn_ids.values())[0]
        self.send(first_id, json.dumps({"type": "ping"}))

    def on_stop(self):
        """Unsubscribe and close all connections."""
        for symbol, conn_id in list(self.conn_ids.items()):
            self.send(
                conn_id,
                json.dumps({"type": "unsubscribe", "symbol": symbol}),
            )
            self.close(conn_id)
        self.conn_ids.clear()
```

Run with:

```bash
locust -f market_feed_test.py --users 20 --spawn-rate 2 --run-time 10m
```

## Best Practices

1. **Open connections in `on_start`.** Each simulated user should establish
   its WebSocket connections when it starts, not in a `@task` method.
   Subsequent tasks then use the pooled connections.
2. **Close connections in `on_stop`.** The base class closes all connections
   automatically, but if your server requires an explicit goodbye message or
   unsubscription, override `on_stop` and send it before calling
   `self.close()`.
3. **Set realistic `max_connections`.** A single user holding hundreds of
   connections can stress client-side resources. Model your expected
   real-world ratio of users to connections.
4. **Handle timeouts gracefully.** `receive()` will raise on timeout. Use
   `try/except` around receive calls when the arrival pattern is irregular.
5. **Use JSON for structured data.** While the template sends text strings,
   using `json.dumps` / `json.loads` keeps your payloads readable and
   consistent with most production WebSocket APIs.
6. **Match the heartbeat interval.** If your production servers expect a
   keep-alive every 30 seconds, set `wait_time = between(25, 30)` on your
   heartbeat task so connections don't get dropped mid-test.
7. **Monitor connection counts.** The Locust web UI shows `ws` request
   statistics — a rising error rate on `connect` may indicate you've hit
   server-side connection limits.
8. **Test with `ws://` first.** Validate your test script against an
   unencrypted endpoint before introducing TLS overhead.
