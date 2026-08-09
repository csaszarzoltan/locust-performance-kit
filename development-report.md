# Development Report

## Implemented Scope

Stabilized the existing run-to-decision product without adding unrelated product scope. US-004 is complete: baseline compatibility, current/baseline/absolute/percentage endpoint deltas, Added/Missing states, aligned p95/RPS history, an accessible SVG, and a keyboard-readable data-table fallback. Runtime/package version is 1.7.0 and a local `v1.7.0-rc1` tag was created.

## Research Items Addressed

Explainable baseline comparison, zero-fabrication data-quality rules, evidence-backed CI decisions, accessible run-detail visualization, and release-candidate verification.

## Plan Requirements Completed

Completed B2, B3, B4, B5, B8, B9, B10 and the remaining US-004 contract. Added complete endpoint comparison to canonical JSON and Markdown, baseline overlap metadata, timeline alignment by elapsed seconds, accessible visual/table output, focused type-check configuration, wheel install smoke, and artifact hash verification.

## User Stories Covered

- US-001: PASS, regression-green.
- US-002: PASS, regression-green.
- US-003: PASS, regression-green.
- US-004: PASS. Common endpoints expose all six planned metric comparisons; Added/Missing values never get fabricated percentages; timeline and baseline compatibility are rendered and exported.
- US-005: PASS, regression-green.
- US-006: PASS, hash and export regressions green.

## Architecture Decisions

Comparison calculation lives in `decision_artifact.py` so CLI, downloads, storage, Markdown, and UI consume one deterministic model. `comparison_view.py` is a presentation-only module. Timeline alignment uses elapsed seconds from each run start, avoiding false wall-clock alignment. SVG is server-rendered and self-hosted; the full underlying data table is always present.

## UI and UX Implementation

Run Detail now includes a compatibility summary, p95 SVG with contrasting solid/dashed series, text description, current/baseline legend, expandable p95/RPS table, and a horizontally scrollable endpoint table. The endpoint table names current/baseline values, absolute delta, percentage delta, RPS, and error-rate delta. Added/Missing states are visible text and never color-only.

Playwright installation was attempted with `PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-stab /opt/pyvenv/bin/playwright install chromium`. All browser mirrors returned HTTP 403, so real browser screenshots and automated axe scanning remain blocked. Flask integration and semantic UI gates passed; no screenshot claim is made.

## TDD Evidence

- RED contract existed in the prior report: US-004 had no endpoint matrix or timeline.
- New RED tests were authored for complete metric deltas, Added/Missing no-fabrication, aligned histories, SVG semantics, captions, and data-table fallback.
- GREEN targeted command: `pytest -q tests/unit/test_decision_artifact.py tests/unit/test_comparison_view.py tests/integration/test_run_import_flow.py` -> 11 passed.
- Full GREEN regression -> 1,105 passed.

## Tests and Coverage

Final complete suite: `.venv/bin/python -m pytest -q` -> **1,105 passed, 0 failed** in 10.76s. TDD gate rerun -> 1,105 passed in 9.88s. BDD gate -> 19 passed. Security gate -> 13 passed. UI gate -> 20 passed.

Coverage was attempted with pytest-cov, Coverage C tracer, timid tracer, `COVERAGE_CORE=sysmon`, disabled pytest plugin autoload, and `--concurrency=gevent`. The normal variants triggered gevent `_thread._local` assertions; concurrency/sysmon runs hung and were terminated after 90 seconds without data. No numeric percentage is claimed. This remains the only unmet quantitative gate.

## Lab Quality Gates

Repository-local gates:

- `bash scripts/tdd-gate-v3.sh` -> PASS, 1,105 tests.
- `bash scripts/bdd-gate.sh` -> PASS, 19 tests and story tags.
- `bash scripts/security-gate.sh` -> PASS, 13 tests plus secret scan.
- `bash scripts/doc-sync-check.sh` -> PASS.
- `bash scripts/ui-gate.sh` -> PASS, 20 tests plus semantic checks.

All requested `~/.hermes/scripts/*` commands were attempted. `/home/oai/.hermes/scripts` is absent, so the Hermes implementations could not run.

## Lint, Formatting, Type-Check, Build, and Startup Results

- Ruff changed-scope: PASS.
- Formatter: no formatter configured.
- Focused Pyright: PASS, 0 errors, 0 warnings.
- Build: PASS with `python -m build --no-isolation`; wheel and sdist version 1.7.0.
- Fresh wheel install: PASS in `/tmp/lpk-rc-venv`.
- CLI version: PASS, `locust-kit 1.7.0`.
- Startup/health: PASS, health returned version 1.7.0.
- Installed-wheel CLI: PASS; expected exit 2, JSON and Markdown written.
- Decision hash: PASS through independent `verify_decision`; six endpoint rows present and timeline aligned.
- Docker: BLOCKED because no `docker` executable is installed.
- Browser E2E/screenshots: BLOCKED by Playwright browser download HTTP 403.

## Files Added

`src/locust_templates/comparison_view.py`, `tests/unit/test_comparison_view.py`, and the two restored `.github/workflows/` files that were absent from transport despite being required by project tests.

## Files Modified

`decision_artifact.py`, `run_import.py`, `workspace_views.py`, `workspace.css`, runtime version files, `pyproject.toml`, version assertions, US-004 tests, README, CHANGELOG, baseline decision guide, FEATURES-DONE, and this report.

## Deferred or Blocked Items

Prometheus/OTel, RBAC/SSO/KMS, hosted execution, billing, visual scenario authoring, and automatic PR posting remain deferred exactly as requested. Numeric coverage, real-browser screenshots/axe, Docker smoke, Hermes binaries, and remote push are environment-blocked.

## Git Commit and Push

A local clean commit and `v1.7.0-rc1` tag were created. `git pull --rebase`, `git push`, and `scripts/git-push-verify.sh` were attempted. Push verification failed because the transported archive had no configured remote/upstream. No remote push success is claimed.

## Known Limitations

Timeline compares aggregate p95 visually while RPS remains available in the accessible table and decision JSON rather than a second plotted scale. The local workspace remains single-operator. Coverage percentage is unknown due to the reproducible gevent/coverage incompatibility in this environment.

## Integrity Verification

Baseline manifest contained 205 pre-existing files. Final reconciliation verifies no pre-existing file disappeared. All changed files map to stabilization, versioning, CI restoration, tests, or required documentation. Virtual environments, caches, coverage database, build outputs, temporary databases, and browser downloads are excluded from final packaging.

## Traceability Matrix

| Research need | User story id | Plan requirement | Implementation evidence | Test evidence | Status |
|---|---|---|---|---|---|
| Explain endpoint regressions | US-004 | B2/B3 | `build_endpoint_comparison` | complete-delta test | COMPLETE |
| Avoid fabricated deltas | US-004 | B3 | Added/Missing metric objects use null deltas | no-fabrication test | COMPLETE |
| Compare histories accessibly | US-004 | B4 | elapsed timeline, SVG, HTML data table | accessible comparison view test | COMPLETE |
| Show compatibility | US-004 | B2 | overlap/common/added/missing model and cards | compatibility test | COMPLETE |
| Preserve audit artifacts | US-006 | B8/B9/B10 | JSON/Markdown include comparison and stable hash | full artifact regression | COMPLETE |
| Release candidate confidence | US-001-US-006 | Definition of Done | 1.7.0 build/install/start/hash | 1,105 full regression | PARTIAL |

## Suggested Commit Message

`fix(workspace): complete US-004 comparison and stabilize v1.7.0-rc1`
