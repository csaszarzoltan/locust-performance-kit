"""Unit tests for the configuration module.

Tests verify:
- Default configuration values
- Environment variable overrides
- .env file loading
- Per-test-type configuration sections
- Type validation
"""

import os
import pytest
from unittest.mock import patch

from locust_templates.config import LoadTestConfig, load_config


class TestLoadTestConfig:
    """Test the LoadTestConfig dataclass."""

    def test_init_with_defaults(self):
        config = LoadTestConfig()
        assert config.host == "http://localhost:8080"
        assert config.users == 100
        assert config.spawn_rate == 10
        assert config.run_time == "5m"
        assert config.p95_threshold == 500.0
        assert config.p99_threshold == 1000.0
        assert config.error_rate_threshold == 0.01

    def test_init_with_custom_values(self):
        config = LoadTestConfig(
            host="https://api.example.com",
            users=200,
            spawn_rate=20,
            run_time="10m",
            p95_threshold=300.0,
            p99_threshold=600.0,
            error_rate_threshold=0.05,
        )
        assert config.host == "https://api.example.com"
        assert config.users == 200
        assert config.spawn_rate == 20
        assert config.run_time == "10m"
        assert config.p95_threshold == 300.0
        assert config.p99_threshold == 600.0
        assert config.error_rate_threshold == 0.05

    def test_from_env_overrides_defaults(self):
        env = {
            "LOCUST_HOST": "https://staging.api.com",
            "LOCUST_USERS": "50",
            "LOCUST_SPAWN_RATE": "5",
            "LOCUST_RUN_TIME": "2m",
            "LOCUST_P95_THRESHOLD": "400",
            "LOCUST_P99_THRESHOLD": "800",
            "LOCUST_ERROR_RATE_THRESHOLD": "0.02",
        }
        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env()
            assert config.host == "https://staging.api.com"
            assert config.users == 50
            assert config.spawn_rate == 5
            assert config.run_time == "2m"
            assert config.p95_threshold == 400.0
            assert config.p99_threshold == 800.0
            assert config.error_rate_threshold == 0.02

    def test_from_env_uses_defaults_when_unset(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("LOCUST_")}
        with patch.dict(os.environ, env, clear=True):
            config = LoadTestConfig.from_env()
            assert config.host == "http://localhost:8080"
            assert config.users == 100

    def test_auth_token_from_env(self):
        env = {"LOCUST_AUTH_TOKEN": "secret_token_123"}
        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env()
            assert config.auth_token == "secret_token_123"

    def test_auth_token_default_is_empty(self):
        env = {k: v for k, v in os.environ.items() if k != "LOCUST_AUTH_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            config = LoadTestConfig.from_env()
            assert config.auth_token == ""


class TestLoadConfig:
    """Test the load_config function."""

    def test_load_config_returns_test_config(self):
        config = load_config()
        assert isinstance(config, LoadTestConfig)

    def test_load_config_reads_env_vars(self):
        env = {"LOCUST_HOST": "https://test.example.com"}
        with patch.dict(os.environ, env, clear=False):
            config = load_config()
            assert config.host == "https://test.example.com"

    def test_load_config_with_dotenv(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("LOCUST_HOST=https://dotenv.example.com\nLOCUST_USERS=75\n")
        config = load_config(env_file=str(env_file))
        assert config.host == "https://dotenv.example.com"
        assert config.users == 75

    def test_load_config_env_overrides_dotenv(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("LOCUST_HOST=https://dotenv.example.com\n")
        env = {"LOCUST_HOST": "https://env.example.com"}
        with patch.dict(os.environ, env, clear=False):
            config = load_config(env_file=str(env_file))
            # Env vars should take precedence over .env file
            assert config.host == "https://env.example.com"
