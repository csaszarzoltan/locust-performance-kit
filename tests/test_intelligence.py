"""Pre-development TDD suite for locust_templates.intelligence (v1.6.0).

Interface tests (imports, dataclass fields, signatures, defaults, type hints)
PASS immediately against the stub module. Behavioral tests FAIL with
NotImplementedError during the RED phase and become active once the developer
implements intelligence.py per analysis/analysis-brief.md §4.1.

Parser tests use REAL Locust-shaped CSV fixtures committed under
tests/fixtures/intelligence/ (headers byte-identical to Locust 2.46.2) — the
parser is never mocked.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

import locust_templates
import locust_templates.intelligence as intelligence_mod
from locust_templates.intelligence import (
    AnalysisReport,
    Anomaly,
    AnomalyDetector,
    Bottleneck,
    BottleneckDetector,
    CapacityProjection,
    CapacityProjector,
    EndpointProfile,
    HistoryPoint,
    Insight,
    InsightGenerator,
    KneePoint,
    LLMInsightProvider,
    RunProfile,
    SLOViolation,
    analyze_run,
    check_slos,
)

FIXTURES = Path(__file__).parent / "fixtures" / "intelligence"
RUN_A = FIXTURES / "run_a" / "run_a"
RUN_B = FIXTURES / "run_b" / "run_b"
RUN_CLEAN = FIXTURES / "run_clean" / "run_clean"
FULL_HISTORY = FIXTURES / "full_history" / "full_history"
LEGACY = FIXTURES / "legacy" / "legacy"
EDGE_MISSING = FIXTURES / "edge" / "edge_missing"
EDGE_EMPTY_HISTORY = FIXTURES / "edge" / "edge_empty_history"

TS0 = 1700000000.0  # first fixture history timestamp (unix seconds)
STATS_HEADER = (
    "Type,Name,Request Count,Failure Count,Median Response Time,Average Response "
    "Time,Min Response Time,Max Response Time,Average Content Size,Requests/s,"
    "Failures/s,50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%"
)

PUBLIC_API = {
    "AnalysisReport", "Anomaly", "AnomalyDetector", "Bottleneck",
    "BottleneckDetector", "CapacityProjection", "CapacityProjector",
    "EndpointProfile", "HistoryPoint", "Insight", "InsightGenerator",
    "KneePoint", "LLMInsightProvider", "RunProfile", "SLOViolation",
    "analyze_run", "check_slos",
}


# ──────────────────────────────────────────────────────────────
# RED-phase helpers (skip when the stub raises NotImplementedError)
# ──────────────────────────────────────────────────────────────


def _parse(prefix: Path, baseline: Path | None = None) -> RunProfile:
    try:
        return RunProfile.from_csv(prefix, baseline_prefix=baseline)
    except NotImplementedError:
        pytest.skip("RunProfile.from_csv not implemented yet — RED phase")


def _detect(profile: RunProfile, detector: AnomalyDetector | None = None) -> list[Anomaly]:
    det = detector or AnomalyDetector()
    try:
        return det.detect(profile)
    except NotImplementedError:
        pytest.skip("AnomalyDetector.detect not implemented yet — RED phase")


def _regressions(current: RunProfile, baseline: RunProfile) -> list[Anomaly]:
    try:
        return AnomalyDetector().detect_baseline_regressions(current, baseline)
    except NotImplementedError:
        pytest.skip("AnomalyDetector.detect_baseline_regressions not implemented yet — RED phase")


def _spikes(profile: RunProfile) -> list[Anomaly]:
    try:
        return AnomalyDetector().detect_error_spikes(profile)
    except NotImplementedError:
        pytest.skip("AnomalyDetector.detect_error_spikes not implemented yet — RED phase")


def _knee(profile: RunProfile) -> KneePoint | None:
    try:
        return BottleneckDetector().detect_rps_saturation_knee(profile)
    except NotImplementedError:
        pytest.skip("BottleneckDetector.detect_rps_saturation_knee not implemented yet — RED phase")


def _weakest(profile: RunProfile, top_n: int = 5) -> list[EndpointProfile]:
    try:
        return BottleneckDetector().rank_weakest_endpoints(profile, top_n=top_n)
    except NotImplementedError:
        pytest.skip("BottleneckDetector.rank_weakest_endpoints not implemented yet — RED phase")


def _correlations(profile: RunProfile) -> list[Bottleneck]:
    try:
        return BottleneckDetector().detect_correlations(profile)
    except NotImplementedError:
        pytest.skip("BottleneckDetector.detect_correlations not implemented yet — RED phase")


def _detect_bottlenecks(profile: RunProfile) -> list[Bottleneck]:
    try:
        return BottleneckDetector().detect(profile)
    except NotImplementedError:
        pytest.skip("BottleneckDetector.detect not implemented yet — RED phase")


def _project(profile: RunProfile, slos: dict[str, float]) -> list[CapacityProjection]:
    try:
        return CapacityProjector().project(profile, slos)
    except NotImplementedError:
        pytest.skip("CapacityProjector.project not implemented yet — RED phase")


def _check_slos(profile: RunProfile, slos: dict[str, float]) -> list[SLOViolation]:
    try:
        return check_slos(profile, slos)
    except NotImplementedError:
        pytest.skip("check_slos not implemented yet — RED phase")


def _generate(
    profile: RunProfile,
    anomalies: list[Anomaly] | None = None,
    bottlenecks: list[Bottleneck] | None = None,
    projections: list[CapacityProjection] | None = None,
) -> list[Insight]:
    try:
        return InsightGenerator().generate(
            profile, anomalies or [], bottlenecks or [], projections or []
        )
    except NotImplementedError:
        pytest.skip("InsightGenerator.generate not implemented yet — RED phase")


def _analyze(prefix: Path, **kwargs) -> AnalysisReport:
    try:
        return analyze_run(str(prefix), **kwargs)
    except NotImplementedError:
        pytest.skip("analyze_run not implemented yet — RED phase")


def _mem_profile(history: list[HistoryPoint] | None = None,
                 endpoints: list[EndpointProfile] | None = None) -> RunProfile:
    """Build an in-memory RunProfile directly (anomaly unit tests, no parser)."""
    return RunProfile(
        csv_prefix="<memory>",
        endpoints=list(endpoints or []),
        aggregated=None,
        failures=[],
        history=list(history or []),
        has_full_history=False,
    )


def _hp(ts: float, error_rate: float, *, rps: float = 100.0, p95: float = 100.0,
        user_count: int = 50, failures_per_sec: float = 0.0,
        request_count: int = 1000) -> HistoryPoint:
    return HistoryPoint(
        timestamp=ts,
        user_count=user_count,
        name="Aggregated",
        method="",
        rps=rps,
        failures_per_sec=failures_per_sec,
        error_rate=error_rate,
        p50=60.0,
        p95=p95,
        p99=130.0,
        request_count=request_count,
        failure_count=0,
    )


# ──────────────────────────────────────────────────────────────
# Interface tests — PASS immediately
# ──────────────────────────────────────────────────────────────


class TestModuleInterface:
    """Module-level contract: importable, __all__ pinned, package re-exports."""

    def test_module_importable(self):
        assert intelligence_mod is not None

    def test_version(self):
        assert intelligence_mod.__version__ == "1.6.0"

    def test_all_export_list_matches_public_api(self):
        assert set(intelligence_mod.__all__) == PUBLIC_API

    def test_all_public_symbols_importable(self):
        for name in sorted(PUBLIC_API):
            assert hasattr(intelligence_mod, name), f"missing {name}"

    def test_package_reexports_intelligence(self):
        for name in sorted(PUBLIC_API):
            assert hasattr(locust_templates, name), f"locust_templates missing {name}"
        assert locust_templates.RunProfile is RunProfile
        assert locust_templates.analyze_run is analyze_run


class TestFixtureInterface:
    """Real Locust CSV fixtures must exist with byte-identical 2.46.2 headers."""

    REQUIRED = [
        "run_a/run_a_stats.csv",
        "run_a/run_a_failures.csv",
        "run_a/run_a_exceptions.csv",
        "run_a/run_a_stats_history.csv",
        "run_b/run_b_stats.csv",
        "run_b/run_b_failures.csv",
        "run_b/run_b_exceptions.csv",
        "run_b/run_b_stats_history.csv",
        "run_clean/run_clean_stats.csv",
        "run_clean/run_clean_stats_history.csv",
        "full_history/full_history_stats.csv",
        "full_history/full_history_stats_history.csv",
        "legacy/legacy_stats.csv",
        "legacy/legacy_history.csv",
        "edge/edge_missing_stats.csv",
        "edge/edge_missing_failures.csv",
        "edge/edge_missing_history.csv",
        "README.md",
    ]

    def test_fixture_files_exist_on_disk(self):
        for rel in self.REQUIRED:
            assert (FIXTURES / rel).is_file(), f"missing fixture {rel}"

    def test_stats_header_byte_identical_to_locust_2462(self):
        first = (FIXTURES / "run_a" / "run_a_stats.csv").read_text(encoding="utf-8").splitlines()[0]
        assert first == STATS_HEADER

    def test_failures_header_byte_identical(self):
        first = (FIXTURES / "run_a" / "run_a_failures.csv").read_text(encoding="utf-8").splitlines()[0]
        assert first == "Method,Name,Error,Occurrences,First Seen,Last Seen"

    def test_history_header_byte_identical(self):
        first = (FIXTURES / "run_a" / "run_a_stats_history.csv").read_text(encoding="utf-8").splitlines()[0]
        assert first == (
            "Timestamp,User Count,Type,Name,Requests/s,Failures/s,50%,66%,75%,80%,90%,"
            "95%,98%,99%,99.9%,99.99%,100%,Total Request Count,Total Failure Count,"
            "Total Median Response Time,Total Average Response Time,Total Min Response "
            "Time,Total Max Response Time,Total Average Content Size"
        )


class TestDataclassInterface:
    """All models are dataclasses with the exact pinned field sets."""

    @pytest.mark.parametrize(
        "cls",
        [EndpointProfile, HistoryPoint, RunProfile, Anomaly, KneePoint, Bottleneck,
         CapacityProjection, SLOViolation, Insight, AnalysisReport],
    )
    def test_is_dataclass(self, cls):
        assert dataclasses.is_dataclass(cls)

    @pytest.mark.parametrize(
        "cls,fields",
        [
            (EndpointProfile, {
                "name", "method", "request_count", "failure_count", "rps",
                "error_rate", "p50", "p95", "p99", "avg_response_time_ms",
                "min_response_time_ms", "max_response_time_ms",
            }),
            (HistoryPoint, {
                "timestamp", "user_count", "name", "method", "rps",
                "failures_per_sec", "error_rate", "p50", "p95", "p99",
                "request_count", "failure_count",
            }),
            (RunProfile, {
                "csv_prefix", "endpoints", "aggregated", "failures", "history",
                "has_full_history", "baseline",
            }),
            (Anomaly, {
                "kind", "endpoint", "metric", "severity", "value", "reference",
                "start_time", "end_time", "message",
            }),
            (KneePoint, {"rps", "p95", "slope_before", "slope_after"}),
            (Bottleneck, {"kind", "endpoint", "severity", "detail", "metrics", "message"}),
            (CapacityProjection, {
                "metric", "endpoint", "slo_value", "current_value",
                "predicted_breach_rps", "method", "confidence", "message",
            }),
            (SLOViolation, {"metric", "endpoint", "slo_value", "actual_value", "status"}),
            (Insight, {"category", "severity", "message"}),
            (AnalysisReport, {
                "csv_prefix", "profile", "anomalies", "bottlenecks", "projections",
                "insights", "slo_violations", "llm_used", "llm_section", "exit_code",
            }),
        ],
    )
    def test_field_sets(self, cls, fields):
        assert {f.name for f in dataclasses.fields(cls)} == fields

    @pytest.mark.parametrize(
        "cls,field",
        [
            (EndpointProfile, "error_rate"),
            (HistoryPoint, "error_rate"),
            (RunProfile, "csv_prefix"),
            (RunProfile, "baseline"),
            (Anomaly, "severity"),
            (Bottleneck, "metrics"),
            (CapacityProjection, "predicted_breach_rps"),
            (SLOViolation, "status"),
            (Insight, "category"),
            (AnalysisReport, "exit_code"),
        ],
    )
    def test_fields_annotated(self, cls, field):
        """Type hints present on every pinned field (strings under future import)."""
        assert field in cls.__annotations__

    def test_run_profile_baseline_defaults_none(self):
        assert RunProfile.__dataclass_fields__["baseline"].default is None

    def test_endpoint_profile_constructs_positionally(self):
        ep = EndpointProfile(
            "GET /api/x", "GET", 100, 1, 10.0, 0.01, 50.0, 95.0, 120.0, 60.0, 1.0, 900.0
        )
        assert ep.name == "GET /api/x"
        assert ep.error_rate == 0.01


class TestSignatureInterface:
    """Exact signatures/defaults from the brief §4.1 — locked for the developer."""

    def test_run_profile_from_csv_is_classmethod_with_baseline(self):
        sig = inspect.signature(RunProfile.from_csv)
        params = sig.parameters
        assert "csv_prefix" in params
        assert "baseline_prefix" in params
        assert params["baseline_prefix"].default is None
        ann = sig.return_annotation
        assert "RunProfile" in (ann if isinstance(ann, str) else str(ann))

    def test_anomaly_detector_init_keyword_only_defaults(self):
        sig = inspect.signature(AnomalyDetector.__init__)
        expected = {
            "z_threshold": 3.0, "ewma_alpha": 0.3, "degradation_pct": 10.0,
            "error_rate_delta": 0.01, "spike_factor": 3.0, "spike_min_rate": 0.01,
            "spike_min_duration_s": 10.0,
        }
        for name, default in expected.items():
            param = sig.parameters[name]
            assert param.kind is inspect.Parameter.KEYWORD_ONLY, name
            assert param.default == default, name

    def test_anomaly_detector_methods(self):
        assert "profile" in inspect.signature(AnomalyDetector.detect).parameters
        cur = inspect.signature(AnomalyDetector.detect_baseline_regressions).parameters
        assert set(cur) == {"self", "current", "baseline"}
        assert "profile" in inspect.signature(AnomalyDetector.detect_error_spikes).parameters
        assert "values" in inspect.signature(AnomalyDetector._zscore_series).parameters
        assert "values" in inspect.signature(AnomalyDetector._ewma_series).parameters
        ann = inspect.signature(AnomalyDetector.detect).return_annotation
        assert "list[Anomaly]" in (ann if isinstance(ann, str) else str(ann))

    def test_bottleneck_detector_init_keyword_only_defaults(self):
        sig = inspect.signature(BottleneckDetector.__init__)
        expected = {
            "knee_min_samples": 5, "knee_slope_ratio": 2.0, "error_threshold": 0.01,
            "corr_threshold": 0.7, "weakness_weights": None,
        }
        for name, default in expected.items():
            param = sig.parameters[name]
            assert param.kind is inspect.Parameter.KEYWORD_ONLY, name
            assert param.default == default, name

    def test_bottleneck_detector_methods(self):
        assert "profile" in inspect.signature(BottleneckDetector.detect).parameters
        assert "profile" in inspect.signature(BottleneckDetector.detect_rps_saturation_knee).parameters
        top_n = inspect.signature(BottleneckDetector.rank_weakest_endpoints).parameters["top_n"]
        assert top_n.default == 5
        assert "profile" in inspect.signature(BottleneckDetector.detect_correlations).parameters
        assert set(inspect.signature(BottleneckDetector._pearson).parameters) == {"self", "xs", "ys"}
        ann = inspect.signature(BottleneckDetector.detect_rps_saturation_knee).return_annotation
        assert "KneePoint" in (ann if isinstance(ann, str) else str(ann))

    def test_capacity_projector_init_keyword_only_defaults(self):
        sig = inspect.signature(CapacityProjector.__init__)
        expected = {
            "min_samples": 5, "confidence_high_corr": 0.7,
            "confidence_medium_corr": 0.4, "noise_ratio": 0.25,
        }
        for name, default in expected.items():
            param = sig.parameters[name]
            assert param.kind is inspect.Parameter.KEYWORD_ONLY, name
            assert param.default == default, name

    def test_capacity_projector_methods(self):
        assert set(inspect.signature(CapacityProjector.project).parameters) == {"self", "profile", "slos"}
        assert set(inspect.signature(CapacityProjector._project_metric).parameters) == {
            "self", "history", "metric", "slo",
        }
        ann = inspect.signature(CapacityProjector.project).return_annotation
        assert "CapacityProjection" in (ann if isinstance(ann, str) else str(ann))

    def test_insight_generator_generate_signature(self):
        sig = inspect.signature(InsightGenerator.generate)
        assert set(sig.parameters) == {"self", "profile", "anomalies", "bottlenecks", "projections"}
        assert set(inspect.signature(InsightGenerator.__init__).parameters) == {"self"}

    def test_llm_provider_init_keyword_only_defaults(self):
        sig = inspect.signature(LLMInsightProvider.__init__)
        expected = {"api_key": None, "base_url": None, "model": None, "timeout_s": 30.0}
        for name, default in expected.items():
            param = sig.parameters[name]
            assert param.kind is inspect.Parameter.KEYWORD_ONLY, name
            assert param.default == default, name

    def test_llm_provider_methods(self):
        assert inspect.signature(LLMInsightProvider.from_env).parameters == {}
        assert "context" in inspect.signature(LLMInsightProvider.enrich).parameters
        ann = inspect.signature(LLMInsightProvider.enrich).return_annotation
        assert "str" in (ann if isinstance(ann, str) else str(ann))

    def test_check_slos_signature(self):
        assert set(inspect.signature(check_slos).parameters) == {"profile", "slos"}

    def test_analyze_run_signature_keyword_only(self):
        sig = inspect.signature(analyze_run)
        params = sig.parameters
        assert params["csv_prefix"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        for name, default in {
            "slos": None, "baseline_prefix": None, "use_llm": False, "llm_provider": None,
        }.items():
            assert params[name].kind is inspect.Parameter.KEYWORD_ONLY, name
            assert params[name].default == default, name
        ann = sig.return_annotation
        assert "AnalysisReport" in (ann if isinstance(ann, str) else str(ann))

    def test_report_methods(self):
        assert "self" in inspect.signature(AnalysisReport.to_markdown).parameters
        assert "self" in inspect.signature(AnalysisReport.to_json).parameters

    def test_detectors_constructible_with_defaults(self):
        assert AnomalyDetector() is not None
        assert BottleneckDetector() is not None
        assert CapacityProjector() is not None
        assert InsightGenerator() is not None
        assert LLMInsightProvider() is not None

    def test_detectors_store_configuration(self):
        det = AnomalyDetector(z_threshold=4.5, spike_min_rate=0.02)
        assert det.z_threshold == 4.5
        assert det.spike_min_rate == 0.02
        bd = BottleneckDetector(knee_min_samples=3, corr_threshold=0.8)
        assert bd.knee_min_samples == 3
        assert bd.corr_threshold == 0.8
        assert bd.weakness_weights == {"error_rate": 0.4, "p95": 0.3, "p99": 0.3}
        cp = CapacityProjector(min_samples=7)
        assert cp.min_samples == 7


# ──────────────────────────────────────────────────────────────
# Behavioral tests — RED phase (NotImplementedError → skip)
# ──────────────────────────────────────────────────────────────


class TestRunProfileParsingBehavior:
    """from_csv against the real fixture files (no parser mocks)."""

    pytestmark = pytest.mark.unit

    def test_parses_run_a_endpoints(self):
        profile = _parse(RUN_A)
        assert len(profile.endpoints) == 6
        assert all(e.name.lower() != "aggregated" for e in profile.endpoints)

    def test_parses_per_endpoint_metrics(self):
        profile = _parse(RUN_A)
        items = next(e for e in profile.endpoints if e.name == "/api/items")
        assert items.method == "GET"
        assert items.p50 == pytest.approx(60.0)
        assert items.p95 == pytest.approx(95.0)
        assert items.p99 == pytest.approx(120.0)
        assert items.rps == pytest.approx(15.0)
        assert items.request_count == 15000
        assert items.error_rate == pytest.approx(0.001)

    def test_aggregated_row_captured_separately(self):
        profile = _parse(RUN_A)
        assert profile.aggregated is not None
        assert profile.aggregated.name == "Aggregated"
        assert profile.aggregated.p95 == pytest.approx(100.0)
        assert profile.aggregated.error_rate == pytest.approx(0.001)

    def test_parses_failures_reusing_failure_record(self):
        profile = _parse(RUN_A)
        assert len(profile.failures) == 2
        assert profile.failures[0].name == "/api/items"
        assert profile.failures[1].name == "/api/orders"

    def test_parses_history_aggregate_rows(self):
        profile = _parse(RUN_A)
        assert len(profile.history) == 13
        assert profile.has_full_history is False
        first = profile.history[0]
        assert first.timestamp == pytest.approx(TS0)
        assert first.user_count == 50
        assert first.name == "Aggregated"
        assert first.rps == pytest.approx(48.0)
        assert first.p95 == pytest.approx(100.0)
        assert first.p99 == pytest.approx(130.0)
        assert first.request_count == 480

    def test_history_error_rate_derived_from_failures_per_sec(self):
        profile = _parse(RUN_A)
        first = profile.history[0]
        expected = first.failures_per_sec / (first.rps + first.failures_per_sec)
        assert first.error_rate == pytest.approx(expected)

    def test_baseline_attached_when_baseline_prefix_given(self):
        profile = _parse(RUN_B, baseline=RUN_A)
        assert profile.baseline is not None
        assert isinstance(profile.baseline, RunProfile)
        assert profile.baseline.csv_prefix == str(RUN_A)
        assert len(profile.baseline.endpoints) == 6

    def test_missing_stats_file_raises(self):
        with pytest.raises((NotImplementedError, FileNotFoundError)):
            RunProfile.from_csv(Path("/nonexistent/prefix_xyz"))

    def test_full_history_flagged(self):
        profile = _parse(FULL_HISTORY)
        assert profile.has_full_history is True
        names = {h.name for h in profile.history}
        assert "Aggregated" in names
        assert any(n != "Aggregated" for n in names)

    def test_legacy_history_filename_and_column(self):
        """_history.csv fallback + legacy 'Request Failure' column tolerance."""
        profile = _parse(LEGACY)
        assert len(profile.history) == 5
        assert profile.has_full_history is False
        first = profile.history[0]
        assert first.failures_per_sec == pytest.approx(0.024)
        assert first.error_rate == pytest.approx(first.failures_per_sec / (first.rps + first.failures_per_sec))

    def test_prefers_stats_history_over_legacy_history(self, tmp_path):
        """When both files exist, _stats_history.csv wins (content proves which)."""
        shutil.copy2(FIXTURES / "run_a" / "run_a_stats.csv", tmp_path / "dual_stats.csv")
        shutil.copy2(FIXTURES / "run_a" / "run_a_stats_history.csv", tmp_path / "dual_stats_history.csv")
        shutil.copy2(FIXTURES / "legacy" / "legacy_history.csv", tmp_path / "dual_history.csv")
        profile = _parse(tmp_path / "dual")
        # 13 modern rows, not the 5 legacy rows
        assert len(profile.history) == 13
        assert profile.history[0].failures_per_sec == pytest.approx(0.048)

    def test_empty_stats_file_does_not_crash(self):
        profile = _parse(EDGE_MISSING)
        assert profile.endpoints == []
        assert profile.aggregated is None
        assert profile.history == []
        assert profile.failures == []

    def test_empty_history_file_does_not_crash(self):
        profile = _parse(EDGE_EMPTY_HISTORY)
        assert len(profile.endpoints) == 1
        assert profile.history == []


class TestCheckSlosBehavior:
    """SLO evaluation against aggregated run metrics (exit-code driver)."""

    pytestmark = pytest.mark.unit

    def test_run_b_p95_violated(self):
        violations = _check_slos(_parse(RUN_B), {"p95": 500})
        assert len(violations) == 1
        v = violations[0]
        assert v.metric == "p95"
        assert v.endpoint == "Aggregated"
        assert v.slo_value == 500
        assert v.actual_value == pytest.approx(560.0)
        assert v.status == "violated"

    def test_run_a_p95_passed(self):
        violations = _check_slos(_parse(RUN_A), {"p95": 500})
        assert violations[0].status == "passed"

    def test_multiple_slos(self):
        violations = _check_slos(_parse(RUN_B), {"p95": 500, "error_rate": 0.01})
        assert {v.metric for v in violations} == {"p95", "error_rate"}
        assert next(v for v in violations if v.metric == "error_rate").status == "violated"

    def test_empty_slos_returns_empty(self):
        assert _check_slos(_parse(RUN_A), {}) == []

    def test_invalid_slo_key_raises(self):
        with pytest.raises((NotImplementedError, ValueError)):
            check_slos(_parse(RUN_A), {"bogus": 1})


class TestAnomalyDetectorBehavior:
    """z-score/EWMA regressions + error spikes, severity + time window."""

    pytestmark = pytest.mark.unit

    def test_detect_healthy_run_without_baseline_is_empty(self):
        """No false positives: detect(run_a, no baseline) MUST return []."""
        assert _detect(_parse(RUN_A)) == []

    def test_detect_regressed_run_with_baseline_flags_orders(self):
        anomalies = _detect(_parse(RUN_B, baseline=RUN_A))
        matches = [
            a for a in anomalies
            if a.kind == "latency_regression" and a.endpoint == "/api/orders" and a.metric == "p95"
        ]
        assert len(matches) >= 1

    def test_orders_regression_values_and_severity(self):
        anomalies = _detect(_parse(RUN_B, baseline=RUN_A))
        match = next(
            a for a in anomalies
            if a.kind == "latency_regression" and a.endpoint == "/api/orders" and a.metric == "p95"
        )
        assert match.value == pytest.approx(652.0)
        assert match.reference == pytest.approx(118.0)
        # degradation (652-118)/118 ≈ 452% ≥ 50% → critical
        assert match.severity == "critical"
        assert match.start_time is None
        assert match.end_time is None
        assert "652" in match.message and "118" in match.message

    def test_error_spike_merged_into_one_window(self):
        """The injected 30 s spike (rows at ts90/100/110) is ONE merged anomaly."""
        anomalies = _detect(_parse(RUN_B, baseline=RUN_A))
        spikes = [a for a in anomalies if a.kind == "error_spike"]
        assert len(spikes) == 1
        spike = spikes[0]
        assert spike.endpoint == "Aggregated"
        assert spike.metric == "error_rate"
        assert spike.start_time == pytest.approx(TS0 + 90)
        assert spike.end_time == pytest.approx(TS0 + 110)
        assert spike.severity == "warning"  # peak 4% < 5%, window 20 s < 60 s

    def test_error_spike_severity_critical_above_5_percent(self):
        profile = _mem_profile([
            _hp(0.0, 0.001), _hp(10.0, 0.07), _hp(20.0, 0.06), _hp(30.0, 0.001),
        ])
        spikes = _spikes(profile)
        assert len(spikes) == 1
        assert spikes[0].severity == "critical"
        assert spikes[0].value == pytest.approx(0.07)
        assert spikes[0].start_time == pytest.approx(10.0)
        assert spikes[0].end_time == pytest.approx(20.0)

    def test_error_spike_merges_consecutive_points(self):
        profile = _mem_profile([
            _hp(0.0, 0.001), _hp(10.0, 0.03), _hp(20.0, 0.04), _hp(30.0, 0.05), _hp(40.0, 0.001),
        ])
        spikes = _spikes(profile)
        assert len(spikes) == 1
        assert spikes[0].start_time == pytest.approx(10.0)
        assert spikes[0].end_time == pytest.approx(30.0)

    def test_error_spike_below_min_duration_not_reported(self):
        """A single sub-10 s blip is not a reportable spike window."""
        profile = _mem_profile([_hp(0.0, 0.001), _hp(10.0, 0.05), _hp(20.0, 0.001)])
        assert _spikes(profile) == []

    def test_regressions_direct_call(self):
        anomalies = _regressions(_parse(RUN_B), _parse(RUN_A))
        assert any(a.kind == "latency_regression" and a.endpoint == "/api/orders" for a in anomalies)

    def test_regressions_empty_when_identical(self):
        assert _regressions(_parse(RUN_A), _parse(RUN_A)) == []

    def test_detect_stats_only_with_baseline_returns_clean(self, tmp_path):
        """Stats-only prefix (no history) + baseline: no IndexError (review #1)."""
        shutil.copy(RUN_B.parent / "run_b_stats.csv", tmp_path / "stats_only_stats.csv")
        profile = _parse(tmp_path / "stats_only", baseline=RUN_A)
        assert profile.history == []
        anomalies = _detect(profile)
        assert anomalies == [] or not any(a.kind == "latency_regression" for a in anomalies)

    def test_regressions_empty_history_returns_clean(self, tmp_path):
        """Empty-history current vs baseline: [] without raising (brief §4.1.1/4.1.2)."""
        shutil.copy(RUN_B.parent / "run_b_stats.csv", tmp_path / "stats_only_stats.csv")
        current = _parse(tmp_path / "stats_only")
        baseline = _parse(RUN_A)
        assert _regressions(current, baseline) == []

    def test_error_spike_reference_uses_history_index(self):
        """Reference EWMA indexes the FULL history, not the flagged subsequence (#4)."""
        det = AnomalyDetector()
        profile = _mem_profile([
            _hp(0.0, 0.06), _hp(10.0, 0.04), _hp(20.0, 0.30), _hp(30.0, 0.25), _hp(40.0, 0.04),
        ])
        spikes = det.detect_error_spikes(profile)
        assert len(spikes) == 1
        ewma = det._ewma_series([h.error_rate for h in profile.history])
        # window starts at history index 2 → background is ewma[1] (pre-spike EWMA)
        assert spikes[0].reference == pytest.approx(
            max(det.spike_factor * ewma[1], det.spike_min_rate)
        )
        assert spikes[0].reference != pytest.approx(
            max(det.spike_factor * ewma[0], det.spike_min_rate)
        )

    def test_zscore_constant_series_is_zero(self):
        det = AnomalyDetector()
        assert det._zscore_series([2.0, 2.0, 2.0, 2.0, 2.0]) == [0.0, 0.0, 0.0, 0.0, 0.0]

    def test_zscore_length_and_positive_tail(self):
        det = AnomalyDetector()
        zs = det._zscore_series([1.0, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        assert len(zs) == 10
        assert zs[-1] > zs[0]

    def test_ewma_seeded_with_first_value(self):
        det = AnomalyDetector()
        assert det._ewma_series([10.0, 10.0, 10.0, 10.0, 10.0]) == [10.0] * 5
        assert det._ewma_series([1.0, 2.0, 3.0])[0] == 1.0

    def test_ewma_alpha_applied(self):
        det = AnomalyDetector(ewma_alpha=0.3)
        assert det._ewma_series([1.0, 2.0, 3.0, 4.0, 5.0]) == pytest.approx(
            [1.0, 1.3, 1.81, 2.467, 3.2269], abs=1e-3
        )


class TestBottleneckDetectorBehavior:
    """RPS knee, weakest-endpoint ranking, Pearson correlations."""

    pytestmark = pytest.mark.unit

    def test_healthy_run_has_no_knee(self):
        assert _knee(_parse(RUN_A)) is None

    def test_run_clean_textbook_knee(self):
        knee = _knee(_parse(RUN_CLEAN))
        assert knee is not None
        assert knee.rps == pytest.approx(150.0, abs=30.0)
        assert knee.p95 == pytest.approx(215.0, abs=30.0)
        assert knee.slope_after > knee.slope_before

    def test_run_b_knee_detected(self):
        knee = _knee(_parse(RUN_B))
        assert knee is not None
        assert 140.0 <= knee.rps <= 200.0

    def test_knee_requires_min_samples(self):
        profile = _mem_profile([_hp(0.0, 0.001), _hp(10.0, 0.001), _hp(20.0, 0.001)])
        assert _knee(profile) is None

    def test_weakest_endpoint_orders_ranked_first(self):
        ranked = _weakest(_parse(RUN_B), top_n=3)
        assert len(ranked) == 3
        assert ranked[0].name == "/api/orders"

    def test_weakest_excludes_zero_request_endpoints(self):
        endpoints = [
            EndpointProfile("/api/used", "GET", 1000, 100, 10.0, 0.1, 50.0, 95.0, 120.0, 60.0, 1.0, 900.0),
            EndpointProfile("/api/never", "GET", 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        ]
        ranked = _weakest(_mem_profile(endpoints=endpoints))
        names = [e.name for e in ranked]
        assert "/api/never" not in names
        assert "/api/used" in names

    def test_correlation_error_rate_grows_with_load(self):
        corrs = _correlations(_parse(RUN_CLEAN))
        assert any("Error rate grows with load" in b.message for b in corrs)

    def test_correlation_p95_grows_with_user_count(self):
        corrs = _correlations(_parse(RUN_CLEAN))
        assert any("P95 latency grows with user count" in b.message for b in corrs)

    def test_detect_run_clean_includes_knee(self):
        bottlenecks = _detect_bottlenecks(_parse(RUN_CLEAN))
        assert any(b.kind == "rps_saturation_knee" for b in bottlenecks)
        assert any(b.kind == "correlation" for b in bottlenecks)

    def test_detect_run_b_includes_weakest_endpoint(self):
        bottlenecks = _detect_bottlenecks(_parse(RUN_B))
        weakest = [b for b in bottlenecks if b.kind == "weakest_endpoint"]
        assert weakest and weakest[0].endpoint == "/api/orders"

    def test_weakest_endpoint_metrics_include_real_p95(self):
        """weakest_endpoint metrics carry the endpoint's real p95/p99/error_rate (#2)."""
        bottlenecks = _detect_bottlenecks(_parse(RUN_B))
        weakest = [
            b for b in bottlenecks
            if b.kind == "weakest_endpoint" and b.endpoint == "/api/orders"
        ]
        assert weakest
        m = weakest[0].metrics
        assert m["p95"] == pytest.approx(652.0)
        assert m["p99"] == pytest.approx(780.0)  # orders 99% column
        assert m["error_rate"] == pytest.approx(750 / 24000)
        assert m["score"] > 0

    def test_pearson_perfect_positive(self):
        bd = BottleneckDetector()
        assert bd._pearson([1.0, 2, 3, 4, 5], [2.0, 4, 6, 8, 10]) == pytest.approx(1.0)

    def test_pearson_zero_variance_returns_zero(self):
        bd = BottleneckDetector()
        assert bd._pearson([1.0, 2, 3], [3.0, 3, 3]) == 0.0

    def test_pearson_too_short_returns_zero(self):
        bd = BottleneckDetector()
        assert bd._pearson([1.0], [2.0]) == 0.0

    def test_pearson_negative(self):
        bd = BottleneckDetector()
        assert bd._pearson([1.0, 2, 3, 4, 5], [5.0, 4, 3, 2, 1]) == pytest.approx(-1.0)


class TestCapacityProjectorBehavior:
    """Trend → predicted SLO breach; flat/insufficient-data semantics."""

    pytestmark = pytest.mark.unit

    def test_run_b_projects_p95_breach(self):
        projections = _project(_parse(RUN_B), {"p95": 500})
        assert len(projections) == 1
        p = projections[0]
        assert p.metric == "p95"
        assert p.endpoint == "Aggregated"
        assert re.fullmatch(r"P95 > 500 ms expected at ~\d+ RPS", p.message)
        assert p.predicted_breach_rps is not None
        # brief pins the message shape; value depends on EWMA alpha — sanity range
        assert 300.0 <= p.predicted_breach_rps <= 500.0
        assert p.method in {"linear", "ewma_linear"}
        assert p.confidence == "high"  # n=13 ≥ 10, |r| ≥ 0.7

    def test_run_clean_projects_p95_breach(self):
        p = _project(_parse(RUN_CLEAN), {"p95": 500})[0]
        assert re.fullmatch(r"P95 > 500 ms expected at ~\d+ RPS", p.message)
        assert p.predicted_breach_rps is not None
        assert 550.0 <= p.predicted_breach_rps <= 950.0

    def test_flat_run_no_breach_projected(self):
        p = _project(_parse(RUN_A), {"p95": 500})[0]
        assert p.predicted_breach_rps is None
        assert p.method == "linear"
        assert p.message == "No breach projected within tested load (trend flat/improving)"

    def test_insufficient_data_when_below_min_samples(self):
        p = _project(_parse(EDGE_MISSING), {"p95": 500})[0]
        assert p.method == "insufficient_data"
        assert p.predicted_breach_rps is None
        assert "Not enough history samples" in p.message
        assert "enable --csv-full-history" in p.message

    def test_multiple_slos_produce_multiple_projections(self):
        projections = _project(_parse(RUN_B), {"p95": 500, "error_rate": 0.01})
        assert [p.metric for p in projections] == ["p95", "error_rate"]

    def test_invalid_slo_key_raises(self):
        with pytest.raises((NotImplementedError, ValueError)):
            CapacityProjector().project(_parse(RUN_A), {"bogus": 1})


class TestInsightGeneratorBehavior:
    """Statistical plain-language insights, ordered by severity."""

    pytestmark = pytest.mark.unit

    def _run_b_objects(self):
        profile = _parse(RUN_B)
        anomalies = [
            Anomaly("latency_regression", "/api/orders", "p95", "critical",
                    652.0, 118.0, None, None, "p95 652ms vs baseline 118ms (+453%)"),
            Anomaly("error_spike", "Aggregated", "error_rate", "warning",
                    0.04, 0.01, TS0 + 90, TS0 + 110, "error rate spiked to 4.00%"),
        ]
        bottlenecks = [
            Bottleneck("rps_saturation_knee", "Aggregated", "warning",
                       "knee at 170 RPS", {"knee_rps": 170.0, "slope_ratio": 2.84},
                       "P95 degrades sharply above ~170 RPS (saturation knee)"),
        ]
        projections = [
            CapacityProjection("p95", "Aggregated", 500.0, 650.0, 343.0,
                               "ewma_linear", "high", "P95 > 500 ms expected at ~343 RPS"),
        ]
        return profile, anomalies, bottlenecks, projections

    def test_summary_insight_generated(self):
        profile = _parse(RUN_B)
        insights = _generate(profile)
        summaries = [i for i in insights if i.category == "summary"]
        assert len(summaries) == 1
        assert summaries[0].severity == "info"
        assert "requests" in summaries[0].message

    def test_one_insight_per_anomaly(self):
        profile, anomalies, _, _ = self._run_b_objects()
        insights = _generate(profile, anomalies=anomalies)
        anomaly_insights = [i for i in insights if i.category == "anomaly"]
        assert len(anomaly_insights) == len(anomalies)
        severities = {i.severity for i in anomaly_insights}
        assert severities == {"critical", "warning"}

    def test_one_insight_per_bottleneck(self):
        profile, _, bottlenecks, _ = self._run_b_objects()
        insights = _generate(profile, bottlenecks=bottlenecks)
        assert len([i for i in insights if i.category == "bottleneck"]) == len(bottlenecks)

    def test_one_insight_per_projection(self):
        profile, _, _, projections = self._run_b_objects()
        insights = _generate(profile, projections=projections)
        capacity = [i for i in insights if i.category == "capacity"]
        assert len(capacity) == len(projections)
        assert capacity[0].message == projections[0].message

    def test_knee_recommendation_mentions_saturation(self):
        profile, _, bottlenecks, _ = self._run_b_objects()
        insights = _generate(profile, bottlenecks=bottlenecks)
        recs = [i for i in insights if i.category == "recommendation"]
        assert any("saturates" in i.message for i in recs)

    def test_weakest_endpoint_recommendation_shows_real_p95(self):
        """Recommendation uses the endpoint's real p95, not zeros (#2)."""
        profile = _parse(RUN_B)
        bottlenecks = _detect_bottlenecks(profile)
        weakest = [
            b for b in bottlenecks
            if b.kind == "weakest_endpoint" and b.endpoint == "/api/orders"
        ]
        insights = _generate(profile, bottlenecks=weakest[:1])
        recs = [i for i in insights if i.category == "recommendation"]
        assert recs and "p95=652ms" in recs[0].message
        assert "error_rate=0.031" in recs[0].message

    def test_insights_ordered_by_severity(self):
        profile, anomalies, bottlenecks, projections = self._run_b_objects()
        insights = _generate(profile, anomalies, bottlenecks, projections)
        rank = {"critical": 0, "warning": 1, "info": 2}
        ranks = [rank[i.severity] for i in insights]
        assert ranks == sorted(ranks)


class TestLLMProviderBehavior:
    """Optional OpenAI-compatible provider with clean statistical fallback."""

    pytestmark = pytest.mark.unit

    def test_from_env_unconfigured(self, monkeypatch):
        monkeypatch.delenv("LOCUST_KIT_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert LLMInsightProvider.from_env().is_configured() is False

    def test_from_env_uses_locust_kit_key_first(self, monkeypatch):
        monkeypatch.setenv("LOCUST_KIT_LLM_API_KEY", "locust-key")
        monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
        provider = LLMInsightProvider.from_env()
        assert provider.is_configured() is True
        assert provider.api_key == "locust-key"

    def test_from_env_falls_back_to_openai_key(self, monkeypatch):
        monkeypatch.delenv("LOCUST_KIT_LLM_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
        provider = LLMInsightProvider.from_env()
        assert provider.is_configured() is True
        assert provider.api_key == "openai-key"

    def test_constructor_key_configures(self):
        assert LLMInsightProvider(api_key="x").is_configured() is True
        assert LLMInsightProvider().is_configured() is False

    def test_enrich_unconfigured_returns_none(self):
        try:
            result = LLMInsightProvider().enrich({"facts": [1, 2, 3]})
        except NotImplementedError:
            pytest.skip("LLMInsightProvider.enrich not implemented yet — RED phase")
        assert result is None

    def test_enrich_never_raises_on_bad_endpoint(self):
        provider = LLMInsightProvider(
            api_key="test-key", base_url="http://127.0.0.1:1/v1", timeout_s=0.5,
        )
        try:
            result = provider.enrich({"facts": [1, 2, 3]})
        except NotImplementedError:
            pytest.skip("LLMInsightProvider.enrich not implemented yet — RED phase")
        assert result is None


class TestAnalyzeRunBehavior:
    """End-to-end orchestration: exit codes, LLM fallback, report model."""

    pytestmark = pytest.mark.unit

    def test_run_a_clean_exit_zero(self):
        report = _analyze(RUN_A)
        assert report.exit_code == 0
        assert report.llm_used is False
        assert report.llm_section is None
        assert report.anomalies == []
        assert report.csv_prefix == str(RUN_A)

    def test_run_b_slo_violation_exit_two(self):
        report = _analyze(RUN_B, slos={"p95": 500})
        assert report.exit_code == 2
        assert any(v.metric == "p95" and v.status == "violated" for v in report.slo_violations)

    def test_run_a_slo_met_exit_zero(self):
        report = _analyze(RUN_A, slos={"p95": 500})
        assert report.exit_code == 0

    def test_no_slos_is_advisory_exit_zero(self):
        report = _analyze(RUN_B)
        assert report.exit_code == 0

    def test_missing_prefix_raises(self):
        with pytest.raises((NotImplementedError, FileNotFoundError)):
            analyze_run("/nonexistent/prefix_xyz")

    def test_unresolvable_baseline_raises(self):
        with pytest.raises((NotImplementedError, ValueError)):
            analyze_run(str(RUN_A), baseline_prefix="no-such-baseline")

    def test_llm_flag_with_unconfigured_provider_falls_back(self, monkeypatch):
        monkeypatch.delenv("LOCUST_KIT_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        report = _analyze(RUN_A, use_llm=True)
        assert report.llm_used is False
        assert report.llm_section is None
        assert report.exit_code == 0  # fallback never changes the exit code

    def test_explicit_unconfigured_provider_falls_back(self):
        report = _analyze(RUN_A, use_llm=True, llm_provider=LLMInsightProvider())
        assert report.llm_used is False
        assert report.llm_section is None


class TestReportRenderingBehavior:
    """Markdown + JSON report rendering (CLI format contract)."""

    pytestmark = pytest.mark.unit

    def _report(self):
        return _analyze(RUN_B, slos={"p95": 500})

    def test_markdown_contains_title(self):
        report = self._report()
        try:
            md = report.to_markdown()
        except NotImplementedError:
            pytest.skip("AnalysisReport.to_markdown not implemented yet — RED phase")
        assert "# AI Performance Intelligence Report" in md
        assert "## SLO Results" in md
        assert "## Anomalies" in md
        assert "## Insights" in md

    def test_markdown_contains_violation_marker(self):
        report = self._report()
        try:
            md = report.to_markdown()
        except NotImplementedError:
            pytest.skip("AnalysisReport.to_markdown not implemented yet — RED phase")
        assert "violated" in md

    def test_to_json_contract_keys(self):
        report = self._report()
        try:
            data = report.to_json()
        except NotImplementedError:
            pytest.skip("AnalysisReport.to_json not implemented yet — RED phase")
        for key in ("csv_prefix", "exit_code", "slo_results", "anomalies",
                    "bottlenecks", "capacity_projections", "insights", "ai_insights"):
            assert key in data, f"missing {key}"
        assert data["exit_code"] == 2
        assert data["ai_insights"] is None
        assert data["slo_results"][0]["status"] == "violated"

    def test_to_json_serializable(self):
        report = self._report()
        try:
            data = report.to_json()
        except NotImplementedError:
            pytest.skip("AnalysisReport.to_json not implemented yet — RED phase")
        json.dumps(data)  # must not raise

    def test_to_json_generated_at_is_real_utc_timestamp(self):
        """generated_at must be a real UTC timestamp, not a static fake (#3)."""
        data = self._report().to_json()
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", data["generated_at"])
        assert data["generated_at"] != "2026-01-01T00:00:00Z"
        ts = datetime.strptime(data["generated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        assert abs((datetime.now(timezone.utc) - ts).total_seconds()) < 300

    def test_markdown_anomalies_table_cells_escaped(self):
        """Anomalies table cells escape '|' and newlines (#6)."""
        profile = _parse(RUN_A)
        report = AnalysisReport(
            str(RUN_A), profile,
            [Anomaly("latency_regression", "/api/a|b", "p95", "warning", 1.0, 0.5,
                     None, None, "line1\nline2")],
            [], [], [], [], False, None, 0,
        )
        md = report.to_markdown()
        assert "| latency_regression | /api/a\\|b | warning | — | line1 line2 |" in md
