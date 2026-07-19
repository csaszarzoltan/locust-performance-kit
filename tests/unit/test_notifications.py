"""Smoke tests for Slack/Teams notifications (TASK-6).

Interface tests verify API surface. Behavioral tests define the contract
for webhook posting with mocked HTTP calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from locust_templates.notifications import (
    ConfigurationError,
    NotificationError,
    Notifier,
    SlackNotifier,
    TeamsNotifier,
)

# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestInterfaceSmoke:
    """Verify that all classes exist with correct signatures."""

    def test_notifier_is_abc(self):
        """Notifier should be an abstract base class."""
        assert issubclass(SlackNotifier, Notifier)
        assert issubclass(TeamsNotifier, Notifier)

    def test_slack_notifier_init(self):
        """SlackNotifier should accept webhook_url and timeout."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test", timeout=15)
        assert notifier.webhook_url == "https://hooks.slack.com/test"
        assert notifier.timeout == 15

    def test_teams_notifier_init(self):
        """TeamsNotifier should accept webhook_url and timeout."""
        notifier = TeamsNotifier(
            webhook_url="https://outlook.office.com/webhook/test", timeout=20
        )
        assert notifier.webhook_url == "https://outlook.office.com/webhook/test"
        assert notifier.timeout == 20

    def test_notifier_has_send_method(self):
        """Both notifiers should have send() method."""
        assert hasattr(SlackNotifier, "send")
        assert hasattr(TeamsNotifier, "send")

    def test_configuration_error_exists(self):
        """ConfigurationError should be an Exception."""
        assert issubclass(ConfigurationError, Exception)

    def test_notification_error_exists(self):
        """NotificationError should be an Exception."""
        assert issubclass(NotificationError, Exception)


# ──────────────────────────────────────────────────────────────
# Behavioral pre-state tests (fail until implementation)
# ──────────────────────────────────────────────────────────────


class TestSlackNotifier:
    """Behavioral tests for SlackNotifier.send() — fail until implemented."""

    @pytest.mark.unit
    def test_send_posts_to_webhook(self):
        """send() should POST to the Slack webhook URL."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")
        with patch("locust_templates.notifications.requests") as mock_requests:
            mock_requests.post.return_value = MagicMock(status_code=200)
            result = notifier.send("Test message", {"pass": True, "fail": False})
        assert result is True
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        assert (
            "hooks.slack.com" in call_args[0][0]
            or "hooks.slack.com" in str(call_args)
        )

    @pytest.mark.unit
    def test_send_raises_on_missing_webhook_url(self):
        """send() should raise ConfigurationError when webhook_url is None."""
        notifier = SlackNotifier(webhook_url=None)
        with pytest.raises(ConfigurationError):
            notifier.send("test", {})

    @pytest.mark.unit
    def test_send_raises_on_http_error(self):
        """send() should raise NotificationError on HTTP failure."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")
        with patch("locust_templates.notifications.requests") as mock_requests:
            mock_requests.post.side_effect = Exception("Connection error")
            with pytest.raises(NotificationError):
                notifier.send("test", {})


class TestTeamsNotifier:
    """Behavioral tests for TeamsNotifier.send() — fail until implemented."""

    @pytest.mark.unit
    def test_send_posts_to_webhook(self):
        """send() should POST to the Teams webhook URL."""
        notifier = TeamsNotifier(webhook_url="https://outlook.office.com/webhook/test")
        with patch("locust_templates.notifications.requests") as mock_requests:
            mock_requests.post.return_value = MagicMock(status_code=200)
            result = notifier.send("Test message", {"pass": True, "fail": False})
        assert result is True
        mock_requests.post.assert_called_once()

    @pytest.mark.unit
    def test_send_raises_on_missing_webhook_url(self):
        """send() should raise ConfigurationError when webhook_url is None."""
        notifier = TeamsNotifier(webhook_url=None)
        with pytest.raises(ConfigurationError):
            notifier.send("test", {})

    @pytest.mark.unit
    def test_send_raises_on_http_error(self):
        """send() should raise NotificationError on HTTP failure."""
        notifier = TeamsNotifier(webhook_url="https://outlook.office.com/webhook/test")
        with patch("locust_templates.notifications.requests") as mock_requests:
            mock_requests.post.side_effect = Exception("Connection error")
            with pytest.raises(NotificationError):
                notifier.send("test", {})
