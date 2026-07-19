"""Pluggable authentication providers for Locust performance tests.

Provides a registry-based auth system where different authentication
strategies (static token, env-var token, OAuth2 client credentials)
can be plugged in at runtime via environment variables or configuration.

Public API:
    AuthError                          — base exception for auth errors
    AuthConfigError                    — raised when required config is missing
    AuthenticationError                — raised when the auth flow fails
    Authenticator                       — abstract base class
    StaticTokenAuthenticator           — token from constructor or env var
    EnvTokenAuthenticator              — token from configurable env var
    OAuth2ClientCredentialsAuthenticator — OAuth2 client_credentials flow
    AuthRegistry                       — provider registry (register/get/unregister)
    default_registry                   — pre-populated AuthRegistry instance
    create_authenticator               — factory function
"""

from __future__ import annotations

import os
import threading
import time
from abc import ABC, abstractmethod
from typing import Any

import requests

# ──────────────────────────────────────────────────────────────
# Exceptions
# ──────────────────────────────────────────────────────────────


class AuthError(Exception):
    """Base exception for all authentication-related errors."""


class AuthConfigError(AuthError):
    """Raised when required configuration (token, env var, URL) is missing."""


class AuthenticationError(AuthError):
    """Raised when the authentication flow fails (HTTP error, network error)."""


# ──────────────────────────────────────────────────────────────
# Abstract base class
# ──────────────────────────────────────────────────────────────


class Authenticator(ABC):
    """Abstract base class for authentication providers.

    Every concrete authenticator must implement authenticate() and
    get_headers().  authenticate() validates config and fetches any
    remote credentials; get_headers() returns the headers dict to
    merge into HTTP requests.
    """

    @abstractmethod
    def authenticate(self) -> dict[str, str]:
        """Validate config and fetch credentials if needed.

        Returns:
            A headers dict (e.g. ``{"Authorization": "Bearer <token>"}``).

        Raises:
            AuthConfigError: If required configuration is missing.
            AuthenticationError: If the authentication flow fails.
        """

    def get_headers(self) -> dict[str, str]:
        """Return the auth headers dict.

        Default implementation returns the result of authenticate().
        Subclasses may override for lazy-refresh behaviour (e.g. OAuth2).

        Raises:
            AuthConfigError: If configuration is missing.
            AuthenticationError: If the auth flow fails.
        """
        return self.authenticate()


# ──────────────────────────────────────────────────────────────
# StaticTokenAuthenticator
# ──────────────────────────────────────────────────────────────


class StaticTokenAuthenticator(Authenticator):
    """Auth provider that uses a static token.

    Reads the token from the constructor argument or the
    ``LOCUST_AUTH_TOKEN`` environment variable.

    Args:
        token: Static token string. If None, reads from ``LOCUST_AUTH_TOKEN``.
        header_name: HTTP header name (default ``"Authorization"``).
        header_format: Format string with ``{token}`` placeholder
            (default ``"Bearer {token}"``).
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        header_name: str = "Authorization",
        header_format: str = "Bearer {token}",
    ) -> None:
        self._token = token if token is not None else os.getenv("LOCUST_AUTH_TOKEN", "")
        self.header_name = header_name
        self.header_format = header_format

    def authenticate(self) -> dict[str, str]:
        """Validate that a non-empty token is available.

        Raises:
            AuthConfigError: If the token is empty.
        """
        if not self._token:
            raise AuthConfigError(
                "No static token configured. Pass token to constructor "
                "or set LOCUST_AUTH_TOKEN env var."
            )
        return self.get_headers()

    def get_headers(self) -> dict[str, str]:
        """Return ``{header_name: header_format.format(token=token)}``.

        Raises:
            AuthConfigError: If the token is empty.
        """
        if not self._token:
            raise AuthConfigError(
                "No static token configured. Pass token to constructor "
                "or set LOCUST_AUTH_TOKEN env var."
            )
        value = self.header_format.format(token=self._token)
        return {self.header_name: value}


# ──────────────────────────────────────────────────────────────
# EnvTokenAuthenticator
# ──────────────────────────────────────────────────────────────


class EnvTokenAuthenticator(Authenticator):
    """Auth provider that reads a token from an environment variable.

    Args:
        env_var: Name of the environment variable to read
            (default ``"LOCUST_AUTH_TOKEN"``).
        header_name: HTTP header name (default ``"Authorization"``).
        header_format: Format string with ``{token}`` placeholder
            (default ``"Bearer {token}"``).
    """

    def __init__(
        self,
        env_var: str = "LOCUST_AUTH_TOKEN",
        *,
        header_name: str = "Authorization",
        header_format: str = "Bearer {token}",
    ) -> None:
        self.env_var = env_var
        self.header_name = header_name
        self.header_format = header_format
        self._token: str = ""

    def authenticate(self) -> dict[str, str]:
        """Read the token from the configured env var.

        Raises:
            AuthConfigError: If the env var is missing or empty.
        """
        self._token = os.environ.get(self.env_var, "")
        if not self._token:
            raise AuthConfigError(
                f"Environment variable '{self.env_var}' is not set or empty."
            )
        return self.get_headers()

    def get_headers(self) -> dict[str, str]:
        """Return ``{header_name: header_format.format(token=token)}``.

        Raises:
            AuthConfigError: If the token has not been loaded yet.
        """
        if not self._token:
            self._token = os.environ.get(self.env_var, "")
        if not self._token:
            raise AuthConfigError(
                f"Environment variable '{self.env_var}' is not set or empty."
            )
        value = self.header_format.format(token=self._token)
        return {self.header_name: value}


# ──────────────────────────────────────────────────────────────
# OAuth2ClientCredentialsAuthenticator
# ──────────────────────────────────────────────────────────────


class OAuth2ClientCredentialsAuthenticator(Authenticator):
    """OAuth2 client-credentials flow authenticator.

    Performs an HTTP POST to ``token_url`` with ``client_id`` and
    ``client_secret`` in form data to obtain a bearer token.  The
    token is cached at the class level so multiple instances within
    the same process share a single token (thread-safe via a lock).

    Constructor args that are ``None`` fall back to environment
    variables:

        token_url      → LOCUST_OAUTH_TOKEN_URL
        client_id      → LOCUST_OAUTH_CLIENT_ID
        client_secret  → LOCUST_OAUTH_CLIENT_SECRET

    Args:
        token_url: OAuth2 token endpoint URL.
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret.
        scope: Optional OAuth2 scope string (space-delimited).
        safety_margin: Seconds before expiry to trigger refresh (default 30).
        timeout: HTTP request timeout in seconds (default 10).
        header_name: HTTP header name (default ``"Authorization"``).
        header_format: Format string (default ``"Bearer {token}"``).
    """

    # Class-level shared token cache (all instances share one token)
    _shared_token: str | None = None
    _shared_expires_at: float = 0.0
    _lock = threading.Lock()

    def __init__(
        self,
        token_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        *,
        scope: str = "",
        safety_margin: int = 30,
        timeout: int = 10,
        header_name: str = "Authorization",
        header_format: str = "Bearer {token}",
    ) -> None:
        self.token_url = token_url or os.getenv("LOCUST_OAUTH_TOKEN_URL", "")
        self.client_id = client_id or os.getenv("LOCUST_OAUTH_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv(
            "LOCUST_OAUTH_CLIENT_SECRET", ""
        )
        self.scope = scope
        self.safety_margin = safety_margin
        self.timeout = timeout
        self.header_name = header_name
        self.header_format = header_format

    # ── internal helpers ──────────────────────────────────

    def _is_token_valid(self) -> bool:
        """Return True if a shared token exists and has not expired.

        The ``safety_margin`` is subtracted from the remaining lifetime
        so that refresh happens *before* actual expiry.
        """
        if self._shared_token is None:
            return False
        return time.monotonic() + self.safety_margin < self._shared_expires_at

    def _request_token(self) -> None:
        """POST to ``token_url`` and store the result in shared cache.

        Raises:
            AuthConfigError: If token_url / client_id / client_secret are missing.
            AuthenticationError: If the HTTP request fails or returns non-200.
        """
        if not self.token_url or not self.client_id or not self.client_secret:
            raise AuthConfigError(
                "OAuth2 client_credentials requires token_url, client_id, "
                "and client_secret. Set them via constructor args or "
                "LOCUST_OAUTH_TOKEN_URL / LOCUST_OAUTH_CLIENT_ID / "
                "LOCUST_OAUTH_CLIENT_SECRET env vars."
            )

        data: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.scope:
            data["scope"] = self.scope

        try:
            resp = requests.post(
                self.token_url,
                data=data,
                timeout=self.timeout,
            )
        except Exception as exc:
            raise AuthenticationError(
                f"OAuth2 token request failed: {exc}"
            ) from exc

        if resp.status_code != 200:
            raise AuthenticationError(
                f"OAuth2 token endpoint returned HTTP {resp.status_code}: "
                f"{getattr(resp, 'text', '')}"
            )

        try:
            body = resp.json()
        except Exception as exc:
            raise AuthenticationError(
                f"OAuth2 token response is not valid JSON: {exc}"
            ) from exc

        token = body.get("access_token")
        expires_in = body.get("expires_in", 3600)
        if not token:
            raise AuthenticationError(
                "OAuth2 token response did not contain 'access_token'."
            )

        with self._lock:
            OAuth2ClientCredentialsAuthenticator._shared_token = token
            OAuth2ClientCredentialsAuthenticator._shared_expires_at = (
                time.monotonic() + float(expires_in)
            )

    # ── public API ─────────────────────────────────────────

    def authenticate(self) -> dict[str, str]:
        """Ensure a valid token is cached, then return headers.

        If the shared token is still valid, no HTTP call is made.

        Raises:
            AuthConfigError: If required config is missing.
            AuthenticationError: If the token request fails.
        """
        if not self._is_token_valid():
            self._request_token()
        return self.get_headers()

    def get_headers(self) -> dict[str, str]:
        """Return ``{header_name: header_format.format(token=token)}``.

        If the cached token has expired, a refresh is triggered first.

        Raises:
            AuthConfigError: If required config is missing.
            AuthenticationError: If the token request fails.
        """
        if not self._is_token_valid():
            self._request_token()
        token = self._shared_token or ""
        value = self.header_format.format(token=token)
        return {self.header_name: value}


# ──────────────────────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────────────────────


class AuthRegistry:
    """Registry of named authenticator classes.

    Allows third-party code to register custom auth providers and
    look them up by name at runtime.

    Usage::

        registry = AuthRegistry()
        registry.register("my-auth", MyAuthenticator)
        cls = registry.get("my-auth")
    """

    def __init__(self) -> None:
        self._providers: dict[str, type[Authenticator]] = {}

    def register(self, name: str, provider_class: type[Authenticator]) -> None:
        """Register *provider_class* under *name*.

        Raises:
            ValueError: If *name* is already registered.
        """
        if name in self._providers:
            raise ValueError(f"Auth provider '{name}' is already registered.")
        self._providers[name] = provider_class

    def unregister(self, name: str) -> None:
        """Remove the provider registered under *name*.

        Raises:
            KeyError: If *name* is not registered.
        """
        if name not in self._providers:
            raise KeyError(name)
        del self._providers[name]

    def get(self, name: str) -> type[Authenticator]:
        """Return the provider class registered under *name*.

        Raises:
            KeyError: If *name* is not registered.
        """
        if name not in self._providers:
            raise KeyError(name)
        return self._providers[name]

    def __contains__(self, name: str) -> bool:
        return name in self._providers


# ──────────────────────────────────────────────────────────────
# Default registry + factory
# ──────────────────────────────────────────────────────────────

default_registry = AuthRegistry()
default_registry.register("static", StaticTokenAuthenticator)
default_registry.register("env", EnvTokenAuthenticator)
default_registry.register(
    "oauth2-client-credentials", OAuth2ClientCredentialsAuthenticator
)


def create_authenticator(
    provider: str = "env",
    *,
    registry: AuthRegistry | None = None,
    **kwargs: Any,
) -> Authenticator:
    """Factory: create an Authenticator by provider name.

    Args:
        provider: Provider name in the registry (default ``"env"``).
        registry: Custom registry to use instead of ``default_registry``.
        **kwargs: Passed to the provider's constructor.

    Returns:
        An instance of the requested Authenticator subclass.

    Raises:
        AuthConfigError: If the provider name is not in the registry.
    """
    reg = registry if registry is not None else default_registry
    try:
        cls = reg.get(provider)
    except KeyError as exc:
        raise AuthConfigError(
            f"Unknown auth provider '{provider}'. "
            f"Available: {', '.join(sorted(reg._providers.keys()))}"
        ) from exc
    return cls(**kwargs)


__all__ = [
    "AuthConfigError",
    "AuthError",
    "AuthRegistry",
    "AuthenticationError",
    "Authenticator",
    "EnvTokenAuthenticator",
    "OAuth2ClientCredentialsAuthenticator",
    "StaticTokenAuthenticator",
    "create_authenticator",
    "default_registry",
]
