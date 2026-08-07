"""Auditable evidence records derived from deterministic run analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from locust_templates.intelligence import AnalysisReport, analyze_run


@dataclass(frozen=True)
class EvidenceSource:
    """A source file and optional metric window supporting a finding."""

    path: str
    metric: str
    endpoint: str
    start_time: float | None = None
    end_time: float | None = None
    row_numbers: tuple[int, ...] = ()


@dataclass(frozen=True)
class EvidenceFinding:
    """A non-causal, source-linked finding with a validation step."""

    category: str
    severity: str
    message: str
    rule_id: str
    rule_version: str
    confidence: str
    data_quality_grade: str
    sources: tuple[EvidenceSource, ...]
    next_check: str
    current_value: float | None = None
    baseline_value: float | None = None


def _quality(report: AnalysisReport) -> tuple[str, str]:
    points = len([point for point in report.profile.history if point.name == "Aggregated"])
    if points >= 10 and report.profile.aggregated is not None:
        return "A", "high"
    if points >= 5:
        return "B", "medium"
    if report.profile.aggregated is not None:
        return "C", "low"
    return "D", "low"


def evidence_from_report(report: AnalysisReport) -> list[EvidenceFinding]:
    """Map an analysis report to auditable findings without causal claims."""
    grade, default_confidence = _quality(report)
    stats = f"{report.csv_prefix}_stats.csv"
    history = Path(f"{report.csv_prefix}_stats_history.csv")
    history_path = str(history if history.exists() else Path(f"{report.csv_prefix}_history.csv"))
    findings: list[EvidenceFinding] = []
    for item in report.anomalies:
        source = history_path if item.start_time is not None else stats
        findings.append(EvidenceFinding(
            category=item.kind,
            severity=item.severity,
            message=item.message,
            rule_id=f"lpk.anomaly.{item.kind}",
            rule_version="1.0",
            confidence=default_confidence,
            data_quality_grade=grade,
            sources=(EvidenceSource(source, item.metric, item.endpoint, item.start_time, item.end_time),),
            next_check=f"Re-run {item.endpoint} in isolation and inspect the same {item.metric} window.",
            current_value=item.value,
            baseline_value=item.reference,
        ))
    for item in report.bottlenecks:
        metric = "p95" if item.kind != "correlation" else "correlated_metrics"
        findings.append(EvidenceFinding(
            category=item.kind,
            severity=item.severity,
            message=item.message,
            rule_id=f"lpk.bottleneck.{item.kind}",
            rule_version="1.0",
            confidence="high" if abs(item.metrics.get("pearson_r", 0.0)) >= 0.85 else default_confidence,
            data_quality_grade=grade,
            sources=(EvidenceSource(history_path, metric, item.endpoint),),
            next_check="Repeat the load step while reviewing service, database, and load-generator telemetry.",
            current_value=next(iter(item.metrics.values()), None),
        ))
    for item in report.projections:
        findings.append(EvidenceFinding(
            category="capacity_projection",
            severity="info",
            message=item.message,
            rule_id=f"lpk.capacity.{item.method}",
            rule_version="1.0",
            confidence=item.confidence,
            data_quality_grade=grade,
            sources=(EvidenceSource(history_path, item.metric, item.endpoint),),
            next_check="Validate the projected boundary with a stepped load run before changing capacity.",
            current_value=item.current_value,
            baseline_value=item.slo_value,
        ))
    return findings


def build_evidence_findings(
    csv_prefix: str,
    *,
    baseline_prefix: str | None = None,
    slos: dict[str, float] | None = None,
) -> list[EvidenceFinding]:
    """Analyze a CSV run and return source-linked deterministic findings."""
    return evidence_from_report(analyze_run(csv_prefix, baseline_prefix=baseline_prefix, slos=slos))


__all__ = ["EvidenceFinding", "EvidenceSource", "build_evidence_findings", "evidence_from_report"]
