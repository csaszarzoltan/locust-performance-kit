"""Canonical release decision, endpoint comparison, and timeline artifacts."""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from locust_templates.evidence import evidence_from_report

SCHEMA = "performance-decision/v1"
_METRICS = ("p95", "p99", "error_rate", "rps", "request_count", "failure_count")


def _finite(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Decision contains non-finite number")
    if isinstance(value, dict):
        return {key: _finite(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_finite(item) for item in value]
    return value


def _safe_label(value: str | None) -> str | None:
    return None if value is None else Path(value).name


def _metric_delta(current: float | int, baseline: float | int) -> dict[str, Any]:
    absolute = current - baseline
    percent = None if baseline == 0 else absolute / baseline * 100
    return {"current": current, "baseline": baseline, "absolute_delta": absolute, "percent_delta": percent}


def build_endpoint_comparison(profile: Any) -> list[dict[str, Any]]:
    """Return complete common/added/missing endpoint comparison rows."""
    current = {(item.method, item.name): item for item in profile.endpoints}
    baseline = {(item.method, item.name): item for item in profile.baseline.endpoints} if profile.baseline else {}
    rows: list[dict[str, Any]] = []
    for key in sorted(set(current) | set(baseline)):
        cur, base = current.get(key), baseline.get(key)
        state = "COMMON" if cur and base else "ADDED" if cur else "MISSING"
        metrics = {}
        for metric in _METRICS:
            if cur and base:
                metrics[metric] = _metric_delta(getattr(cur, metric), getattr(base, metric))
            else:
                metrics[metric] = {
                    "current": getattr(cur, metric) if cur else None,
                    "baseline": getattr(base, metric) if base else None,
                    "absolute_delta": None,
                    "percent_delta": None,
                }
        rows.append({"method": key[0], "endpoint": key[1], "state": state, "metrics": metrics})
    rows.sort(key=lambda row: (0 if row["state"] == "COMMON" else 1, -(row["metrics"]["p95"]["percent_delta"] or -10**9), row["endpoint"]))
    return rows


def build_timeline(profile: Any) -> dict[str, Any]:
    """Build aligned aggregate p95/RPS series and a compatibility explanation."""
    current = [point for point in profile.history if point.name == "Aggregated"]
    baseline = [point for point in profile.baseline.history if point.name == "Aggregated"] if profile.baseline else []
    def series(points: list[Any]) -> list[dict[str, Any]]:
        if not points:
            return []
        start = points[0].timestamp
        return [{"offset_seconds": point.timestamp - start, "timestamp": point.timestamp, "p95": point.p95, "rps": point.rps} for point in points]
    cur, base = series(current), series(baseline)
    aligned = bool(cur and base)
    reason = "Aligned by elapsed seconds from each run start." if aligned else "A comparable aggregate history series is unavailable."
    return {"aligned": aligned, "reason": reason, "current": cur, "baseline": base}


def baseline_compatibility(profile: Any) -> dict[str, Any]:
    """Describe endpoint overlap and history compatibility without inventing data."""
    if not profile.baseline:
        return {"status": "NO_BASELINE", "common": 0, "added": 0, "missing": 0, "overlap_percent": None, "timeline_aligned": False}
    rows = build_endpoint_comparison(profile)
    common = sum(row["state"] == "COMMON" for row in rows)
    added = sum(row["state"] == "ADDED" for row in rows)
    missing = sum(row["state"] == "MISSING" for row in rows)
    denominator = len({row["endpoint"] for row in rows})
    return {"status": "COMPATIBLE" if common else "AGGREGATE_ONLY", "common": common, "added": added, "missing": missing, "overlap_percent": common / denominator * 100 if denominator else 0.0, "timeline_aligned": build_timeline(profile)["aligned"]}


def build_decision(report: Any, *, run_label: str | None = None, environment: str | None = None, branch: str | None = None, input_hashes: dict[str, str] | None = None) -> dict[str, Any]:
    findings = [asdict(item) for item in evidence_from_report(report)]
    for finding in findings:
        for source in finding.get("sources", []):
            source["path"] = Path(source["path"]).name
    findings.sort(key=lambda item: ({"critical": 0, "warning": 1, "info": 2}.get(item["severity"], 3), item["rule_id"], item["message"]))
    payload = {
        "schema": SCHEMA,
        "analyzer": {"name": "locust-performance-kit", "version": "1.7.0"},
        "run": {"label": run_label or _safe_label(report.csv_prefix), "environment": environment, "branch": branch},
        "inputs": dict(sorted((input_hashes or {}).items())),
        "quality": {"grade": findings[0]["data_quality_grade"] if findings else ("A" if len(report.profile.history) >= 10 else "C")},
        "baseline": {"label": _safe_label(report.profile.baseline.csv_prefix) if report.profile.baseline else None, "compatibility": baseline_compatibility(report.profile)},
        "slos": {item.metric: item.slo_value for item in report.slo_violations},
        "decision": {"status": "FAIL" if report.exit_code == 2 else ("PASS" if report.slo_violations else "ADVISORY"), "exit_code": report.exit_code},
        "summary": report.to_json().get("summary", {}),
        "endpoint_comparison": build_endpoint_comparison(report.profile),
        "timeline": build_timeline(report.profile),
        "findings": findings,
    }
    payload = _finite(payload)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    return {**payload, "hash": {"algorithm": "sha256", "value": digest, "generated_at": datetime.now(timezone.utc).isoformat(), "generated_at_excluded": True}}


def verify_decision(decision: dict[str, Any]) -> bool:
    raw = {key: value for key, value in decision.items() if key != "hash"}
    digest = hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return digest == decision.get("hash", {}).get("value")


def render_markdown(decision: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;").replace("\n", " ")
    lines = ["# Performance Decision", f"**{decision['decision']['status']}** · quality {decision['quality']['grade']}", "", f"Decision hash: `{decision['hash']['value']}`", "", "## Endpoint comparison", "", "| Endpoint | State | Current p95 | Baseline p95 | Delta |", "|---|---:|---:|---:|---:|"]
    for row in decision["endpoint_comparison"]:
        metric = row["metrics"]["p95"]
        percent = "n/a" if metric["percent_delta"] is None else f"{metric['percent_delta']:+.1f}%"
        lines.append(f"| {esc(row['method'])} {esc(row['endpoint'])} | {row['state']} | {metric['current']} | {metric['baseline']} | {percent} |")
    lines += ["", "## Findings"]
    lines += [f"- **{esc(item['severity'].upper())}** {esc(item['message'])} Next check: {esc(item['next_check'])}" for item in decision["findings"][:20]]
    if len(decision["findings"]) > 20:
        lines.append(f"- {len(decision['findings']) - 20} additional findings are available in decision JSON.")
    return "\n".join(lines) + "\n"


def atomic_write(path: str | Path, data: bytes) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_dir():
        raise IsADirectoryError(destination)
    fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix=f".{destination.name}.")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
    return destination


__all__ = ["SCHEMA", "atomic_write", "baseline_compatibility", "build_decision", "build_endpoint_comparison", "build_timeline", "render_markdown", "verify_decision"]
