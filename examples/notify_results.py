"""Send performance test results to Slack or Teams.

Usage:
    # Set webhook URL:
    export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
    # or
    export TEAMS_WEBHOOK_URL="https://outlook.office.com/webhook/..."

    # Send notification:
    # python examples/notify_results.py slack "Test completed" \
    #     '{"p95": "350ms", "status": "PASS"}'
    # python examples/notify_results.py teams "Test completed" \
    #     '{"p95": "350ms", "status": "PASS"}'
"""

import json
import sys
from pathlib import Path

# Ensure src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from locust_templates.notifications import (
    ConfigurationError,
    NotificationError,
    SlackNotifier,
    TeamsNotifier,
)


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python examples/notify_results.py "
            "<provider> <message> [results_json]"
        )
        print("  provider: 'slack' or 'teams'")
        print("  message: summary message string")
        print("  results_json: optional JSON string with results dict")
        sys.exit(1)

    provider = sys.argv[1]
    message = sys.argv[2]
    results = {}

    if len(sys.argv) > 3:
        try:
            results = json.loads(sys.argv[3])
        except json.JSONDecodeError as e:
            print(f"Error parsing results JSON: {e}")
            sys.exit(1)

    try:
        if provider == "slack":
            notifier = SlackNotifier()
        elif provider == "teams":
            notifier = TeamsNotifier()
        else:
            print(f"Unknown provider: {provider} (use 'slack' or 'teams')")
            sys.exit(1)

        notifier.send(message, results)
        print(f"Notification sent to {provider}!")

    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except NotificationError as e:
        print(f"Notification failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
