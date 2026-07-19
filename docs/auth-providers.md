# Authentication Providers Guide

The `locust_templates.auth` module provides a pluggable authentication system
for Locust load tests.  Instead of hard-coding tokens in test scripts, you
select an auth provider at runtime via configuration or environment variables.

## Architecture

```
Authenticator (ABC)
├── authenticate() → dict[str, str]   # validate config, fetch credentials
├── get_headers()  → dict[str, str]   # return headers to merge into requests
│
├── StaticTokenAuthenticator           # fixed token
├── EnvTokenAuthenticator              # token from env var
└── OAuth2ClientCredentialsAuthenticator  # OAuth2 flow with caching

AuthRegistry
├── register(name, cls)               # add a provider
├── get(name) → cls                   # look up by name
└── unregister(name)                  # remove

create_authenticator(provider, **kwargs) → Authenticator   # factory
default_registry                                            # pre-populated instance
```

### Exception Hierarchy

```
AuthError                  # base for all auth errors
├── AuthConfigError        # missing config (no token, no URL, etc.)
└── AuthenticationError    # auth flow failed (HTTP error, bad response)
```

## Available Providers

### StaticTokenAuthenticator (`static`)

Uses a fixed bearer token.  The token can be passed to the constructor or
read from the `LOCUST_AUTH_TOKEN` environment variable.

| Parameter | Default | Description |
|---|---|---|
| `token` | `None` → env `LOCUST_AUTH_TOKEN` | Static token string |
| `header_name` | `"Authorization"` | HTTP header name |
| `header_format` | `"Bearer {token}"` | Format string with `{token}` placeholder |

**Use case:** development, testing against APIs with long-lived tokens.

```python
from locust_templates.auth import StaticTokenAuthenticator

auth = StaticTokenAuthenticator(token="my-secret-token")
headers = auth.get_headers()
# {"Authorization": "Bearer my-secret-token"}
```

### EnvTokenAuthenticator (`env`)

Reads a token from a configurable environment variable at call time.
Unlike `StaticTokenAuthenticator`, the token is not cached — it is re-read
on each `get_headers()` call, making it suitable for environments where the
token is rotated externally.

| Parameter | Default | Description |
|---|---|---|
| `env_var` | `"LOCUST_AUTH_TOKEN"` | Environment variable to read |
| `header_name` | `"Authorization"` | HTTP header name |
| `header_format` | `"Bearer {token}"` | Format string with `{token}` placeholder |

**Use case:** CI/CD pipelines where tokens are injected via secrets management.

```python
from locust_templates.auth import EnvTokenAuthenticator

# Reads from MY_CUSTOM_TOKEN env var
auth = EnvTokenAuthenticator(env_var="MY_CUSTOM_TOKEN")
headers = auth.get_headers()
```

### OAuth2ClientCredentialsAuthenticator (`oauth2-client-credentials`)

Performs an OAuth2 `client_credentials` grant to obtain a bearer token.
The token is cached at the class level (shared across all instances in the
same process) with thread-safe refresh.

| Parameter | Default | Env var fallback | Description |
|---|---|---|---|
| `token_url` | `""` | `LOCUST_OAUTH_TOKEN_URL` | OAuth2 token endpoint |
| `client_id` | `""` | `LOCUST_OAUTH_CLIENT_ID` | OAuth2 client ID |
| `client_secret` | `""` | `LOCUST_OAUTH_CLIENT_SECRET` | OAuth2 client secret |
| `scope` | `""` | — | Space-delimited scope string |
| `safety_margin` | `30` | — | Seconds before expiry to trigger refresh |
| `timeout` | `10` | — | HTTP timeout for token request |
| `header_name` | `"Authorization"` | — | HTTP header name |
| `header_format` | `"Bearer {token}"` | — | Format string |

**Use case:** enterprise APIs requiring short-lived tokens (banking, fintech,
healthcare).

```python
from locust_templates.auth import OAuth2ClientCredentialsAuthenticator

auth = OAuth2ClientCredentialsAuthenticator(
    token_url="https://auth.example.com/oauth/token",
    client_id="my-client-id",
    client_secret="my-client-secret",
    scope="read write",
    safety_margin=30,   # refresh 30s before expiry
)
headers = auth.get_headers()
# {"Authorization": "Bearer <token>"}
```

#### Token Caching and Thread Safety

- The token is stored in class-level variables (`_shared_token`,
  `_shared_expires_at`), so all instances within the same Python process
  share a single token.
- A `threading.Lock` protects the token refresh, ensuring that concurrent
  Locust users do not trigger duplicate token requests.
- The `safety_margin` parameter (default 30 seconds) causes refresh to
  happen *before* actual expiry, preventing 401 errors during a test run.
- Token expiry is tracked with `time.monotonic()`, which is immune to
  wall-clock adjustments.

## Configuration via Environment Variables

The `LoadTestConfig` dataclass reads auth-related environment variables:

| Env var | Config field | Default |
|---|---|---|
| `LOCUST_AUTH_PROVIDER` | `auth_provider` | `"static"` |
| `LOCUST_AUTH_TOKEN` | `auth_token` | `""` |
| `LOCUST_AUTH_CLIENT_ID` | `auth_client_id` | `""` |
| `LOCUST_AUTH_CLIENT_SECRET` | `auth_client_secret` | `""` |
| `LOCUST_AUTH_TOKEN_URL` | `auth_token_url` | `""` |
| `LOCUST_AUTH_SCOPES` | `auth_scopes` | `""` |

Example `.env` file:

```bash
LOCUST_AUTH_PROVIDER=oauth2-client-credentials
LOCUST_OAUTH_TOKEN_URL=https://auth.example.com/oauth/token
LOCUST_OAUTH_CLIENT_ID=my-client-id
LOCUST_OAUTH_CLIENT_SECRET=my-client-secret
LOCUST_AUTH_SCOPES=read write
```

## Integration with APIUser

The `APIUser` base class (in `api_load.py`) integrates auth automatically:

1. On `on_start()`, it calls `create_authenticator()` with the class-level
   `auth_provider` name and `auth_kwargs` dict.
2. The resulting `Authenticator` instance is stored as `self._authenticator`.
3. The `_get_token()` method calls `self._authenticator.get_headers()` to
   obtain the `Authorization` header for each request.
4. If auth setup fails (e.g. missing env var in dev), it falls back
   gracefully to `"test_token_123"`.

```python
from locust_templates.api_load import APIUser

class MyUser(APIUser):
    auth_provider = "env"          # read token from LOCUST_AUTH_TOKEN
    auth_kwargs = {}               # no extra config needed

class OAuthUser(APIUser):
    auth_provider = "oauth2-client-credentials"
    auth_kwargs = {
        "token_url": "https://auth.example.com/oauth/token",
        "client_id": "my-client-id",
        "client_secret": "my-client-secret",
    }
```

## Writing a Custom Authenticator

1. Extend the `Authenticator` ABC.
2. Implement `authenticate()` — validate config and fetch credentials if
   needed. Return a headers dict.
3. Optionally override `get_headers()` for lazy-refresh behaviour (the
   default just calls `authenticate()`).
4. Register the class with `default_registry.register(name, cls)` or use
   a standalone `AuthRegistry`.

```python
from locust_templates.auth import (
    Authenticator, AuthConfigError, default_registry
)

class HMACAuthenticator(Authenticator):
    """Custom HMAC-SHA256 authenticator."""

    def __init__(self, api_key: str = "", secret: str = "") -> None:
        self._api_key = api_key
        self._secret = secret

    def authenticate(self) -> dict[str, str]:
        if not self._api_key or not self._secret:
            raise AuthConfigError("HMAC requires api_key and secret")
        # Build HMAC signature here...
        return {"X-API-Key": self._api_key, "X-Signature": "..."}

# Register so create_authenticator("hmac") works
default_registry.register("hmac", HMACAuthenticator)
```

### Using a Standalone Registry

For isolation (test suites, multi-tenant setups), create a private
`AuthRegistry` instead of polluting the global one:

```python
from locust_templates.auth import AuthRegistry, create_authenticator, StaticTokenAuthenticator

private = AuthRegistry()
private.register("static", StaticTokenAuthenticator)
auth = create_authenticator("static", registry=private, token="abc123")
```

## Thread-Safety Notes

- `OAuth2ClientCredentialsAuthenticator` uses a `threading.Lock` to protect
  the shared token cache.  Multiple Locust users calling `get_headers()`
  concurrently will not trigger duplicate token requests — only the first
  caller performs the HTTP POST; others block on the lock and reuse the
  cached token.
- `StaticTokenAuthenticator` and `EnvTokenAuthenticator` are stateless
  (or read-only state) and inherently thread-safe.
- `AuthRegistry` is **not** thread-safe for `register()` / `unregister()`.
  Register all providers at import time before spawning users, not during
  the test run.

## Migration Guide: From Hardcoded `_get_token()` to Pluggable Auth

### Before (hardcoded)

```python
class MyUser(HttpUser):
    def _get_token(self):
        # Hardcoded or simple env-var read
        return os.environ.get("MY_API_TOKEN", "fallback-token")

    @task
    def get_data(self):
        self.client.get("/api/data", headers={"Authorization": f"Bearer {self._get_token()}"})
```

### After (pluggable)

```python
from locust_templates.api_load import APIUser

class MyUser(APIUser):
    auth_provider = "env"
    auth_kwargs = {"env_var": "MY_API_TOKEN"}

    @task
    def get_data(self):
        # _get_token() now delegates to the authenticator
        self.client.get("/api/data", headers={"Authorization": f"Bearer {self._get_token()}"})
```

### Migration Steps

1. Change the base class from `HttpUser` to `APIUser`.
2. Set `auth_provider` to `"static"`, `"env"`, or
   `"oauth2-client-credentials"`.
3. Move any constructor arguments into the `auth_kwargs` dict.
4. Remove the custom `_get_token()` method — `APIUser` provides one that
   delegates to the authenticator.
5. For OAuth2, move `client_id` / `client_secret` / `token_url` into env
   vars or `auth_kwargs`.
6. Test with `locust -f your_script.py --users 1 --run-time 10s` to verify
   the token is fetched correctly.
