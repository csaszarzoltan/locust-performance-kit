"""Runner utility for building Locust command-line arguments.

Provides a programmatic way to construct Locust commands,
useful for CI/CD pipelines and test orchestration.

Usage:
    from locust_templates.runner import build_locust_command

    cmd = build_locust_command(
        script="examples/api_load_test.py",
        headless=True,
        users=100,
        spawn_rate=10,
        host="https://api.example.com",
    )
    # Returns: "locust -f examples/api_load_test.py --headless --users 100 ..."
"""


def build_locust_command(
    script: str,
    headless: bool = False,
    users: int | None = None,
    spawn_rate: int | None = None,
    host: str | None = None,
    run_time: str | None = None,
    html_report: str | None = None,
    csv_prefix: str | None = None,
) -> str:
    """Build a Locust command string from parameters.

    Args:
        script: Path to the Locust test script.
        headless: Run without web UI (for CI/CD).
        users: Number of concurrent users.
        spawn_rate: Users spawned per second.
        host: Target host URL.
        run_time: Test duration (e.g. "5m", "1h").
        html_report: Path for HTML report output.
        csv_prefix: Prefix for CSV result files.

    Returns:
        Complete Locust command string.
    """
    parts = ["locust", "-f", script]

    if headless:
        parts.append("--headless")
    if users is not None:
        parts.extend(["--users", str(users)])
    if spawn_rate is not None:
        parts.extend(["--spawn-rate", str(spawn_rate)])
    if host is not None:
        parts.extend(["--host", host])
    if run_time is not None:
        parts.extend(["--run-time", run_time])
    if html_report is not None:
        parts.extend(["--html", html_report])
    if csv_prefix is not None:
        parts.extend(["--csv", csv_prefix])

    return " ".join(parts)
