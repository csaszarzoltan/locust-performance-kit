"""Acceptance tests for the pluggable auth system (TASK: pre-test).

These tests are written FIRST (TDD red phase) — they import from
``locust_templates.auth``, which does not exist yet.  The developer
(task t_fc01deb9) will implement the module to make all tests pass.

Pattern follows ``tests/unit/test_notifications.py``:
  - Interface smoke tests verify the API surface (classes, signatures).
  - Behavioral tests verify the contract with mocked dependencies.
  - HTTP calls are mocked with ``unittest.mock.patch`` (same as
    test_notifications.py) to avoid gevent / responses import-order
    conflicts.
"""

from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from locust_templates.auth import (
    AuthConfigError,
    AuthenticationError,
    Authenticator,
    AuthError,
    AuthRegistry,
    EnvTokenAuthenticator,
    OAuth2ClientCredentialsAuthenticator,
    StaticTokenAuthenticator,
    create_authenticator,
    default_registry,
)

# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_oauth2_shared_state():
    """Reset OAuth2 class-level shared token cache before/after each test."""
    OAuth2ClientCredentialsAuthenticator._shared_token = None
    OAuth2ClientCredentialsAuthenticator._shared_expires_at = 0.0
    yield
    OAuth2ClientCredentialsAuthenticator._shared_token = None
    OAuth2ClientCredentialsAuthenticator._shared_expires_at = 0.0


# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestInterfaceSmoke:
    """Verify that all classes exist with correct signatures."""

    def test_authenticator_is_abc(self):
        """Authenticator should be an abstract base class — can't instantiate."""
        with pytest.raises(TypeError):
            Authenticator()  # type: ignore[abstract]

    def test_static_token_authenticator_subclasses_authenticator(self):
        assert issubclass(StaticTokenAuthenticator, Authenticator)

    def test_env_token_authenticator_subclasses_authenticator(self):
        assert issubclass(EnvTokenAuthenticator, Authenticator)

    def test_oauth2_authenticator_subclasses_authenticator(self):
        assert issubclass(OAuth2ClientCredentialsAuthenticator, Authenticator)

    def test_static_token_init_accepts_token(self):
        """Constructor accepts token, header_name, header_format."""
        auth = StaticTokenAuthenticator(
            token="abc123",
            header_name="X-API-Key",
            header_format="{token}",
        )
        assert auth.header_name == "X-API-Key"
        assert auth.header_format == "{token}"

    def test_env_token_init_defaults(self):
        """Default env_var should be LOCUST_AUTH_TOKEN, header Authorization."""
        auth = EnvTokenAuthenticator()
        assert auth.env_var == "LOCUST_AUTH_TOKEN"
        assert auth.header_name == "Authorization"
        assert auth.header_format == "Bearer {token}"

    def test_oauth2_init_defaults(self):
        """OAuth2 constructor should have sensible defaults."""
        auth = OAuth2ClientCredentialsAuthenticator(
            token_url="https://example.com/token",
            client_id="id",
            client_secret="secret",
        )
        assert auth.safety_margin == 30
        assert auth.timeout == 10
        assert auth.header_name == "Authorization"
        assert auth.header_format == "Bearer {token}"

    def test_authenticator_has_authenticate_method(self):
        """All three providers must have authenticate()."""
        assert hasattr(StaticTokenAuthenticator, "authenticate")
        assert hasattr(EnvTokenAuthenticator, "authenticate")
        assert hasattr(OAuth2ClientCredentialsAuthenticator, "authenticate")

    def test_authenticator_has_get_headers_method(self):
        """All three providers must have get_headers()."""
        assert hasattr(StaticTokenAuthenticator, "get_headers")
        assert hasattr(EnvTokenAuthenticator, "get_headers")
        assert hasattr(OAuth2ClientCredentialsAuthenticator, "get_headers")

    def test_auth_error_exists(self):
        """AuthError should be an Exception."""
        assert issubclass(AuthError, Exception)

    def test_auth_config_error_subclasses_auth_error(self):
        assert issubclass(AuthConfigError, AuthError)

    def test_authentication_error_subclasses_auth_error(self):
        assert issubclass(AuthenticationError, AuthError)

    def test_auth_registry_exists(self):
        """AuthRegistry should be a class."""
        assert isinstance(AuthRegistry, type)

    def test_default_registry_has_builtins(self):
        """default_registry should have static, env, oauth2-client-credentials."""
        assert "static" in default_registry
        assert "env" in default_registry
        assert "oauth2-client-credentials" in default_registry
        assert default_registry.get("static") is StaticTokenAuthenticator
        assert default_registry.get("env") is EnvTokenAuthenticator
        assert (
            default_registry.get("oauth2-client-credentials")
            is OAuth2ClientCredentialsAuthenticator
        )

    def test_create_authenticator_exists(self):
        """create_authenticator should be callable."""
        assert callable(create_authenticator)


# ──────────────────────────────────────────────────────────────
# StaticTokenAuthenticator behavioral tests
# ──────────────────────────────────────────────────────────────


class TestStaticTokenAuthenticator:
    """Behavioral tests for the static-token provider."""

    def test_authenticate_with_valid_token(self):
        """authenticate() should succeed when token is non-empty."""
        auth = StaticTokenAuthenticator(token="my_token")
        auth.authenticate()  # should not raise

    def test_authenticate_raises_on_empty_token(self):
        """authenticate() should raise AuthConfigError when token is empty."""
        auth = StaticTokenAuthenticator(token="")
        with pytest.raises(AuthConfigError):
            auth.authenticate()

    def test_get_headers_returns_bearer_format(self):
        """get_headers() returns {'Authorization': 'Bearer <token>'}."""
        auth = StaticTokenAuthenticator(token="abc123")
        auth.authenticate()
        headers = auth.get_headers()
        assert headers == {"Authorization": "Bearer abc123"}

    def test_get_headers_custom_header_name(self):
        """Custom header_name should appear in the returned dict."""
        auth = StaticTokenAuthenticator(
            token="abc123",
            header_name="X-API-Key",
        )
        auth.authenticate()
        headers = auth.get_headers()
        assert headers == {"X-API-Key": "Bearer abc123"}

    def test_get_headers_custom_format(self):
        """Custom header_format should be applied."""
        auth = StaticTokenAuthenticator(
            token="abc123",
            header_format="{token}",
        )
        auth.authenticate()
        headers = auth.get_headers()
        assert headers == {"Authorization": "abc123"}


# ──────────────────────────────────────────────────────────────
# EnvTokenAuthenticator behavioral tests
# ──────────────────────────────────────────────────────────────


class TestEnvTokenAuthenticator:
    """Behavioral tests for the env-token provider."""

    def test_authenticate_reads_env_var(self):
        """With LOCUST_AUTH_TOKEN set, authenticate() succeeds."""
        with patch.dict(os.environ, {"LOCUST_AUTH_TOKEN": "env_token_value"}):
            auth = EnvTokenAuthenticator()
            auth.authenticate()
            headers = auth.get_headers()
        assert headers == {"Authorization": "Bearer env_token_value"}

    def test_authenticate_raises_on_missing_env(self):
        """With LOCUST_AUTH_TOKEN unset, authenticate() raises AuthConfigError."""
        with patch.dict(os.environ, {}, clear=True):
            auth = EnvTokenAuthenticator()
            with pytest.raises(AuthConfigError):
                auth.authenticate()

    def test_authenticate_raises_on_empty_env(self):
        """With LOCUST_AUTH_TOKEN='', authenticate() raises AuthConfigError."""
        with patch.dict(os.environ, {"LOCUST_AUTH_TOKEN": ""}):
            auth = EnvTokenAuthenticator()
            with pytest.raises(AuthConfigError):
                auth.authenticate()

    def test_custom_env_var(self):
        """Using env_var='MY_TOKEN' should read that variable."""
        with patch.dict(os.environ, {"MY_TOKEN": "custom_value"}):
            auth = EnvTokenAuthenticator(env_var="MY_TOKEN")
            auth.authenticate()
            headers = auth.get_headers()
        assert headers == {"Authorization": "Bearer custom_value"}

    def test_get_headers_returns_bearer_format(self):
        """Default format is Bearer."""
        with patch.dict(os.environ, {"LOCUST_AUTH_TOKEN": "tok123"}):
            auth = EnvTokenAuthenticator()
            auth.authenticate()
            headers = auth.get_headers()
        assert headers["Authorization"] == "Bearer tok123"


# ──────────────────────────────────────────────────────────────
# OAuth2ClientCredentialsAuthenticator behavioral tests
# ──────────────────────────────────────────────────────────────


class TestOAuth2ClientCredentialsAuthenticator:
    """Behavioral tests for the OAuth2 client-credentials provider.

    HTTP calls are mocked with ``patch('locust_templates.auth.requests')``
    to stay consistent with the test_notifications.py pattern and to
    avoid gevent / responses import-order conflicts.
    """

    TOKEN_URL = "https://auth.example.com/oauth/token"

    def _make_auth(self, **kwargs):
        """Helper: create an OAuth2 authenticator with required args."""
        defaults = dict(
            token_url=self.TOKEN_URL,
            client_id="test_client_id",
            client_secret="test_client_secret",
        )
        defaults.update(kwargs)
        return OAuth2ClientCredentialsAuthenticator(**defaults)

    def _mock_token_response(self, token="token_abc", expires_in=3600, status=200):
        """Build a MagicMock that looks like a requests.Response."""
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = {
            "access_token": token,
            "expires_in": expires_in,
        }
        resp.raise_for_status.return_value = None
        return resp

    def test_authenticate_requests_token(self):
        """authenticate() should POST grant_type=client_credentials."""
        with patch("locust_templates.auth.requests") as mock_requests:
            mock_requests.post.return_value = self._mock_token_response()
            auth = self._make_auth()
            auth.authenticate()
            mock_requests.post.assert_called_once()
            call_kwargs = mock_requests.post.call_args
            # Verify grant_type is in the POST data
            data = (
                call_kwargs[1].get("data") or call_kwargs[0][1]
                if len(call_kwargs[0]) > 1
                else call_kwargs[1].get("data", {})
            )
            assert "client_credentials" in str(data)

    def test_authenticate_caches_shared_token(self):
        """Two instances should share the same _shared_token after first auth."""
        with patch("locust_templates.auth.requests") as mock_requests:
            mock_requests.post.return_value = self._mock_token_response("shared_tok")
            auth1 = self._make_auth()
            auth2 = self._make_auth()
            auth1.authenticate()
            auth2.authenticate()
            # Only one HTTP call because the token is shared
            assert mock_requests.post.call_count == 1
            assert auth2._shared_token == "shared_tok"

    def test_authenticate_reuses_valid_token(self):
        """When _shared_token is valid, authenticate() does NOT call requests.post."""
        with patch("locust_templates.auth.requests") as mock_requests:
            mock_requests.post.return_value = self._mock_token_response("tok_reused")
            auth = self._make_auth()
            auth.authenticate()
            call_count_after_first = mock_requests.post.call_count
            # Second authenticate() should not make another HTTP call
            auth.authenticate()
            assert mock_requests.post.call_count == call_count_after_first

    def test_get_headers_returns_bearer_token(self):
        """After authenticate(), get_headers() returns Bearer token."""
        with patch("locust_templates.auth.requests") as mock_requests:
            mock_requests.post.return_value = self._mock_token_response("tok_header")
            auth = self._make_auth()
            auth.authenticate()
            headers = auth.get_headers()
        assert headers == {"Authorization": "Bearer tok_header"}

    def test_get_headers_refreshes_on_expiry(self):
        """When _shared_expires_at is past, get_headers() triggers _request_token()."""
        with patch("locust_templates.auth.requests") as mock_requests:
            mock_requests.post.return_value = self._mock_token_response("tok_refreshed")
            auth = self._make_auth()
            auth.authenticate()
            # Expire the token
            OAuth2ClientCredentialsAuthenticator._shared_expires_at = (
                time.monotonic() - 1
            )
            headers = auth.get_headers()
            # Should have made a second request to refresh
            assert mock_requests.post.call_count == 2
        assert headers == {"Authorization": "Bearer tok_refreshed"}

    def test_request_token_raises_on_http_error(self):
        """Non-200 response should raise AuthenticationError."""
        with patch("locust_templates.auth.requests") as mock_requests:
            mock_requests.post.return_value = MagicMock(
                status_code=500, text="server error"
            )
            auth = self._make_auth()
            with pytest.raises(AuthenticationError):
                auth.authenticate()

    def test_request_token_raises_on_network_error(self):
        """requests.post raising exception → AuthenticationError."""
        with patch("locust_templates.auth.requests") as mock_requests:
            mock_requests.post.side_effect = Exception("Connection refused")
            auth = self._make_auth()
            with pytest.raises(AuthenticationError):
                auth.authenticate()

    def test_authenticate_raises_on_missing_config(self):
        """Missing token_url/client_id/client_secret → AuthConfigError."""
        with patch.dict(os.environ, {}, clear=True):
            auth = OAuth2ClientCredentialsAuthenticator(
                token_url=None,
                client_id=None,
                client_secret=None,
            )
            with pytest.raises(AuthConfigError):
                auth.authenticate()

    def test_env_var_fallback(self):
        """Constructor args None + env vars set → authenticate() succeeds."""
        env = {
            "LOCUST_OAUTH_TOKEN_URL": self.TOKEN_URL,
            "LOCUST_OAUTH_CLIENT_ID": "env_client_id",
            "LOCUST_OAUTH_CLIENT_SECRET": "env_client_secret",
        }
        with patch.dict(os.environ, env, clear=False), patch(
            "locust_templates.auth.requests"
        ) as mock_requests:
                mock_requests.post.return_value = self._mock_token_response(
                    "env_fallback_tok"
                )
                auth = OAuth2ClientCredentialsAuthenticator(
                    token_url=None,
                    client_id=None,
                    client_secret=None,
                )
                auth.authenticate()
        assert (
            OAuth2ClientCredentialsAuthenticator._shared_token == "env_fallback_tok"
        )

    def test_is_token_valid_false_when_no_token(self):
        """_shared_token is None → _is_token_valid() returns False."""
        auth = self._make_auth()
        OAuth2ClientCredentialsAuthenticator._shared_token = None
        assert auth._is_token_valid() is False

    def test_is_token_valid_false_when_expired(self):
        """_shared_expires_at in the past → False."""
        auth = self._make_auth()
        OAuth2ClientCredentialsAuthenticator._shared_token = "some_tok"
        OAuth2ClientCredentialsAuthenticator._shared_expires_at = (
            time.monotonic() - 10
        )
        assert auth._is_token_valid() is False

    def test_is_token_valid_true_when_fresh(self):
        """_shared_expires_at far in future → True."""
        auth = self._make_auth()
        OAuth2ClientCredentialsAuthenticator._shared_token = "fresh_tok"
        OAuth2ClientCredentialsAuthenticator._shared_expires_at = (
            time.monotonic() + 3600
        )
        assert auth._is_token_valid() is True

    def test_safety_margin_triggers_early_refresh(self):
        """Token expires in 20s, safety_margin=30 → _is_token_valid() returns False."""
        auth = self._make_auth(safety_margin=30)
        OAuth2ClientCredentialsAuthenticator._shared_token = "marginal_tok"
        OAuth2ClientCredentialsAuthenticator._shared_expires_at = (
            time.monotonic() + 20
        )
        assert auth._is_token_valid() is False


# ──────────────────────────────────────────────────────────────
# AuthRegistry behavioral tests
# ──────────────────────────────────────────────────────────────


class TestAuthRegistry:
    """Tests for the AuthRegistry provider registry."""

    def test_register_and_get(self):
        """register(name, cls) then get(name) returns cls."""
        registry = AuthRegistry()
        registry.register("foo", StaticTokenAuthenticator)
        assert registry.get("foo") is StaticTokenAuthenticator

    def test_register_duplicate_raises(self):
        """Registering the same name twice raises ValueError."""
        registry = AuthRegistry()
        registry.register("foo", StaticTokenAuthenticator)
        with pytest.raises(ValueError):
            registry.register("foo", EnvTokenAuthenticator)

    def test_get_unknown_raises_keyerror(self):
        """get() for a non-existent name raises KeyError."""
        registry = AuthRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_unregister_removes(self):
        """unregister removes the entry; __contains__ returns False after."""
        registry = AuthRegistry()
        registry.register("foo", StaticTokenAuthenticator)
        assert "foo" in registry
        registry.unregister("foo")
        assert "foo" not in registry

    def test_unregister_unknown_raises(self):
        """unregister for unknown name raises KeyError."""
        registry = AuthRegistry()
        with pytest.raises(KeyError):
            registry.unregister("nonexistent")

    def test_contains(self):
        """__contains__ returns True after register, False before."""
        registry = AuthRegistry()
        assert "foo" not in registry
        registry.register("foo", StaticTokenAuthenticator)
        assert "foo" in registry


# ──────────────────────────────────────────────────────────────
# create_authenticator factory tests
# ──────────────────────────────────────────────────────────────


class TestCreateAuthenticator:
    """Tests for the create_authenticator factory function."""

    def test_create_default_provider(self):
        """create_authenticator() with no args returns EnvTokenAuthenticator."""
        auth = create_authenticator()
        assert isinstance(auth, EnvTokenAuthenticator)

    def test_create_static_provider(self):
        """create_authenticator('static', token=...) returns StaticTokenAuthenticator.

        Returns a StaticTokenAuthenticator instance."""
        auth = create_authenticator("static", token="abc")
        assert isinstance(auth, StaticTokenAuthenticator)

    def test_create_oauth2_provider(self):
        """create_authenticator('oauth2-client-credentials', ...) returns OAuth2."""
        auth = create_authenticator(
            "oauth2-client-credentials",
            token_url="https://example.com/token",
            client_id="id",
            client_secret="secret",
        )
        assert isinstance(auth, OAuth2ClientCredentialsAuthenticator)

    def test_create_unknown_provider_raises(self):
        """create_authenticator('nonexistent') raises AuthConfigError."""
        with pytest.raises(AuthConfigError):
            create_authenticator("nonexistent")

    def test_create_with_custom_registry(self):
        """Passing a custom AuthRegistry uses that registry."""
        registry = AuthRegistry()
        registry.register("custom", StaticTokenAuthenticator)
        auth = create_authenticator("custom", registry=registry, token="xyz")
        assert isinstance(auth, StaticTokenAuthenticator)


# ──────────────────────────────────────────────────────────────
# APIUser integration tests
# ──────────────────────────────────────────────────────────────


class TestAPIUserIntegration:
    """Test auth integration in APIUser (api_load.py).

    Uses APIUser.__new__(APIUser) pattern to avoid Locust HttpUser init.
    """

    def test_api_user_has_auth_provider_attribute(self):
        """APIUser class should have auth_provider defaulting to 'env'."""
        from locust_templates.api_load import APIUser
        assert hasattr(APIUser, "auth_provider")
        assert APIUser.auth_provider == "env"

    def test_api_user_has_auth_kwargs_attribute(self):
        """APIUser class should have auth_kwargs defaulting to empty dict."""
        from locust_templates.api_load import APIUser
        assert hasattr(APIUser, "auth_kwargs")
        assert APIUser.auth_kwargs == {}

    def test_on_start_creates_authenticator(self):
        """on_start() should set self._authenticator."""
        from locust_templates.api_load import APIUser
        user = APIUser.__new__(APIUser)
        # Use static provider to avoid env dependency
        user.auth_provider = "static"
        user.auth_kwargs = {"token": "test_token_123"}
        user.on_start()
        assert hasattr(user, "_authenticator")
        assert user._authenticator is not None

    def test_get_token_uses_cached_token(self):
        """_get_token() should return the token from the authenticator."""
        from locust_templates.api_load import APIUser
        user = APIUser.__new__(APIUser)
        user._authenticator = StaticTokenAuthenticator(token="test_token_123")
        user._authenticator.authenticate()
        token = user._get_token()
        assert isinstance(token, str)
        assert len(token) > 0
        assert token == "test_token_123"
