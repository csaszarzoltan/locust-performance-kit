# Multi-Protocol Troubleshooting Guide

Common issues when using the multi-protocol load testing templates (gRPC, GraphQL,
WebSocket) and how to resolve them.

## gRPC Import Errors

### Symptom: `ImportError: No module named 'grpc'`

**Cause:** The `grpcio` package is not installed.

**Solution:** Install the optional dependency:

```bash
pip install locust-performance-kit[grpc]
```

Or install manually:

```bash
pip install grpcio>=1.60.0
```

### Symptom: `ImportError: No module named 'helloworld_pb2'`

**Cause:** The protobuf-generated stub modules are not in the Python path.

**Solution:** Run `protoc` to generate your service's Python stubs:

```bash
python -m grpc_tools.protoc \
    -I./protos \
    --python_out=. \
    --grpc_python_out=. \
    ./protos/helloworld.proto
```

Add the output directory to `sys.path` or install it as a package. See
the [gRPC Testing Guide](grpc-testing.md) for a full example.

### Symptom: `RuntimeError: Channel not created. Call _get_channel(target) first.`

**Cause:** A task method is calling `_call_rpc` before the channel has been
initialised in `on_start`.

**Solution:** Ensure your `on_start` method calls `self._get_channel(target)`
(and optionally `self._get_stub(stub_class)`) before any `@task` method runs:

```python
def on_start(self):
    super().on_start()
    self._get_channel("localhost:50051")
    self.stub = self._get_stub(GreeterStub)
```

## GraphQL Complexity Violations

### Symptom: `ValueError: Query complexity X exceeds threshold Y`

**Cause:** A GraphQL query's complexity score exceeds the configured
`LOCUST_GRAPHQL_COMPLEXITY_THRESHOLD` or the class-level
`complexity_threshold`.

**Solution(s):**

- Raise the threshold:
  ```bash
  export LOCUST_GRAPHQL_COMPLEXITY_THRESHOLD=50
  ```
  Or set it per-class:
  ```python
  class MyGraphQLUser(GraphQLUser):
      complexity_threshold = 50
  ```
- Simplify the query (fewer nested fields, smaller selection sets).
- Disable complexity checking entirely by setting the threshold to `0`
  (the default).

### Symptom: GraphQL queries succeed but `response.errors` is non-empty

**Cause:** The server returned GraphQL-level errors (e.g., validation errors,
 resolver errors, rate limiting).

**Solution:** Log the actual error messages from `response.errors`:

```python
response = self.query(query, variables={"id": "123"})
if response.errors:
    for err in response.errors:
        print(f"GraphQL error: {err.get('message', err)}")
```

Common causes:

- **Invalid variable types** — ensure variable values match the schema types.
- **Missing required fields** — check that your query includes all required
  `!` (non-null) fields.
- **Auth token expired** — configure a provider that refreshes tokens (see
  [Authentication Providers Guide](auth-providers.md)).

## WebSocket Timeouts

### Symptom: `WebSocketTimeoutException: timed out` on `self.receive()`

**Cause:** The server did not send a response within the configured timeout.

**Solution(s):**

- Increase the timeout value:
  ```python
  response = self.receive(self.conn_id, timeout=10)
  ```
- Verify the server is actually processing the sent message. Add a small
  `wait_time` between send and receive to allow server processing time.
- Check that the server's WebSocket endpoint is reachable and that the
  protocol matches (`ws://` vs `wss://`).

### Symptom: `WebSocketError: Max connections (N) reached`

**Cause:** A single user instance is trying to open more connections than
`max_connections` allows.

**Solution:** Increase `max_connections` on the class:

```python
class MyWebSocketUser(WebSocketUser):
    max_connections = 10
```

Or adjust via the environment variable:

```bash
export LOCUST_WS_MAX_CONNECTIONS=10
```

### Symptom: Connection drops mid-test

**Cause:** The server's idle timeout may be shorter than the interval between
user tasks.

**Solution:** Add a heartbeat task that sends a lightweight ping message:

```python
@task(1)
def heartbeat(self):
    self.send(self.conn_id, '{"type": "ping"}')
    self.receive(self.conn_id, timeout=5)
```

## Auth Metadata Problems

### Symptom: gRPC calls fail with `UNAUTHENTICATED` or HTTP 401

**Cause:** The authenticator is not configured or the token has expired.

**Solution(s):**

- Verify the `auth_provider` class attribute is set correctly:
  ```python
  class MyGrpcUser(GrpcUser):
      auth_provider = "oauth2-client-credentials"
      auth_kwargs = {
          "token_url": "https://auth.example.com/oauth/token",
          "client_id": "my-client",
          "client_secret": "my-secret",
      }
  ```
- Ensure the required environment variables are exported (e.g.,
  `LOCUST_AUTH_TOKEN`, `LOCUST_AUTH_CLIENT_ID`).
- For long-running tests, ensure the token TTL covers the full duration, or
  implement token refresh inside a task.

### Symptom: Auth headers are not being sent

**Cause:** The gRPC metadata conversion failed or the authenticator raised an
exception silently.

**Solution:** Check the authenticator initialisation by inspecting the
`_authenticator` attribute after `on_start`:

```python
def on_start(self):
    super().on_start()
    print(f"Auth headers: {self._get_auth_metadata()}")
```

## Dependency Installation Failures

### Symptom: `pip install locust-performance-kit[grpc]` fails

**Cause:** `grpcio` requires a C++ compiler or has platform-specific build
dependencies.

**Solution(s):**

- On Linux, install build tools:
  ```bash
  sudo apt-get install build-essential python3-dev
  ```
- On macOS, install Xcode Command Line Tools:
  ```bash
  xcode-select --install
  ```
- For Windows, use a pre-built wheel (pip will attempt this automatically).
- Consider using a pre-built Docker image that includes gRPC (see
  [Deployment](../README.md#deployment)).

### Symptom: `pip install locust-performance-kit[websocket]` fails

**Cause:** The `websocket-client` package is a pure-Python wheel and rarely
fails. If it does, it may be a network or PyPI mirror issue.

**Solution(s):**

- Try installing with a longer timeout:
  ```bash
  pip install --default-timeout=120 locust-performance-kit[websocket]
  ```
- Upgrade pip:
  ```bash
  pip install --upgrade pip
  ```
- Install from a mirror:
  ```bash
  pip install -i https://pypi.org/simple/ locust-performance-kit[websocket]
  ```

## General Tips

1. **Test each protocol in isolation first** — run a minimal script against a
   known-good endpoint before combining protocols in a single test.
2. **Check Locust logs** — set `--logfile locust.log` when running headless
   to capture full stack traces.
3. **Mock external services** — for local development and CI, mock the gRPC
   server, GraphQL endpoint, or WebSocket server to avoid flaky network failures.
4. **Update pip and setuptools** — stale installers can cause subtle import
   resolution issues:
   ```bash
   pip install --upgrade pip setuptools wheel
   ```

## See Also

- [gRPC Testing Guide](grpc-testing.md)
- [GraphQL Testing Guide](graphql-testing.md)
- [WebSocket Testing Guide](websocket-testing.md)
- [Multi-Protocol Configuration](multi-protocol-configuration.md)
- [Authentication Providers Guide](auth-providers.md)
