# Multi-Protocol Configuration Reference

Cross-reference of environment variables, class-level attributes, and defaults
across the three multi-protocol templates (gRPC, GraphQL, WebSocket).

> For detailed API references, see the individual protocol guides:
> [gRPC](grpc-testing.md) · [GraphQL](graphql-testing.md) ·
> [WebSocket](websocket-testing.md)

## Environment Variables

| Variable | Affects | Default | Description |
|---|---|---|---|
| `LOCUST_GRAPHQL_ENDPOINT` | GraphQL | `/graphql` | GraphQL endpoint path relative to the target host. |
| `LOCUST_GRAPHQL_COMPLEXITY_THRESHOLD` | GraphQL | `0` (disabled) | Maximum allowed query complexity score. Queries exceeding this threshold raise `ValueError`. Set to `0` to disable. |
| `LOCUST_WS_MAX_CONNECTIONS` | WebSocket | `5` | Maximum number of concurrent WebSocket connections per user instance. |

**Common auth variables** (shared across all protocols via the pluggable authenticator system):

| Variable | Applies to | Description |
|---|---|---|
| `LOCUST_AUTH_PROVIDER` | All | Authenticator provider name (`static`, `env`, `oauth2-client-credentials`). |
| `LOCUST_AUTH_TOKEN` | All | Static bearer token (used by `static` and `env` providers). |
| `LOCUST_AUTH_CLIENT_ID` | All | OAuth2 client ID (used by `oauth2-client-credentials` provider). |
| `LOCUST_AUTH_CLIENT_SECRET` | All | OAuth2 client secret. |
| `LOCUST_AUTH_TOKEN_URL` | All | OAuth2 token endpoint URL. |
| `LOCUST_AUTH_SCOPES` | All | Space-separated OAuth2 scopes. |

See the [Authentication Providers Guide](auth-providers.md) for full details.

## Class-Level Attributes

### `GrpcUser`

| Attribute | Type | Default | Description |
|---|---|---|---|
| `wait_time` | `between(a, b)` | `between(1, 5)` | Time range (seconds) between task executions. |
| `auth_provider` | `str` | `"env"` | Authenticator provider name. |
| `auth_kwargs` | `dict` | `{}` | Keyword arguments for the authenticator constructor. |

### `GraphQLUser`

| Attribute | Type | Default | Description |
|---|---|---|---|
| `wait_time` | `between(a, b)` | `between(1, 5)` | Time range (seconds) between task executions. |
| `graphql_endpoint` | `str` | `"/graphql"` | GraphQL endpoint path (overridable via `LOCUST_GRAPHQL_ENDPOINT`). |
| `complexity_threshold` | `int` | `0` | Maximum query complexity score. `0` disables the check. |
| `auth_provider` | `str` | `"env"` | Authenticator provider name. |
| `auth_kwargs` | `dict` | `{}` | Keyword arguments for the authenticator constructor. |

### `WebSocketUser`

| Attribute | Type | Default | Description |
|---|---|---|---|
| `wait_time` | `between(a, b)` | `between(2, 8)` | Time range (seconds) between task executions. |
| `max_connections` | `int` | `5` | Maximum concurrent WebSocket connections per user (overridable via `LOCUST_WS_MAX_CONNECTIONS`). |

## Method Quick Reference

### `GrpcUser` Methods

| Method | Description | When to Call |
|---|---|---|
| `_get_channel(target, secure=False, credentials=None)` | Create or return cached gRPC channel to `target`. | In `on_start` before creating stubs. |
| `_get_stub(stub_class)` | Return a cached instance of `stub_class`. | After channel is ready. |
| `_call_rpc(stub_method, request, timeout=10)` | Execute a unary-unary RPC and fire Locust event. | Inside `@task` methods. |
| `on_start()` | Initialise auth and set up channel/stub. | Override in subclass. |
| `on_stop()` | Close the gRPC channel. | Override in subclass. |

### `GraphQLUser` Methods

| Method | Description | When to Call |
|---|---|---|
| `query(query_str, variables=None, operation_name=None)` | Execute a GraphQL query via POST. Returns `GraphQLResponse`. | Inside `@task` methods. |
| `on_start()` | Set up authentication. | Inherited from `HttpUser`; override if custom init needed. |

### `WebSocketUser` Methods

| Method | Description | When to Call |
|---|---|---|
| `connect(url, subprotocols=None, headers=None)` | Open a new WebSocket connection. Returns a connection id. | In `on_start`. |
| `send(connection_id, message)` | Send a text message over the connection. | Inside `@task` methods. |
| `receive(connection_id, timeout=5)` | Receive a message (blocks up to `timeout` seconds). | Inside `@task` methods. |
| `close(connection_id)` | Close the connection and remove it from the pool. | In `on_stop`. |
| `on_start()` | Optional — override to open connections. | Override in subclass. |
| `on_stop()` | Close all tracked connections and clear the pool. | Inherited; override to add custom teardown. |

## Common Configuration Patterns

### Insecure Local Development

```python
# gRPC — no TLS, no auth
class DevGrpcUser(GrpcUser):
    def on_start(self):
        super().on_start()
        self._get_channel("localhost:50051")
        self.stub = self._get_stub(GreeterStub)

# GraphQL — default endpoint, no complexity check
class DevGraphQLUser(GraphQLUser):
    pass

# WebSocket — local ws:// endpoint
class DevWSUser(WebSocketUser):
    def on_start(self):
        self.conn_id = self.connect("ws://localhost:8080/ws")
```

### Production with Auth and TLS

```python
# gRPC with TLS and OAuth2
class ProdGrpcUser(GrpcUser):
    auth_provider = "oauth2-client-credentials"
    auth_kwargs = {"token_url": "...", "client_id": "...", "client_secret": "..."}
    def on_start(self):
        super().on_start()
        self._get_channel("api.example.com:443", secure=True)
        self.stub = self._get_stub(GreeterStub)

# GraphQL with complexity guard
class ProdGraphQLUser(GraphQLUser):
    complexity_threshold = 30
    auth_provider = "oauth2-client-credentials"
    auth_kwargs = {"token_url": "...", "client_id": "...", "client_secret": "..."}
```

### High-Connection WebSocket

```python
class HighConcurrencyWSUser(WebSocketUser):
    max_connections = 20

    def on_start(self):
        # Open multiple channels for multiplexed testing
        self.conn_a = self.connect("wss://chat.example.com/room/a")
        self.conn_b = self.connect("wss://chat.example.com/room/b")
```

## See Also

- [gRPC Testing Guide](grpc-testing.md) — full API, best practices, TLS setup
- [GraphQL Testing Guide](graphql-testing.md) — queries, mutations, complexity analysis
- [WebSocket Testing Guide](websocket-testing.md) — connection lifecycle, heartbeat patterns
- [Multi-Protocol Troubleshooting](multi-protocol-troubleshooting.md) — common issues and fixes
- [Authentication Providers Guide](auth-providers.md) — auth configuration
