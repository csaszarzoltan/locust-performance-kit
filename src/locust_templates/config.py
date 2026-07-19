"""Configuration management for Locust performance tests.

Provides environment-based configuration with sensible defaults.
Supports .env files via python-dotenv and environment variable overrides.

Usage:
    from locust_templates.config import load_config

    config = load_config()
    # or with .env file:
    config = load_config(env_file=".env")

    print(config.host)  # http://localhost:8080
    print(config.users)  # 100
"""

import json
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass
class LoadTestConfig:
    """Configuration for Locust performance tests."""

    # Connection
    host: str = "http://localhost:8080"
    auth_token: str = ""

    # Load profile
    users: int = 100
    spawn_rate: int = 10
    run_time: str = "5m"

    # Thresholds
    p95_threshold: float = 500.0
    p99_threshold: float = 1000.0
    error_rate_threshold: float = 0.01

    # Auth
    auth_provider: str = "static"
    auth_client_id: str = ""
    auth_client_secret: str = ""
    auth_token_url: str = ""
    auth_scopes: str = ""

    # Live Dashboard (v1.3.0)
    dashboard_enabled: bool = True
    dashboard_refresh_interval: int = 5
    dashboard_max_points: int = 300
    dashboard_output: str = ""

    # Threshold Alerts (v1.3.0)
    alerts_enabled: bool = True
    alert_rules: list = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "LoadTestConfig":
        """Create configuration from environment variables.

        Environment variables (all optional, defaults used if unset):
            LOCUST_HOST - Target host URL
            LOCUST_AUTH_TOKEN - Authentication token
            LOCUST_USERS - Number of concurrent users
            LOCUST_SPAWN_RATE - Users spawned per second
            LOCUST_RUN_TIME - Test duration (e.g. "5m", "1h")
            LOCUST_P95_THRESHOLD - p95 latency threshold in ms
            LOCUST_P99_THRESHOLD - p99 latency threshold in ms
            LOCUST_ERROR_RATE_THRESHOLD - Max error rate (0.0-1.0)
        """
        return cls(
            host=os.environ.get("LOCUST_HOST", cls.host),
            auth_token=os.environ.get("LOCUST_AUTH_TOKEN", cls.auth_token),
            users=int(os.environ.get("LOCUST_USERS", str(cls.users))),
            spawn_rate=int(os.environ.get("LOCUST_SPAWN_RATE", str(cls.spawn_rate))),
            run_time=os.environ.get("LOCUST_RUN_TIME", cls.run_time),
            p95_threshold=float(
                os.environ.get("LOCUST_P95_THRESHOLD", str(cls.p95_threshold))
            ),
            p99_threshold=float(
                os.environ.get("LOCUST_P99_THRESHOLD", str(cls.p99_threshold))
            ),
            error_rate_threshold=float(
                os.environ.get(
                    "LOCUST_ERROR_RATE_THRESHOLD", str(cls.error_rate_threshold)
                )
            ),
            auth_provider=os.environ.get("LOCUST_AUTH_PROVIDER", cls.auth_provider),
            auth_client_id=os.environ.get("LOCUST_AUTH_CLIENT_ID", cls.auth_client_id),
            auth_client_secret=os.environ.get(
                "LOCUST_AUTH_CLIENT_SECRET", cls.auth_client_secret
            ),
            auth_token_url=os.environ.get(
                "LOCUST_AUTH_TOKEN_URL", cls.auth_token_url
            ),
            auth_scopes=os.environ.get("LOCUST_AUTH_SCOPES", cls.auth_scopes),
            dashboard_enabled=os.environ.get(
                "LOCUST_DASHBOARD_ENABLED", "true"
            ).lower()
            in ("true", "1", "yes"),
            dashboard_refresh_interval=int(
                os.environ.get(
                    "LOCUST_DASHBOARD_REFRESH",
                    str(cls.dashboard_refresh_interval),
                )
            ),
            dashboard_max_points=int(
                os.environ.get(
                    "LOCUST_DASHBOARD_MAX_POINTS",
                    str(cls.dashboard_max_points),
                )
            ),
            dashboard_output=os.environ.get(
                "LOCUST_DASHBOARD_OUTPUT", cls.dashboard_output
            ),
            alerts_enabled=os.environ.get(
                "LOCUST_ALERTS_ENABLED", "true"
            ).lower()
            in ("true", "1", "yes"),
            alert_rules=_parse_alert_rules(
                os.environ.get("LOCUST_ALERT_RULES", "")
            ),
        )


def load_config(env_file: str | None = None) -> LoadTestConfig:
    """Load configuration from .env file and environment variables.

    Args:
        env_file: Path to .env file. If None, only reads env vars.

    Returns:
        TestConfig instance with values from env > .env > defaults.
    """
    if env_file:
        load_dotenv(env_file, override=False)

    return LoadTestConfig.from_env()


def _parse_alert_rules(raw: str) -> list:
    """Parse alert rules from a JSON string env var.

    Args:
        raw: JSON string (e.g. '[{"name": "p95", ...}]') or empty string.

    Returns:
        List of rule dicts, or empty list if parsing fails.
    """
    if not raw or not raw.strip():
        return []
    try:
        rules = json.loads(raw)
        if isinstance(rules, list):
            return rules
        return []
    except (json.JSONDecodeError, TypeError):
        return []
