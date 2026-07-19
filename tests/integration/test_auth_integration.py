"""Integration tests for the pluggable auth system.

Tests cover:
  - OAuth2 client_credentials flow end-to-end with mocked HTTP
  - APIUser lifecycle (on_start → task → _get_token) with each provider
  - Config loading with auth env vars set
  - Backwards compatibility: no auth provider configured → static token works

HTTP calls are mocked with ``unittest.mock.patch`` (same pattern as
``tests/unit/test_auth.py``) to avoid gevent / responses import-order
conflicts with locust's SSL monkey-patching.
"""

from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from locust_templates.auth import (
    AuthenticationError,
    EnvTokenAuthenticator,
    OAuth2ClientCredentialsAuthenticator,
    StaticTokenAuthenticator,
    create_authenticator,
)
from locust_templates.config import LoadTestConfig, load_config

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


def _mock_token_response(
    token: str = "mock_tok",
    expires_in: int = 3600,
    status: int = 200,
    body: str | None = None,
) -> MagicMock:
    """Build a MagicMock that looks like a requests.Response."""
    resp = MagicMock()
    resp.status_code = status
    if body is not None:
        resp.text = body
        resp.json.side_effect = Exception("not JSON")
    else:
        resp.json.return_value = {
            "access_token": token,
            "expires_in": expires_in,
        }
    resp.raise_for_status.return_value = None
    return resp


# ──────────────────────────────────────────────────────────────
# OAuth2 end-to-end with mocked HTTP
# ──────────────────────────────────────────────────────────────


class TestOAuth2EndToEnd:
    """End-to-end OAuth2 client_credentials flow using mocked requests."""

    TOKEN_URL = "https://auth.example.com/oauth/token"

    def _make_auth(self, **kwargs):
        """Helper: create an OAuth2 authenticator with required args."""
        defaults = dict(
            token_url=self.TOKEN_URL,
            client_id="e2e_client",
            client_secret="e2e_secret",
        )
        defaults.update(kwargs)
        return OAuth2ClientCredentialsAuthenticator(**defaults)

    def test_full_oauth2_flow_returns_valid_token(self):
        """POST to token endpoint → access_token cached → headers returned."""
        with patch("locust_templates.auth.requests") as mock_req:
            mock_req.post.return_value = _mock_token_response("e2e_token_abc")
            auth = self._make_auth()
            auth.authenticate()
            headers = auth.get_headers()

        assert headers == {"Authorization": "Bearer e2e_token_abc"}

    def test_oauth2_sends_client_credentials_grant_type(self):
        """The POST body must contain grant_type=client_credentials."""
        with patch("locust_templates.auth.requests") as mock_req:
            mock_req.post.return_value = _mock_token_response()
            auth = self._make_auth(client_id="cid", client_secret="csec")
            auth.authenticate()

            assert mock_req.post.call_count == 1
            call_kwargs = mock_req.post.call_args
            data = call_kwargs[1].get("data", {})
            assert data["grant_type"] == "client_credentials"
            assert data["client_id"] == "cid"
            assert data["client_secret"] == "csec"

    def test_oauth2_includes_scope_when_set(self):
        """When scope is provided, it appears in the POST data."""
        with patch("locust_templates.auth.requests") as mock_req:
            mock_req.post.return_value = _mock_token_response("scoped_tok")
            auth = self._make_auth(scope="read write")
            auth.authenticate()

            data = mock_req.post.call_args[1]["data"]
            assert data["scope"] == "read write"

    def test_oauth2_caches_token_across_multiple_calls(self):
        """Multiple authenticate() calls → only one HTTP POST."""
        with patch("locust_templates.auth.requests") as mock_req:
            mock_req.post.return_value = _mock_token_response("cached_tok")
            auth = self._make_auth()
            auth.authenticate()
            auth.authenticate()
            auth.get_headers()

            assert mock_req.post.call_count == 1

    def test_oauth2_refreshes_after_expiry(self):
        """When token expires, a new POST is made to refresh."""
        with patch("locust_templates.auth.requests") as mock_req:
            mock_req.post.return_value = _mock_token_response("first_tok")
            auth = self._make_auth()
            auth.authenticate()
            assert mock_req.post.call_count == 1

            # Expire the token
            OAuth2ClientCredentialsAuthenticator._shared_expires_at = (
                time.monotonic() - 1
            )

            # Update mock for refresh response
            mock_req.post.return_value = _mock_token_response("refreshed_tok")
            headers = auth.get_headers()

            assert mock_req.post.call_count == 2
            assert headers == {"Authorization": "Bearer refreshed_tok"}

    def test_oauth2_raises_on_500_response(self):
        """HTTP 500 from token endpoint → AuthenticationError."""
        with patch("locust_templates.auth.requests") as mock_req:
            mock_req.post.return_value = MagicMock(
                status_code=500, text="server error"
            )
            auth = self._make_auth()
            with pytest.raises(AuthenticationError):
                auth.authenticate()

    def test_oauth2_raises_on_missing_access_token(self):
        """Response without access_token → AuthenticationError."""
        with patch("locust_templates.auth.requests") as mock_req:
            mock_req.post.return_value = MagicMock(status_code=200)
            mock_req.post.return_value.json.return_value = {
                "error": "invalid_client"
            }
            auth = self._make_auth()
            with pytest.raises(AuthenticationError):
                auth.authenticate()

    def test_oauth2_raises_on_invalid_json(self):
        """Non-JSON response → AuthenticationError."""
        with patch("locust_templates.auth.requests") as mock_req:
            mock_req.post.return_value = _mock_token_response(
                body="<html>Bad Gateway</html>", status=502
            )
            auth = self._make_auth()
            with pytest.raises(AuthenticationError):
                auth.authenticate()

    def test_oauth2_shared_cache_across_instances(self):
        """Two separate instances share the same cached token."""
        with patch("locust_templates.auth.requests") as mock_req:
            mock_req.post.return_value = _mock_token_response("shared_e2e")
            auth1 = self._make_auth()
            auth2 = self._make_auth()
            auth1.authenticate()
            headers2 = auth2.get_headers()

            assert mock_req.post.call_count == 1
            assert headers2 == {"Authorization": "Bearer shared_e2e"}

    def test_oauth2_custom_header_name_and_format(self):
        """Custom header_name and header_format are respected end-to-end."""
        with patch("locust_templates.auth.requests") as mock_req:
            mock_req.post.return_value = _mock_token_response("custom_tok")
            auth = self._make_auth(
                header_name="X-API-Key",
                header_format="Token {token}",
            )
            auth.authenticate()
            headers = auth.get_headers()

        assert headers == {"X-API-Key": "Token custom_tok"}

    def test_oauth2_network_error_raises_authentication_error(self):
        """Network error during token request → AuthenticationError."""
        with patch("locust_templates.auth.requests") as mock_req:
            mock_req.post.side_effect = ConnectionError("DNS resolution failed")
            auth = self._make_auth()
            with pytest.raises(AuthenticationError):
                auth.authenticate()

    def test_oauth2_env_var_fallback_e2e(self):
        """Constructor args None + env vars set → full flow works."""
        env = {
            "LOCUST_OAUTH_TOKEN_URL": self.TOKEN_URL,
            "LOCUST_OAUTH_CLIENT_ID": "env_client",
            "LOCUST_OAUTH_CLIENT_SECRET": "env_secret",
        }
        with (
            patch.dict(os.environ, env, clear=False),
            patch("locust_templates.auth.requests") as mock_req,
        ):
            mock_req.post.return_value = _mock_token_response(
                "env_fallback_e2e"
            )
            auth = OAuth2ClientCredentialsAuthenticator(
                token_url=None,
                client_id=None,
                client_secret=None,
            )
            auth.authenticate()

        assert (
            OAuth2ClientCredentialsAuthenticator._shared_token
            == "env_fallback_e2e"
        )


# ──────────────────────────────────────────────────────────────
# APIUser lifecycle with each auth provider
# ──────────────────────────────────────────────────────────────


class TestAPIUserLifecycle:
    """Test APIUser on_start → _get_token lifecycle with each provider."""

    def test_lifecycle_with_static_provider(self):
        """on_start → _get_token with static provider returns the token."""
        from locust_templates.api_load import APIUser

        user = APIUser.__new__(APIUser)
        user.auth_provider = "static"
        user.auth_kwargs = {"token": "static_lifecycle_tok"}
        user.on_start()

        assert user._authenticator is not None
        token = user._get_token()
        assert token == "static_lifecycle_tok"

    def test_lifecycle_with_env_provider(self):
        """on_start → _get_token with env provider reads from env var."""
        from locust_templates.api_load import APIUser

        with patch.dict(os.environ, {"LOCUST_AUTH_TOKEN": "env_lifecycle_tok"}):
            user = APIUser.__new__(APIUser)
            user.auth_provider = "env"
            user.auth_kwargs = {}
            user.on_start()

            assert user._authenticator is not None
            token = user._get_token()
            assert token == "env_lifecycle_tok"

    def test_lifecycle_with_oauth2_provider(self):
        """on_start → _get_token with oauth2 provider fetches a token."""
        from locust_templates.api_load import APIUser

        with patch("locust_templates.auth.requests") as mock_req:
            mock_req.post.return_value = _mock_token_response(
                "oauth_lifecycle_tok"
            )
            user = APIUser.__new__(APIUser)
            user.auth_provider = "oauth2-client-credentials"
            user.auth_kwargs = {
                "token_url": "https://auth.example.com/token",
                "client_id": "lc_id",
                "client_secret": "lc_secret",
            }
            user.on_start()

            assert user._authenticator is not None
            token = user._get_token()
            assert token == "oauth_lifecycle_tok"

    def test_on_start_fallback_on_auth_failure(self):
        """When auth setup fails, _authenticator is None and _get_token falls back."""
        from locust_templates.api_load import APIUser

        with patch.dict(os.environ, {}, clear=True):
            user = APIUser.__new__(APIUser)
            user.auth_provider = "env"
            user.auth_kwargs = {}
            user.on_start()

            # _authenticator should be None due to fallback
            assert user._authenticator is None
            # _get_token should return the fallback token
            token = user._get_token()
            assert token == "test_token_123"

    def test_get_token_returns_string_from_authenticator(self):
        """_get_token returns a non-empty string when auth is configured."""
        from locust_templates.api_load import APIUser

        user = APIUser.__new__(APIUser)
        user._authenticator = StaticTokenAuthenticator(token="direct_token")
        user._authenticator.authenticate()
        token = user._get_token()
        assert isinstance(token, str)
        assert token == "direct_token"

    def test_get_token_with_custom_header_format(self):
        """_get_token extracts the token from custom header formats."""
        from locust_templates.api_load import APIUser

        user = APIUser.__new__(APIUser)
        user._authenticator = StaticTokenAuthenticator(
            token="raw_token",
            header_format="{token}",
        )
        user._authenticator.authenticate()
        token = user._get_token()
        # When format is "{token}", there's no "Bearer " prefix
        assert token == "raw_token"

    def test_lifecycle_multiple_tasks_share_token(self):
        """Multiple _get_token() calls return the same cached token."""
        from locust_templates.api_load import APIUser

        user = APIUser.__new__(APIUser)
        user.auth_provider = "static"
        user.auth_kwargs = {"token": "multi_call_tok"}
        user.on_start()

        t1 = user._get_token()
        t2 = user._get_token()
        t3 = user._get_token()
        assert t1 == t2 == t3 == "multi_call_tok"


# ──────────────────────────────────────────────────────────────
# Config loading with auth env vars
# ──────────────────────────────────────────────────────────────


class TestConfigAuthEnvVars:
    """Test LoadTestConfig.from_env() with auth-related env vars."""

    def test_auth_provider_from_env(self):
        """LOCUST_AUTH_PROVIDER sets config.auth_provider."""
        with patch.dict(
            os.environ, {"LOCUST_AUTH_PROVIDER": "oauth2-client-credentials"}
        ):
            config = LoadTestConfig.from_env()
            assert config.auth_provider == "oauth2-client-credentials"

    def test_auth_client_id_from_env(self):
        """LOCUST_AUTH_CLIENT_ID sets config.auth_client_id."""
        with patch.dict(
            os.environ, {"LOCUST_AUTH_CLIENT_ID": "cfg_client_id"}
        ):
            config = LoadTestConfig.from_env()
            assert config.auth_client_id == "cfg_client_id"

    def test_auth_client_secret_from_env(self):
        """LOCUST_AUTH_CLIENT_SECRET sets config.auth_client_secret."""
        with patch.dict(
            os.environ, {"LOCUST_AUTH_CLIENT_SECRET": "cfg_secret"}
        ):
            config = LoadTestConfig.from_env()
            assert config.auth_client_secret == "cfg_secret"

    def test_auth_token_url_from_env(self):
        """LOCUST_AUTH_TOKEN_URL sets config.auth_token_url."""
        with patch.dict(
            os.environ,
            {"LOCUST_AUTH_TOKEN_URL": "https://cfg.example.com/token"},
        ):
            config = LoadTestConfig.from_env()
            assert config.auth_token_url == "https://cfg.example.com/token"

    def test_auth_scopes_from_env(self):
        """LOCUST_AUTH_SCOPES sets config.auth_scopes."""
        with patch.dict(
            os.environ, {"LOCUST_AUTH_SCOPES": "read write admin"}
        ):
            config = LoadTestConfig.from_env()
            assert config.auth_scopes == "read write admin"

    def test_all_auth_fields_default(self):
        """With no auth env vars, config gets sensible defaults."""
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith("LOCUST_")
        }
        with patch.dict(os.environ, env, clear=True):
            config = LoadTestConfig.from_env()
            assert config.auth_provider == "static"
            assert config.auth_client_id == ""
            assert config.auth_client_secret == ""
            assert config.auth_token_url == ""
            assert config.auth_scopes == ""

    def test_load_config_with_auth_env_vars(self):
        """load_config() reads auth env vars correctly."""
        env = {
            "LOCUST_AUTH_PROVIDER": "env",
            "LOCUST_AUTH_TOKEN": "loaded_token",
        }
        with patch.dict(os.environ, env, clear=False):
            config = load_config()
            assert config.auth_provider == "env"
            assert config.auth_token == "loaded_token"

    def test_load_config_dotenv_with_auth(self, tmp_path):
        """load_config() reads auth vars from a .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "LOCUST_AUTH_PROVIDER=oauth2-client-credentials\n"
            "LOCUST_AUTH_CLIENT_ID=dotenv_client\n"
            "LOCUST_AUTH_CLIENT_SECRET=dotenv_secret\n"
            "LOCUST_AUTH_TOKEN_URL=https://dotenv.example.com/token\n"
        )
        config = load_config(env_file=str(env_file))
        assert config.auth_provider == "oauth2-client-credentials"
        assert config.auth_client_id == "dotenv_client"
        assert config.auth_client_secret == "dotenv_secret"
        assert config.auth_token_url == "https://dotenv.example.com/token"

    def test_env_overrides_dotenv_for_auth(self, tmp_path):
        """Env vars override .env for auth fields."""
        env_file = tmp_path / ".env"
        env_file.write_text("LOCUST_AUTH_PROVIDER=static\n")
        with patch.dict(os.environ, {"LOCUST_AUTH_PROVIDER": "env"}):
            config = load_config(env_file=str(env_file))
            assert config.auth_provider == "env"


# ──────────────────────────────────────────────────────────────
# Backwards compatibility
# ──────────────────────────────────────────────────────────────


class TestBackwardsCompatibility:
    """Verify that existing code without auth providers still works."""

    def test_no_auth_provider_configured_static_token_works(self):
        """Default auth_provider='static' + auth_token → works."""
        with patch.dict(os.environ, {"LOCUST_AUTH_TOKEN": "legacy_token"}):
            auth = create_authenticator("static")
            auth.authenticate()
            headers = auth.get_headers()
        assert headers == {"Authorization": "Bearer legacy_token"}

    def test_no_auth_env_set_static_constructor_token(self):
        """StaticTokenAuthenticator with constructor arg works without env."""
        auth = StaticTokenAuthenticator(token="constructor_only_token")
        auth.authenticate()
        headers = auth.get_headers()
        assert headers == {"Authorization": "Bearer constructor_only_token"}

    def test_api_user_default_auth_provider_is_env(self):
        """APIUser.auth_provider defaults to 'env' (unchanged from before)."""
        from locust_templates.api_load import APIUser

        assert APIUser.auth_provider == "env"

    def test_api_user_fallback_token_without_auth(self):
        """When no authenticator is set, _get_token returns fallback token."""
        from locust_templates.api_load import APIUser

        user = APIUser.__new__(APIUser)
        # Don't call on_start — simulates no auth configured
        token = user._get_token()
        assert token == "test_token_123"

    def test_config_default_auth_provider_is_static(self):
        """LoadTestConfig.auth_provider defaults to 'static'."""
        config = LoadTestConfig()
        assert config.auth_provider == "static"

    def test_env_provider_reads_locust_auth_token(self):
        """EnvTokenAuthenticator reads LOCUST_AUTH_TOKEN (same as before)."""
        with patch.dict(os.environ, {"LOCUST_AUTH_TOKEN": "compat_env_token"}):
            auth = EnvTokenAuthenticator()
            auth.authenticate()
            headers = auth.get_headers()
        assert headers == {"Authorization": "Bearer compat_env_token"}

    def test_registry_has_static_provider(self):
        """The 'static' provider is registered by default for backwards compat."""
        from locust_templates.auth import default_registry

        assert "static" in default_registry
        cls = default_registry.get("static")
        assert cls is StaticTokenAuthenticator

    def test_factory_creates_static_with_token_kwarg(self):
        """create_authenticator('static', token=...) works as before."""
        auth = create_authenticator("static", token="factory_static_tok")
        assert isinstance(auth, StaticTokenAuthenticator)
        auth.authenticate()
        assert auth.get_headers() == {
            "Authorization": "Bearer factory_static_tok"
        }
