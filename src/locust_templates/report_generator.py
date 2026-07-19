"""HTML report generator for Locust test results.

Parses Locust CSV output files and generates a self-contained HTML report
with summary stats, per-endpoint metrics, CSS-only bar charts, and threshold
pass/fail indicators.

Public API:
    HTMLReportGenerator — parse CSV, generate HTML report
"""

from __future__ import annotations

import csv
import html
from datetime import datetime
from pathlib import Path
from typing import Any


class HTMLReportGenerator:
    """Generate self-contained HTML reports from Locust CSV output.

    Parses the stats and failures CSV files produced by Locust's --csv flag
    and produces a single HTML file with no external CSS/JS dependencies.

    Example:
        gen = HTMLReportGenerator.from_csv("results")
        gen.generate("report.html")
    """

    def __init__(
        self,
        stats: list[dict[str, Any]],
        failures: list[dict[str, Any]] | None = None,
        thresholds: dict[str, float] | None = None,
    ) -> None:
        """Initialize with pre-parsed stats and failures.

        Args:
            stats: List of stat dicts (one per endpoint).
            failures: List of failure dicts.
            thresholds: Optional dict with p95/p99 threshold values.
        """
        self.stats = stats
        self.failures = failures or []
        self.thresholds = thresholds or {}

    @classmethod
    def from_csv(
        cls,
        csv_prefix: str,
        *,
        thresholds: dict[str, float] | None = None,
    ) -> HTMLReportGenerator:
        """Create generator from Locust CSV files."""
        stats_path = Path(f"{csv_prefix}_stats.csv")
        stats: list[dict[str, Any]] = []
        if stats_path.exists():
            with open(stats_path, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    parsed: dict[str, Any] = {}
                    for k, v in row.items():
                        if k in (
                            "Request Count", "Failure Count",
                        ):
                            parsed[k] = int(v or 0)
                        elif k in (
                            "Average Response Time", "Min Response Time",
                            "Max Response Time", "Average Content Size",
                            "Requests/s",
                        ) or "%" in (k or ""):
                            try:
                                parsed[k] = float(v or 0)
                            except (ValueError, TypeError):
                                parsed[k] = v
                        else:
                            parsed[k] = v
                    stats.append(parsed)
        failures_path = Path(f"{csv_prefix}_failures.csv")
        failures: list[dict[str, Any]] = []
        if failures_path.exists():
            with open(failures_path, newline="") as f:
                reader = csv.DictReader(f)
                failures = list(reader)
        return cls(stats=stats, failures=failures, thresholds=thresholds)

    def generate(self, output_path: str | Path) -> str:
        """Generate the HTML report and write it to output_path."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        html_content = self._build_html()
        output.write_text(html_content, encoding="utf-8")
        return str(output.resolve())

    def _build_html(self) -> str:
        """Build the complete self-contained HTML report."""
        rows_html = self._build_stats_table()
        charts_html = self._build_bar_charts()
        failures_html = self._build_failures_table()
        threshold_html = self._build_threshold_section()
        summary = self._compute_summary()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
  .bar-container {{ margin: 0.5rem 0; }}
  .bar-label {{ display: inline-block; width: 200px; font-size: 0.85rem; }}
  .bar-bg {{ display: inline-block; background: #ecf0f1; height: 20px;
    width: 60%; vertical-align: middle; border-radius: 3px; }}
  .bar-fill {{ display: inline-block; height: 20px; border-radius: 3px; }}
  .bar-fill.p95 {{ background: #e74c3c; }}
  .bar-fill.p99 {{ background: #f39c12; }}
  .pass {{ color: #27ae60; font-weight: bold; }}
  .fail {{ color: #e74c3c; font-weight: bold; }}
  .pass-bg {{ background: #27ae60 !important; }}
  .fail-bg {{ background: #e74c3c !important; }}
  .footer {{ margin-top: 2rem; color: #95a5a6; font-size: 0.8rem; }}
</style>
</head>
<body>
<h1>Locust Performance Report</h1>
<p>Generated: {now}</p>
<div class="summary">
  <div class="card"><div class="label">Total Requests</div>
    <div class="value">{summary['total_requests']}</div></div>
  <div class="card"><div class="label">Total Failures</div>
    <div class="value">{summary['total_failures']}</div></div>
  <div class="card"><div class="label">Endpoints</div>
    <div class="value">{summary['endpoint_count']}</div></div>
  <div class="card"><div class="label">Overall RPS</div>
    <div class="value">{summary['total_rps']:.1f}</div></div>
</div>
{threshold_html}
<h2>Per-Endpoint Metrics</h2>
{rows_html}
<h2>p95 / p99 Response Times</h2>
{charts_html}
{failures_html}
<div class="footer">Generated by locust-performance-kit HTMLReportGenerator</div>
</body>
</html>"""

    def _compute_summary(self) -> dict[str, Any]:
        total_requests = 0
        total_failures = 0
        total_rps = 0.0
        endpoint_count = 0
        for row in self.stats:
            name = str(row.get("Name", ""))
            if name.lower() == "aggregated":
                continue
            endpoint_count += 1
            total_requests += int(row.get("Request Count", 0) or 0)
            total_failures += int(row.get("Failure Count", 0) or 0)
            total_rps += float(row.get("Requests/s", 0) or 0)
        return {
            "total_requests": total_requests,
            "total_failures": total_failures,
            "endpoint_count": endpoint_count,
            "total_rps": total_rps,
        }

    def _build_stats_table(self) -> str:
        if not self.stats:
            return "<p>No stats data available.</p>"
        headers = [
            "Type", "Name", "Requests", "Failures",
            "Avg (ms)", "p50", "p95", "p99", "RPS",
        ]
        header_row = "".join(f"<th>{h}</th>" for h in headers)
        body_rows = []
        for row in self.stats:
            name = html.escape(str(row.get("Name", "")))
            if name.lower() == "aggregated":
                continue
            cells = [
                html.escape(str(row.get("Type", ""))),
                name,
                str(row.get("Request Count", "")),
                str(row.get("Failure Count", "")),
                str(row.get("Average Response Time", "")),
                str(row.get("50%", "")),
                str(row.get("95%", "")),
                str(row.get("99%", "")),
                str(row.get("Requests/s", "")),
            ]
            body_rows.append(
                "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
            )
        return (
            f"<table><thead><tr>{header_row}</tr></thead>"
            f"<tbody>{''.join(body_rows)}</tbody></table>"
        )

    def _build_bar_charts(self) -> str:
        if not self.stats:
            return "<p>No chart data available.</p>"
        max_p95 = 1.0
        max_p99 = 1.0
        for row in self.stats:
            name = str(row.get("Name", ""))
            if name.lower() == "aggregated":
                continue
            p95 = float(row.get("95%", 0) or 0)
            p99 = float(row.get("99%", 0) or 0)
            max_p95 = max(max_p95, p95)
            max_p99 = max(max_p99, p99)
        charts = []
        for row in self.stats:
            name = str(row.get("Name", ""))
            if name.lower() == "aggregated":
                continue
            p95 = float(row.get("95%", 0) or 0)
            p99 = float(row.get("99%", 0) or 0)
            p95_pct = (p95 / max_p95 * 100) if max_p95 > 0 else 0
            p99_pct = (p99 / max_p99 * 100) if max_p99 > 0 else 0
            esc_name = html.escape(name)
            charts.append(f"""
            <div class="bar-container">
              <span class="bar-label">{esc_name}</span>
              <div class="bar-bg"><div class="bar-fill p95"
                style="width: {p95_pct:.1f}%"></div></div>
              <span>p95: {p95}ms</span>
              <div class="bar-bg"><div class="bar-fill p99"
                style="width: {p99_pct:.1f}%"></div></div>
              <span>p99: {p99}ms</span>
            </div>""")
        return "\n".join(charts)

    def _build_failures_table(self) -> str:
        if not self.failures:
            return ""
        headers = ["Method", "Name", "Type", "Error"]
        header_row = "".join(f"<th>{h}</th>" for h in headers)
        body_rows = []
        for row in self.failures:
            cells = [
                html.escape(str(row.get("Method", ""))),
                html.escape(str(row.get("Name", ""))),
                html.escape(str(row.get("Type", ""))),
                html.escape(str(row.get("Error", ""))),
            ]
            body_rows.append(
                "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
            )
        return (
            f'<h2>Failures</h2><table><thead><tr>{header_row}</tr></thead>'
            f'<tbody>{"".join(body_rows)}</tbody></table>'
        )

    def _build_threshold_section(self) -> str:
        if not self.thresholds:
            return ""
        p95_thresh = self.thresholds.get("p95")
        p99_thresh = self.thresholds.get("p99")
        items = []
        for row in self.stats:
            name = str(row.get("Name", ""))
            if name.lower() == "aggregated":
                continue
            p95 = float(row.get("95%", 0) or 0)
            p99 = float(row.get("99%", 0) or 0)
            status = "PASS"
            css_class = "pass"
            if p95_thresh and p95 > p95_thresh:
                status = "FAIL"
                css_class = "fail"
            if p99_thresh and p99 > p99_thresh:
                status = "FAIL"
                css_class = "fail"
            esc_name = html.escape(name)
            items.append(
                f'<tr><td>{esc_name}</td><td>p95={p95}ms / p99={p99}ms</td>'
                f'<td class="{css_class}">{status}</td></tr>'
            )
        return (
            '<h2>Threshold Results</h2>'
            f'<table><thead><tr><th>Endpoint</th>'
            '<th>Metrics</th><th>Status</th></tr></thead>'
            f'<tbody>{"".join(items)}</tbody></table>'
        )


__all__ = ["HTMLReportGenerator"]
