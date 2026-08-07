# Implementation Plan

## Executive Summary

This pass will deliver one coherent, local-first run-to-decision workflow for Locust users by integrating three research-backed capabilities: **evidence-linked diagnostics and run-quality grading**, a **guided server-rendered analysis workspace**, and a **portable CI evidence bundle**. The implementation will reuse the existing deterministic analyzer, Flask/SQLite workspace, argparse CLI, real CSV fixtures, CSS asset, and report models. It will not introduce a new test engine, SPA framework, cloud control plane, or mandatory LLM.

The selected scope is achievable as one minor release because all three features share one application service and evidence schema. The CLI and workspace will invoke the same analyzer and bundle builder. Existing APIs, CSV behavior, CLI exit codes, workspace routes, and SQLite data remain compatible through additive changes.

## Current-State Validation

The research matches the repository. `pyproject.toml` defines Python 3.9+, version 1.6.0, three console scripts, and Locust-centred dependencies. `intelligence.py` already parses stats/history, detects anomalies and bottlenecks, projects capacity, checks SLOs, emits deterministic insights, optionally enriches through an OpenAI-compatible endpoint, and renders Markdown/JSON. `product_workspace.py` provides transactional SQLite workflows and one generic server-rendered shell; `workspace_api.py` exposes Flask pages and versioned JSON endpoints. Tests use real Locust-shaped CSV fixtures.

Validated gaps:

- Findings do not share a structured evidence/provenance contract or deterministic data-quality grade.
- Correlations and recommendations are not consistently tied to exact source metrics and next validation steps.
- The workspace diagnostics page is generic and does not execute the analyzer.
- CLI output is Markdown or JSON only; there is no checksummed artifact envelope or JUnit SLO member.
- Flask is imported by workspace code but is not an install dependency or optional extra.
- The Dockerfile startup contract is malformed.
- Visual tests inspect structure, not a complete browser flow or accessibility state.

The research is actionable: its top recommendations map directly to existing modules, its evidence warns against causal/opaque AI claims, and it explicitly recommends a narrow run-to-decision pass. Before development, the engineer must install declared dependencies and establish an independently green baseline. The documented test count is not a substitute for an actual baseline run.

## Research Priorities

Candidate items translated from `research-findings.md`:

1. P0 evidence-linked performance diagnosis.
2. P0 guided project-to-run workspace.
3. P0 portable CI evidence bundle.
4. P1 run-quality and generator-health guardrails.
5. P1 scenario import, preview, and repair.
6. P1 local-first team history and approvals.
7. P2 ecosystem integration packs.

This pass selects items 1–3 and includes only the data-quality portion of item 4 required to prevent misleading diagnostics. “Guided workspace” is bounded to analysis of existing server-local Locust CSV prefixes. Starting or controlling Locust is deferred.

## Selected Scope for This Pass

### A. Evidence-linked diagnostics and run-quality assessment

Add structured evidence, stable rule identity, confidence, finding class, next validation step, and deterministic quality checks to every anomaly, bottleneck, projection, measured SLO result, and recommendation. Measured facts, associations, forecasts, and suggestions must be distinguishable. LLM output remains optional and cannot modify facts, confidence, SLO status, or exit code.

### B. Guided local analysis workspace

Turn `/workspace/diagnostics` into an accessible form-to-result journey. Users enter a CSV prefix under an allowed root, optional baseline, and optional SLOs; the workspace runs deterministic analysis through the shared service, persists normalized results, redirects to a stable result, and offers JSON and evidence-bundle downloads. Existing non-diagnostics workspace pages remain compatible.

### C. Portable CI evidence bundle

Extend `locust-kit analyze` and the workspace with an opt-in ZIP bundle containing a versioned manifest, strict analysis JSON, Markdown summary, JUnit SLO results, provenance, and explicitly selected input files. Bundle creation is atomic and does not alter measured exit-code semantics.

## Deferred Scope and Rationale

Eight items are deferred:

1. **Locust process start/pause/cancel:** requires target authorization, process isolation, cancellation, logs, and generator telemetry. Future runner-provider phase.
2. **Real remote/distributed zones:** requires provider adapters and integration environments. Future runner-provider phase.
3. **Visual scenario IDE/HAR/Postman repair:** separate authoring workflow and safe code-generation problem. Future scenario-authoring phase.
4. **Comments, approvals, RBAC, and SSO:** requires identity, tenant policy, migrations, and deployment architecture. Future collaboration/security phase.
5. **Production KMS/vault adapters:** required for multi-tenant production but unrelated to this local analysis flow. Future security phase.
6. **Additional protocols/plugin packs:** existing coverage is broad; these do not close the primary gap. Future ecosystem phase.
7. **Managed cloud, billing, metering:** requires commercial validation and infrastructure. Future product-validation phase.
8. **Causal root-cause claims:** current data supports association, not causation. Future telemetry-correlation research.

## Product Requirements

### Feature A: Evidence-linked diagnostics

**Research problem and user story.** Developers need trustworthy answers and broad developer evidence shows distrust of almost-correct AI conclusions. A developer or performance engineer must be able to validate every finding before blocking a release or beginning remediation.

**Functional behavior.** Add JSON-serializable models:

- `EvidenceRef`: source role, endpoint, metric, current value, optional reference value, optional time range, and display-safe locator.
- `DataQualityCheck`: stable check ID, `pass|warning|fail`, observed value, requirement, and message.
- `DataQualitySummary`: grade `A|B|C|D`, checks, and whether projection is permitted.
- `FindingProvenance`: stable finding ID, rule ID/version, class `measured|association|projection|recommendation`, confidence `high|medium|low`, evidence, and next validation step.

Apply provenance to every anomaly, bottleneck, capacity projection, SLO result, and recommendation without removing existing fields. Quality checks cover required stats parse, aggregate row, history presence, minimum five aggregate samples, timestamp ordering, non-zero RPS range, baseline endpoint overlap, and optional/full-history availability. Grade A means all applicable checks pass; B means only non-blocking warnings; C means forecast prerequisites are missing; invalid required stats/aggregate input raises the existing input error instead of producing a report. Grade D can be used in persisted failed workspace records but not as a misleading completed analysis.

**Inputs and validation.** Inputs remain CSV prefix, optional baseline, and SLO map. Numeric values must be finite; JSON must never emit NaN or infinity. Locators identify logical roles such as `stats:Aggregated:p95`, not unrestricted absolute paths. JSON gains a positive `schema_version` and retains existing keys.

**Business rules.** Measured SLOs alone control exit code. Grade C suppresses numeric breach forecasts that lack prerequisites. Associations must use non-causal language. Recommendations reference at least one measured/association/projection finding. Missing baseline evidence is omitted, never invented. Optional LLM receives normalized facts only and may add narrative only.

**Edge/failure behavior.** Missing stats returns current input error and CLI 1. Missing history still renders aggregate/SLO data, grade C, and unavailable forecasts. No-overlap baseline produces a warning and no endpoint regression claims. Duplicate timestamps are normalized deterministically with warning. Zero requests/RPS never divides by zero or predicts capacity.

**Dependencies and compatibility.** No new runtime dependency. Existing Python imports, constructor patterns, JSON keys, Markdown sections, fixtures, and CLI codes remain. New existing-dataclass fields require defaults or provenance is stored in an additive report mapping.

**Acceptance criteria.** For `run_b` versus `run_a`, every finding has rule/version, confidence, evidence, and next check. Healthy `run_a` has grade A/B and no regression. Missing-history input has grade C and no numeric forecast. Strict JSON contains schema version and no non-finite tokens. Existing 0/1/2 CLI tests pass. Tests prohibit causal wording. New/changed analysis modules reach at least 90% measured statement coverage.

**Non-goals.** New statistical algorithms, asserted root cause, telemetry retrieval, or mandatory LLM.

### Feature B: Guided local analysis workspace

**Research problem and user story.** Existing CLI, analyzer, and workspace capabilities are fragmented. A Python developer or QA engineer with Locust CSV output must be able to analyze it locally without memorizing CLI syntax and recover from input errors without losing valid values.

**Functional behavior.** `/workspace/diagnostics` becomes “Analyze a Locust run” with CSV prefix, optional baseline, p95/p99/error-rate SLOs, primary submit, local-analysis notice, recent analyses, and a development-only example. POST executes the same service used by the CLI, creates a `PROCESSING` record, transitions it to `READY` or sanitized `FAILED`, and returns HTTP 303 to a stable result. Reload never reruns analysis.

Result hierarchy: breadcrumb/source label, Pass/Fail/Advisory banner, quality grade and checks, current/baseline summary, SLO table, ranked finding groups, evidence disclosures, capacity/unavailable state, provenance, bundle/JSON downloads, and “Analyze another run.” Store normalized report/configuration/status/timestamps/display labels/artifact metadata, not raw CSV bytes.

Add a health endpoint that checks application/database availability without exposing records or paths. Add a supported `locust-workspace` entry point accepting host, port, database, and allowed root; default host is `127.0.0.1`.

**Validation.** Browser-submitted CSV/baseline paths must resolve under mandatory `LOCUST_WORKSPACE_ALLOWED_ROOT`; reject traversal, symlink escape, NUL, directory-as-prefix, nonexistent stats, and strings over 1,024 characters. SLOs are finite; error rate is 0–1; p95/p99 are >0. Errors appear in a focused summary linked to field-level messages. Result URLs use IDs, not paths. Escape every source label, endpoint, message, locator, and XML value.

**Business rules.** Browser analysis never enables LLM in this pass. Violated measured SLO is Fail; configured all-pass is Pass; no SLO is Advisory. Grade C limits forecasts but does not overwrite measured decision. Expected failures persist sanitized codes/correlation IDs, never traces or absolute paths. Example is disabled without explicit development configuration.

**Failure/recovery.** Database unavailability yields 503 and correlation ID. User-correctable errors yield 422 preserving safe values. Unexpected errors are logged with correlation ID and show a generic recovery page. Post/Redirect/Get and a request fingerprint/token prevent duplicate refresh records. Bundle failure does not invalidate a READY analysis. Persisted result renders after sources are deleted.

**Dependencies and compatibility.** Add optional `workspace` extra with a Python-3.9-compatible Flask range. Add Playwright/pytest browser tooling to a dedicated test/dev extra. No React, Vue, HTMX, ORM, CSS framework, or JS build chain. Preserve `/workspace/<page>`, existing JSON APIs, SQLite tables and `create_workspace_app()`.

**Acceptance criteria.** Real fixture flow from `run_b`, baseline `run_a`, p95 500 redirects to a result showing Fail, grade, regression evidence, and verified bundle download. Healthy run shows Pass; no SLO shows Advisory. Invalid prefix/traversal/symlink/malformed SLO/missing baseline produce 422, focused summary, inline errors, and preserved safe values. Reload does not rerun. At 360, 768, and 1440 px there is no document overflow. Keyboard order, visible focus, disclosures, error focus, and result focus work. Automated scans on landing, error, success, and failure have zero serious/critical accessibility violations. Reduced-motion and WCAG 2.2 AA contrast are verified. Startup, health, and container smoke pass.

**Non-goals.** Uploads, process execution, remote storage, multi-user collaboration, or browser scenario editing.

### Feature C: Portable CI evidence bundle

**Research problem and user story.** CI and release users need a reproducible artifact independent of a SaaS dashboard. An SRE must archive one bundle whose facts, configuration, versions, and member hashes can be verified later.

**Functional behavior.** Add a shared bundle builder and opt-in CLI flags for bundle path, normal source inclusion, and sensitive source inclusion. Defaults remain unchanged. ZIP root contains exactly `manifest.json`, `analysis.json`, `summary.md`, `slo-results.xml`, `provenance.json`, plus optional safe `inputs/` members.

Manifest includes bundle schema version 1, package version, UTC creation time, display-safe source/baseline labels, SLOs, quality grade, measured exit code, member paths, sizes, and SHA-256 hashes; it does not hash itself. Provenance includes input roles/hashes, rule versions, Python version, Locust version when available, and normalized options; it excludes environment, API keys, webhook URLs, secrets, and absolute paths.

JUnit has one test case per SLO; violation is failure, pass is pass, no SLO produces one skipped advisory test. Optional normal input includes stats/history. Failures/exceptions require a second explicit sensitive opt-in. Fixed member names never derive directories from user data. Bundle creation completes on SLO violation and CLI returns 2. Write to a sibling temporary ZIP, verify using `testzip()`, then atomically replace.

**Validation and edge behavior.** Reject output that is a directory/unwritable/overlaps input. Validate regular files, role limit, and conservative total-size limit. Missing optional files are recorded absent. Changed-during-read source fails rather than creating mixed evidence. Existing destination remains unchanged on failure. Endpoint text cannot create paths or invalid XML. Non-UTF-8 input can still be copied/hashed.

**Dependencies and compatibility.** Standard library only: `zipfile`, `hashlib`, `json`, `ElementTree`, `tempfile`, `pathlib`. Existing CLI output and exit meanings remain; no bundle unless requested.

**Acceptance criteria.** Healthy, failed-SLO, no-history, and no-SLO fixtures produce valid ZIPs. Every manifest member hash/size matches extracted bytes. No absolute/traversal/unexpected members. JUnit parses and represents all states. `run_b --slo p95=500` writes valid bundle and returns 2. Inclusion matrix is enforced. Sentinel secrets/absolute paths are absent from manifest/provenance. Atomic failure preserves prior destination. Bundle module reaches 95% measured statement coverage.

**Non-goals.** Signing, upload, retention service, or embedded HTML dashboard.

## UI and UX Specification

### Personas and primary journey

Primary personas are a Python backend developer checking a change and a QA/performance engineer comparing a controlled run. Secondary personas are an SRE archiving release evidence and a manager reading the decision. The journey is: start local workspace, open Diagnostics, enter current/baseline/SLOs, submit, review decision and evidence, download bundle, reopen from recent analyses.

### Stack and design system

Keep Flask/Jinja-style server rendering and extend `static/workspace.css`. A SPA is unjustified for a form-driven, read-heavy workflow and would duplicate contracts. Core flow works without JavaScript; one small packaged script is permitted for busy state/focus only.

CSS tokens: spacing 4/8/12/16/24/32/48 px; system sans; 16 px body and minimum 14 px metadata; neutral canvas/surface/border, one accent, semantic success/warning/failure/info colors with AA contrast; small/medium radii; at most two shadow levels; 2 px high-contrast focus outline plus offset; transitions ≤150 ms and disabled for reduced motion.

Components and states: button default/hover/focus/active/disabled/busy; input default/focus/invalid/disabled/help/error; status badges; alerts; native evidence `details/summary`; responsive table wrapper; static skeleton; empty and recovery panels.

### Information architecture

Preserve Scenarios, Runs, Diagnostics, Policies, Vault, Capacity. Diagnostics has Analyze run, Recent analyses, and Result detail. A “Deterministic local analysis” indicator is persistent. Remove ambiguous global “Create new” on diagnostics.

### Page hierarchy and calls to action

**Diagnostics landing:** breadcrumb, heading/guidance, privacy notice, CSV field, baseline field, SLO fieldset with units, primary “Analyze run”, development-only “Load example”, recent results/empty guidance.

**Result:** breadcrumb/source/timestamp, decision banner, quality grade, current-vs-baseline metrics, SLO table, findings by category, evidence disclosures, capacity/unavailable state, audit provenance, primary “Download evidence bundle”, secondary “Download JSON” and “Analyze another run.”

**Recent analyses:** newest 100; label, decision, grade, baseline, timestamp; decision/grade filters; cards on mobile and table on larger screens.

**Health:** minimal JSON service/database/version, no path/count/config/secret.

### States and recovery

Empty state explains Locust `_stats.csv` and history naming. Loading/PROCESSING shows a skeleton and polite text, no fake percentage. Validation error has an alert summary, inline messages, preserved values, and focus. READY supports pass/fail/advisory and limited-data. FAILED shows sanitized code/correlation ID and retry. Bundle state supports ready/error/retry without invalidating analysis. Disabled controls explain prerequisites.

### Responsive behavior

320–599 px: single column, horizontally scrollable navigation, stacked metrics, evidence definition lists, labeled table scroll regions. 600–1023 px: two-column summaries/SLO fields. ≥1024 px: persistent left nav, form max width about 800 px, 12-column result grid with 8-column findings and 4-column provenance. At 200% zoom no fixed control obscures content.

### Accessibility

One `h1`; correct heading order and banner/nav/main/footer landmarks; skip link; labels/descriptions/error associations; error summary alert and focus; text+shape status; native disclosure; table captions and scoped headers; main heading focus after redirect; page title includes decision; all controls keyboard reachable; no trap. Automated checks are supplemented by keyboard, 200% zoom, reduced-motion, and screen-reader smoke evidence.

### End-to-end flows

Success: enter `run_b`, baseline `run_a`, p95 500; 303 redirect; focus result heading; Fail banner; open latency-regression evidence with current/reference/rule/confidence/next check; download valid ZIP; reopen persisted result.

Recovery: enter path outside allowed root and error rate 4; receive 422; focus summary linking both fields; messages explain root and 0–1; safe values preserved; correction succeeds without presenting failed partial analysis as complete.

### UI verification

Install UI extra and browser, start app with temporary DB and fixture allowed root, verify health, run Playwright for initial/invalid/pass/fail/advisory/limited/bundle flows, run accessibility checks, and capture 360×800, 768×1024, 1440×900 screenshots for pass/fail/error when tooling permits. Use semantic assertions; only add pixel baselines if stable across CI.

## Screen Inventory and User Flows

1. **Analyze run:** onboarding, form, recent list, empty/loading/validation/service-error states.
2. **Analysis result:** PROCESSING, READY pass/fail/advisory/limited-data, FAILED, bundle ready/error.
3. **Recent analyses:** filters, responsive list/table, empty state.
4. **Health endpoint:** machine-readable operational status.

The complete successful and recovery journeys, calls to action, focus behavior, persistence, and downloads are defined in the UI section and are mandatory acceptance flows.

## Architecture and Technical Design

### Boundaries

- Existing `report_data.py` and `intelligence.py` remain parsing/statistics owners; no duplicate parser.
- New `analysis_evidence.py`: evidence models, quality evaluator, stable rule registry, provenance attachment.
- New `analysis_service.py`: validated request, invokes `analyze_run`, adds quality/provenance; shared by CLI/workspace.
- New `evidence_bundle.py`: JUnit, manifest/provenance, safe ZIP, atomic write/verification.
- `PerformanceWorkspace`: additive analysis result/artifact persistence.
- `workspace_api.py`: form/result/download/health/security headers.
- New `workspace_cli.py`: supported startup.
- `cli_analyze.py`: additive bundle flags and shared service.
- Existing CSS plus optional minimal JS.

### Data flow and state

CLI: arguments → `AnalysisRequest` → shared service → current analyzer → quality/provenance → text/JSON → optional bundle → existing exit code.

Workspace: POST → path/SLO/CSRF validation → PROCESSING record → shared service → READY/FAILED → 303 result → persisted normalized JSON → optional bundle. Viewing does not require source files; raw-input regeneration does.

### Persistence

Add idempotently:

- `analysis_runs(id,state,source_label,source_fingerprint,baseline_label,slos_json,report_json,decision,quality_grade,error_code,correlation_id,created,updated)`.
- `analysis_artifacts(id,analysis_id,kind,path_or_metadata,sha256,size,state,created)`.

Do not repurpose `results`. Do not store raw CSV bytes. Absolute paths, if operationally unavoidable, remain non-display metadata and never enter report/bundle. Existing tables/rows are untouched. Add schema metadata only if needed for future migration.

### API/routes

- `GET /workspace/diagnostics`
- `POST /workspace/diagnostics/analyze`
- `GET /workspace/diagnostics/<analysis_id>`
- `GET /workspace/diagnostics/<analysis_id>/analysis.json`
- immutable `GET` or state-changing `POST` for `/bundle`, chosen consistently
- `GET /healthz`

Optional programmatic routes are additive `/api/v1/analyses` and use existing error envelopes. Existing routes remain.

### Packaging/deployment

Add optional `workspace` extra for Flask; UI/build/coverage dependencies to dev/test extras; `locust-workspace` script; package CSS/JS. Repair Dockerfile and select one documented image purpose. If workspace image, install workspace extra, expose concrete port, run supported entry point. Reconcile `requirements.txt` and package installation docs.

### Logging/error handling

Use `logging`. Generate/validate correlation IDs. Log state transition, duration, decision, grade, safe error code. Never log secrets, environment, raw failure text, API keys, absolute source paths, or report JSON. Expected validation errors have no traceback; unexpected errors log trace server-side and show generic client recovery.

### Alternatives and rationale

Reject SPA, raw CSV-in-SQLite, repurposed generic results table, LLM-primary answers, run orchestration, and non-ZIP artifact directory. These increase scope, sensitivity, duplication, or lock-in without improving this pass’s core outcome.

## Data, API, and Compatibility Changes

Analysis JSON gains positive `schema_version`, `data_quality`, `rule_versions`, and provenance keyed by stable deterministic finding ID or embedded additively. Arrays are deterministically ordered; generated timestamps do not affect finding IDs.

Bundle schema version is 1. Required member meanings remain stable within version 1; readers reject unsupported versions; optional keys may be added compatibly. Member paths are relative POSIX paths; hashes are lowercase SHA-256.

SQLite changes are additive and initialized transactionally. A pre-feature DB must open without manual migration and preserve old query results.

Existing exports remain. New dataclass fields have defaults or report-level mappings. `analyze_run()` keeps current parameters; optional keyword-only extensions or wrapper are permitted. Existing Markdown core sections and CLI flags/codes remain. No bundle by default.

## Security and Privacy Considerations

- Resolve workspace paths under mandatory allowed root and reject traversal/symlink escape.
- Bind to loopback by default; external bind warns that authentication/TLS are absent.
- Browser never enables LLM.
- Contextually escape HTML/XML/Markdown values.
- ZIP uses fixed member names, no user paths, and safe extraction tests.
- Stats/history input needs explicit inclusion; failures/exceptions need second sensitive opt-in.
- Manifest/provenance use allowlists and exclude environment/absolute path/secrets.
- State-changing forms use CSRF protection or a documented/tested same-origin strategy; Flask secret-key production misconfiguration fails closed.
- Add CSP using self-hosted assets, `nosniff`, no-referrer, and frame protection; avoid inline script.
- Downloads use safe filename, attachment disposition, no-store.
- Enforce path length, regular file, total bundle size, and synchronous resource limits.
- Existing local cipher is not promoted as production KMS; analysis tables store no secret plaintext.

## Test Strategy

### RED/GREEN order

For each feature, write failing contract tests, record targeted RED, implement minimum behavior, record GREEN, refactor, then run affected group. Do not weaken existing tests.

### Baseline/tooling

Planned supported commands after adding explicit extras:

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev,workspace,ui-test]"
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/pyright
```

Add `build`, coverage, Playwright, pytest integration, and accessibility tooling explicitly if used.

### Feature A tests

RED tests for model/default compatibility, grades A/B/C/D, missing/insufficient history, baseline overlap/no-overlap, every provenance category, strict JSON, stable IDs/order, causal-language prohibition, LLM immutability, and old constructor compatibility. Use real fixtures. Target:

```bash
.venv/bin/python -m pytest -q tests/unit/test_analysis_evidence.py tests/test_intelligence.py tests/test_cli_analyze.py
```

### Feature B tests

Unit: path confinement/traversal/symlink, finite SLO parse, persistence state/idempotency, sanitization, DB-failure health, security/download headers.

Integration: Flask client, temporary SQLite, real fixture CSVs, valid fail/pass/advisory, 303, reload no rerun, bundle/JSON download, pre-feature DB compatibility, render after source deletion.

Browser: live server, keyboard/focus, viewports, error recovery, all decision/quality states, bundle download, zero serious/critical accessibility violations. Target:

```bash
.venv/bin/python -m pytest -q tests/unit/test_product_workspace.py tests/integration/test_workspace_analysis.py
.venv/bin/python -m pytest -q -m visual tests/visual/test_workspace_analysis_e2e.py
```

### Feature C tests

Required members, manifest hash/size, `testzip`, safe paths, JUnit pass/fail/advisory parse, valid bundle plus return 2, inclusion matrix, sentinel-secret/path exclusion, atomic replacement/failure, changed-during-read, size boundary, malicious-value escaping, deterministic member order. Target:

```bash
.venv/bin/python -m pytest -q tests/unit/test_evidence_bundle.py tests/test_cli_analyze.py tests/integration/test_workspace_analysis.py
```

### Final verification

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/pyright
.venv/bin/python -m build
.venv/bin/python -m pip install --force-reinstall dist/*.whl
.venv/bin/locust-kit analyze --csv tests/fixtures/intelligence/run_a/run_a --slo p95=500 --bundle /tmp/run-a.zip
.venv/bin/locust-workspace --host 127.0.0.1 --port 8090 --database /tmp/workspace.db --allowed-root "$PWD/tests/fixtures"
curl --fail --silent http://127.0.0.1:8090/healthz
```

Also build/start Docker and health-check according to its documented purpose. Formatter check is not currently configured; do not invent one. If adding a formatter, declare and configure it first. Coverage targets: ≥90% statements for new/changed evidence/service/workspace modules, ≥95% bundle module, all listed branches covered, and no project-wide regression below measured baseline.

Pass requires all targeted/full tests, Ruff, Pyright, build/wheel install, CLI bundle, startup/health, E2E, and accessibility checks. Missing browser binary, skipped critical acceptance test, or unverified artifact is failure and must be reported.

## Documentation Deliverables

`README.md`: core/workspace installation, bundle command, loopback workspace command with allowed root, deterministic-local meaning, main journey, troubleshooting, explicit no process launch/authentication.

`CHANGELOG.md`: dated minor release with evidence/quality, guided diagnostics, bundle schema, flags/entry point, additive tables, dependency/deployment fixes, compatibility/security notes, and only verified test totals.

API/CLI docs: create `docs/evidence-linked-analysis.md` with models, grades/rules, JSON/bundle schema, sensitivity, CLI/examples/codes, workspace routes/config/startup/troubleshooting, pass/fail/advisory/limited examples, non-causal policy. Update existing intelligence/getting-started/CI/workspace docs only for accuracy and links.

`FEATURES-DONE.md`: exact required structure, only completed outcomes, public APIs/flags/schema/UI states/test evidence/limitations.

`development-report.md`: exact required 16 sections; RED/GREEN evidence; command/count/failure details; coverage; lint/type/build/wheel/startup/Docker/browser/accessibility; screenshots; security checks; files; blockers; traceability; no weakened/skipped-test statement.

Every documented command must be run against source or built wheel, or explicitly labeled conceptual with reason. Links, versions, flags, variables, schemas, and routes must match code.

## Expected File Changes

Expected additions: `development-report.md`, `analysis_evidence.py`, `analysis_service.py`, `evidence_bundle.py`, `workspace_cli.py`, optional focused renderer and `workspace.js`, `docs/evidence-linked-analysis.md`, unit tests for evidence/bundle, integration workspace analysis test, browser E2E test, and only necessary edge fixtures.

Expected modifications: `intelligence.py`, `cli_analyze.py`, `product_workspace.py`, `workspace_api.py`, `workspace.css`, `__init__.py`, `pyproject.toml`, deployment files needed for one verified startup contract, README, CHANGELOG, FEATURES-DONE, focused existing docs, and additive assertions in existing tests.

Unrelated protocol templates, OpenAPI generation, baseline semantics, notifications, dashboards, and examples should not change without explicit development-report justification.

## Traceability Matrix

| Research need | Research evidence | Planned requirement | Acceptance criterion | Planned implementation location | Planned test evidence | Priority |
|---|---|---|---|---|---|---|
| Trustworthy explanation | S4/S7/S8 demand; S19 distrust | Provenance on every finding; deterministic authority | Every `run_b` finding has rule, confidence, evidence, next check | `analysis_evidence.py`, `intelligence.py`, service | evidence/analyzer tests | P0 |
| Avoid false causality | Research risks/differentiation | Finding classes and non-causal language | No causal wording; association has validation step | evidence and insight rendering | text-policy fixture tests | P0 |
| Avoid misleading forecasts | P1 quality guardrail | Quality checks/grades gate projection | Missing history is C and no numeric forecast | evidence/analyzer | real edge-fixture tests | P0 |
| Exact baseline evidence | P0 diagnosis | Current/reference/time locators | p95 disclosure shows exact values and stable locator | analyzer/result UI | run_b/run_a integration + E2E | P0 |
| Reduce fragmented onboarding | Current-state/UX research | Guided diagnostics and persisted results | Valid form redirects; pass/fail/advisory work | workspace API/domain/CSS | Flask I/O + browser | P0 |
| Preserve local privacy | Persona/pricing/privacy evidence | Allowed-root local analysis; no browser LLM | UI labels local; no outbound LLM | validation/service/config | network-denial test + UI assertion | P0 |
| Friendly recovery | Required UX states | Focused summary, inline errors, preserved values | Traversal/bad SLO gives 422 and no path leak | routes/render/CSS | Flask + Playwright recovery | P0 |
| Accessible responsive UI | Modern UX baseline | Tokens, responsive states, keyboard/screen-reader | No overflow; zero serious/critical; focus visible | CSS/render/optional JS | viewport/keyboard/axe/screenshots | P0 |
| Review after sources disappear | History precursor | Persist normalized report, not raw CSV | Delete source; result still renders, no duplicate | workspace persistence | integration test | P0 |
| Portable CI evidence | P0 bundle/CI demand | Versioned checksummed ZIP | ZIP/hash/member verification | bundle/CLI | unit/extraction tests | P0 |
| Preserve gate semantics | Existing contract | Bundle on violation with code 2 | `run_b` writes valid bundle and returns 2 | CLI/bundle | real CLI test | P0 |
| Prevent leakage | Privacy differentiator | Double input opt-in; provenance allowlist | Default no raw CSV; sentinel absent | bundle/options | inclusion/secret tests | P0 |
| Installable workspace | Packaging gap | Flask extra, startup CLI, health, container fix | clean wheel install/start/health/Docker | package/startup/deployment | build/startup smoke | P0 |
| Compatibility | Project convention | Additive APIs/tables/flags | pre-feature DB and full suite green | all touched areas | compatibility/full regression | P0 |

## Risks and Mitigations

- Scope creep: enforce non-goals and existing CSV-only journey.
- Dataclass breakage: default additive fields or report mapping, compatibility tests first.
- Evidence interpreted as cause: explicit class, banned words, next checks.
- Arbitrary grades: fixed documented rules and branch tests.
- File disclosure: mandatory allowed root, realpath/symlink checks, limits.
- SQLite failures: short transactions, additive init, temporary DB tests, sanitized 503.
- Bundle leakage/corruption: opt-ins, allowlists, sentinel tests, atomic verified replacement.
- Browser CI brittleness: pinned explicit setup, semantic assertions, non-pixel gating unless stable.
- Core dependency bloat: Flask remains optional.
- CSS sprawl: bounded tokens/components.
- Schema drift: version contracts and compatibility tests.
- Stale verification claims: run clean baseline/final commands and record exact counts only.

## Definition of Done

- [ ] Three selected features are complete with no production stubs, placeholders, fake data, or unconditional success.
- [ ] Existing local CSVs complete form-to-persisted-result-to-verified-bundle flow.
- [ ] Pass, Fail, Advisory, grade-C, validation, storage, and bundle recovery states are tested.
- [ ] Every finding category has evidence, stable rule/version, confidence, and next check.
- [ ] No association is presented as causal.
- [ ] Quality rules and bundle schema version 1 are documented and exhaustively tested.
- [ ] Existing APIs/imports/CLI codes/routes/tables/CSV behavior remain compatible.
- [ ] RED/GREEN evidence exists for each feature; targeted and full suite pass.
- [ ] Ruff, Pyright, measured coverage, build, wheel install, CLI, startup, health, and Docker checks pass.
- [ ] Playwright flows pass at three viewports; required accessibility scans have zero serious/critical violations.
- [ ] Keyboard, focus, 200% zoom, reduced-motion, and screen-reader smoke checks are recorded.
- [ ] README, CHANGELOG, accurate API/CLI docs, exact-structure FEATURES-DONE, and development report agree with code.
- [ ] CSRF strategy, path confinement, escaping, security headers, safe ZIP paths, sensitive opt-ins, and sentinel tests pass.
- [ ] No secrets, caches, environments, dependencies, temporary DB/downloads, coverage/build output, or stray artifacts remain.
- [ ] Every selected requirement is traceable to implementation/test evidence; deferred scope is not advertised.
- [ ] Final complete project is reconciled to baseline, packaged without wrapper directory, integrity-tested, separately extracted, and verified.
