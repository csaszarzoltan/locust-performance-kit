# Run Inbox and Smart Import

`/workspace/runs` is the local run history. Import accepts ZIP evidence and performs an inventory before extraction. It recognizes `_stats.csv`, `_stats_history.csv` or `_history.csv`, `_failures.csv`, and `_exceptions.csv` by exact prefix. Multiple candidates require an explicit choice.

Quality A requires an aggregate row and at least 10 ordered aggregate history samples. B covers 5–9 samples or timestamp warnings. C is valid aggregate statistics with fewer than five samples and disables numeric capacity forecasts.

Safety limits are 100 MiB compressed, 500 MiB expanded, 2,000 members, and 100:1 member expansion. Absolute paths, traversal, drive paths, symlinks, encrypted members, duplicate normalized paths, control characters, CRC errors, and invalid stats are rejected. Successful commit copies only mapped evidence to owner-only managed storage and deletes staging.

Routes: `GET /workspace/runs`, `GET /workspace/runs/import`, `POST /workspace/runs/import/validate`, `POST /workspace/runs/import/commit`, and `GET /workspace/runs/<id>`. A validation error returns 422, expired/changed state returns 409, oversize upload returns 413, and unavailable storage returns 503.
