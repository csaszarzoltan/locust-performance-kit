"""Performance regression baseline comparison.

Stores baseline metrics from Locust test runs and compares new runs against
them to detect performance regressions.

Public API:
    PerformanceBaseline — save and compare baselines
    RegressionResult     — comparison result with regressions/improvements
    Regression           — single regression entry
    Improvement          — single improvement entry
    BaselineNotFoundError — raised when a named baseline doesn't exist
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from locust_templates.correlator import CorrelationSummary


class BaselineNotFoundError(Exception):
    """Raised when a named baseline cannot be found."""


@dataclass
class Regression:
    """A single detected performance regression.

    Attributes:
        endpoint: The endpoint name (e.g. "GET /api/items").
        metric: The metric that regressed (e.g. "p95").
        baseline_value: The baseline value.
        current_value: The current (worse) value.
        degradation_pct: Percentage degradation (e.g. 15.0 for 15% worse).
    """

    endpoint: str
    metric: str
    baseline_value: float
    current_value: float
    degradation_pct: float


@dataclass
class Improvement:
    """A single detected performance improvement.

    Attributes:
        endpoint: The endpoint name.
        metric: The metric that improved.
        baseline_value: The baseline value.
        current_value: The current (better) value.
        improvement_pct: Percentage improvement.
    """

    endpoint: str
    metric: str
    baseline_value: float
    current_value: float
    improvement_pct: float


@dataclass
class RegressionResult:
    """Result of comparing a run against a baseline.

    Attributes:
        regressions: List of detected regressions.
        improvements: List of detected improvements.
        summary: Human-readable summary (1-3 sentences).
    """

    regressions: list[Regression] = field(default_factory=list)
    improvements: list[Improvement] = field(default_factory=list)
    summary: str = ""


class PerformanceBaseline:
    """Save and compare Locust test baselines.

    Stores baseline metrics as JSON files in a configurable directory.
    Comparison detects p95 degradations greater than a threshold (default 10%).

    Example:
        baseline = PerformanceBaseline()
        baseline.save_baseline("results", name="v1.0")
        result = baseline.compare("results_new", baseline_name="v1.0")
        if result.regressions:
            print(result.summary)
    """

    DEFAULT_BASELINE_DIR = ".baselines"
    REGRESSION_THRESHOLD_PCT = 10.0

    def __init__(self, baseline_dir: str | Path | None = None) -> None:
        """Initialize with optional baseline directory.

        Args:
            baseline_dir: Directory to store baseline JSON files.
                          Defaults to ".baselines" in cwd.
        """
        self.baseline_dir = Path(baseline_dir or self.DEFAULT_BASELINE_DIR)

    def save_baseline(
        self,
        csv_prefix: str,
        name: str,
        path: str | Path | None = None,
        correlation_summary: CorrelationSummary | None = None,
    ) -> Path:
        """Save current run metrics as a named baseline."""
        target_dir = Path(path) if path else self.baseline_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        stats = self._parse_stats_csv(csv_prefix)
        endpoints = []
        for row in stats:
            if row.get("Name", "").lower() == "aggregated":
                continue
            endpoints.append(
                {
                    "name": row.get("Name", ""),
                    "type": row.get("Type", ""),
                    "request_count": int(row.get("Request Count", 0) or 0),
                    "failure_count": int(row.get("Failure Count", 0) or 0),
                    "avg_response_time": float(
                        row.get("Average Response Time", 0) or 0
                    ),
                    "p50": float(row.get("50%", 0) or 0),
                    "p95": float(row.get("95%", 0) or 0),
                    "p99": float(row.get("99%", 0) or 0),
                    "rps": float(row.get("Requests/s", 0) or 0),
                }
            )
        baseline_data = {
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "endpoints": endpoints,
        }
        if correlation_summary:
            total = correlation_summary.total_failures
            cascade = correlation_summary.cascade_failures
            baseline_data["cascade_rate"] = (
                cascade / total if total > 0 else 0.0
            )
            baseline_data["cascade_failures"] = cascade
            baseline_data["root_failures"] = correlation_summary.root_failures
        file_path = target_dir / f"{name}.json"
        with open(file_path, "w") as f:
            json.dump(baseline_data, f, indent=2)
        return file_path

    def compare(
        self,
        csv_prefix: str,
        baseline_name: str,
        *,
        threshold_pct: float | None = None,
    ) -> RegressionResult:
        """Compare a current run against a stored baseline."""
        thresh = (
            threshold_pct
            if threshold_pct is not None
            else self.REGRESSION_THRESHOLD_PCT
        )
        baseline_path = self.baseline_dir / f"{baseline_name}.json"
        if not baseline_path.exists():
            raise BaselineNotFoundError(
                f"Baseline '{baseline_name}' not found at {baseline_path}"
            )
        with open(baseline_path) as f:
            baseline_data = json.load(f)
        baseline_endpoints = {
            ep["name"]: ep for ep in baseline_data.get("endpoints", [])
        }
        current_stats = self._parse_stats_csv(csv_prefix)
        current_endpoints = {}
        for row in current_stats:
            if row.get("Name", "").lower() == "aggregated":
                continue
            current_endpoints[row.get("Name", "")] = {
                "p95": float(row.get("95%", 0) or 0),
                "p99": float(row.get("99%", 0) or 0),
                "avg_response_time": float(row.get("Average Response Time", 0) or 0),
            }
        regressions: list[Regression] = []
        improvements: list[Improvement] = []
        for ep_name, baseline_ep in baseline_endpoints.items():
            current_ep = current_endpoints.get(ep_name)
            if not current_ep:
                continue
            for metric in ("p95", "p99", "avg_response_time"):
                b_val = float(baseline_ep.get(metric, 0) or 0)
                c_val = float(current_ep.get(metric, 0) or 0)
                if b_val == 0:
                    continue
                delta_pct = ((c_val - b_val) / b_val) * 100.0
                if delta_pct > thresh:
                    regressions.append(
                        Regression(
                            endpoint=ep_name,
                            metric=metric,
                            baseline_value=b_val,
                            current_value=c_val,
                            degradation_pct=round(delta_pct, 2),
                        )
                    )
                elif delta_pct < -thresh:
                    improvements.append(
                        Improvement(
                            endpoint=ep_name,
                            metric=metric,
                            baseline_value=b_val,
                            current_value=c_val,
                            improvement_pct=round(-delta_pct, 2),
                        )
                    )
        if regressions:
            summary = (
                f"Detected {len(regressions)} regression(s) "
                f"compared to baseline '{baseline_name}' (threshold: {thresh}%)."
            )
        elif improvements:
            summary = (
                f"No regressions. {len(improvements)} improvement(s) "
                f"vs baseline '{baseline_name}'."
            )
        else:
            summary = (
                f"No regressions or improvements vs baseline '{baseline_name}' "
                f"(threshold: {thresh}%)."
            )
        return RegressionResult(
            regressions=regressions,
            improvements=improvements,
            summary=summary,
        )

    def list_baselines(self) -> list[str]:
        """List all stored baseline names."""
        if not self.baseline_dir.exists():
            return []
        return sorted(
            f.stem for f in self.baseline_dir.glob("*.json") if f.is_file()
        )

    @staticmethod
    def _parse_stats_csv(csv_prefix: str) -> list[dict[str, str]]:
        """Parse a Locust _stats.csv file into a list of dicts."""
        stats_path = Path(f"{csv_prefix}_stats.csv")
        if not stats_path.exists():
            return []
        with open(stats_path, newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)


__all__ = [
    "BaselineNotFoundError",
    "Improvement",
    "PerformanceBaseline",
    "Regression",
    "RegressionResult",
]
