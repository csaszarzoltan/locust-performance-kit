"""Report exporters using the Strategy pattern.

Each exporter renders a ReportData model into a specific format
(HTML, JSON, Markdown, JUnit XML) and writes it to disk.

Public API:
    ReportExporter — abstract base class
    HTMLExporter, JSONExporter, MarkdownExporter, JUnitXMLExporter
"""

from __future__ import annotations

import dataclasses
import html as html_module
import json
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from locust_templates.report_data import (
    ReportData,
)

# ──────────────────────────────────────────────────────────────
# Abstract base
# ──────────────────────────────────────────────────────────────


class ReportExporter(ABC):
    """Abstract base for report exporters (Strategy pattern)."""

    @abstractmethod
    def render(self, data: ReportData) -> str:
        """Render ReportData to a format-specific string."""

    def export(self, data: ReportData, output_path: str | Path) -> str:
        """Render *data* and write to *output_path*.

        Creates parent directories if needed.  Returns the absolute
        path of the written file as a string.
        """
        content = self.render(data)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        return str(out.resolve())


# ──────────────────────────────────────────────────────────────
# HTML exporter
# ──────────────────────────────────────────────────────────────


class HTMLExporter(ReportExporter):
    """Export ReportData as a self-contained HTML report."""

    def render(self, data: ReportData) -> str:
        return _build_html(data)


def _build_html(data: ReportData) -> str:
    """Build a complete self-contained HTML report from ReportData."""
    s = data.summary
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Summary cards
    summary_cards = f"""
  <div class="card"><div class="label">Total Requests</div>
    <div class="value">{s.total_requests:,}</div></div>
  <div class="card"><div class="label">Total Failures</div>
    <div class="value">{s.total_failures:,}</div></div>
  <div class="card"><div class="label">Endpoints</div>
    <div class="value">{s.endpoint_count}</div></div>
  <div class="card"><div class="label">Overall RPS</div>
    <div class="value">{s.total_rps:.1f}</div></div>
  <div class="card"><div class="label">Failure Rate</div>
    <div class="value">{s.failure_rate:.4f}</div></div>"""

    # Endpoint table
    endpoint_rows = []
    for ep in data.endpoints:
        endpoint_rows.append(
            f"<tr><td>{html_module.escape(ep.request_type)}</td>"
            f"<td>{html_module.escape(ep.name)}</td>"
            f"<td>{ep.request_count:,}</td>"
            f"<td>{ep.failure_count:,}</td>"
            f"<td>{ep.average_response_time_ms:.1f}</td>"
            f"<td>{ep.percentile_50:.1f}</td>"
            f"<td>{ep.percentile_95:.1f}</td>"
            f"<td>{ep.percentile_99:.1f}</td>"
            f"<td>{ep.requests_per_sec:.1f}</td></tr>"
        )
    endpoint_table = (
        '<table><thead><tr>'
        "<th>Type</th><th>Name</th><th>Requests</th><th>Failures</th>"
        "<th>Avg (ms)</th><th>p50</th><th>p95</th><th>p99</th><th>RPS</th>"
        f'</tr></thead><tbody>{"".join(endpoint_rows)}</tbody></table>'
    )

    # Threshold section
    threshold_section = _build_html_thresholds(data)

    # Failures section
    failures_section = _build_html_failures(data)

    # Failure hotspots section
    hotspots_section = _build_html_hotspots(data)

    # Exceptions section
    exceptions_section = _build_html_exceptions(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Locust Performance Report</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 2rem;
    background: #f5f5f5; color: #333; }}
  h1 {{ color: #2c3e50; }}
  h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 0.3rem; }}
  .summary {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; }}
  .card {{ background: #fff; border-radius: 8px; padding: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1); min-width: 150px; }}
  .card .label {{ font-size: 0.8rem; color: #7f8c8d; text-transform: uppercase; }}
  .card .value {{ font-size: 1.5rem; font-weight: bold; color: #2c3e50; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0;
    background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
  th, td {{ border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; }}
  th {{ background: #3498db; color: #fff; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  .pass {{ color: #27ae60; font-weight: bold; }}
  .fail {{ color: #e74c3c; font-weight: bold; }}
  .footer {{ margin-top: 2rem; color: #95a5a6; font-size: 0.8rem; }}
</style>
</head>
<body>
<h1>Locust Performance Report</h1>
<p>Generated: {now}</p>
<p>Tool: {data.metadata.tool} v{data.metadata.version}</p>
<div class="summary">{summary_cards}
</div>
{threshold_section}
<h2>Per-Endpoint Metrics</h2>
{endpoint_table}
{failures_section}
{hotspots_section}
{exceptions_section}
<div class="footer">Generated by {data.metadata.tool}</div>
</body>
</html>"""


def _build_html_thresholds(data: ReportData) -> str:
    """Build the threshold results section."""
    if data.thresholds is None:
        return ""
    items = []
    for ep in data.endpoints:
        css = "pass" if ep.threshold_status == "PASS" else "fail"
        items.append(
            f"<tr><td>{html_module.escape(ep.name)}</td>"
            f"<td>p95={ep.percentile_95:.1f}ms / p99={ep.percentile_99:.1f}ms</td>"
            f'<td class="{css}">{ep.threshold_status}</td></tr>'
        )
    return (
        "<h2>Threshold Results</h2>"
        '<table><thead><tr><th>Endpoint</th><th>Metrics</th>'
        f'<th>Status</th></tr></thead><tbody>{"".join(items)}</tbody></table>'
    )


def _build_html_failures(data: ReportData) -> str:
    """Build the failures table section."""
    if not data.failures:
        return ""
    rows = []
    for f in data.failures:
        rows.append(
            f"<tr><td>{html_module.escape(f.method)}</td>"
            f"<td>{html_module.escape(f.name)}</td>"
            f"<td>{html_module.escape(f.type)}</td>"
            f"<td>{html_module.escape(f.error)}</td></tr>"
        )
    return (
        '<h2>Failures</h2><table><thead><tr>'
        "<th>Method</th><th>Name</th><th>Type</th><th>Error</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


def _build_html_hotspots(data: ReportData) -> str:
    """Build the failure hotspots section."""
    hotspots = data.get_failure_hotspots()
    if not hotspots:
        return ""
    rows = []
    for h in hotspots:
        rate_pct = h["failure_rate"] * 100
        esc_name = html_module.escape(h["name"])
        rows.append(
            f"<tr><td>{esc_name}</td>"
            f"<td>{h['failure_count']:,}</td>"
            f"<td>{h['request_count']:,}</td>"
            f'<td class="fail">{rate_pct:.2f}%</td></tr>'
        )
    return (
        "<h2>Failure Hotspots</h2>"
        '<table><thead><tr><th>Endpoint</th>'
        "<th>Failures</th><th>Total Requests</th><th>Failure Rate</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


def _build_html_exceptions(data: ReportData) -> str:
    """Build the exceptions table section."""
    if not data.exceptions:
        return ""
    rows = []
    for ex in data.exceptions:
        rows.append(
            f"<tr><td>{html_module.escape(ex.context)}</td>"
            f"<td>{html_module.escape(ex.exception)}</td>"
            f"<td><pre>{html_module.escape(ex.traceback)}</pre></td></tr>"
        )
    return (
        '<h2>Exceptions</h2><table><thead><tr>'
        "<th>Context</th><th>Exception</th><th>Traceback</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


# ──────────────────────────────────────────────────────────────
# JSON exporter
# ──────────────────────────────────────────────────────────────


class JSONExporter(ReportExporter):
    """Export ReportData as a JSON document."""

    def render(self, data: ReportData) -> str:
        return json.dumps(self._to_dict(data), indent=2, ensure_ascii=False)

    def _to_dict(self, data: ReportData) -> dict:
        return {
            "metadata": dataclasses.asdict(data.metadata),
            "summary": dataclasses.asdict(data.summary),
            "thresholds": (
                dataclasses.asdict(data.thresholds)
                if data.thresholds is not None
                else {}
            ),
            "endpoints": [
                {
                    "name": ep.name,
                    "type": ep.request_type,
                    "request_count": ep.request_count,
                    "failure_count": ep.failure_count,
                    "avg_response_time_ms": ep.average_response_time_ms,
                    "min_response_time_ms": ep.min_response_time_ms,
                    "max_response_time_ms": ep.max_response_time_ms,
                    "avg_content_size": ep.average_content_size,
                    "rps": ep.requests_per_sec,
                    "p50": ep.percentile_50,
                    "p66": ep.percentile_66,
                    "p75": ep.percentile_75,
                    "p80": ep.percentile_80,
                    "p90": ep.percentile_90,
                    "p95": ep.percentile_95,
                    "p98": ep.percentile_98,
                    "p99": ep.percentile_99,
                    "threshold_status": ep.threshold_status,
                }
                for ep in data.endpoints
            ],
            "failures": [dataclasses.asdict(f) for f in data.failures],
            "exceptions": [dataclasses.asdict(ex) for ex in data.exceptions],
        }


# ──────────────────────────────────────────────────────────────
# Markdown exporter
# ──────────────────────────────────────────────────────────────


class MarkdownExporter(ReportExporter):
    """Export ReportData as GitHub-flavored Markdown."""

    def render(self, data: ReportData) -> str:
        lines: list[str] = []
        s = data.summary

        lines.append("# Locust Performance Report")
        lines.append("")
        lines.append(
            f"Generated: {data.metadata.generated_at} | "
            f"Tool: {data.metadata.tool} v{data.metadata.version}"
        )
        lines.append("")

        # Summary table
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Requests | {s.total_requests:,} |")
        lines.append(f"| Total Failures | {s.total_failures:,} |")
        lines.append(f"| Endpoints | {s.endpoint_count} |")
        lines.append(f"| Overall RPS | {s.total_rps:.1f} |")
        lines.append(f"| Failure Rate | {s.failure_rate:.4f} |")
        lines.append("")

        # Endpoint table
        lines.append("## Per-Endpoint Metrics")
        lines.append("")
        lines.append(
            "| Type | Name | Requests | Failures | Avg (ms) | p50 | p95 | p99 | RPS |"
        )
        lines.append(
            "|------|------|----------|----------|----------|-----|-----|-----|-----|"
        )
        for ep in data.endpoints:
            lines.append(
                f"| {ep.request_type} | {ep.name} "
                f"| {ep.request_count:,} | {ep.failure_count:,} "
                f"| {ep.average_response_time_ms:.1f} "
                f"| {ep.percentile_50:.1f} | {ep.percentile_95:.1f} "
                f"| {ep.percentile_99:.1f} | {ep.requests_per_sec:.1f} |"
            )
        lines.append("")

        # Threshold section
        if data.thresholds is not None:
            lines.append("## Threshold Results")
            lines.append("")
            lines.append("| Endpoint | p95 (ms) | p99 (ms) | Status |")
            lines.append("|----------|----------|----------|--------|")
            for ep in data.endpoints:
                emoji = "✅" if ep.threshold_status == "PASS" else "❌"
                lines.append(
                    f"| {ep.name} | {ep.percentile_95:.1f} "
                    f"| {ep.percentile_99:.1f} "
                    f"| {emoji} {ep.threshold_status} |"
                )
            lines.append("")

        # Failures
        if data.failures:
            lines.append("## Failures")
            lines.append("")
            lines.append("| Method | Name | Type | Error |")
            lines.append("|--------|------|------|-------|")
            for f in data.failures:
                lines.append(f"| {f.method} | {f.name} | {f.type} | {f.error} |")
            lines.append("")

        # Failure hotspots
        hotspots = data.get_failure_hotspots()
        if hotspots:
            lines.append("## Failure Hotspots")
            lines.append("")
            lines.append("| Endpoint | Failures | Total | Failure Rate |")
            lines.append("|----------|----------|-------|--------------|")
            for h in hotspots:
                rate_pct = h["failure_rate"] * 100
                lines.append(
                    f"| {h['name']} | {h['failure_count']:,} "
                    f"| {h['request_count']:,} | {rate_pct:.2f}% |"
                )
            lines.append("")

        # Exceptions
        if data.exceptions:
            lines.append("## Exceptions")
            lines.append("")
            for ex in data.exceptions:
                lines.append(f"- **{ex.exception}**: {ex.context}")
            lines.append("")

        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# JUnit XML exporter
# ──────────────────────────────────────────────────────────────


class JUnitXMLExporter(ReportExporter):
    """Export ReportData as JUnit XML for CI integration."""

    def render(self, data: ReportData) -> str:
        root = ET.Element("testsuites")
        suite = ET.SubElement(
            root,
            "testsuite",
            {
                "name": "Locust Performance Test",
                "tests": str(len(data.endpoints)),
            },
        )

        # Properties
        props = ET.SubElement(suite, "properties")
        s = data.summary
        for name, value in [
            ("total_requests", str(s.total_requests)),
            ("total_failures", str(s.total_failures)),
            ("endpoint_count", str(s.endpoint_count)),
            ("total_rps", f"{s.total_rps:.1f}"),
        ]:
            ET.SubElement(props, "property", {"name": name, "value": value})

        # Testcases
        failure_count = 0
        for ep in data.endpoints:
            tc = ET.SubElement(
                suite,
                "testcase",
                {
                    "classname": "locust.endpoints",
                    "name": ep.name,
                    "time": f"{ep.average_response_time_ms / 1000:.4f}",
                },
            )
            # System-out with metrics
            sys_out = ET.SubElement(tc, "system-out")
            sys_out.text = (
                f"requests={ep.request_count} failures={ep.failure_count} "
                f"p95={ep.percentile_95:.1f}ms p99={ep.percentile_99:.1f}ms "
                f"rps={ep.requests_per_sec:.1f}"
            )
            if ep.threshold_status == "FAIL":
                failure_count += 1
                fail_el = ET.SubElement(
                    tc,
                    "failure",
                    {
                        "type": "ThresholdExceeded",
                        "message": (
                            f"p95={ep.percentile_95:.1f}ms "
                            f"p99={ep.percentile_99:.1f}ms exceeds threshold"
                        ),
                    },
                )
                fail_el.text = (
                    f"Endpoint {ep.name} exceeded threshold: "
                    f"p95={ep.percentile_95:.1f}ms, p99={ep.percentile_99:.1f}ms"
                )

        suite.set("failures", str(failure_count))

        # XML declaration
        xml_str = ET.tostring(root, encoding="unicode")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str


__all__ = [
    "HTMLExporter",
    "JSONExporter",
    "JUnitXMLExporter",
    "MarkdownExporter",
    "ReportExporter",
]
