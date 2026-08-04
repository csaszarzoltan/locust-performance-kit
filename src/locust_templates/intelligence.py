"""AI Performance Intelligence — pre-development TDD stub (v1.6.0).

Dataclasses are fully defined so interface tests pass immediately; every
behavioral method raises ``NotImplementedError`` until the developer implements
it against the spec in ``analysis/analysis-brief.md`` (§4.1).

Public API (also re-exported from ``locust_templates/__init__.py``):
    EndpointProfile, HistoryPoint, RunProfile, Anomaly, KneePoint, Bottleneck,
    CapacityProjection, SLOViolation, Insight, AnalysisReport,
    AnomalyDetector, BottleneckDetector, CapacityProjector, InsightGenerator,
    LLMInsightProvider, check_slos, analyze_run
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from locust_templates.report_data import FailureRecord

__version__ = "1.6.0"

# ──────────────────────────────────────────────────────────────
# 4.1.1 CSV parsing → RunProfile
# ──────────────────────────────────────────────────────────────


@dataclass
class EndpointProfile:
    """Per-endpoint metrics parsed from {prefix}_stats.csv (excludes Aggregated)."""

    name: str
    method: str
    request_count: int
    failure_count: int
    rps: float
    error_rate: float
    p50: float
    p95: float
    p99: float
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float


@dataclass
class HistoryPoint:
    """One row of {prefix}_stats_history.csv (new Locust) or {prefix}_history.csv (legacy)."""

    timestamp: float
    user_count: int
    name: str
    method: str
    rps: float
    failures_per_sec: float
    error_rate: float
    p50: float
    p95: float
    p99: float
    request_count: int
    failure_count: int


@dataclass
class RunProfile:
    """Structured view of one Locust --csv run (stats + failures + history [+ baseline])."""

    csv_prefix: str
    endpoints: list[EndpointProfile]
    aggregated: EndpointProfile | None
    failures: list[FailureRecord]
    history: list[HistoryPoint]
    has_full_history: bool
    baseline: RunProfile | None = None

    @classmethod
    def from_csv(
        cls,
        csv_prefix: str | Path,
        baseline_prefix: str | Path | None = None,
    ) -> RunProfile:
        """Parse a Locust CSV prefix into a RunProfile (see brief §4.1.1)."""
        raise NotImplementedError


# ──────────────────────────────────────────────────────────────
# 4.1.2 Anomaly detection
# ──────────────────────────────────────────────────────────────


@dataclass
class Anomaly:
    """A detected regression or error spike with severity + time window."""

    kind: str
    endpoint: str
    metric: str
    severity: str
    value: float
    reference: float
    start_time: float | None
    end_time: float | None
    message: str


class AnomalyDetector:
    """z-score + EWMA regression detection vs a baseline, plus error spikes."""

    def __init__(
        self,
        *,
        z_threshold: float = 3.0,
        ewma_alpha: float = 0.3,
        degradation_pct: float = 10.0,
        error_rate_delta: float = 0.01,
        spike_factor: float = 3.0,
        spike_min_rate: float = 0.01,
        spike_min_duration_s: float = 10.0,
    ) -> None:
        self.z_threshold = z_threshold
        self.ewma_alpha = ewma_alpha
        self.degradation_pct = degradation_pct
        self.error_rate_delta = error_rate_delta
        self.spike_factor = spike_factor
        self.spike_min_rate = spike_min_rate
        self.spike_min_duration_s = spike_min_duration_s

    def detect(self, profile: RunProfile) -> list[Anomaly]:
        """All anomaly kinds; uses profile.baseline when present. See brief §4.1.2."""
        raise NotImplementedError

    def detect_baseline_regressions(
        self, current: RunProfile, baseline: RunProfile,
    ) -> list[Anomaly]:
        """Per-endpoint (and Aggregated) z-score + EWMA comparison vs baseline."""
        raise NotImplementedError

    def detect_error_spikes(self, profile: RunProfile) -> list[Anomaly]:
        """Error-rate spikes on the aggregated history, merged into windows."""
        raise NotImplementedError

    def _zscore_series(self, values: Sequence[float]) -> list[float]:
        raise NotImplementedError

    def _ewma_series(self, values: Sequence[float]) -> list[float]:
        raise NotImplementedError


# ──────────────────────────────────────────────────────────────
# 4.1.3 Bottleneck detection
# ──────────────────────────────────────────────────────────────


@dataclass
class KneePoint:
    """RPS-saturation knee of the aggregated P95-vs-RPS curve."""

    rps: float
    p95: float
    slope_before: float
    slope_after: float


@dataclass
class Bottleneck:
    """A detected bottleneck: knee, weakest endpoint, or metric correlation."""

    kind: str
    endpoint: str
    severity: str
    detail: str
    metrics: dict[str, float]
    message: str


class BottleneckDetector:
    """RPS knee, weakest-endpoint ranking, and Pearson metric correlations."""

    def __init__(
        self,
        *,
        knee_min_samples: int = 5,
        knee_slope_ratio: float = 2.0,
        error_threshold: float = 0.01,
        corr_threshold: float = 0.7,
        weakness_weights: dict[str, float] | None = None,
    ) -> None:
        self.knee_min_samples = knee_min_samples
        self.knee_slope_ratio = knee_slope_ratio
        self.error_threshold = error_threshold
        self.corr_threshold = corr_threshold
        self.weakness_weights = weakness_weights or {"error_rate": 0.4, "p95": 0.3, "p99": 0.3}

    def detect(self, profile: RunProfile) -> list[Bottleneck]:
        """knee + weakest endpoints (top 5) + correlations. See brief §4.1.3."""
        raise NotImplementedError

    def detect_rps_saturation_knee(self, profile: RunProfile) -> KneePoint | None:
        """Max-distance-from-chord knee with slope-ratio corroboration."""
        raise NotImplementedError

    def rank_weakest_endpoints(
        self, profile: RunProfile, top_n: int = 5,
    ) -> list[EndpointProfile]:
        """Composite weakness score, descending."""
        raise NotImplementedError

    def detect_correlations(self, profile: RunProfile) -> list[Bottleneck]:
        """Pearson r on aggregated history: r(rps,error_rate) and r(p95,user_count)."""
        raise NotImplementedError

    def _pearson(self, xs: Sequence[float], ys: Sequence[float]) -> float:
        raise NotImplementedError


# ──────────────────────────────────────────────────────────────
# 4.1.4 Capacity projection
# ──────────────────────────────────────────────────────────────


@dataclass
class CapacityProjection:
    """Trend projection of one metric to the load where an SLO would break."""

    metric: str
    endpoint: str
    slo_value: float
    current_value: float
    predicted_breach_rps: float | None
    method: str
    confidence: str
    message: str


class CapacityProjector:
    """Linear/EWMA projection of p95/p99/error_rate vs RPS to SLO breach."""

    def __init__(
        self,
        *,
        min_samples: int = 5,
        confidence_high_corr: float = 0.7,
        confidence_medium_corr: float = 0.4,
        noise_ratio: float = 0.25,
    ) -> None:
        self.min_samples = min_samples
        self.confidence_high_corr = confidence_high_corr
        self.confidence_medium_corr = confidence_medium_corr
        self.noise_ratio = noise_ratio

    def project(self, profile: RunProfile, slos: dict[str, float]) -> list[CapacityProjection]:
        """One projection per SLO key (p95, p99, error_rate). Invalid keys → ValueError."""
        raise NotImplementedError

    def _project_metric(
        self, history: Sequence[HistoryPoint], metric: str, slo: float,
    ) -> CapacityProjection:
        raise NotImplementedError


# ──────────────────────────────────────────────────────────────
# 4.1.5 SLO checking (exit-code driver)
# ──────────────────────────────────────────────────────────────


@dataclass
class SLOViolation:
    """Evaluation of one SLO entry against the aggregated run metrics."""

    metric: str
    endpoint: str
    slo_value: float
    actual_value: float
    status: str


def check_slos(profile: RunProfile, slos: dict[str, float]) -> list[SLOViolation]:
    """Evaluate --slo entries against aggregated p95/p99/error_rate. See brief §4.1.5."""
    raise NotImplementedError


# ──────────────────────────────────────────────────────────────
# 4.1.6 Statistical insight generation
# ──────────────────────────────────────────────────────────────


@dataclass
class Insight:
    """One deterministic plain-language insight."""

    category: str
    severity: str
    message: str


class InsightGenerator:
    """Deterministic, plain-language insights from the analysis results."""

    def __init__(self) -> None:
        pass

    def generate(
        self,
        profile: RunProfile,
        anomalies: list[Anomaly],
        bottlenecks: list[Bottleneck],
        projections: list[CapacityProjection],
    ) -> list[Insight]:
        """Summary + one insight per anomaly/bottleneck/projection + recommendations."""
        raise NotImplementedError


# ──────────────────────────────────────────────────────────────
# 4.1.7 Optional LLM provider (OpenAI-compatible) with clean fallback
# ──────────────────────────────────────────────────────────────


class LLMInsightProvider:
    """OpenAI-compatible enrichment via stdlib urllib; never raises, clean fallback."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model or "gpt-4o-mini"
        self.timeout_s = timeout_s

    @staticmethod
    def from_env() -> LLMInsightProvider:
        """Env precedence: LOCUST_KIT_LLM_API_KEY then OPENAI_API_KEY; etc."""
        return LLMInsightProvider(
            api_key=os.environ.get("LOCUST_KIT_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("LOCUST_KIT_LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL"),
            model=os.environ.get("LOCUST_KIT_LLM_MODEL"),
        )

    def is_configured(self) -> bool:
        """True when an API key is available (env or ctor)."""
        return bool(self.api_key)

    def enrich(self, context: dict[str, Any]) -> str | None:
        """POST {base_url}/chat/completions; returns None on ANY failure, never raises."""
        raise NotImplementedError


# ──────────────────────────────────────────────────────────────
# Report model + orchestration
# ──────────────────────────────────────────────────────────────


@dataclass
class AnalysisReport:
    """Full analysis result: profile, findings, insights, SLO verdict, exit code."""

    csv_prefix: str
    profile: RunProfile
    anomalies: list[Anomaly]
    bottlenecks: list[Bottleneck]
    projections: list[CapacityProjection]
    insights: list[Insight]
    slo_violations: list[SLOViolation]
    llm_used: bool
    llm_section: str | None
    exit_code: int

    def to_markdown(self) -> str:
        """Render the report as markdown (see brief §4.2.2)."""
        raise NotImplementedError

    def to_json(self) -> dict[str, Any]:
        """Serialize the report as a JSON-serializable dict (dataclasses.asdict-based)."""
        raise NotImplementedError


def analyze_run(
    csv_prefix: str,
    *,
    slos: dict[str, float] | None = None,
    baseline_prefix: str | None = None,
    use_llm: bool = False,
    llm_provider: LLMInsightProvider | None = None,
) -> AnalysisReport:
    """End-to-end pipeline; see brief §4.1.7 (analyze_run orchestration)."""
    raise NotImplementedError


__all__ = [
    "AnalysisReport",
    "Anomaly",
    "AnomalyDetector",
    "Bottleneck",
    "BottleneckDetector",
    "CapacityProjection",
    "CapacityProjector",
    "EndpointProfile",
    "HistoryPoint",
    "Insight",
    "InsightGenerator",
    "KneePoint",
    "LLMInsightProvider",
    "RunProfile",
    "SLOViolation",
    "analyze_run",
    "check_slos",
]
