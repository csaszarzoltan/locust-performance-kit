# Request Correlation and Cascade Failure Detection

## Overview

When running load tests against complex APIs, a single upstream failure (e.g., an authentication token expiring or a database connection dropping) can cascade into multiple downstream failures. The `RequestCorrelator` tracks request chains per user/session and identifies these cascade failures — failures caused by an upstream failure within a configurable time window.

### Problem Statement

Traditional Locust reports show aggregate failure counts but don't answer:

- Was the 500 on `/api/v1/orders` caused by the 401 on `/api/v1/auth/login` 200ms earlier?
- How many of the 50 failures were root causes vs. cascading from something else?
- What's the average cascade depth — how far does a single failure propagate?

`RequestCorrelator` answers these by attaching to Locust's `events.request` hook and tracking per-user request history with timestamps, exception info, and correlation metadata from the request context.

## Quick Start

```python
from locust import events
from locust_templates import RequestCorrelator

correlator = RequestCorrelator(cascade_window_s=5.0)

@events.init.add_listener
def on_init(environment, **kwargs):
    correlator.register(environment)

@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    correlator.export_csv("results/correlated_events.csv")
    correlator.export_json("results/failure_chains.json")
    print(correlator.get_summary())
```

Each request should include a `user_id` in its context so the correlator can group requests by user:

```python
with self.client.get(
    "/api/v1/profile",
    context={"user_id": "user-42"},
) as response:
    ...
```

## API Reference

### RequestCorrelator

```python
class RequestCorrelator:
    def __init__(self, *, cascade_window_s: float = 5.0) -> None
    def register(self, environment: Any) -> None
    def get_correlated_events(self) -> list[CorrelatedEvent]
    def get_failure_chains(self) -> list[FailureChain]
    def export_csv(self, path: str | Path) -> Path
    def export_json(self, path: str | Path, *, chains_only: bool = True) -> Path
    def get_summary(self) -> CorrelationSummary
```

**`__init__(cascade_window_s=5.0)`**

Time window in seconds for cascade detection. A failure is considered a cascade if a previous request from the same user failed within this window. Default: 5 seconds.

**`register(environment)`**

Attaches to `environment.events.request` and `environment.events.quitting`. Call this inside an `events.init` listener.

**`get_correlated_events()`**

Returns all recorded `CorrelatedEvent` objects in chronological order. Thread-safe.

**`get_failure_chains()`**

Builds and returns `FailureChain` objects. A chain starts at a root failure (failed, not a cascade) and includes all subsequent cascade failures from the same user. Sorted by `cascade_count` descending.

**`export_csv(path)`**

Writes all correlated events to a CSV file with columns: `timestamp`, `request_type`, `name`, `response_time`, `status_code`, `exception`, `user_id`, `correlation_id`, `parent_request`, `is_cascade_failure`, `chain_depth`. Returns the resolved `Path`.

**`export_json(path, chains_only=True)`**

Writes failure chains (default) or all events to a JSON file. When `chains_only=True`, each entry contains `root_request`, `failed_dependents`, `cascade_count`, and `total_chain_length`. When `chains_only=False`, writes a flat list of all `CorrelatedEvent` dicts. Returns the resolved `Path`.

**`get_summary()`**

Returns a `CorrelationSummary` with aggregate statistics.

### CorrelatedEvent

```python
@dataclass
class CorrelatedEvent:
    timestamp: float           # Unix timestamp of request start
    request_type: str          # HTTP method (GET, POST, etc.)
    name: str                  # Request name (e.g. "GET /api/v1/profile")
    response_time: float       # Response time in milliseconds
    status_code: int           # HTTP status code (0 if no response)
    exception: str | None      # Exception string, or None if successful
    user_id: str | None        # User identifier from context
    correlation_id: str | None # Explicit correlation ID from context
    parent_request: str | None # Previous request name from same user within window
    is_cascade_failure: bool   # True if caused by an upstream failure
    chain_depth: int           # 0 for root, 1+ for cascade dependents
```

### FailureChain

```python
@dataclass
class FailureChain:
    root_request: CorrelatedEvent        # The initial failure
    failed_dependents: list[CorrelatedEvent]  # Cascade failures caused by root
    cascade_count: int                   # Number of cascade failures
    total_chain_length: int              # Root + dependents
```

### CorrelationSummary

```python
@dataclass
class CorrelationSummary:
    total_requests: int               # All recorded requests
    total_failures: int               # All failed requests
    cascade_failures: int             # Failures caused by upstream
    root_failures: int                # Standalone or chain-root failures
    top_failure_chains: list[FailureChain]  # Top 10 by cascade_count
    avg_chain_depth: float            # Average chain depth across all events
```

## Cascade Detection

### How It Works

1. **Per-user tracking**: Each request is grouped by `user_id` from the request context. If `user_id` is absent, the correlator falls back to `correlation_id`.

2. **Parent linking**: When a request arrives, the correlator scans backward through the user's recent request history. If a previous request from the same user occurred within `cascade_window_s` seconds, it becomes the `parent_request`.

3. **Cascade detection**: A request is marked `is_cascade_failure=True` when:
   - The previous request from the same user failed (had an exception), AND
   - The current request also fails, AND
   - Both occurred within the cascade window.

4. **Chain depth**: Root failures have `chain_depth=0`. Each cascade dependent increments from its predecessor's depth.

5. **Root failures**: Failures where `exception is not None and not is_cascade_failure`. These are standalone failures or the start of a cascade chain.

### Example Scenario

```
User-42 timeline (cascade_window_s=5.0):
  t=0.0s  POST /api/v1/auth/login    → 500 (exception)   root failure, depth=0
  t=0.3s  GET  /api/v1/profile       → 401 (exception)   cascade, depth=1
  t=0.5s  GET  /api/v1/orders        → 401 (exception)   cascade, depth=1
  t=0.8s  GET  /api/v1/orders/12345  → 401 (exception)   cascade, depth=1
```

This produces one `FailureChain`:
- Root: `POST /api/v1/auth/login`
- Dependents: 3 cascade failures
- `cascade_count=3`, `total_chain_length=4`

### Configuration

The only configuration option is `cascade_window_s`:

| Value | Use Case |
|-------|----------|
| 1.0s  | Microservices with fast failover |
| 5.0s  | Default — general-purpose APIs |
| 10.0s | Slow APIs with long retry chains |
| 30.0s | Integration tests with retries |

## Integration with HTMLReportGenerator

`HTMLReportGenerator` accepts an optional `correlation_summary` parameter. When provided, the HTML report includes a correlation section with summary cards (total/cascade/root failures) and a table of top failure chains.

```python
from locust_templates import HTMLReportGenerator, RequestCorrelator

correlator = RequestCorrelator()

# ... run test ...

gen = HTMLReportGenerator(
    stats=parsed_stats,
    failures=parsed_failures,
    correlation_summary=correlator.get_summary(),
)
gen.generate("report.html")
```

## Integration with PerformanceBaseline

`PerformanceBaseline.save_baseline()` accepts an optional `correlation_summary` parameter. When provided, it stores `cascade_rate`, `cascade_failures`, and `root_failures` in the baseline JSON for regression tracking.

```python
from locust_templates import PerformanceBaseline

baseline = PerformanceBaseline()
baseline.save_baseline(
    "results",
    name="v1.2.0",
    correlation_summary=correlator.get_summary(),
)
```

## Export Formats

### CSV (all events)

```csv
timestamp,request_type,name,response_time,status_code,exception,user_id,correlation_id,parent_request,is_cascade_failure,chain_depth
1721390400.0,POST,POST /api/v1/auth/login,150,500,"ConnectionError(...)",user-42,,,False,0
1721390400.3,GET,GET /api/v1/profile,80,401,"HttpError(...)",user-42,,POST /api/v1/auth/login,True,1
```

### JSON (failure chains, default)

```json
[
  {
    "root_request": {"timestamp": 1721390400.0, "name": "POST /api/v1/auth/login", ...},
    "failed_dependents": [
      {"timestamp": 1721390400.3, "name": "GET /api/v1/profile", ...}
    ],
    "cascade_count": 1,
    "total_chain_length": 2
  }
]
```

### JSON (all events, chains_only=False)

Pass `chains_only=False` to `export_json()` for a flat list of all `CorrelatedEvent` dicts — useful for post-processing in external tools.

## See Also

- [Report Generation Guide](report-generation.md) — HTML report integration
- [Baseline Comparison Guide](baseline-comparison.md) — Regression baseline with cascade rate
- [Example: Correlated Load Test](../examples/correlated_load_test.py) — Complete working example
