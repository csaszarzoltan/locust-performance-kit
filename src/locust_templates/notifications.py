"""Slack and Microsoft Teams notification for performance test results.

Sends formatted test result summaries to Slack or Teams via incoming
webhook URLs.

Public API:
    Notifier           — abstract base class
    SlackNotifier      — post to Slack webhook
    TeamsNotifier      — post to Teams webhook
    ConfigurationError — raised when webhook URL is missing
    NotificationError  — raised when the HTTP POST fails
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

import requests


class ConfigurationError(Exception):
    """Raised when required configuration (e.g. webhook URL) is missing."""


class NotificationError(Exception):
    """Raised when the notification HTTP request fails."""


class Notifier(ABC):
    """Abstract base class for notification providers.

    Every concrete notifier must implement send().
    """

    @abstractmethod
    def send(self, message: str, results: dict[str, Any]) -> bool:
        """Send a notification with a message and results dict.

        Args:
            message: Human-readable summary message.
            results: Dict with test results (stats, thresholds, pass/fail).

        Returns:
            True if the notification was sent successfully.

        Raises:
            NotificationError: If the HTTP request fails.
            ConfigurationError: If the webhook URL is not configured.
        """


class SlackNotifier(Notifier):
    """Send notifications to Slack via incoming webhook.

    Reads the webhook URL from the SLACK_WEBHOOK_URL environment variable
    or the constructor argument.

    Args:
        webhook_url: Slack incoming webhook URL. If None, reads from env.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        webhook_url: str | None = None,
        *,
        timeout: int = 10,
    ) -> None:
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.timeout = timeout

    def send(self, message: str, results: dict[str, Any]) -> bool:
        """Post a formatted message block to Slack webhook."""
        if not self.webhook_url:
            raise ConfigurationError(
                "Slack webhook URL not configured. Set SLACK_WEBHOOK_URL env var "
                "or pass webhook_url to the constructor."
            )
        payload: dict[str, Any] = {
            "text": message,
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": message},
                },
            ],
        }
        if results:
            results_text = "\n".join(
                f"  • {k}: {v}" for k, v in results.items()
            )
            payload["blocks"].append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Results:*\n{results_text}"},
                }
            )
        try:
            resp = requests.post(
                self.webhook_url, json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
        except Exception as exc:
            raise NotificationError(f"Slack notification failed: {exc}") from exc
        return True


class TeamsNotifier(Notifier):
    """Send notifications to Microsoft Teams via incoming webhook.

    Reads the webhook URL from the TEAMS_WEBHOOK_URL environment variable
    or the constructor argument.

    Args:
        webhook_url: Teams incoming webhook URL. If None, reads from env.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        webhook_url: str | None = None,
        *,
        timeout: int = 10,
    ) -> None:
        self.webhook_url = webhook_url or os.getenv("TEAMS_WEBHOOK_URL")
        self.timeout = timeout

    def send(self, message: str, results: dict[str, Any]) -> bool:
        """Post an Adaptive Card to Teams webhook."""
        if not self.webhook_url:
            raise ConfigurationError(
                "Teams webhook URL not configured. Set TEAMS_WEBHOOK_URL env var "
                "or pass webhook_url to the constructor."
            )
        facts = [{"name": str(k), "value": str(v)} for k, v in results.items()]
        body: list[dict[str, Any]] = [
            {
                "type": "TextBlock",
                "text": message,
                "size": "Medium",
                "weight": "Bolder",
            }
        ]
        if facts:
            body.append(
                {
                    "type": "FactSet",
                    "facts": facts,
                }
            )
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": body,
                    },
                }
            ],
        }
        try:
            resp = requests.post(
                self.webhook_url, json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
        except Exception as exc:
            raise NotificationError(f"Teams notification failed: {exc}") from exc
        return True


__all__ = [
    "ConfigurationError",
    "NotificationError",
    "Notifier",
    "SlackNotifier",
    "TeamsNotifier",
]
