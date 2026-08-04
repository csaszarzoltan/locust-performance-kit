# AI Performance Intelligence (v1.6.0)

Turn Locust `--csv` outputs into decisions. The `locust-kit analyze` CLI (and
the `intelligence.py` module behind it) parses a run's statistics, failures,
and history files into a structured `RunProfile`, then detects anomalies,
ranks bottlenecks, projects capacity against your SLOs, and renders a
plain-language report — all from deterministic statistical rules with **zero
configuration**. An optional OpenAI-compatible LLM enriches the report and
degrades cleanly to the statistical output when no API key is configured.

The report plugs into the existing flows: baseline comparison
([`docs/baseline-comparison.md`](baseline-comparison.md)) and the CI/CD
performance gates ([`docs/ci-cd-gates.md`](ci-cd-gates.md)).

## Quick Start

```bash
# Analyze a healthy run (advisory — no SLOs)
locust-kit analyze --csv tests/fixtures/intelligence/run_a/run_a

# Compare a run against a prior run and gate on SLOs (exit 2 on breach)
locust-kit analyze \
  --csv tests/fixtures/intelligence/run_b/run_b \
  --baseline tests/fixtures/intelligence/run_a/run_a \
  --slo p95=500 \
  --slo error_rate=0.01

# Machine-readable JSON for CI
locust-kit analyze --csv results --format json --output intelligence-report.json
```

The `tests/fixtures/intelligence/` prefixes are **real Locust-shaped CSVs
committed in this repo** (generated with `locust 2.46.2`, headers byte-identical
to Locust's schema) — `run_a` is a healthy baseline, `run_b` is a regressed
run. See `tests/fixtures/intelligence/README.md` for the scenario tables.

## CLI Reference

```
locust-kit analyze --csv <prefix>
                  [--slo KEY=VALUE ...]
                  [--baseline <prior-prefix|baseline-name>]
                  [--format markdown|json]
                  [--output PATH|-]
                  [--llm]
                  [--version]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--csv <prefix>` | *(required)* | Locust CSV prefix; the run's `{prefix}_stats.csv` must exist. `_failures.csv`, `_exceptions.csv`, and history files are consumed when present. |
| `--slo KEY=VALUE` | *(none)* | Repeatable. Valid keys: `p95`, `p99` (milliseconds) and `error_rate` (ratio, e.g. `0.01` = 1 %). Drives the exit code and capacity projection. |
| `--baseline <prefix\|name>` | *(none)* | Prior-run CSV prefix, or a stored baseline name resolved from `.baselines/<name>.json` (the same store used by `PerformanceBaseline`). Regressions are reported as anomalies; baseline comparison is advisory unless SLOs are set. |
| `--format markdown\|json` | `markdown` | Report format. |
| `--output PATH\|-` | `-` | Output file path (parent dirs auto-created) or `-` for stdout. |
| `--llm` | off | Enable OpenAI-compatible LLM enrichment. Falls back to the statistical insights with a stderr warning when no API key is configured. |
| `--version` | — | Print `locust-kit <version>` (subcommand flag). |

### Exit codes (CI gate signal)

| Exit code | Meaning |
|---|---|
| `0` | OK — no SLOs configured (advisory) or every configured SLO passed |
| `1` | Usage / IO / parse error — missing `{prefix}_stats.csv`, unresolvable `--baseline`, invalid `--slo` key or `KEY=VALUE` form, unsupported `--format`, missing `--csv` |
| `2` | **Measured SLO violation** — at least one `--slo` breached (gate failure) |

> Note: argparse-level usage errors (e.g. an unknown flag) also exit with
> code `2` and print to stderr, so treat a `2` without a report on stdout as
> a usage error rather than an SLO breach.

## Report Formats

### Markdown

`--format markdown` renders an `# AI Performance Intelligence Report` with
the sections `SLO Results`, `Anomalies`, `Bottlenecks`, `Capacity
Projections`, `Insights`, and — when LLM enrichment succeeded — `AI
Insights`. Real output for the regressed fixture:

```markdown
# AI Performance Intelligence Report

- CSV prefix: `tests/fixtures/intelligence/run_b/run_b`
- Baseline: `tests/fixtures/intelligence/run_a/run_a`

## SLO Results
| Metric | SLO | Actual | Status |
|---|---|---|---|
| p95 | 500.0 | 560 | ✘ violated |
| error_rate | 0.01 | 0.015 | ✘ violated |

## Anomalies
| Kind | Endpoint | Severity | Window | Message |
|---|---|---|---|---|
| latency_regression | /api/orders | critical | — | p95 652ms vs baseline 118ms (+453%) |
| error_rate_regression | Aggregated | critical | — | error rate 0.0150 vs baseline 0.0010 (+0.0177) |
| error_spike | Aggregated | warning | 1700000090..1700000110 | error rate spiked to 4.00% between t=1700000090 and t=1700000110 |

## Bottlenecks
- **rps_saturation_knee** (warning): P95 degrades sharply above ~170 RPS (saturation knee)
- **weakest_endpoint** (warning): Endpoint /api/orders is weak: p95=652ms, error_rate=0.031
- **correlation** (warning): P95 latency grows with user count (r=0.97)

## Capacity Projections
- **p95**: P95 > 500 ms expected at ~343 RPS _(method=ewma_linear, confidence=high)_
- **error_rate**: error_rate > 0.01 expected at ~300 RPS _(method=ewma_linear, confidence=high)_

## Insights
- [CRITICAL] p95 652ms vs baseline 118ms (+453%)
- [WARNING] System saturates around ~170 RPS — investigate scaling, connection-pool limits, or DB contention
- [INFO] Run completed: 73,000 requests, 1,095 failures (1.50% error rate) across 6 endpoints; peak RPS 300 at 300 users; aggregated p95 560 ms

---
Generated by locust-performance-kit 1.6.0
```

### JSON

`--format json` emits the same data machine-readable: `csv_prefix`,
`summary` (totals, peak RPS/users, aggregate p95), `slo_results`,
`anomalies`, `bottlenecks`, `capacity_projections`, `insights`,
`ai_insights`, and `exit_code`:

```json
{
  "csv_prefix": "tests/fixtures/intelligence/run_b/run_b",
  "version": "1.6.0",
  "summary": {
    "total_requests": 73000,
    "total_failures": 1095,
    "error_rate": 0.015,
    "endpoint_count": 6,
    "peak_rps": 300.0,
    "peak_users": 300,
    "aggregate_p95": 560.0
  },
  "slo_results": [
    {"metric": "p95", "endpoint": "Aggregated", "slo_value": 500.0,
     "actual_value": 560.0, "status": "violated"}
  ],
  "capacity_projections": [
    {"metric": "p95", "endpoint": "Aggregated", "slo_value": 500.0,
     "current_value": 494.55, "predicted_breach_rps": 343.31,
     "method": "ewma_linear", "confidence": "high",
     "message": "P95 > 500 ms expected at ~343 RPS"}
  ],
  "exit_code": 2
}
```

## Python API

The public API is exported from `locust_templates`:

```python
from locust_templates import (
    AnalysisReport, Anomaly, AnomalyDetector, Bottleneck, BottleneckDetector,
    CapacityProjection, CapacityProjector, EndpointProfile, HistoryPoint,
    Insight, InsightGenerator, KneePoint, LLMInsightProvider, RunProfile,
    SLOViolation, analyze_run, check_slos,
)
```

### One-call pipeline

```python
from locust_templates import analyze_run

report = analyze_run(
    "tests/fixtures/intelligence/run_a/run_a",   # {prefix}_stats.csv required
    slos={"p95": 500, "error_rate": 0.01},       # optional SLOs
    baseline_prefix="tests/fixtures/intelligence/run_a/run_a",  # optional
    use_llm=False,                               # optional LLM enrichment
)
report.to_markdown()          # str — the markdown report
report.to_json()              # dict — JSON-serializable report
report.exit_code              # 0 = ok, 2 = SLO violation
report.insights               # list[Insight]
report.slo_violations         # list[SLOViolation]
```

### Granular stages

```python
from locust_templates import (
    AnomalyDetector, BottleneckDetector, CapacityProjector,
    RunProfile, check_slos,
)

profile = RunProfile.from_csv(
    "tests/fixtures/intelligence/run_b/run_b",
    baseline_prefix="tests/fixtures/intelligence/run_a/run_a",
)
profile.endpoints            # list[EndpointProfile] (Aggregated excluded)
profile.aggregated           # EndpointProfile | None (the Aggregated row)
profile.history              # list[HistoryPoint] (from _stats_history.csv / _history.csv)
profile.has_full_history     # True when per-endpoint rows present (--csv-full-history)

anomalies   = AnomalyDetector().detect(profile)          # z-score/EWMA regressions + error spikes
bottlenecks = BottleneckDetector().detect(profile)       # knee, weakest endpoints, correlations
violations  = check_slos(profile, {"p95": 500, "error_rate": 0.01})
projections = CapacityProjector().project(profile, {"p95": 500})
```

`RunProfile.from_csv()` raises `FileNotFoundError` when `{prefix}_stats.csv`
is missing. Baseline resolution order: a `{value}_stats.csv` file if it
exists, then `.baselines/{value}.json`, else `ValueError`.

### LLM enrichment

`LLMInsightProvider` talks to any OpenAI-compatible `/chat/completions`
endpoint via the stdlib (`urllib`), never raises, and returns `None` on any
failure — `analyze_run(use_llm=True)` then prints a warning and keeps the
statistical insights:

| Env var | Default | Description |
|---|---|---|
| `LOCUST_KIT_LLM_API_KEY` | — | API key. Falls back to `OPENAI_API_KEY` (precedence: `LOCUST_KIT_LLM_API_KEY` first). |
| `LOCUST_KIT_LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible base URL. Falls back to `OPENAI_BASE_URL`. |
| `LOCUST_KIT_LLM_MODEL` | `gpt-4o-mini` | Model name. |

```python
from locust_templates import LLMInsightProvider, analyze_run

provider = LLMInsightProvider.from_env()          # reads the env vars above
provider.is_configured()                          # False → statistical fallback
report = analyze_run("results", slos={"p95": 500}, use_llm=True, llm_provider=provider)
```

## What Each Stage Detects

| Stage | Output | Rule (verified in `intelligence.py`) |
|---|---|---|
| CSV parsing | `RunProfile` | Reuses `ReportData` for stats; adds the `Aggregated` row (stats) and history parsing (modern `_stats_history.csv` or legacy `_history.csv`). |
| Anomalies | `Anomaly[]` | z-score (default threshold 3.0) + EWMA (alpha 0.3) regression vs a baseline; within-run drift when no baseline; error spikes merged into windows on the aggregated history. Severity: `critical` / `warning` / `info`. |
| Bottlenecks | `Bottleneck[]` | RPS-saturation knee (max-distance-from-chord on P95-vs-RPS, slope-ratio corroboration), weakest-endpoint ranking (weighted error_rate 0.4 / p95 0.3 / p99 0.3, top 5), Pearson correlations `r(rps, error_rate)` and `r(p95, user_count)` (threshold 0.7). |
| Capacity | `CapacityProjection[]` | Linear or EWMA-smoothed (when noisy) OLS trend of p95/p99/error_rate vs RPS → the load level where the SLO breaches; `confidence` high/medium/low from correlation and sample count; `predicted_breach_rps=None` when the trend is flat/improving. |
| SLOs | `SLOViolation[]` | Aggregated p95/p99/error_rate vs each `--slo`; any violation → exit code 2. |
| Insights | `Insight[]` | Deterministic summary + one insight per finding + scaling recommendations. |

All detectors are constructible with keyword overrides
(`AnomalyDetector(z_threshold=4.0)`, `BottleneckDetector(corr_threshold=0.8)`,
`CapacityProjector(min_samples=10)`, …).

## Input Files

`{prefix}_stats.csv` is **required** (matches the `--csv` output of a Locust
run). The following are consumed when present next to it:

| File | Parsed into |
|---|---|
| `{prefix}_stats.csv` | per-endpoint p50/p95/p99, RPS, error rate, counts (+ `Aggregated` row) |
| `{prefix}_failures.csv` | `FailureRecord[]` (via `ReportData`) |
| `{prefix}_exceptions.csv` | exception records (via `ReportData`) |
| `{prefix}_stats_history.csv` (modern) or `{prefix}_history.csv` (legacy) | `HistoryPoint[]` time series — drives error spikes, the saturation knee, correlations, and capacity projection. Interval-aggregated rows (`Aggregated` name) unless the run used `--csv-full-history`. |

With no history file the anomaly/bottleneck/capacity stages degrade
gracefully (empty series) and only stats-derived findings remain.

## Limitations

- Capacity projection needs history rows — with fewer than 5 aggregated
  samples it reports `insufficient_data` and suggests `--csv-full-history`.
- LLM enrichment is a single stdlib HTTP attempt with no retry/backoff;
  treat it as an enhancement, never as the source of truth (statistical
  insights always ship first).
- The JSON `generated_at` field is a static placeholder, not the wall-clock
  time of generation.
