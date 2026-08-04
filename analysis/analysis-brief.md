# Analysis Brief: AI Performance Intelligence — Anomaly Detection, Bottleneck Insights & Capacity Prediction

**Feature**: `intelligence.py` module + `locust-kit analyze` CLI
**Repo**: `/home/zoltan/locust-performance-kit` (branch `main`) — NOT `/home/zoltan/micro-saas-lab`
**Target version**: v1.6.0 (from v1.5.0)
**Source requirement**: kanban task `t_d5601b83` (root) — research validation inline in the root body (OneUptime 2026-01-28; loadfocus/loadTEST.io commercial SaaS; Gatling 2026 AI tooling survey; pistack.xyz self-hosted trend). No separate researcher brief exists for this decomposition; evidence links are retained from the root task.

---

## 0. Goal, Success Criteria, Constraints

**Goal**: Turn Locust `--csv` outputs into decisions. Parse statistics/failures/history CSVs into a structured run profile; detect anomalies (latency/error regressions vs a prior run, error spikes); identify bottlenecks (RPS-saturation knee, weakest endpoints, metric correlations); predict capacity (trend P95/error-rate to the load level where an SLO breaks, e.g. "P95 > 500 ms expected at ~200 RPS"); generate plain-language insights from deterministic statistical rules with **zero config**, and optionally enrich with an OpenAI-compatible LLM that **degrades cleanly** to the statistical output. New CLI: `locust-kit analyze` with a CI-gating exit-code contract.

**Success criteria** (traceable to root acceptance criteria 1–9):
1. `intelligence.py` parses `{prefix}_stats.csv`, `{prefix}_failures.csv`, `{prefix}_history.csv` / `{prefix}_stats_history.csv` into `RunProfile` with per-endpoint p50/p95/p99, RPS, error rates, and time series.
2. Anomaly detection: configurable z-score + EWMA regression detection vs a baseline run; error-spike detection; every anomaly carries severity + time window.
3. Bottleneck detection: RPS-saturation knee (P95 degrades as load rises), weakest-endpoint ranking, correlation heuristics (error rate vs RPS).
4. Capacity projection: linear/EWMA trend of P95 and error rate → predicted load level where `--slo` breaks.
5. Insight generation: statistical by default (NO LLM required); optional OpenAI-compatible provider with clean fallback.
6. CLI: `locust-kit analyze --csv <prefix> [--slo p95=500 --baseline <prior-prefix> --format markdown|json]` → stdout/file; exit code reflects SLO violations for CI gating.
7. Report artifact plugs into the existing baseline-comparison (`docs/baseline-comparison.md`) and CI/CD gate flow (`docs/ci-cd-gates.md`).
8. Tests: unit + integration for CSV parsing (**real Locust CSV fixtures on disk, no mocks on the parser**), anomaly detection, capacity projection, CLI; existing 810-test suite stays green.
9. Docs: README section, CLI/API reference, CHANGELOG entry, FEATURES-DONE.md entry (documenter task `t_796bd723`).

**Constraints**:
- Reuse existing parsers — `report_data.py` already parses stats/failures/exceptions; extend, do not duplicate (root Tech Context).
- Python 3.9+ — **no `statistics.correlation`** (added in 3.10); implement Pearson manually.
- Zero new runtime dependencies (stdlib `statistics`, `math`, `urllib` only). LLM call via stdlib `urllib.request`.
- Match repo conventions: type hints + docstrings everywhere, dataclasses for models, `argparse` CLIs with `_build_parser()`/`main() -> int`, `from __future__ import annotations`.
- Pre-tester writes tests against the interfaces in this brief **without modifying existing test files**; developer implements to make them pass without touching tests.

---

## 1. Current State Assessment

### 1.1 Repo module/CLI layout (v1.5.0, HEAD 0454330, 810 tests passing)

Package: `src/locust_templates/` (setuptools `packages.find where=["src"]`, `requires-python >=3.9`).

| Module | Role (verified by reading source) |
|---|---|
| `report_data.py` (v1.3.0) | `ReportData.from_csv(prefix)` parses `{prefix}_stats.csv` (required), `_failures.csv`, `_exceptions.csv` (optional) into dataclasses `EndpointStats`, `FailureRecord`, `ExceptionRecord`, `ReportSummary`, `ReportMetadata`, `ThresholdConfig`. Skips the `Aggregated` row. Does **not** parse history files. |
| `report_generator.py` | Legacy `HTMLReportGenerator.from_csv()` — same stats/failures parsing; superseded by report_data but kept. |
| `thresholds.py` | `ThresholdChecker(p95_threshold=500, p99_threshold=1000, error_rate_threshold=0.01).check(p95, p99, error_rate) -> ThresholdResult(passed, failures, metrics)`. |
| `baseline.py` | `PerformanceBaseline(baseline_dir=".baselines")` — `save_baseline(csv_prefix, name)`, `compare(csv_prefix, baseline_name, threshold_pct=10.0) -> RegressionResult(regressions, improvements, summary)`; JSON store; `BaselineNotFoundError`. Compares p95/p99/avg only, percentage-based. |
| `alerts.py` | `AlertRule`, `Alert`, `AlertEngine` — real-time threshold alerts during a running test (not post-hoc analysis). |
| `correlator.py` | `RequestCorrelator`, `CorrelationSummary` — **request-chain** cascade failure detection during a run. Distinct concept from the metric-to-metric correlations in this feature (naming collision risk documented in §4.2.3). |
| `metrics.py` | `MetricsCollector` — thread-safe in-run percentile collection. |
| `live_dashboard.py` | `LiveDashboard`, `TimeSeriesPoint(timestamp, avg_response_time, p95_response_time, throughput, error_rate, active_users)` — in-run rolling time series. |
| `exporters.py` | Strategy pattern: `HTMLExporter`, `JSONExporter`, `MarkdownExporter`, `JUnitXMLExporter` — `render(ReportData) -> str`, `export(data, path) -> str`. |
| `cli.py` | `locust-report` console script → `main(argv=None) -> int`. Exit codes: **0 ok, 1 error, 2 threshold violation**. |
| `cli_gen.py` | `locust-gen` console script with `argparse` subcommands (`from-openapi`). |
| `__init__.py` | Exports public API incl. `ReportData`, `ThresholdChecker`, `PerformanceBaseline`, `LiveDashboard`. New modules must be added here. |

Console scripts in `pyproject.toml`:
```toml
[project.scripts]
locust-report = "locust_templates.cli:main"
locust-gen = "locust_templates.cli_gen:main"
```

### 1.2 Existing test layout

- `tests/conftest.py` — adds `src` to `sys.path`; fixture factories for user classes.
- `tests/unit/` — per-module tests (test_report_data.py, test_cli.py, test_baseline.py, …) with `@pytest.mark.unit`.
- `tests/integration/` — `test_templates.py`, `test_auth_integration.py`.
- `tests/visual/` — structure/output checks.
- `tests/fixtures/` — **existing hand-written fixtures** `sample_stats.csv`, `sample_failures.csv`, `sample_exceptions.csv` (used by `test_report_data.py`). Note they are NOT byte-faithful to real Locust 2.46.2 output (stats lack `Failures/s`; failures use a `Type` column instead of `Occurrences, First Seen, Last Seen`; exceptions use `Context/Exception/Traceback` instead of `Count/Message/Traceback/Nodes`). They are tolerated by tolerant parsers but must **not** be reused as the "real Locust" fixtures for this feature.
- `pytest.ini_options`: testpaths `tests`, markers `unit/integration/visual/slow`. Ruff select `E,F,UP,B,SIM,I`, per-file E501 ignore for tests/src.

### 1.3 Existing CI/baseline flow (integration targets)

- `docs/ci-cd-gates.md` — reusable workflow `.github/workflows/perf-test.yml`: load-test → generate-reports (`locust-report`) → quality-gate (p95/p99/error-rate/RPS; **exit code 2 on breach**) → notify. Outputs: `gate-passed`, `p95-max`, `p99-max`, `error-rate`, `metrics-json`.
- `docs/baseline-comparison.md` — `PerformanceBaseline` JSON-store flow; CI snippet exits 1 on regression.

### 1.4 Gap analysis (what "AI intelligence" must add)

| Gap | Today | Target |
|---|---|---|
| History parsing | Not parsed anywhere in the repo | `RunProfile` time series from `_stats_history.csv` / legacy `_history.csv` |
| "What does this run mean?" | Manual CSV review; thresholds only | Deterministic plain-language insights |
| Regression vs prior run | `baseline.py` %-based p95/p99/avg only, single aggregated comparison | z-score + EWMA regression detection with severity + time window; error-rate included |
| Error spikes | Not detected (only aggregates) | Spike detection on history with window + severity |
| Saturation knee | Not detected | RPS-saturation knee on aggregated p95-vs-RPS curve |
| Weakest endpoint | `get_failure_hotspots()` (failure rate only) | Composite weakness ranking (error rate + p95 + p99) |
| Metric correlations | Not present (correlator.py = request chains) | Pearson correlation heuristics (error vs RPS, P95 vs users) |
| Capacity prediction | Not present | Trend → "SLO expected to breach at ~N RPS" |
| AI narrative | Not present | Optional OpenAI-compatible provider with statistical fallback |
| CI-gating exit code for SLOs | Only threshold check via `locust-report` exit 2 | `locust-kit analyze` exit code 0/1/2 with SLO semantics |

---

## 2. Clustered Options

| Option cluster | A (chosen) | B | C | Effort | Impact |
|---|---|---|---|---|---|
| **CSV parsing** | Reuse `ReportData.from_csv` for stats/failures/exceptions; add a small history parser in `intelligence.py` | Duplicate a new full parser inside `intelligence.py` | Parse history only, derive stats from history aggregates | Low | High — no duplication (root requirement), tolerant to legacy fixtures |
| **Stats math** | Pure stdlib (`statistics`, `math`): manual Pearson, linear least squares closed form, EWMA | `numpy`/`scipy` dependency | `pandas` + rolling | Low | High — zero new deps, Python 3.9-safe, deterministic tests |
| **LLM client** | stdlib `urllib.request` POST to OpenAI-compatible `/chat/completions`, env-configured, optional `--llm` flag | `openai` SDK as optional `[llm]` extra | No LLM at all | Low-Med | Medium — zero deps, clean fallback, SDK optional later |
| **CLI shape** | New console script `locust-kit` (subcommand `analyze`), module `cli_analyze.py` mirroring `cli.py`/`cli_gen.py` patterns | Extend `locust-report` with `--analyze` | Separate standalone script file | Low | High — repo convention (one script per tool), `--csv` stays a flag as specified |
| **Baseline input** | `--baseline <value>` accepts a prior-run CSV prefix **or** a `.baselines/<name>.json` stored baseline (resolution order documented) | Only prior-run prefix | Only stored baseline name | Low | Med — plugs into both existing flows (baseline-comparison.md + raw prefixes) |
| **Fixture strategy** | Commit real-Locust-shaped CSVs under `tests/fixtures/intelligence/` (headers byte-identical to installed Locust 2.46.2) + provenance README + hand-tuned deterministic scenario sets | Mock `csv.DictReader` rows | Generate fixtures at test time by running Locust | Low | High — deterministic tests, no mocks on parser (root acceptance 8), CI-safe |

**Justification for chosen (A)**: satisfies every root constraint (reuse, zero deps, 3.9, no parser mocks), matches repo patterns exactly, and every algorithm is closed-form deterministic — which is precisely what the pre-tester needs to write RED tests with pinned expected values.

---

## 3. Chosen Tech Stack

| Component | Choice | Rationale |
|---|---|---|
| Language | Python 3.9+ (repo floor) | `statistics`, `math`, `urllib`, `csv`, `dataclasses`, `argparse` all stdlib |
| Module | `src/locust_templates/intelligence.py` | Package is `locust_templates` (pre-tester body's `locust_kit/…` is an "e.g." — pin the real path here) |
| CLI module | `src/locust_templates/cli_analyze.py` | Mirrors `cli.py`/`cli_gen.py` (argparse, `_build_parser()`, `main(argv) -> int`) |
| Entry point | `locust-kit = "locust_templates.cli_analyze:main"` | New console script; `analyze` subcommand (repo has subcommand precedent in `locust-gen`) |
| Stats | stdlib `statistics`/`math` — manual Pearson, closed-form OLS, EWMA | `statistics.correlation` is 3.10+; manual keeps 3.9 compat and is trivially testable |
| LLM | stdlib `urllib.request` → `POST {base_url}/chat/completions`, 30 s timeout | Zero deps; env-config via `LOCUST_KIT_LLM_*` / `OPENAI_*`; every failure path → `None` → statistical fallback |
| New runtime deps | **None** | `dependencies` unchanged; version bump 1.5.0 → 1.6.0 |
| Version | v1.6.0 | Semver minor (new feature, no breaking change) |

---

## 4. Proposed Interfaces (exact)

### 4.1 `src/locust_templates/intelligence.py` — public API

All dataclasses follow repo style (`@dataclass`, `from __future__ import annotations`, type hints). `__all__` export list at the bottom; top-level names also re-exported from `locust_templates/__init__.py`.

#### 4.1.1 CSV parsing → RunProfile

```python
@dataclass
class EndpointProfile:
    """Per-endpoint metrics parsed from {prefix}_stats.csv (excludes Aggregated)."""
    name: str
    method: str
    request_count: int
    failure_count: int
    rps: float
    error_rate: float            # failure_count / request_count (0.0 when request_count == 0)
    p50: float
    p95: float
    p99: float
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float

@dataclass
class HistoryPoint:
    """One row of {prefix}_stats_history.csv (new Locust) or {prefix}_history.csv (legacy)."""
    timestamp: float             # unix seconds (int in Locust CSV; keep as float)
    user_count: int
    name: str                    # "Aggregated" or endpoint name (full-history runs)
    method: str
    rps: float
    failures_per_sec: float      # column "Failures/s" (2.46.2) or legacy "Request Failure"
    error_rate: float            # failures_per_sec / (rps + failures_per_sec); 0.0 if denominator <= 0
    p50: float
    p95: float
    p99: float
    request_count: int           # "Total Request Count" on aggregate rows (0 for per-endpoint rows)
    failure_count: int           # "Total Failure Count" on aggregate rows

@dataclass
class RunProfile:
    """Structured view of one Locust --csv run (stats + failures + history [+ baseline])."""
    csv_prefix: str
    endpoints: list[EndpointProfile]        # all non-Aggregated endpoints
    aggregated: EndpointProfile | None      # Aggregated row, if present
    failures: list[FailureRecord]           # reuse locust_templates.report_data.FailureRecord
    history: list[HistoryPoint]             # aggregate-only by default; per-endpoint rows when full history
    has_full_history: bool                  # True when history contains non-Aggregated rows
    baseline: RunProfile | None = None      # attached when baseline_prefix was resolved

    @classmethod
    def from_csv(
        cls,
        csv_prefix: str | Path,
        baseline_prefix: str | Path | None = None,
    ) -> RunProfile:
        """Parse a Locust CSV prefix into a RunProfile.

        - {prefix}_stats.csv is REQUIRED (FileNotFoundError with a clear message if missing).
        - {prefix}_failures.csv / {prefix}_exceptions.csv are parsed via
          ReportData.from_csv() and reused (never re-parsed by hand).
        - History: prefers {prefix}_stats_history.csv (Locust >= ~2.15), falls back to
          {prefix}_history.csv (legacy). Optional — empty list if neither exists.
        - Column-tolerant: missing numeric columns parse as 0.0 (existing sample_* fixtures
          must keep working); header names are matched case-insensitively.
        - When baseline_prefix is given, resolves it (see §4.2.4 resolution rules) and attaches
          the parsed baseline profile to ``baseline``.
        Raises:
            FileNotFoundError: stats file missing.
            ValueError: unreadable/malformed CSV (bad header, undecodable rows).
        """
```

Implementation notes for the developer:
- `ReportData.from_csv()` is called internally for stats/failures/exceptions; map its `EndpointStats` list → `EndpointProfile` list (skip the `Aggregated` row there, capture it separately), and reuse its `failures` verbatim.
- History rows: use `csv.DictReader`; aggregate-only runs have `Name == "Aggregated"`; `has_full_history` = any row with a non-Aggregated name. Percentiles are matched by exact header keys `"50%"`, `"95%"`, `"99%"` (present in both modern and legacy history schemas). Timestamp column is `"Timestamp"`.
- Do not mutate `report_data.py`; all history logic lives in `intelligence.py`.

#### 4.1.2 Anomaly detection (z-score, EWMA, error spikes)

```python
@dataclass
class Anomaly:
    kind: str                  # "latency_regression" | "error_rate_regression" | "error_spike"
    endpoint: str              # endpoint name or "Aggregated"
    metric: str                # "p95" | "p99" | "error_rate"
    severity: str              # "info" | "warning" | "critical"
    value: float               # offending value (aggregated or peak within window)
    reference: float           # baseline value / EWMA reference / rolling mean
    start_time: float | None   # window start (unix s) — None for aggregated comparisons
    end_time: float | None     # window end (unix s) — None for aggregated comparisons
    message: str               # human-readable, e.g. "p95 652ms vs baseline 118ms (+452%)"

class AnomalyDetector:
    def __init__(
        self,
        *,
        z_threshold: float = 3.0,          # |z| above this flags a point (within-run drift)
        ewma_alpha: float = 0.3,           # EWMA smoothing factor for regression/spike reference
        degradation_pct: float = 10.0,     # p95/p99 regression threshold vs baseline (percent)
        error_rate_delta: float = 0.01,    # absolute error-rate regression threshold vs baseline
        spike_factor: float = 3.0,         # error-rate spike threshold: rate > factor * EWMA(ref)
        spike_min_rate: float = 0.01,      # absolute floor for a spike (1% error rate)
        spike_min_duration_s: float = 10.0,# minimum window length to report a spike (s)
    ) -> None:
        ...

    def detect(self, profile: RunProfile) -> list[Anomaly]:
        """All anomaly kinds. Uses profile.baseline when present (z-score + EWMA regressions),
        otherwise within-run drift (z-score on the history series) + error spikes.
        Returns [] for a healthy run. Never raises on missing data."""

    def detect_baseline_regressions(
        self, current: RunProfile, baseline: RunProfile,
    ) -> list[Anomaly]:
        """Per-endpoint (and Aggregated) comparison vs baseline:
        1) z-score: z = (cur - base) / (std(cur history series) + 1e-9);
           flag when z >= z_threshold AND cur > base (regression direction).
        2) EWMA: ewma_ref = EWMA(alpha) over the current history series;
           p95/p99 regression when (ewma_last - base) / base * 100 >= degradation_pct;
           error-rate regression when ewma_last - base >= error_rate_delta.
        Severity: critical if z >= 6 or degradation >= 50% or error delta >= 0.05;
                  warning if z >= 4 or degradation >= 20% or error delta >= 0.02;
                  else info."""

    def detect_error_spikes(self, profile: RunProfile) -> list[Anomaly]:
        """On the aggregated history error-rate series:
        baseline = EWMA(alpha) of error rate (seeded with first value).
        Flag point when error_rate > max(spike_factor * baseline, spike_min_rate).
        Merge consecutive flagged points into ONE anomaly with start_time/end_time.
        Severity: critical if any point in window >= 0.05 or window >= 60 s;
                  warning if >= spike_min_rate; else info."""

    # ── helpers (private, but unit-testable via the public methods) ──
    def _zscore_series(self, values: Sequence[float]) -> list[float]: ...
    def _ewma_series(self, values: Sequence[float]) -> list[float]: ...
```

Deterministic contract for pre-tester: with the fixture family in §5 (`run_a` baseline healthy, `run_b` regressed), `detect(run_b_with_baseline)` MUST emit at least one `latency_regression` on the endpoint whose p95 jumped (e.g. `POST /api/orders`), at least one `error_spike` covering the injected 30 s window, and `detect(run_a_without_baseline)` MUST return `[]` (no false positives).

#### 4.1.3 Bottleneck detection

```python
@dataclass
class KneePoint:
    rps: float
    p95: float
    slope_before: float          # p95-per-RPS slope of the segment before the knee
    slope_after: float           # p95-per-RPS slope of the segment after the knee

@dataclass
class Bottleneck:
    kind: str                    # "rps_saturation_knee" | "weakest_endpoint" | "correlation"
    endpoint: str
    severity: str                # "info" | "warning" | "critical"
    detail: str                  # short machine-readable summary
    metrics: dict[str, float]    # e.g. {"knee_rps": 152.3, "slope_ratio": 4.1} or {"pearson_r": 0.83}
    message: str                 # human-readable

class BottleneckDetector:
    def __init__(
        self,
        *,
        knee_min_samples: int = 5,         # min history points (aggregated) to attempt knee detection
        knee_slope_ratio: float = 2.0,     # corroboration: slope_after / slope_before >= this
        error_threshold: float = 0.01,     # min error rate for correlation bottlenecks
        corr_threshold: float = 0.7,       # |Pearson r| at/above which a correlation is reported
        weakness_weights: dict[str, float] | None = None,  # default {"error_rate":0.4,"p95":0.3,"p99":0.3}
    ) -> None:
        ...

    def detect(self, profile: RunProfile) -> list[Bottleneck]:
        """knee (aggregated history) + weakest endpoints (top_n=5) + correlations."""

    def detect_rps_saturation_knee(self, profile: RunProfile) -> KneePoint | None:
        """Aggregated history: sort points by rps ascending (dedupe), keep the upper envelope
        (max p95 per rps bucket to ignore dips). Primary method = max-distance-from-chord
        (kneedle-style): normalize rps and p95 to [0,1], take the point with the maximum
        perpendicular distance from the chord joining first and last point.
        Corroborate: slope_after / slope_before >= knee_slope_ratio (slopes from linear fits
        of each segment). Returns None when < knee_min_samples points or no knee found."""

    def rank_weakest_endpoints(
        self, profile: RunProfile, top_n: int = 5,
    ) -> list[EndpointProfile]:
        """Composite weakness score, descending:
        score = 0.4*err_norm + 0.3*p95_norm + 0.3*p99_norm
        where x_norm = x / max(x across endpoints) (0 when max == 0).
        Excludes endpoints with request_count == 0 and the Aggregated row."""

    def detect_correlations(self, profile: RunProfile) -> list[Bottleneck]:
        """Pearson r on aggregated history:
        - r(rps, error_rate): if r >= corr_threshold AND max error_rate > error_threshold
          → kind "correlation", message 'Error rate grows with load (r=0.83)'; critical if
          max error_rate >= 0.05 else warning.
        - r(p95, user_count): if r >= corr_threshold
          → kind "correlation", message 'P95 latency grows with user count (r=0.74)'.
        Naming note: this is METRIC-to-METRIC correlation — deliberately distinct from
        locust_templates.correlator (request-chain cascade failures)."""

    def _pearson(self, xs: Sequence[float], ys: Sequence[float]) -> float:
        """Manual Pearson r (statistics.correlation is 3.10+; manual keeps 3.9 compat).
        Returns 0.0 when either input has < 2 points or zero variance."""
```

#### 4.1.4 Capacity projection

```python
@dataclass
class CapacityProjection:
    metric: str                  # "p95" | "p99" | "error_rate"
    endpoint: str                # "Aggregated"
    slo_value: float             # e.g. 500.0 (ms) or 0.01 (ratio)
    current_value: float         # aggregated value of the run
    predicted_breach_rps: float | None  # ~N RPS where the SLO is expected to break (None = no breach)
    method: str                  # "linear" | "ewma_linear" | "insufficient_data"
    confidence: str              # "high" | "medium" | "low"
    message: str                 # e.g. "P95 > 500 ms expected at ~200 RPS" / "No breach projected within tested load"

class CapacityProjector:
    def __init__(
        self,
        *,
        min_samples: int = 5,
        confidence_high_corr: float = 0.7,
        confidence_medium_corr: float = 0.4,
        noise_ratio: float = 0.25,   # std/mean of p95 series above which EWMA smoothing is used
    ) -> None:
        ...

    def project(self, profile: RunProfile, slos: dict[str, float]) -> list[CapacityProjection]:
        """One projection per SLO key in slos (supported keys: p95, p99, error_rate)
        using the aggregated history series. Invalid keys → ValueError."""

    def _project_metric(self, history: Sequence[HistoryPoint], metric: str, slo: float) -> CapacityProjection:
        """Linear least squares of metric vs rps on the aggregated history (closed-form slope
        and intercept; no numpy). If std/mean of the metric series > noise_ratio, first
        EWMA-smooth (method "ewma_linear").
        slope > 0 and crossing within/above observed rps range → predicted_breach_rps =
        (slo - intercept) / slope, clamped to >= max observed rps (extrapolation), rounded to
        nearest integer for the message ("~200 RPS").
        slope <= 0 → predicted_breach_rps = None, message "No breach projected within tested
        load (trend flat/improving)".
        Confidence: corr(metric, rps) >= 0.7 and n >= 10 → high; >= 0.4 and n >= 5 → medium;
        else low. n < min_samples → method "insufficient_data", message
        'Not enough history samples (N < 5) to project capacity; enable --csv-full-history'."""
```

#### 4.1.5 SLO checking (exit-code driver)

```python
@dataclass
class SLOViolation:
    metric: str          # "p95" | "p99" | "error_rate"
    endpoint: str        # "Aggregated"
    slo_value: float
    actual_value: float
    status: str          # "violated" | "passed"

def check_slos(profile: RunProfile, slos: dict[str, float]) -> list[SLOViolation]:
    """Evaluate --slo entries against the aggregated run metrics:
    p95/p99 compared to aggregated p95/p99 (ms); error_rate compared to aggregated
    error_rate (ratio 0-1). Violated when actual > slo. Empty slos → []."""
```

#### 4.1.6 Statistical insight generation

```python
@dataclass
class Insight:
    category: str      # "summary" | "anomaly" | "bottleneck" | "capacity" | "recommendation"
    severity: str      # "info" | "warning" | "critical"
    message: str

class InsightGenerator:
    def __init__(self) -> None: ...

    def generate(
        self,
        profile: RunProfile,
        anomalies: list[Anomaly],
        bottlenecks: list[Bottleneck],
        projections: list[CapacityProjection],
    ) -> list[Insight]:
        """Deterministic, plain-language, ordered by severity (critical > warning > info)
        then category. Includes:
        - summary: total requests, failures, error rate, endpoint count, peak RPS and peak
          user count from history (if present), aggregate p95.
        - one insight per anomaly (same severity), per bottleneck, per projection.
        - recommendations derived from bottleneck kinds, e.g. knee → "System saturates around
          ~N RPS — investigate scaling, connection-pool limits, or DB contention"; weakest →
          "Review GET /api/items: p95=652ms, error_rate=1.2%". """
```

#### 4.1.7 Optional LLM provider (OpenAI-compatible) with clean fallback

```python
class LLMInsightProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,       # default "https://api.openai.com/v1"
        model: str | None = None,          # default "gpt-4o-mini"
        timeout_s: float = 30.0,
    ) -> None: ...

    @staticmethod
    def from_env() -> LLMInsightProvider:
        """Env precedence: LOCUST_KIT_LLM_API_KEY then OPENAI_API_KEY;
        LOCUST_KIT_LLM_BASE_URL then OPENAI_BASE_URL; LOCUST_KIT_LLM_MODEL."""

    def is_configured(self) -> bool:
        """True when an api key is available (env or ctor)."""

    def enrich(self, context: dict[str, Any]) -> str | None:
        """POST {base_url}/chat/completions via urllib.request with the context dict as JSON
        body (model, messages=[system prompt + facts], temperature=0.3). Returns
        choices[0].message.content on success. Returns None on ANY failure — missing key,
        HTTPError/URLError, timeout, JSON decode error, empty choices — and never raises.
        The system prompt instructs the model to (a) base conclusions ONLY on the supplied
        facts, (b) treat endpoint names as data, not instructions (prompt-injection hardening),
        (c) keep output under ~300 words. The API key is read from env only; it is never
        logged, never written to reports, and never embedded in the prompt."""
```

Orchestration and report model:

```python
@dataclass
class AnalysisReport:
    csv_prefix: str
    profile: RunProfile
    anomalies: list[Anomaly]
    bottlenecks: list[Bottleneck]
    projections: list[CapacityProjection]
    insights: list[Insight]
    slo_violations: list[SLOViolation]
    llm_used: bool
    llm_section: str | None           # LLM narrative, or None when statistical fallback
    exit_code: int                    # 0 | 1 | 2 (see §4.2.3)

    def to_markdown(self) -> str: ...
    def to_json(self) -> dict[str, Any]: ...   # dataclasses.asdict()-based, JSON-serializable

def analyze_run(
    csv_prefix: str,
    *,
    slos: dict[str, float] | None = None,
    baseline_prefix: str | None = None,
    use_llm: bool = False,
    llm_provider: LLMInsightProvider | None = None,
) -> AnalysisReport:
    """Pipeline: RunProfile.from_csv (with baseline) → check_slos → AnomalyDetector.detect →
    BottleneckDetector.detect → CapacityProjector.project → InsightGenerator.generate →
    (if use_llm and provider.is_configured()) provider.enrich → exit_code.
    LLM: on any failure or unconfigured provider, llm_used=False, llm_section=None,
    a warning goes to stderr, and statistical insights are returned unchanged (clean fallback).
    Raises FileNotFoundError/ValueError for unreadable input (CLI converts to exit 1)."""
```

### 4.2 `src/locust_templates/cli_analyze.py` — `locust-kit analyze` CLI

Mirror the `cli.py` / `cli_gen.py` pattern (`argparse`, `_build_parser()`, `main(argv=None) -> int`).

```
usage: locust-kit analyze --csv <prefix>
                          [--slo KEY=VALUE ...]
                          [--baseline <prior-prefix|baseline-name>]
                          [--format markdown|json]
                          [--output PATH|-]
                          [--llm]
                          [--version]
```

#### 4.2.1 Flags

| Flag | Required | Default | Semantics |
|---|---|---|---|
| `--csv <prefix>` | yes | — | Locust CSV prefix; `{prefix}_stats.csv` must exist. Missing → stderr message + exit 1. |
| `--slo KEY=VALUE` | no | none | Repeatable. Keys: `p95`, `p99` (ms), `error_rate` (ratio 0–1). Invalid key/value → stderr + exit 1. |
| `--baseline <value>` | no | none | Prior-run CSV prefix OR stored baseline name (resolution in §4.2.4). Enables z-score/EWMA regression anomalies. Unresolvable → stderr + exit 1. |
| `--format {markdown,json}` | no | `markdown` | Report rendering. |
| `--output PATH` | no | `-` (stdout) | Write report to file (parents created) or stdout with `-`. |
| `--llm` | no | off | Opt-in OpenAI-compatible enrichment. Unconfigured/failed → statistical fallback + stderr warning, exit code unchanged. |
| `--version` | no | — | `locust-kit 1.6.0` |

`locust-kit` with no subcommand prints help and exits 1 (usage error), matching repo CLI behavior.

#### 4.2.2 Output formats

- **markdown** (default, human-facing): `# AI Performance Intelligence Report`; Run summary block; `## SLO Results` table (Metric / SLO / Actual / Status with ✔/✘); `## Anomalies` table (Kind / Endpoint / Severity / Window / Message); `## Bottlenecks` list; `## Capacity Projections` list; `## Insights` bullets (`[CRITICAL]`, `[WARNING]`, `[INFO]`); `## AI Insights` (only when `--llm` succeeded); footer `Generated by locust-performance-kit 1.6.0 at <ts>`, csv prefix, baseline used.
- **json** (CI/automation contract): `{csv_prefix, generated_at, tool, version, baseline, summary{...}, slo_results[{metric,endpoint,slo_value,actual_value,status}], anomalies[...], bottlenecks[...], capacity_projections[...], insights[...], ai_insights: str|null, exit_code}` — every dataclass serialized via `dataclasses.asdict` (deterministic key order), `json.dumps(indent=2)`.

#### 4.2.3 Exit-code contract (CI gating)

| Code | Meaning | When |
|---|---|---|
| `0` | Success, all SLOs met | Analysis completed; no `--slo` given, or every SLO `passed`. |
| `1` | Usage / I/O / parse error | Missing `--csv`, stats file not found, malformed CSV, invalid `--slo` key/value, unresolvable `--baseline`, unknown `--format`. Message on stderr. |
| `2` | SLO violation | Analysis completed; ≥ 1 `--slo` entry reports `violated` on the **measured** run. |

- **Projected** breaches (capacity projection) never change the exit code — they are advisory (documented in the report). This keeps CI deterministic: only measured SLO violations gate the pipeline.
- Exit code 2 mirrors the existing `locust-report` convention and the `quality-gate` job ("Exit code 2 on failure") in `docs/ci-cd-gates.md` — consistent, no new code semantics.
- Without `--slo`, the command is purely advisory and always exits 0 on successful analysis.

#### 4.2.4 `--baseline` resolution order (deterministic)

1. If `Path("{value}_stats.csv").exists()` → treat `value` as a **prior-run CSV prefix**, parse via `RunProfile.from_csv(value)`.
2. Elif `Path(".baselines/{value}.json").exists()` → treat `value` as a **stored baseline name**, load its per-endpoint p95/p99/avg/error-rate map and build a minimal `RunProfile` baseline (history empty).
3. Else → stderr `error: baseline '<value>' not found (neither <value>_stats.csv nor .baselines/<value>.json)` + exit 1.

This plugs into **both** existing flows: raw prior prefixes (developer's `--baseline <prior-prefix>` requirement) and the `PerformanceBaseline` JSON store (`docs/baseline-comparison.md`).

### 4.3 `pyproject.toml` changes

```toml
version = "1.6.0"
# dependencies: UNCHANGED (no new runtime deps)

[project.scripts]
locust-report = "locust_templates.cli:main"
locust-gen = "locust_templates.cli_gen:main"
locust-kit = "locust_templates.cli_analyze:main"   # NEW
```

### 4.4 Integration with existing baseline-comparison + CI/CD gate flow

- **CI step** (documented, implemented by the developer in `docs/ci-cd-gates.md`, optional input `run-analysis` default `true`): in the `quality-gate` job, after the existing threshold check:
  ```yaml
  - name: AI performance analysis
    run: |
      locust-kit analyze --csv results --slo p95=${{ inputs.p95-threshold }} \
        --baseline production --format json --output analysis-report.json
    # exit 2 fails the job → deploy blocked; analysis-report.json uploaded as artifact
  ```
- `analysis-report.json` is added to the workflow artifacts and its `summary`/`exit_code` exposed as step outputs (`analysis-exit-code`); `metrics-json` output remains the canonical metrics source — the new report is additive.
- **Baseline flow**: `--baseline production` resolves via §4.2.4 step 2 against the same `.baselines/production.json` the existing `PerformanceBaseline.compare()` writes — no changes to `baseline.py` needed.

### 4.5 `__init__.py` exports (additive)

```python
from locust_templates.intelligence import (
    AnalysisReport, Anomaly, AnomalyDetector, Bottleneck, BottleneckDetector,
    CapacityProjection, CapacityProjector, EndpointProfile, HistoryPoint,
    Insight, InsightGenerator, KneePoint, LLMInsightProvider, RunProfile,
    SLOViolation, analyze_run, check_slos,
)
```
(+ matching `__all__` additions.)

---

## 5. Real-Locust CSV Fixture Strategy (for tests)

**Constraint (root acceptance 8): REAL Locust CSV fixtures, no mocks on the parser.** Fixtures are committed static files under `tests/fixtures/intelligence/`; parser tests read them from disk with `csv.DictReader` — never fabricated row dicts.

### 5.1 Schema (authoritative — from the installed Locust 2.46.2 in the repo `.venv`, `locust/stats.py`)

- **stats** `{prefix}_stats.csv`: `Type, Name, Request Count, Failure Count, Median Response Time, Average Response Time, Min Response Time, Max Response Time, Average Content Size, Requests/s, Failures/s, 50%, 66%, 75%, 80%, 90%, 95%, 98%, 99%, 99.9%, 99.99%, 100%`
- **failures** `{prefix}_failures.csv`: `Method, Name, Error, Occurrences, First Seen, Last Seen`
- **exceptions** `{prefix}_exceptions.csv`: `Count, Message, Traceback, Nodes`
- **history** (2.46.2) `{prefix}_stats_history.csv`: `Timestamp, User Count, Type, Name, Requests/s, Failures/s, 50%, 66%, 75%, 80%, 90%, 95%, 98%, 99%, 99.9%, 99.99%, 100%, Total Request Count, Total Failure Count, Total Median Response Time, Total Average Response Time, Total Min Response Time, Total Max Response Time, Total Average Content Size`
- **legacy** (≤2.7) `{prefix}_history.csv`: history with `Request Failure` instead of `Failures/s`, and `Total Requests/s, Total Requests, Total Failures` trailing columns. Used for the tolerance test only.
- History cadence: 10 s sliding window, one row per interval; **only `Aggregated` rows unless `--csv-full-history`** (then one row per endpoint too). Timestamps are unix seconds.

### 5.2 Fixture families (all headers byte-identical to §5.1)

| Dir under `tests/fixtures/intelligence/` | Files | Scenario (deterministic, hand-tuned AFTER generation, headers untouched) |
|---|---|---|
| `run_a/` | `run_a_stats.csv`, `run_a_failures.csv`, `run_a_exceptions.csv`, `run_a_stats_history.csv` | **Healthy baseline**: 6 endpoints (GET /api/items, GET /api/users, POST /api/orders, GET /api/products, GET /api/search, GET /api/report); ~120 s history at 10 s cadence (13 aggregate rows); p95 flat 80–120 ms; error rate 0.05–0.2 %; RPS 45–55 flat. |
| `run_b/` | `run_b_stats.csv`, `run_b_failures.csv`, `run_b_exceptions.csv`, `run_b_stats_history.csv` | **Regressed current**: same endpoints; p95 climbs 100→650 ms as RPS ramps 50→300; injected error spike window (error_rate 0.1 %→4 % for 30 s = 3 consecutive rows) near the end; aggregate error rate ≈1.5 %. Drives: `--slo p95=500` → exit 2; baseline regression anomalies vs `run_a` (POST /api/orders p95 200→652 ms); knee ≈ 150 RPS; capacity projection "P95 > 500 ms expected at ~N RPS". |
| `run_clean/` | `run_clean_stats.csv`, `run_clean_stats_history.csv` | Monotonic p95 vs RPS with a textbook knee (for high-confidence capacity + kneedle test); no failures file. |
| `full_history/` | `full_history_stats.csv`, `full_history_stats_history.csv` | History with **per-endpoint rows** (simulates `--csv-full-history`) → `has_full_history=True`, per-endpoint series tests. |
| `legacy/` | `legacy_stats.csv`, `legacy_history.csv` | Old-schema history (`Request Failure`, `_history.csv` naming) → tolerance test. |
| `edge/` | `edge_missing_stats.csv` (empty stats file), `edge_missing_failures.csv`, `edge_missing_history.csv` (empty files) | Empty/malformed inputs → parser must not crash (empty `endpoints`/`history`, or ValueError with clear message only for undecodable content). |

### 5.3 Provenance & regeneration

- Commit `tests/fixtures/intelligence/README.md` stating: fixtures were generated with `locust -f examples/api_load_test.py --headless --users 50 --spawn-rate 5 --run-time 2m --csv <prefix> --csv-full-history` against a local stub server, then values were hand-edited to create the deterministic scenarios above **keeping the header row byte-identical to Locust 2.46.2**; regeneration recipe + tool version (`locust 2.46.2`) recorded.
- The pre-tester must NOT mock the parser; tests read the committed files with `Path` + `csv.DictReader`.

---

## 6. Prioritized Task List

### P0 — Core analyzer (must ship)
1. `intelligence.py`: dataclasses (`EndpointProfile`, `HistoryPoint`, `RunProfile`, `Anomaly`, `KneePoint`, `Bottleneck`, `CapacityProjection`, `SLOViolation`, `Insight`, `AnalysisReport`) + `RunProfile.from_csv` (stats/failures/exceptions via `ReportData`, history parsing, baseline attach) + `check_slos`.
2. `AnomalyDetector` (baseline z-score + EWMA regressions, error spikes), `BottleneckDetector` (knee, weakest ranking, correlations), `CapacityProjector` (linear/EWMA projection), `InsightGenerator` (statistical rules).
3. `cli_analyze.py` + `locust-kit` entry point: `analyze` subcommand with `--csv`, `--slo`, `--format markdown|json`, `--output`, exit codes 0/1/2; `analyze_run()` orchestration; markdown + JSON renderers.
4. Fixture families (§5.2) + `tests/fixtures/intelligence/README.md`.
5. `__init__.py` exports + `pyproject.toml` version 1.6.0 + `locust-kit` script.
6. Pre-tester RED suite + developer GREEN pass; existing 810 tests stay green.

### P1 — Baseline & LLM enrichment (should ship in the same feature)
7. `--baseline` resolution (§4.2.4) incl. `.baselines/<name>.json` support; baseline regression anomalies wired into report.
8. `LLMInsightProvider` (stdlib urllib, env config, clean fallback) + `--llm` flag + `## AI Insights` markdown section + `ai_insights` JSON field.
9. CI gate integration: `docs/ci-cd-gates.md` new `run-analysis` step + artifact/output wiring; `docs/baseline-comparison.md` cross-reference.

### P2 — Polish & release docs (documenter task, after code green)
10. README section "AI Performance Intelligence (v1.6.0)" + CLI/API reference (`docs/ai-performance-intelligence.md`).
11. CHANGELOG entry + `FEATURES-DONE.md` entry (create file if absent — not currently in repo).
12. Optional: `examples/analyze_example.py` runnable example using a fixture prefix; recommendations polish.

---

## 7. Acceptance Criteria (per task, traceable)

### 7.1 Pre-tester task `t_398e82ca` (already created as child — will be annotated with this brief)
- A. Create `tests/test_intelligence.py` (+ `tests/test_cli_analyze.py` if needed) with: interface tests (imports, dataclass fields, signatures, type hints) that PASS immediately against the stub modules; behavioral tests that FAIL with `NotImplementedError` until implemented. Do not modify existing test files; run the existing suite before and after and report regressions (must be none).
- B. Stub modules `src/locust_templates/intelligence.py` and `src/locust_templates/cli_analyze.py` (all public symbols per §4.1/§4.2 raising `NotImplementedError` for behavior; dataclasses may be fully defined so interface tests pass).
- C. Real fixtures per §5 committed under `tests/fixtures/intelligence/` (exact headers), used by the parser tests — no mocks.
- D. Coverage: RunProfile parsing (per-endpoint p50/p95/p99, RPS, error rates, time series, aggregated exclusion, history naming fallback, legacy `Request Failure` column); z-score/EWMA regressions + error spikes with severity + time window; knee/weakest/correlations; capacity projection with pinned expected `predicted_breach_rps` and message text; SLO checks; statistical insights; LLM fallback (unconfigured → statistical output); CLI flags, markdown+json rendering, exit codes 0/1/2 (via `main([...])`).
- E. Everything run via `.venv/bin/python -m pytest` / `.venv/bin/python -m ruff`; all runtime deps pinned in `pyproject.toml` (none new needed); report total tests added, file paths, stub paths, and pytest output showing interface PASS + behavioral RED as expected.

### 7.2 Developer task `t_539b5c01`
- A. Implement `intelligence.py` + `cli_analyze.py` to make ALL pre-tester behavioral tests pass WITHOUT modifying test files; existing 810-test suite stays green; `ruff check` clean (E/F/UP/B/SIM/I).
- B. `RunProfile.from_csv` reuses `ReportData.from_csv` for stats/failures/exceptions (no duplicated parser); history parsing handles both `_stats_history.csv` and `_history.csv`, both `Failures/s` and `Request Failure`, missing numeric columns → 0.0.
- C. Anomalies carry severity + time window; `detect(healthy_without_baseline) == []`; regressions require baseline; error spikes merged into windows.
- D. Bottlenecks: knee via max-distance-from-chord with slope-ratio corroboration; weakest-endpoint composite score; Pearson correlations (manual, 3.9-safe).
- E. Capacity: closed-form OLS; `predicted_breach_rps` None when slope ≤ 0; `insufficient_data` when n < 5; message format matches "P95 > 500 ms expected at ~200 RPS".
- F. LLM: stdlib-only, `enrich()` never raises and returns None on any failure; statistical output identical with/without `--llm` when provider unconfigured or failing.
- G. CLI: exit codes 0/1/2 per §4.2.3 (verified by the pre-tester tests + tester task); `--slo` repeatable; invalid key → 1; `--baseline` resolution order per §4.2.4.
- H. `pyproject.toml` version 1.6.0 + `locust-kit` script; `__init__.py` exports; no new runtime deps.
- I. Run quality gates per root task (TDD v3, security, doc-sync, pre-tester contract check, full suite) before completing.

### 7.3 Reviewer task `t_0b5c3102` (tech-lead)
- Verify: type hints on all public functions/classes; error handling (file I/O, CSV parse, LLM HTTP, malformed input); no security issues (CSV injection — values HTML/JSON-escaped in reports; secret leakage — API key never logged/reported; prompt injection — numeric-facts-only prompt + data-not-instructions instruction); no performance anti-patterns (single-pass history parsing, no O(n²)); CLI contract + exit codes verified against §4.2.3; adherence to repo patterns.

### 7.4 Tester task `t_2aef2345`
- Full suite green (existing + new) in repo `.venv`; `ruff check` no new warnings; manual verification: `locust-kit analyze` against `tests/fixtures/intelligence/run_b` renders markdown + JSON; `--baseline run_a` surfaces regression anomalies; `--slo p95=500` exits 2 on `run_b` and 0 on `run_a`; report artifact integrates with the CI gate flow documented in §4.4. Block (dependency) on any failure with test names + messages; complete only if all green.

### 7.5 Documenter task `t_796bd723`
- README section + `docs/ai-performance-intelligence.md` (CLI/API reference, `locust-kit analyze` usage, `intelligence.py` API, exit-code table, `--baseline` semantics, LLM env vars); CHANGELOG entry for v1.6.0; `FEATURES-DONE.md` entry (create if missing); example with a real fixture prefix; verify code examples via repo `.venv/bin/python -c`; only document behavior verified in code.

### 7.6 Root acceptance mapping
1 → §4.1.1 (RunProfile) · 2 → §4.1.2 (AnomalyDetector) · 3 → §4.1.3 (BottleneckDetector) · 4 → §4.1.4 (CapacityProjector) · 5 → §4.1.6–7 (InsightGenerator + LLMInsightProvider fallback) · 6 → §4.2 (CLI + exit codes) · 7 → §4.4 (CI/baseline integration) · 8 → §5 + §7.1–7.4 (tests, real fixtures, 810 suite green) · 9 → §7.5 (docs).

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Pre-tester/developer signature drift | This brief pins exact signatures + defaults; pre-tester interface tests lock them immediately; reviewer checks contract (§7.3). |
| Python 3.9 compat (no `statistics.correlation`, no `|` unions at runtime are fine via `from __future__ import annotations`) | Manual Pearson; repo already uses `X | None` syntax with future import. |
| Locust version drift in CSV schema (`Failures/s` vs `Request Failure`, `_stats_history.csv` vs `_history.csv`) | Tolerant parsing (both column names, both filenames) + legacy fixture test (§5.2). |
| LLM flakiness in tests/CI | `--llm` is opt-in; provider never raises; fallback path covered by tests with an unconfigured provider; CI never calls the LLM. |
| Naming collision with `correlator.py` | Bottleneck kind is `"correlation"` (metric-to-metric); documented in §4.1.3 and docstrings; no import of `RequestCorrelator` in `intelligence.py`. |
| Capacity projection misleading when data noisy | EWMA smoothing above `noise_ratio`, confidence levels, `insufficient_data` guard, advisory-only exit-code semantics (§4.2.3). |
| Overwriting the repo's existing `analysis/analysis-brief.md` (prior "Observable Performance Pipeline" brief) | Backed up to `/tmp/analysis-brief-prev-locust-performance-kit.md`; this brief supersedes it for the v1.6.0 feature. |

---

## 9. Evidence / Source Links (retained from root task)

- OneUptime — "How to Analyze Locust Test Results" (2026-01-28): analysis is the real value; manual CSV techniques today. https://oneuptime.com (linked from root task body)
- loadfocus AI Load Test Analysis + loadTEST.io — AI bottleneck detection, capacity insights (commercial SaaS only). https://loadfocus.com, https://loadtest.io
- Gatling — "Best AI Load Testing Tools (2026)": every major tool adds AI features (commercial/cloud).
- pistack.xyz — "k6 vs Locust vs Gatling: Best Self-Hosted Load Testing Tools 2026": self-hosted keeps data private and cuts cost.
- Locust docs — CSV output naming/history semantics: https://docs.locust.io/en/stable/retrieving-stats.html (files `_stats.csv`, `_failures.csv`, `_exceptions.csv`, `_stats_history.csv`; aggregate-only history by default; `--csv-full-history` for per-endpoint rows).
- **Authoritative CSV schemas**: installed `locust 2.46.2` in the repo `.venv` — `locust/stats.py` (`requests_csv_columns` L1010–1022, `failures_columns` L1024–1031, `exceptions_columns` L1033–1038, `stats_history_csv_columns` L1133–1148, `stats_history_file_name()` L1256–1257, `CSV_STATS_INTERVAL_SEC = 1` L107).
