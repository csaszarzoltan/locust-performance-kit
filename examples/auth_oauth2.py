"""OAuth2 Client Credentials Auth Example.

Demonstrates how to use the pluggable auth system with an
OAuth2 client_credentials flow.  The token is fetched once
at user start-up, cached at the class level, and refreshed
automatically before expiry (thread-safe).

Usage:
    # Set OAuth2 credentials via env vars
    export LOCUST_OAUTH_TOKEN_URL=https://auth.example.com/oauth/token
    export LOCUST_OAUTH_CLIENT_ID=my-client-id
    export LOCUST_OAUTH_CLIENT_SECRET=my-client-secret
    export LOCUST_AUTH_SCOPES="read write"

    # Run with Locust
    locust -f examples/auth_oauth2.py --users 50 --spawn-rate 5 --run-time 2m

    # Or headless
    locust -f examples/auth_oauth2.py \\
        --headless --users 50 --spawn-rate 5 --run-time 2m \\
        --host https://api.example.com

Alternatively, pass credentials directly via auth_kwargs (not recommended
for shared environments — prefer env vars for secrets).
"""

import os
import sys
from pathlib import Path

# Ensure src is on the path for template imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from locust import between, task

from locust_templates.api_load import APIUser
from locust_templates.auth import (
    Authenticator,
    AuthRegistry,
    OAuth2ClientCredentialsAuthenticator,
    StaticTokenAuthenticator,
    create_authenticator,
    default_registry,
)

# ──────────────────────────────────────────────────────────────
# Example 1: APIUser subclass with OAuth2 client_credentials
# ──────────────────────────────────────────────────────────────

class OAuth2APIUser(APIUser):
    """API user that authenticates via OAuth2 client_credentials.

    Credentials are read from environment variables:
        LOCUST_OAUTH_TOKEN_URL
        LOCUST_OAUTH_CLIENT_ID
        LOCUST_OAUTH_CLIENT_SECRET
        LOCUST_AUTH_SCOPES (optional)
    """

    wait_time = between(1, 3)
    host = os.environ.get("LOCUST_HOST", "https://api.example.com")

    auth_provider = "oauth2-client-credentials"
    auth_kwargs = {
        # Pass explicitly or leave to env-var fallback
        "token_url": os.environ.get("LOCUST_OAUTH_TOKEN_URL", ""),
        "client_id": os.environ.get("LOCUST_OAUTH_CLIENT_ID", ""),
        "client_secret": os.environ.get("LOCUST_OAUTH_CLIENT_SECRET", ""),
        "scope": os.environ.get("LOCUST_AUTH_SCOPES", ""),
        "safety_margin": 30,   # refresh 30s before expiry
        "timeout": 10,         # HTTP timeout for token request
    }

    @task(3)
    def get_items(self):
        """GET /items — token is injected automatically by APIUser."""
        with self.client.get(
            "/api/v1/items",
            headers=self._authenticator.get_headers() if self._authenticator else {},
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Token expired or invalid")
            else:
                response.failure(f"Unexpected: {response.status_code}")

    @task(1)
    def create_item(self):
        """POST /items — demonstrates auth headers on a write endpoint."""
        with self.client.post(
            "/api/v1/items",
            json={"name": "test-item"},
            headers=self._authenticator.get_headers() if self._authenticator else {},
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                response.success()
            else:
                response.failure(f"Create failed: {response.status_code}")


# ──────────────────────────────────────────────────────────────
# Example 2: Register a custom authenticator
# ──────────────────────────────────────────────────────────────

class APIKeyAuthenticator(Authenticator):
    """Custom authenticator that sends an API key header.

    This demonstrates how to extend the Authenticator ABC for
    non-standard auth schemes (e.g. X-API-Key instead of Bearer).
    """

    def __init__(self, api_key: str = "", *, header_name: str = "X-API-Key") -> None:
        self._api_key = api_key or os.environ.get("MY_API_KEY", "")
        self.header_name = header_name

    def authenticate(self) -> dict[str, str]:
        if not self._api_key:
            from locust_templates.auth import AuthConfigError
            raise AuthConfigError(
                "No API key. Pass api_key to constructor or set MY_API_KEY env var."
            )
        return {self.header_name: self._api_key}

    def get_headers(self) -> dict[str, str]:
        return self.authenticate()


# Register the custom provider in the default registry
default_registry.register("api-key", APIKeyAuthenticator)


# ──────────────────────────────────────────────────────────────
# Example 3: Using a standalone registry (for isolation)
# ──────────────────────────────────────────────────────────────

def build_isolated_auth() -> Authenticator:
    """Create an authenticator from a private registry.

    Useful when you want to avoid polluting the global default_registry
    (e.g. in test suites or multi-tenant setups).
    """
    private_registry = AuthRegistry()
    private_registry.register("static", StaticTokenAuthenticator)
    private_registry.register("oauth2", OAuth2ClientCredentialsAuthenticator)

    return create_authenticator(
        "oauth2",
        registry=private_registry,
        token_url=os.environ.get("LOCUST_OAUTH_TOKEN_URL", ""),
        client_id=os.environ.get("LOCUST_OAUTH_CLIENT_ID", ""),
        client_secret=os.environ.get("LOCUST_OAUTH_CLIENT_SECRET", ""),
    )


# At import time, demonstrate that the custom provider is registered
if __name__ == "__main__":
    print("Registered providers:", sorted(default_registry._providers.keys()))
    # Output: ['api-key', 'env', 'oauth2-client-credentials', 'static']
