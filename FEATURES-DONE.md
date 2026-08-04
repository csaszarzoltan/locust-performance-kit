## Features Done (v1.6.0)
- ai-performance-intelligence: Parses real Locust CSV runs (stats/failures/exceptions/history, modern and legacy schemas) into a structured `RunProfile`; detects latency/error regressions vs a baseline and merged error-spike windows via z-score + EWMA; ranks bottlenecks (RPS-saturation knee, weakest-endpoint scoring, Pearson correlations); projects p95/p99/error_rate to the load level where an SLO would breach; emits zero-config deterministic insights with optional OpenAI-compatible LLM enrichment and clean statistical fallback.
- locust-kit-analyze-cli: `locust-kit analyze` with `--csv`, repeatable `--slo KEY=VALUE`, `--baseline` (prior-run prefix or `.baselines/<name>.json`), `--format markdown|json`, `--output PATH|-`, `--llm`; markdown + JSON report artifact; exit-code contract 0/1/2 for CI gating.
- ai-intelligence-tests: 169 pre-development behavioral tests (131 `test_intelligence` + 38 `test_cli_analyze`) against real Locust 2.46.2 CSV fixtures committed under `tests/fixtures/intelligence/` (run_a healthy, run_b regressed, run_clean knee, full_history, legacy, edge); full suite 1068 passed, ruff clean on `src/` and `tests/`, no new runtime deps (stdlib only).
- ai-intelligence-docs: `docs/ai-performance-intelligence.md` CLI/API reference, `examples/analyze_run.py`, README section + badges (v1.6.0, 1068 tests), `docs/ci-cd-gates.md` AI analysis step, CHANGELOG v1.6.0.

## Sources
- `analysis/analysis-brief.md` (v1.6.0 spec)
- `CHANGELOG.md` v1.6.0
- `docs/ai-performance-intelligence.md` (CLI/API reference)
- `docs/ci-cd-gates.md` — "AI Performance Intelligence Analysis (`locust-kit analyze`)" section
- `tests/fixtures/intelligence/README.md` (fixture provenance)
