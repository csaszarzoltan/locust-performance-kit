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

Report generation:
    from locust_templates.runner import generate_report

    path = generate_report("results", "report.json", fmt="json")
"""

from __future__ import annotations

from pathlib import Path

from locust_templates.exporters import (
    HTMLExporter,
    JSONExporter,
    JUnitXMLExporter,
    MarkdownExporter,
)
from locust_templates.report_data import ReportData


def build_locust_command(
    script: str,
    headless: bool = False,
    users: int | None = None,
    spawn_rate: int | None = None,
    host: str | None = None,
    run_time: str | None = None,
    html_report: str | None = None,
    csv_prefix: str | None = None,
    report_format: str | None = None,
    report_output: str | None = None,
    p95_threshold: float | None = None,
    p99_threshold: float | None = None,
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
        report_format: If set, append ``&& locust-report`` to generate
            a report in the given format (html/json/markdown/junit).
        report_output: Output path for the report (passed to --output).
        p95_threshold: p95 threshold in ms (passed to --p95-threshold).
        p99_threshold: p99 threshold in ms (passed to --p99-threshold).

    Returns:
        Complete Locust command string, optionally with a
        ``&& locust-report ...`` suffix for report generation.
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

    cmd = " ".join(parts)

    # Append report generation command if requested
    if report_format is not None and csv_prefix is not None:
        report_parts = ["locust-report", csv_prefix, "--format", report_format]
        if report_output is not None:
            report_parts.extend(["--output", report_output])
        if p95_threshold is not None:
            report_parts.extend(["--p95-threshold", str(int(p95_threshold))])
        if p99_threshold is not None:
            report_parts.extend(["--p99-threshold", str(int(p99_threshold))])
        cmd = f"{cmd} && {' '.join(report_parts)}"

    return cmd


# ──────────────────────────────────────────────────────────────
# Report generation helper
# ──────────────────────────────────────────────────────────────

_EXPORTERS = {
    "html": HTMLExporter,
    "json": JSONExporter,
    "markdown": MarkdownExporter,
    "junit": JUnitXMLExporter,
}


def generate_report(
    csv_prefix: str | Path,
    output_path: str | Path,
    fmt: str = "html",
    thresholds: dict[str, float] | None = None,
) -> str:
    """Generate a report from Locust CSV output.

    Args:
        csv_prefix: Prefix for Locust CSV files.
        output_path: Where to write the report.
        fmt: Output format — html, json, markdown, or junit.
        thresholds: Optional dict with ``p95`` and/or ``p99`` keys.

    Returns:
        Absolute path of the generated report file.
    """
    data = ReportData.from_csv(csv_prefix, thresholds=thresholds)
    exporter_cls = _EXPORTERS.get(fmt, HTMLExporter)
    exporter = exporter_cls()
    return exporter.export(data, output_path)


__all__ = ["build_locust_command", "generate_report"]
