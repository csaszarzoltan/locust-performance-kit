"""Accessible endpoint comparison and timeline rendering."""
from __future__ import annotations

import html
from typing import Any


def _e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)

def _fmt(value: Any, percent: bool = False) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.1f}%" if percent else f"{value:.3f}" if isinstance(value, float) else str(value)

def _svg(timeline: dict[str, Any]) -> str:
    current, baseline = timeline.get("current", []), timeline.get("baseline", [])
    all_points = current + baseline
    if not all_points:
        return '<div class="empty"><p>Timeline unavailable: no aggregate history samples.</p></div>'
    max_x = max((point["offset_seconds"] for point in all_points), default=1) or 1
    max_y = max((point["p95"] for point in all_points), default=1) or 1
    def points(series: list[dict[str, Any]]) -> str:
        return " ".join(f"{40 + point['offset_seconds'] / max_x * 520:.1f},{190 - point['p95'] / max_y * 150:.1f}" for point in series)
    reason = _e(timeline.get("reason"))
    return f'<figure class="timeline"><svg role="img" aria-labelledby="timeline-title timeline-desc" viewBox="0 0 600 220"><title id="timeline-title">Current and baseline p95 timeline</title><desc id="timeline-desc">{reason}</desc><line x1="40" y1="190" x2="570" y2="190"/><line x1="40" y1="30" x2="40" y2="190"/><polyline class="series current" points="{points(current)}"/><polyline class="series baseline" points="{points(baseline)}"/></svg><figcaption><span class="legend current">Current p95</span> <span class="legend baseline">Baseline p95</span>. {reason}</figcaption></figure>'

def render_comparison(decision: dict[str, Any]) -> str:
    compatibility = decision.get("baseline", {}).get("compatibility", {})
    compat = ''.join(f'<article><small>{label}</small><strong>{value}</strong></article>' for label, value in (
        ("Status", _e(compatibility.get("status", "NO_BASELINE"))),
        ("Common", _fmt(compatibility.get("common", 0))),
        ("Added", _fmt(compatibility.get("added", 0))),
        ("Missing", _fmt(compatibility.get("missing", 0))),
        ("Overlap", _fmt(compatibility.get("overlap_percent"), True)),
    ))
    endpoint_rows = []
    for row in decision.get("endpoint_comparison", []):
        p95, rps, errors = row["metrics"]["p95"], row["metrics"]["rps"], row["metrics"]["error_rate"]
        endpoint_rows.append(f'<tr><th scope="row">{_e(row["method"])} {_e(row["endpoint"])}</th><td><span class="badge {_e(row["state"].lower())}">{_e(row["state"])}</span></td><td>{_fmt(p95["current"])}</td><td>{_fmt(p95["baseline"])}</td><td>{_fmt(p95["absolute_delta"])}</td><td>{_fmt(p95["percent_delta"], True)}</td><td>{_fmt(rps["current"])}</td><td>{_fmt(rps["baseline"])}</td><td>{_fmt(errors["percent_delta"], True)}</td></tr>')
    comparison = '<div class="table-wrap" tabindex="0" aria-label="Endpoint comparison, horizontally scrollable"><table><caption>Current run compared with baseline</caption><thead><tr><th>Endpoint</th><th>State</th><th>Current p95</th><th>Baseline p95</th><th>Absolute delta</th><th>Percent delta</th><th>Current RPS</th><th>Baseline RPS</th><th>Error-rate delta</th></tr></thead><tbody>' + ''.join(endpoint_rows) + '</tbody></table></div>' if endpoint_rows else '<div class="empty">No baseline endpoint comparison is available.</div>'
    timeline = decision.get("timeline", {})
    data_rows = ''.join(f'<tr><td>{label}</td><td>{_fmt(point["offset_seconds"])}</td><td>{_fmt(point["p95"])}</td><td>{_fmt(point["rps"])}</td></tr>' for label, series in (("Current", timeline.get("current", [])), ("Baseline", timeline.get("baseline", []))) for point in series)
    data_table = '<details><summary>View accessible timeline data</summary><div class="table-wrap" tabindex="0"><table><caption>Timeline data in elapsed seconds</caption><thead><tr><th>Series</th><th>Elapsed seconds</th><th>p95 ms</th><th>RPS</th></tr></thead><tbody>' + data_rows + '</tbody></table></div></details>'
    return f'<section><h2>Baseline compatibility</h2><div class="metrics">{compat}</div></section><section><h2>p95 and RPS timeline</h2>{_svg(timeline)}{data_table}</section><section><h2>Endpoint comparison</h2><p>Added and Missing endpoints intentionally have no fabricated percentage delta.</p>{comparison}</section>'

__all__ = ["render_comparison"]
