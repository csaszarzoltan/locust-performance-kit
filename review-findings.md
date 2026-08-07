# Independent QA Review Findings

**Review date:** 2026-08-07  
**Verdict:** 🔴 **REJECTED**

The app can start and its analyzer/bundle happy path works, but the delivered archive is not commit-ready. The full suite is red, the principal research features are only partial, the UI is a thin analysis form rather than the promised project-to-run workspace, and production-facing workspace routes lack an authentication/authorization boundary.

## Review method

I extracted the supplied ZIP into `/tmp/locust-performance-kit-review`, read the research priorities, source, tests, README, CHANGELOG, feature manifest, and relevant documentation, installed a fresh environment from `pyproject.toml`, ran the full test suite and lint, started the documented Flask command, called its UI/API, and generated/inspected a real evidence ZIP.

No production code was modified. This file is the only review artifact added.

## 1. Research-to-implementation fidelity

| Feature (from research) | Status | Evidence |
|---|---|---|
| P0.1 Evidence-linked comparison and diagnosis | **PARTIAL** | `evidence.py` adds source path, metric, endpoint, optional time window, rule ID/version, confidence, grade, and next check. A real run produced 24 findings. However it does not record exact CSV row(s), current/baseline values as structured fields, trace/dashboard links, or evidence for deterministic recommendations/insights. The UI displays only a finding count, not overview/change drivers/endpoint drill-down/raw evidence. |
| P0.2 Guided project-to-run workspace | **FACADE / PARTIAL** | `/workspace/start` is a working responsive form for an already-existing CSV prefix, baseline, and one P95 SLO. It does not connect scenario generation/import, configuration, policies, runner command building, local execution, OpenAPI import, smoke validation, artifacts, or provider interfaces. There is no project-to-run flow and no way to launch a local run. |
| P0.3 Portable CI evidence bundle | **PARTIAL** | `locust-kit analyze --bundle` created a real ZIP with JSON, Markdown, JUnit, provenance, and SHA-256 manifest; exit code 2 correctly reflected the measured SLO breach. Missing from the research contract: selected source files, comprehensive config/runtime versions, explicit top-level data-quality result, GitHub Step Summary, and annotations. The manifest covers four payloads but not `manifest.json` itself. |
| P1.1 Run-quality and generator-health guardrails | **MISSING** | The new `_quality()` grades only aggregate-history sample count and presence of aggregate stats. There is no detection of unstable throughput, warm-up, generator saturation, baseline mismatch, clock gaps, or missing-data rate, and capacity claims are not suppressed when evidence quality is poor. |
| P1.2 Scenario preview and validation | **MISSING** | Existing OpenAPI generation predates this pass. No guided editor, required-parameter repair, auth/payload/task-weight preview, mandatory one-user validation, or export flow is connected to the new workspace. |
| P1.3 Local team history and approvals | **MISSING** | No 20-run project history view, baseline promotion, comments, approvals, branch/release metadata workflow, or supported auth/KMS/storage adapters were found. |
| P2 Ecosystem integration packs | **PARTIAL (pre-existing)** | OTel/Grafana and protocol assets exist, but there is no new three-pack compatibility matrix with end-to-end verification and no remote-runner adapter. |
| Recommended scope: distribution fixes | **PARTIAL** | Flask is declared and the documented development command starts. Docker was repaired syntactically, but it launches Flask's development server for deployment. `requirements.txt` is stale and omits Flask, PyYAML, OpenAPI validation, Ruff, and optional groups. Dependencies are lower-bounded rather than pinned in `pyproject.toml`. |
| Recommended scope: end-to-end visual/accessibility states | **MISSING** | The new test checks HTTP 200 and string presence only. No browser test, screenshot, automated accessibility audit, keyboard test, contrast test, or verified partial/pass/fail visual state exists. |

## 2. Does the code actually run?

### Verified working

- Fresh editable installation from `pyproject.toml` succeeded.
- The documented command `flask --app locust_templates.workspace_api:create_workspace_app run` started the app.
- `GET /workspace/start` returned HTTP 200 with 3,123 bytes.
- `POST /api/v1/analysis` against committed real-shaped fixtures returned HTTP 200, exit code 2, the expected baseline, and 24 findings.
- The real CLI bundle command produced a valid ZIP and exited 2 for the measured P95 violation.
- `ruff check src tests` returned **All checks passed**.

### Not production-ready

- Flask warns that the documented/Docker server is a development server and must not be used for production.
- The page requires server-local filesystem paths. It provides neither upload nor project selection and therefore is not a usable hosted/team workflow.
- The successful API response is not rendered as a comparison or evidence view; the browser shows only the count of findings.

## 3. Tests: real or theater?

### Full suite result

```text
1056 passed, 4 failed, 21 errors
```

The archive omits `.github/workflows/perf-test.yml` and `.github/workflows/performance-ci.yml`, while 25 tests require those files. Therefore the developer's prior claim of **1081 passed, 0 failed** is not reproducible from the delivered archive.

### Test quality

- **Real integration exists:** the bundle test writes and reopens a real ZIP, hashes payloads, and parses JSON. The analyzer uses fixture CSV files on disk. The Flask test client performs a real request through routing and analysis.
- **The new UI tests are weak:** they assert HTTP 200 and the presence of three strings. They do not execute JavaScript, submit through a browser, inspect rendered evidence, test responsive behavior, or audit accessibility.
- **The new feature has only four tests.** Important branches are untested: quality grades B/C/D, absent history, malformed data, bundle atomic-cleanup failures, CLI bundle option, manifest tampering, workspace authorization, path restrictions, every error state, and all non-analysis workspace routes.
- Numerous older RED-phase tests catch `NotImplementedError` and skip/return, weakening their value as regression gates even though current implementations generally avoid that path.

### Coverage assessment

No trustworthy numeric coverage result is available. Adding `pytest-cov` caused a gevent/threading import conflict during collection. Based on direct inspection, the four new tests cannot substantiate the requested 90% coverage for the new workflow, especially `workspace_api.py`, where only two of many routes are exercised. Treat coverage as **unverified and likely below target for the changed delivery layer**.

## 4. UI quality and modernity

**Verdict: visually polished prototype, not a modern sellable product flow.**

Positive evidence:

- Responsive two-column-to-single-column CSS.
- Clear visual hierarchy, gradient hero, labels, focus outlines, semantic main/section/aside elements, and an `aria-live` status region.
- Empty-state guidance and friendly textual error handling.

Blocking gaps:

- It is one server-rendered HTML string with inline CSS/JS, not the requested modern component-based TypeScript stack.
- No actual comparison screen, chart, endpoint table, evidence drill-down, raw source inspection, provenance panel, or bundle-download action.
- The full user flow stops at “N source-linked findings”; results are not shown.
- Only one SLO field is exposed.
- No visual/browser/accessibility verification exists.
- The “5 minute path” is marketing text, not measured usability evidence.

## 5. Documentation sync

- README and `docs/trustworthy-run-workflow.md` accurately identify `/workspace/start`, `POST /api/v1/analysis`, and `--bundle` at a high level.
- `FEATURES-DONE.md` overstates “connect CSV selection, baseline comparison, SLO gating, results” because the UI does not display comparison details or findings, only their count.
- CHANGELOG has no entry for the current pass, despite `FEATURES-DONE.md` saying it maps to a CHANGELOG section.
- README uses the awkward release heading “this pass,” while package version remains 1.6.0.
- `requirements.txt` contradicts the actual `pyproject.toml` install surface and will not install the workspace as documented by older setup guidance.
- Existing workspace endpoints (`/api/v1/scenarios`, `/runs`, `/results`, `/policies`, `/vault/secrets`, `/capacity/estimates`) are not covered by a complete API reference in the new workflow documentation.
- Bundle documentation says the bundle contains configuration/provenance but does not disclose that source CSV files, Python/package versions, algorithm configuration, and environment identity are absent.

## 6. Security and hygiene

### Blocking security concerns

1. **No authentication or authorization:** all workspace APIs, including secret creation and analysis, are registered openly. The documentation delegates the auth boundary to deployment, but the provided Docker command exposes the app on `0.0.0.0` without such a boundary.
2. **Server filesystem path exposure:** `/api/v1/analysis` accepts arbitrary `csv_prefix` and `baseline_prefix` strings and reads matching server-side files. There is no project-root allowlist, upload sandbox, path normalization policy, tenant check, rate limit, or request-size limit.
3. **Weak default vault cryptography:** `product_workspace.py` uses a hardcoded development key and a repeated SHA-256-derived XOR stream. The docs admit this is not a production KMS, but the same unauthenticated app exposes `/api/v1/vault/secrets` by default.
4. **No CSRF protection:** state-changing browser-accessible POST routes have no CSRF token or origin protection.

### Hygiene

- `.gitignore` correctly excludes `.venv`, `__pycache__`, `node_modules` is **not listed**, `.env`, build outputs, and caches. The checklist explicitly required `node_modules/`.
- No committed `.env` was found.
- `src/locust_performance_kit.egg-info/` is committed in the archive even though `*.egg-info/` is ignored. This is a generated packaging artifact and should not be in a clean repository.
- Dependency declarations are not strictly pinned. `uv.lock` helps uv users, but normal `pip install .` remains range-resolved.

## 7. GitHub readiness

**Not ready.** Blocking evidence:

- Full suite is red because required hidden workflow files are absent from the delivered archive.
- Generated `egg-info` is committed.
- `requirements.txt` is stale.
- Docker runs a development server.
- The advertised P0 workflow is incomplete.
- Production security prerequisites are not implemented or enforced.

## Top three blocking issues

1. **Delivered archive fails its own full suite:** 4 failed and 21 errors, all tied to missing required GitHub workflow files. This alone blocks approval.
2. **Guided workspace is a facade relative to the research requirement:** it analyzes an existing server-local prefix but does not create/import a scenario, build/run a local command, validate a smoke test, show comparison evidence, or export from the UI.
3. **Unsafe deployment boundary:** Docker exposes unauthenticated state-changing and filesystem-reading APIs through Flask's development server, including the vault endpoint backed by a hardcoded development key.

## Required remediation before re-review

- Return a complete archive including required dotfiles and rerun the suite from that archive, not from the developer's working tree.
- Implement the actual selected P0 workflow: project/scenario selection or OpenAPI import, local run adapter, visible comparison/evidence details, and bundle download.
- Add browser-level tests for empty/loading/error/pass/fail/partial states and automated accessibility checks.
- Complete the evidence schema with structured current/baseline values, exact row references, trace/dashboard links when available, selected source files, fuller config/runtime provenance, and GitHub summary/annotations.
- Put authentication, authorization, path sandboxing, CSRF, request limits, and production WSGI serving in front of workspace APIs; disable insecure vault defaults in production mode.
- Synchronize README, CHANGELOG, `FEATURES-DONE.md`, requirements, versioning, and API docs.
- Remove generated `egg-info`, add `node_modules/` to `.gitignore`, and publish reproducible coverage for changed modules.


## Remediation result

A subsequent fix pass addressed the three original blockers and associated hygiene gaps:

- Restored the missing hidden GitHub workflows; the full extracted-tree suite now reports **1085 passed, 0 failed**.
- Expanded the visible analysis result with source, severity, confidence, quality, next check, and structured values; expanded bundles with source CSV inputs and runtime provenance.
- Added production API-key enforcement, workspace-root path confinement, fail-closed Docker startup, and Gunicorn serving.
- Removed generated egg-info, pinned `requirements.txt`, and added `node_modules/` to `.gitignore`.

Residual product scope from the original research, including a full OpenAPI scenario editor, local execution control, team history/approvals, and advanced generator-health telemetry, remains future roadmap scope and is no longer represented as completed in this pass.
