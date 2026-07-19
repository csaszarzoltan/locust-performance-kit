# Baseline Comparison Guide

Store performance baselines and compare new test runs against them to detect regressions automatically.

## Overview

The `PerformanceBaseline` class lets you:

1. **Save** a test run's metrics as a named baseline (stored as JSON)
2. **Compare** a new run against a stored baseline
3. **Detect** p95, p99, and avg response time regressions (> 10% degradation by default)
4. **List** all stored baselines

## Quick Start

### Save a Baseline

```python
from locust_templates.baseline import PerformanceBaseline

baseline = PerformanceBaseline()

# After running a test with --csv results
baseline.save_baseline("results", name="v1.0")
# Creates .baselines/v1.0.json
```

### Compare a New Run

```python
from locust_templates.baseline import PerformanceBaseline

baseline = PerformanceBaseline()

# After running a new test with --csv results_new
result = baseline.compare("results_new", baseline_name="v1.0")

if result.regressions:
    print(f"REGRESSIONS DETECTED!")
    print(result.summary)
    for r in result.regressions:
        print(f"  {r.endpoint} {r.metric}: {r.degradation_pct}% degradation")
        print(f"    baseline={r.baseline_value}ms -> current={r.current_value}ms")
elif result.improvements:
    print(f"No regressions. {len(result.improvements)} improvement(s).")
    for imp in result.improvements:
        print(f"  {imp.endpoint} {imp.metric}: {imp.improvement_pct}% improvement")
else:
    print("No significant changes.")
```

## API Reference

### `PerformanceBaseline`

#### Constructor

```python
PerformanceBaseline(baseline_dir: str | Path | None = None)
```

- **baseline_dir**: Directory to store baseline JSON files. Defaults to `.baselines` in cwd.

#### `save_baseline(csv_prefix, name, path=None) -> Path`

Save current run metrics as a named baseline.

- **csv_prefix**: Locust CSV prefix (e.g. `"results"` for `results_stats.csv`)
- **name**: Baseline name (e.g. `"v1.0"`, `"before-refactor"`)
- **path**: Optional override for baseline directory
- **Returns**: Path to the saved JSON file

The baseline JSON contains per-endpoint metrics: name, type, request_count, failure_count, avg_response_time, p50, p95, p99, rps.

#### `compare(csv_prefix, baseline_name, *, threshold_pct=None) -> RegressionResult`

Compare a current run against a stored baseline.

- **csv_prefix**: Locust CSV prefix for the current run
- **baseline_name**: Name of the baseline to compare against
- **threshold_pct**: Regression detection threshold (default: 10.0%)
- **Returns**: `RegressionResult`
- **Raises**: `BaselineNotFoundError` if the named baseline doesn't exist

#### `list_baselines() -> list[str]`

List all stored baseline names.

### `RegressionResult` (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `regressions` | `list[Regression]` | Detected regressions |
| `improvements` | `list[Improvement]`` | Detected improvements |
| `summary` | `str` | Human-readable summary (1-3 sentences) |

### `Regression` (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `endpoint` | `str` | Endpoint name |
| `metric` | `str` | Metric that regressed (e.g. `"p95"`) |
| `baseline_value` | `float` | Baseline value |
| `current_value` | `float` | Current (worse) value |
| `degradation_pct` | `float` | Percentage degradation |

### `Improvement` (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `endpoint` | `str` | Endpoint name |
| `metric` | `str` | Metric that improved |
| `baseline_value` | `float` | Baseline value |
| `current_value` | `float` | Current (better) value |
| `improvement_pct` | `float` | Percentage improvement |

## CI/CD Integration

### GitHub Actions: Block Deployments on Regression

```yaml
- name: Run performance test
  run: |
    locust -f examples/api_load_test.py \
      --headless --users 100 --spawn-rate 10 --run-time 2m \
      --host ${{ env.TARGET_HOST }} --csv results_current

- name: Check for regressions
  run: |
    python -c "
    from locust_templates.baseline import PerformanceBaseline, BaselineNotFoundError
    
    baseline = PerformanceBaseline()
    try:
        result = baseline.compare('results_current', 'production')
        if result.regressions:
            print('REGRESSIONS DETECTED:')
            print(result.summary)
            for r in result.regressions:
                print(f'  {r.endpoint} {r.metric}: {r.degradation_pct}%')
            exit(1)  # Fail the build
        else:
            print('No regressions detected.')
    except BaselineNotFoundError:
        print('No baseline found — skipping comparison.')
    "
```

### Save Baseline After Release

```yaml
- name: Save new baseline
  run: |
    python -c "
    from locust_templates.baseline import PerformanceBaseline
    baseline = PerformanceBaseline()
    baseline.save_baseline('results_current', name='production')
    "
```

## Workflow Example

```python
from locust_templates.baseline import PerformanceBaseline

baseline = PerformanceBaseline()

# 1. Before a code change: save baseline
baseline.save_baseline("results_before", name="before-refactor")

# ... make code changes ...

# 2. After the change: compare
result = baseline.compare("results_after", baseline_name="before-refactor")

# 3. Act on results
if result.regressions:
    # Rollback or investigate
    for r in result.regressions:
        print(f"REGRESSION: {r.endpoint} {r.metric} degraded {r.degradation_pct}%")
elif result.improvements:
    # Celebrate
    for imp in result.improvements:
        print(f"IMPROVEMENT: {imp.endpoint} {imp.metric} improved {imp.improvement_pct}%")

# 4. List all baselines
print("Stored baselines:", baseline.list_baselines())
# ['before-refactor', 'production', 'v1.0', 'v1.1']
```

## Custom Threshold

Default regression threshold is 10%. Override it per comparison:

```python
# Stricter: flag anything > 5% degradation
result = baseline.compare("results", "v1.0", threshold_pct=5.0)

# More lenient: only flag > 25% degradation
result = baseline.compare("results", "v1.0", threshold_pct=25.0)
```

## Tips

- Store baselines in a versioned directory (e.g. `.baselines/v1.0.json`)
- Commit baseline JSONs to your repo for team-wide regression tracking
- Use descriptive baseline names: `"pre-refactor"`, `"v2.0-release"`, `"production-2026-01"`
- The comparison checks p95, p99, and avg_response_time for each endpoint
- Endpoints present in the baseline but missing from the current run are skipped
