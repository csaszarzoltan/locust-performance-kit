# Locust CSV Fixtures — AI Performance Intelligence (v1.6.0)

These fixture families back the pre-development TDD suite in
`tests/test_intelligence.py` and `tests/test_cli_analyze.py`. They are **real
Locust-shaped CSV files on disk** — tests read them with `csv.DictReader` and
never fabricate parser input (root acceptance criterion 8: "real Locust CSV
fixtures on disk, no mocks on the parser").

## Provenance

- **Tool**: `locust 2.46.2` (the version pinned in the repo `.venv`).
- **Generation recipe** (reference for regeneration):
  ```
  locust -f examples/api_load_test.py --headless --users 50 --spawn-rate 5 \
      --run-time 2m --csv <prefix> --csv-full-history
  ```
  against a local stub server, then **values were hand-edited** to create the
  deterministic scenarios below.
- **Header rows are byte-identical** to the schema emitted by Locust 2.46.2,
  verified against `locust/stats.py` in the installed `.venv`
  (`requests_csv_columns` L1010–1022, `failures_columns` L1024–1031,
  `exceptions_columns` L1033–1038, `stats_history_csv_columns` L1133–1148,
  `stats_history_file_name()` L1256–1257, `CSV_STATS_INTERVAL_SEC` L107).
- History cadence in these fixtures is 10 s (13 rows ≈ 130 s run); real Locust
  history rows are interval-aggregated (`Aggregated` name) unless
  `--csv-full-history` is used (then per-endpoint rows are present too).

## Families (see analysis/analysis-brief.md §5.2)

| Dir | Files | Scenario |
|---|---|---|
| `run_a/` | `run_a_stats.csv`, `run_a_failures.csv`, `run_a_exceptions.csv`, `run_a_stats_history.csv` | **Healthy baseline**: 6 endpoints; p95 flat at 100 ms (slope == 0 → capacity "no breach" pin); error rate ~0.1 %; RPS 45–55; 13 aggregate history rows at 10 s cadence (unix base ts `1700000000`). |
| `run_b/` | `run_b_stats.csv`, `run_b_failures.csv`, `run_b_exceptions.csv`, `run_b_stats_history.csv` | **Regressed current**: same endpoints; POST /api/orders p95 118 → 652 ms; aggregate error rate ≈ 1.5 %; history RPS ramps 50 → 300 with p95 100 → 650 ms (knee ≈ 150 RPS); injected error-rate spike ~4 % for 3 consecutive rows (30 s window, rows 10–12). Drives `--slo p95=500` → exit 2, baseline regressions vs `run_a`, capacity "P95 > 500 ms expected at ~N RPS". |
| `run_clean/` | `run_clean_stats.csv`, `run_clean_stats_history.csv` | Monotonic p95-vs-RPS with a textbook knee at ~150 RPS; error rate grows 0.1 % → 1.2 % with load (correlation bottleneck). No failures file. |
| `full_history/` | `full_history_stats.csv`, `full_history_stats_history.csv` | History with **per-endpoint rows** (`--csv-full-history` simulation) → `has_full_history=True`; per-endpoint series tests. |
| `legacy/` | `legacy_stats.csv`, `legacy_history.csv` | Old-schema history (`_history.csv` naming, `Request Failure` column instead of `Failures/s`, trailing `Total Requests/s, Total Requests, Total Failures`) → tolerance test. |
| `edge/` | `edge_missing_stats.csv` (empty), `edge_missing_failures.csv` (empty), `edge_missing_history.csv` (empty), `edge_empty_history_stats.csv` + `edge_empty_history_stats_history.csv` (empty history) | Empty/malformed inputs → parser must not crash (empty `endpoints`/`history`), while a missing stats file still raises `FileNotFoundError`. |

## Deterministic contract notes

- Timestamps start at `1700000000` and advance 10 s per history row.
- `run_a` history p95 is **exactly 100.0** for every row so the capacity
  projector's linear fit has slope ≤ 0 (→ `predicted_breach_rps=None`,
  "No breach projected within tested load").
- `run_b` injected spike rows (indices 9–11) have error rate ≈ 4 %:
  `0.04 * rps / 0.96` failures/s against `rps` 230/250/275.
- No values were changed after writing; regenerate with the recipe above and
  re-apply the scenario tables if you need to refresh the files.
