"""Report data model for decoupling CSV parsing from report rendering.

Defines dataclasses for Locust test results and a from_csv() factory
that parses Locust CSV output files (_stats, _failures, _exceptions).

Public API:
    ReportData — top-level container
    EndpointStats, FailureRecord, ExceptionRecord — row models
    ReportSummary, ReportMetadata, ThresholdConfig — metadata models
"""

from __future__ import annotations

import csv
import dataclasses
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__version__ = "1.3.0"


# ──────────────────────────────────────────────────────────────
# Sub-models
# ──────────────────────────────────────────────────────────────


@dataclasses.dataclass
class ReportMetadata:
    """Metadata about the report generation."""

    generated_at: str
    tool: str = "locust-performance-kit"
    version: str = __version__
    csv_prefix: str = ""


@dataclasses.dataclass
class ReportSummary:
    """Aggregated summary statistics across all endpoints."""

    total_requests: int = 0
    total_failures: int = 0
    endpoint_count: int = 0
    total_rps: float = 0.0
    failure_rate: float = 0.0


@dataclasses.dataclass
class ThresholdConfig:
    """Threshold configuration for p95/p99 pass-fail evaluation."""

    p95: float | None = None
    p99: float | None = None


@dataclasses.dataclass
class EndpointStats:
    """Per-endpoint performance metrics parsed from _stats.csv."""

    name: str
    request_type: str
    request_count: int
    failure_count: int
    average_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    average_content_size: float
    requests_per_sec: float
    percentile_50: float
    percentile_66: float
    percentile_75: float
    percentile_80: float
    percentile_90: float
    percentile_95: float
    percentile_98: float
    percentile_99: float
    threshold_status: str = "SKIP"


@dataclasses.dataclass
class FailureRecord:
    """A single failure entry from _failures.csv."""

    method: str
    name: str
    type: str
    error: str


@dataclasses.dataclass
class ExceptionRecord:
    """A single exception entry from _exceptions.csv."""

    context: str
    exception: str
    traceback: str


# ──────────────────────────────────────────────────────────────
# Top-level container
# ──────────────────────────────────────────────────────────────


@dataclasses.dataclass
class ReportData:
    """Top-level report data container.

    Decouples CSV parsing from report rendering so that exporters
    (HTML, JSON, Markdown, JUnit XML) can work with a clean model.
    """

    endpoints: list[EndpointStats]
    failures: list[FailureRecord]
    exceptions: list[ExceptionRecord]
    summary: ReportSummary
    metadata: ReportMetadata
    thresholds: ThresholdConfig | None = None

    # ── failure hotspots ──────────────────────────────────────

    def get_failure_hotspots(self) -> list[dict[str, Any]]:
        """Return endpoints sorted by failure rate (descending).

        Only endpoints with at least one failure are included.

        Returns:
            List of dicts with keys: name, failure_count, request_count,
            failure_rate. Sorted by failure_rate descending.
        """
        hotspots: list[dict[str, Any]] = []
        for ep in self.endpoints:
            if ep.failure_count == 0:
                continue
            rate = (
                ep.failure_count / ep.request_count
                if ep.request_count > 0
                else 0.0
            )
            hotspots.append(
                {
                    "name": ep.name,
                    "failure_count": ep.failure_count,
                    "request_count": ep.request_count,
                    "failure_rate": rate,
                }
            )
        hotspots.sort(key=lambda h: h["failure_rate"], reverse=True)
        return hotspots

    # ── factory ──────────────────────────────────────────────

    @classmethod
    def from_csv(
        cls,
        csv_prefix: str | Path,
        *,
        thresholds: dict[str, float] | None = None,
    ) -> ReportData:
        """Build ReportData from Locust CSV output files.

        Args:
            csv_prefix: Prefix path (string or Path). ``{prefix}_stats.csv``
                is required; ``_failures.csv`` and ``_exceptions.csv`` are
                optional.
            thresholds: Optional dict with keys ``"p95"`` and/or ``"p99"``.

        Raises:
            FileNotFoundError: If ``{prefix}_stats.csv`` does not exist.
            ValueError: If thresholds dict contains invalid keys.
        """
        prefix = Path(csv_prefix)
        stats_path = prefix.parent / f"{prefix.name}_stats.csv"
        failures_path = prefix.parent / f"{prefix.name}_failures.csv"
        exceptions_path = prefix.parent / f"{prefix.name}_exceptions.csv"

        if not stats_path.exists():
            raise FileNotFoundError(f"Stats file not found: {stats_path}")

        # Validate threshold keys
        threshold_config: ThresholdConfig | None = None
        if thresholds is not None:
            valid_keys = {"p95", "p99"}
            invalid_keys = set(thresholds.keys()) - valid_keys
            if invalid_keys:
                raise ValueError(
                    f"Invalid threshold keys: {invalid_keys}. "
                    f"Valid keys are: {valid_keys}"
                )
            threshold_config = ThresholdConfig(
                p95=thresholds.get("p95"),
                p99=thresholds.get("p99"),
            )

        # Parse stats
        endpoints: list[EndpointStats] = []
        with open(stats_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Name", "")
                if name.lower() == "aggregated":
                    continue
                ep = _parse_endpoint(row, threshold_config)
                endpoints.append(ep)

        # Parse failures (optional)
        failures: list[FailureRecord] = []
        if failures_path.exists():
            with open(failures_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    failures.append(
                        FailureRecord(
                            method=row.get("Method", ""),
                            name=row.get("Name", ""),
                            type=row.get("Type", ""),
                            error=row.get("Error", ""),
                        )
                    )

        # Parse exceptions (optional)
        exceptions: list[ExceptionRecord] = []
        if exceptions_path.exists():
            with open(exceptions_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    exceptions.append(
                        ExceptionRecord(
                            context=row.get("Context", ""),
                            exception=row.get("Exception", ""),
                            traceback=row.get("Traceback", ""),
                        )
                    )

        # Compute summary
        total_requests = sum(e.request_count for e in endpoints)
        total_failures = sum(e.failure_count for e in endpoints)
        total_rps = sum(e.requests_per_sec for e in endpoints)
        failure_rate = (
            total_failures / total_requests if total_requests > 0 else 0.0
        )
        summary = ReportSummary(
            total_requests=total_requests,
            total_failures=total_failures,
            endpoint_count=len(endpoints),
            total_rps=total_rps,
            failure_rate=failure_rate,
        )

        # Metadata
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        metadata = ReportMetadata(
            generated_at=now,
            csv_prefix=str(prefix),
        )

        return cls(
            endpoints=endpoints,
            failures=failures,
            exceptions=exceptions,
            summary=summary,
            metadata=metadata,
            thresholds=threshold_config,
        )


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────


def _safe_float(value: str | None, default: float = 0.0) -> float:
    """Parse a string as float, returning *default* on failure."""
    try:
        return float(value or default)
    except (ValueError, TypeError):
        return default


def _safe_int(value: str | None, default: int = 0) -> int:
    """Parse a string as int, returning *default* on failure."""
    try:
        return int(float(value or default))
    except (ValueError, TypeError):
        return default


def _parse_endpoint(
    row: dict[str, Any],
    thresholds: ThresholdConfig | None,
) -> EndpointStats:
    """Parse a CSV stat row into an EndpointStats dataclass."""
    p95 = _safe_float(row.get("95%"))
    p99 = _safe_float(row.get("99%"))

    # Determine threshold status
    if thresholds is None:
        threshold_status = "SKIP"
    else:
        status = "PASS"
        if thresholds.p95 is not None and p95 > thresholds.p95:
            status = "FAIL"
        if thresholds.p99 is not None and p99 > thresholds.p99:
            status = "FAIL"
        threshold_status = status

    return EndpointStats(
        name=str(row.get("Name", "")),
        request_type=str(row.get("Type", "")),
        request_count=_safe_int(row.get("Request Count")),
        failure_count=_safe_int(row.get("Failure Count")),
        average_response_time_ms=_safe_float(row.get("Average Response Time")),
        min_response_time_ms=_safe_float(row.get("Min Response Time")),
        max_response_time_ms=_safe_float(row.get("Max Response Time")),
        average_content_size=_safe_float(row.get("Average Content Size")),
        requests_per_sec=_safe_float(row.get("Requests/s")),
        percentile_50=_safe_float(row.get("50%")),
        percentile_66=_safe_float(row.get("66%")),
        percentile_75=_safe_float(row.get("75%")),
        percentile_80=_safe_float(row.get("80%")),
        percentile_90=_safe_float(row.get("90%")),
        percentile_95=p95,
        percentile_98=_safe_float(row.get("98%")),
        percentile_99=p99,
        threshold_status=threshold_status,
    )


__all__ = [
    "EndpointStats",
    "ExceptionRecord",
    "FailureRecord",
    "ReportData",
    "ReportMetadata",
    "ReportSummary",
    "ThresholdConfig",
]
