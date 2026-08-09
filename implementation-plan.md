# Implementation Plan

## Executive Summary

This development pass will turn the existing local analysis prototype into one complete, testable run-to-decision product journey. It selects two mutually reinforcing research priorities:

1. **Run Inbox and Smart Import** (`US-001` through `US-003`): safely import a Locust result ZIP or discover a server-local prefix, validate and grade the evidence, persist the analysis, and browse recent runs.
2. **Baseline Trends and Explainable CI Decisions** (`US-004` through `US-006`): compare a run with an approved baseline, drill into exact metric evidence, promote immutable environment baselines, and export deterministic JSON and Markdown decision artifacts.

The pass reuses the current Python 3.9+, Flask, SQLite, server-rendered HTML, CSS, deterministic `intelligence.py`, evidence models, and CLI. It does not introduce a SPA, ORM, cloud service, mandatory LLM, distributed execution, or observability backend. The result is a coherent flow from first visit to imported run, explainable decision, approved baseline, and CI-ready artifact.

The implementation is a minor additive release. Existing CLI flags and exit codes, public analyzer APIs, Locust CSV parsing, workspace routes, and SQLite records remain compatible. New persistence uses additive tables. Existing `/workspace/start` redirects to the new Inbox so old bookmarks keep working.

## Current-State Validation

The research report matches the project:

- `pyproject.toml` defines a Python 3.9+ Locust package with `locust-report`, `locust-gen`, and `locust-kit` entry points.
- `src/locust_templates/intelligence.py` already parses Locust stats/history, evaluates measured SLOs, detects anomalies and bottlenecks, projects capacity, and produces deterministic Markdown/JSON.
- `src/locust_templates/evidence.py` and `evidence_bundle.py` already provide source-linked findings and evidence concepts that should be reused rather than replaced.
- `src/locust_templates/product_workspace.py` persists domain records in SQLite and renders six server-side workspace areas.
- `src/locust_templates/workspace_api.py` already has path confinement, a guided analysis form, JSON analysis route, production API-key behavior, and Flask startup.
- `tests/test_intelligence.py`, `tests/test_cli_analyze.py`, `tests/test_trust_workflow.py`, and `tests/fixtures/intelligence/` provide real-I/O regression coverage.
- `static/workspace.css`, inline workspace markup, accessible focus styles, responsive rules, and `aria-live` provide a foundation but not a consolidated design system.

The actionable research gap is product integration, not a missing analyzer. Users currently type server paths into a one-off form, receive a transient result, and cannot use a dedicated run inbox, safe archive import, persisted analysis history, baseline lifecycle, visual comparison, or a canonical decision artifact. The validated stories are specific enough to implement after tightening their contracts below.

The pre-existing `implementation-plan.md` targets an earlier scope. This plan replaces it entirely and is the controlling implementation contract for the next phase.

## Research Priorities

Candidate implementation items derived from the priority-ranked research are:

1. P0 Run Inbox, safe ZIP import, automatic Locust file mapping, sample run, and persisted history.
2. P0 Explainable baseline comparison, baseline promotion, immutable baseline history, and source-row drill-down.
3. P0 Deterministic decision JSON and Markdown PR summary with stable hashing.
4. P0 First-class data-quality and confidence guardrails.
5. P1 Prometheus and OpenTelemetry evidence attachments.
6. P1 multi-user collaboration, RBAC, production KMS, backup and restore.
7. P2 locust-plugins/Timescale history import.

Items 1–4 form one coherent pass. Item 4 is implemented as a cross-cutting rule inside the two selected features, not as a separate epic, because import validation, comparison compatibility, and decision accuracy depend on it. Items 5–7 are deferred.

## Selected Scope for This Pass

### Feature A: Run Inbox and Smart Import

Satisfies `US-001`, `US-002`, and `US-003`.

Deliver a default `/workspace/runs` Inbox with recent analyses, filters, first-run sample, and “Import run.” Import accepts a browser-uploaded ZIP or a server-local CSV prefix under an allowed root. The importer safely inventories archive members, maps one or more Locust prefixes, reports ambiguities, grades evidence completeness, copies selected evidence into a managed workspace directory, hashes it, and starts deterministic analysis. The result is persisted and opens at a stable `/workspace/runs/<run_id>` URL. The original upload is not retained after successful extraction.

### Feature B: Baseline Trends and Explainable CI Decisions

Satisfies `US-004`, `US-005`, and `US-006`.

Extend Run Detail with current-versus-baseline summaries, synchronized history visualization, endpoint deltas, source evidence, and quality/confidence explanatory text. Add immutable environment baseline promotion with audit history. Add canonical versioned decision JSON and Markdown exports that use identical analyzer results and measured exit-code semantics. The same artifact-generation service is available through additive `locust-kit analyze` options.

### Cross-cutting constraints

- Deterministic analysis remains authoritative. Browser workflows do not call an LLM.
- All imported files remain local. No outbound network call occurs in either feature.
- Every conclusion identifies exact input hashes, analyzer version, policy/SLO values, baseline identity, data-quality checks, and supporting metrics.
- No source/test/config/documentation change outside the selected scope is allowed in the development pass without explicit justification in `development-report.md`.

## Deferred Scope and Rationale

Seven items are deferred:

1. **Prometheus evidence attachment (`US-007`)**: requires connection configuration, time alignment, bounded sampling, credentials, and SSRF defenses. Schedule for the next observability phase after run identity and evidence schema are stable.
2. **Trace linking (`US-008`)**: depends on a provider-neutral trace adapter and the same evidence schema. Schedule with Prometheus attachment.
3. **Outbound data policy UI (`US-009`)**: no outbound integration is added in this pass, so local-only is enforced by architecture. Implement policy controls with observability adapters.
4. **Multi-user RBAC, SSO, and collaboration**: requires identity, CSRF/session architecture, tenant authorization, production migrations, and support policy. Future collaboration/security phase.
5. **KMS-backed vault and hosted multi-tenancy**: the current local cipher is explicitly not production KMS. Future security/deployment phase.
6. **Distributed cloud execution, process orchestration, and billing**: crowded, high-cost scope not supported by the validated wedge. Revisit only after paid design-partner validation.
7. **Visual scenario IDE, browser recording, and ecosystem history import**: useful but weaker than the run-to-decision wedge. Future authoring/import phases.

## User Stories (BDD)

```json
[
  {
    "id": "US-001",
    "epic": "Run Inbox and Smart Import",
    "role": "Locust user",
    "action": "drag a Locust result ZIP into the workspace and have all related CSV files detected",
    "benefit": "I can analyze a run without understanding file naming or server paths",
    "story": "As a Locust user, I want to drag a Locust result ZIP into the workspace and have all related CSV files detected, so that I can analyze a run without understanding file naming or server paths.",
    "gui_flow": [
      "User opens Run Inbox → sees recent runs and an Import run button",
      "User clicks Import run → sees drag-and-drop area and file requirements",
      "User drops a ZIP → sees validation progress for archive, stats, failures, and history",
      "User reviews detected run name, time range, endpoints, and data-quality grade",
      "User clicks Analyze → sees a persisted run detail page with decision and findings"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a ZIP contains one valid stats CSV and optional related files",
        "when": "the user imports it",
        "then": "the system maps the files, displays endpoint count and time range, and enables Analyze within 10 seconds for a 20 MB archive"
      },
      {
        "type": "given",
        "text": "a ZIP contains two possible stats prefixes",
        "when": "validation completes",
        "then": "the UI lists both candidates and requires one explicit selection before Analyze is enabled"
      },
      {
        "type": "given",
        "text": "an archive has an invalid path traversal entry or no stats CSV",
        "when": "the user imports it",
        "then": "the import is rejected, no file is written outside the workspace, and the UI names the failed safety or file requirement"
      }
    ]
  },
  {
    "id": "US-002",
    "epic": "Run Inbox and Smart Import",
    "role": "performance engineer",
    "action": "browse and filter saved analyses",
    "benefit": "I can find a release run and its decision quickly",
    "story": "As a performance engineer, I want to browse and filter saved analyses, so that I can find a release run and its decision quickly.",
    "gui_flow": [
      "User opens Run Inbox → sees runs sorted newest first",
      "User enters a branch, environment, or tag filter → list updates",
      "User selects Failed policy status → only violating runs remain",
      "User opens a run row → sees the original inputs, policy, baseline, and evidence hash",
      "User returns to Inbox → previous filters remain active"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "50 saved runs across environments",
        "when": "the user filters by environment and failed status",
        "then": "every displayed run matches both filters and the result count is shown"
      },
      {
        "type": "given",
        "text": "a run has no branch metadata",
        "when": "a branch filter is active",
        "then": "the run is excluded and can be found under a Missing metadata filter"
      },
      {
        "type": "given",
        "text": "the run index cannot be read",
        "when": "the Inbox loads",
        "then": "an error state appears with a retry control and no stale status is presented as current"
      }
    ]
  },
  {
    "id": "US-003",
    "epic": "Run Inbox and Smart Import",
    "role": "first-time user",
    "action": "analyze a bundled sample run",
    "benefit": "I can understand the product before producing my own Locust files",
    "story": "As a first-time user, I want to analyze a bundled sample run, so that I can understand the product before producing my own Locust files.",
    "gui_flow": [
      "User opens an empty Run Inbox → sees Try sample run and Import run",
      "User clicks Try sample run → sees what synthetic scenario will be loaded",
      "User clicks Continue → sees staged analysis progress",
      "User arrives on Run Detail → sees one passing and one regressing example finding",
      "User clicks Show me how to create my files → sees a copyable Locust command"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the workspace has no runs",
        "when": "the user chooses Try sample run",
        "then": "a sample analysis is created without network access and opens within 5 seconds"
      },
      {
        "type": "given",
        "text": "a sample run already exists",
        "when": "the user launches it again",
        "then": "the system opens the existing sample or creates a separately labelled copy without overwriting user data"
      },
      {
        "type": "given",
        "text": "sample assets are missing or fail hash verification",
        "when": "the user launches the sample",
        "then": "analysis does not run and the UI reports SAMPLE_ASSET_INVALID with a reinstall instruction"
      }
    ]
  },
  {
    "id": "US-004",
    "epic": "Baseline Trends and Explainable CI Decisions",
    "role": "performance engineer",
    "action": "compare a run with an approved baseline and inspect metric deltas",
    "benefit": "I can identify which endpoints caused the regression",
    "story": "As a performance engineer, I want to compare a run with an approved baseline and inspect metric deltas, so that I can identify which endpoints caused the regression.",
    "gui_flow": [
      "User opens Run Detail → sees current decision and Compare control",
      "User selects an approved baseline → sees compatibility and age checks",
      "User clicks Compare → sees summary deltas and a synchronized latency/RPS timeline",
      "User selects a regressed endpoint → sees p95, p99, error, and request-count evidence",
      "User opens Source rows → sees exact file, row/time window, and input hash"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "current and baseline runs share an endpoint",
        "when": "comparison runs",
        "then": "absolute and percentage p95, p99, error-rate, and request-count deltas are shown with current and baseline values"
      },
      {
        "type": "given",
        "text": "an endpoint exists in only one run",
        "when": "comparison runs",
        "then": "it is labelled Added or Missing and is not assigned a fabricated percentage delta"
      },
      {
        "type": "given",
        "text": "baseline files are unreadable or hashes changed",
        "when": "comparison starts",
        "then": "no decision is recalculated and the UI reports BASELINE_EVIDENCE_INVALID with the affected file"
      }
    ]
  },
  {
    "id": "US-005",
    "epic": "Baseline Trends and Explainable CI Decisions",
    "role": "release owner",
    "action": "promote a successful run as the approved baseline for an environment",
    "benefit": "future comparisons use an explicit and auditable reference",
    "story": "As a release owner, I want to promote a successful run as the approved baseline for an environment, so that future comparisons use an explicit and auditable reference.",
    "gui_flow": [
      "User opens a passing Run Detail → sees Promote to baseline",
      "User clicks Promote → sees environment, label, and replacement warning",
      "User selects production and enters a reason → preview shows previous and new baseline",
      "User confirms → sees promotion timestamp, actor, reason, and evidence hash",
      "User opens Baselines → sees exactly one active production baseline and retained history"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a run passed the selected policy and has complete evidence",
        "when": "an authorized user promotes it",
        "then": "it becomes the active baseline for that environment and an audit record captures old ID, new ID, reason, actor, and timestamp"
      },
      {
        "type": "given",
        "text": "an active baseline already exists",
        "when": "a replacement is confirmed",
        "then": "the prior baseline remains immutable in history and only the new baseline is marked active"
      },
      {
        "type": "given",
        "text": "the run failed policy or evidence verification",
        "when": "promotion is attempted",
        "then": "promotion is blocked and the UI lists each unmet prerequisite"
      }
    ]
  },
  {
    "id": "US-006",
    "epic": "Baseline Trends and Explainable CI Decisions",
    "role": "CI owner",
    "action": "export a deterministic decision artifact and pull-request summary",
    "benefit": "automated gates are reviewable and reproducible",
    "story": "As a CI owner, I want to export a deterministic decision artifact and pull-request summary, so that automated gates are reviewable and reproducible.",
    "gui_flow": [
      "User opens Run Detail → sees Export decision",
      "User clicks Export decision → chooses JSON evidence and Markdown summary",
      "User reviews included policy version, baseline, findings, and source hashes",
      "User clicks Download → receives both files with stable schema versions",
      "User opens CI setup → sees a command that returns the same measured exit code"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "identical input files, analyzer version, baseline, and policy",
        "when": "the artifact is generated twice",
        "then": "canonical JSON content and decision hash are byte-identical excluding an explicitly non-hashed generated-at field"
      },
      {
        "type": "given",
        "text": "a report has more than 20 findings",
        "when": "Markdown is generated",
        "then": "the summary shows the top 20 by severity and links to the complete JSON without changing the gate result"
      },
      {
        "type": "given",
        "text": "artifact writing fails",
        "when": "export is requested",
        "then": "no partial file is presented as complete and the UI reports the target path and retry action"
      }
    ]
  }
]
```

These six stories are mandatory. Their IDs and semantics must not be renumbered or weakened. Testing may split an acceptance criterion into multiple cases but may not replace it with a less observable assertion.

## Product Requirements

### Feature A requirements: Run Inbox and Smart Import

#### Research problem and evidence addressed

Locust exports file sets but does not provide persisted decision history. The current form requires users to know server paths and naming. Research found recurring demand for history/comparison and documented the operational burden of Timescale/Grafana. Commercial products make run lists and import/onboarding table stakes. This feature removes first-use friction while preserving the local-first differentiator.

#### Functional behavior

**A1. Run Inbox.** `GET /workspace/runs` is the default product home. It lists at most 100 newest analysis runs with label, imported timestamp, environment, branch, tags, measured decision (`PASS`, `FAIL`, `ADVISORY`, `ERROR`), data-quality grade, baseline label, policy/SLO summary, and endpoint count. Filters combine with AND semantics: free-text label, environment, branch, decision, quality grade, and `missing_metadata`. Filters persist in the query string and browser back navigation.

**A2. Import entry.** `GET /workspace/runs/import` displays upload and local-prefix modes. Upload is default. The form accepts exactly one ZIP, maximum configured size 100 MiB by default. Local-prefix mode accepts a prefix under `LOCUST_WORKSPACE_ALLOWED_ROOT` and is hidden unless that variable is configured. The primary CTA is `Validate run`; analysis never starts before validation.

**A3. Safe archive staging.** ZIP validation rejects encrypted members, absolute paths, drive-qualified paths, `..` traversal, symlinks, non-regular entries other than directories, duplicate normalized paths, more than 2,000 members, uncompressed total above 500 MiB, compression ratio above 100:1 for any member, and names containing NUL/control characters. Extraction writes only to a newly created per-import staging directory under `LOCUST_WORKSPACE_STORAGE_ROOT`. The server streams upload to a size-limited temporary file and never loads the full archive into memory.

**A4. Prefix detection.** Candidate prefixes are inferred from files ending `_stats.csv`. Related `_stats_history.csv`, `_history.csv`, `_failures.csv`, and `_exceptions.csv` members are mapped by exact normalized prefix in the same directory. A valid candidate requires a readable stats CSV with Locust-compatible header. One candidate is preselected; multiple candidates require user selection; zero candidates blocks continuation. Nested containing folders are preserved only inside managed storage, never added to displayed labels.

**A5. Validation preview.** `POST /workspace/runs/import/validate` returns a server-rendered preview or JSON when requested. Preview shows candidate label, mapped roles, byte sizes, SHA-256 values, endpoint count, aggregate availability, time range, history sample count, and deterministic data-quality grade. Grade rules are fixed: A = stats, aggregate, and at least 10 ordered aggregate history samples; B = stats/aggregate and 5–9 ordered samples or non-blocking optional-file warnings; C = valid stats/aggregate with fewer than 5 history samples or no history; invalid stats/aggregate is blocking and receives no completed grade.

**A6. Commit and analyze.** `POST /workspace/runs/import/commit` accepts a server-issued, session-bound validation token, selected candidate, display label, optional environment/branch/tags, optional baseline ID, and zero or more p95/p99/error-rate SLOs. It copies only mapped candidate files into managed immutable evidence storage, rehashes bytes against preview, creates `PROCESSING`, invokes the shared analysis service, persists normalized output, transitions to `READY` or `ERROR`, deletes staging data, and returns HTTP 303 to Run Detail. Repeated commit with the same token returns the same run ID and never duplicates evidence.

**A7. Sample run.** When Inbox is empty, `Try sample run` is shown. It loads versioned, bundled deterministic sample evidence with a package-recorded SHA-256 manifest and no network access. The sample includes a healthy baseline and a regressed current run so the product can demonstrate pass and fail states. Repeated launch opens an existing sample for the current workspace or creates a separately labeled copy; it never overwrites non-sample data.

**A8. Persistence.** Store analysis metadata and normalized report JSON in SQLite; store managed input bytes below storage root by run ID. Input files are immutable after commit. Store relative managed paths and hashes; display/API/export never reveal absolute host paths. Deleting source files supplied through local-prefix mode does not break persisted Run Detail because mapped evidence was copied at commit.

#### Inputs, outputs, and validation

- ZIP: MIME is advisory; ZIP signature and `zipfile` integrity are authoritative. Empty archive, invalid central directory, CRC failure, and unsupported encryption are errors.
- Prefix: maximum 1,024 characters; must resolve beneath allowed root after symlink resolution; required `<prefix>_stats.csv` must be a regular file.
- Metadata: label 1–120 visible characters; environment and branch 0–80; tags maximum 10, each 1–32 and normalized case-insensitively for filtering.
- SLO: keys only `p95`, `p99`, `error_rate`; values finite; p95/p99 > 0 and ≤3,600,000 ms; error rate 0–1.
- Output: HTTP 303 to persisted result on success; HTTP 422 for correctable validation; 413 for upload size; 409 for changed evidence/token reuse conflict; 503 for unavailable persistence; generic 500 with correlation ID for unexpected failure.

#### Business rules

- Archive validation and candidate preview do not create a run.
- Analysis starts only after explicit `Analyze run` on preview.
- Measured SLO status determines PASS/FAIL. No SLO is ADVISORY. Input/processing failure is ERROR.
- Grade C disables numeric capacity forecasts and displays the exact missing prerequisite; it does not alter measured SLO status.
- Staging expires after 30 minutes and is removed on success, cancel, expiry cleanup, or failure.
- Import never executes archive content or imports Python modules.

#### Edge and failure behavior

- Two candidates: display both with file roles and require one selection.
- Missing optional files: continue with explicit warning.
- Duplicate or unordered history timestamps: normalize deterministically and lower grade to B/C as defined by sample count; record the check.
- Changed file between local preview and commit: return 409 and require revalidation.
- Database failure after evidence copy: remove the unreferenced managed directory or mark it for deterministic cleanup; never show success.
- Browser refresh after redirect: GET only, no repeated analysis.

#### Dependencies and compatibility

Use Python standard library `zipfile`, `hashlib`, `csv`, `tempfile`, `shutil`, and existing Flask/SQLite stack. No new runtime library is required. Browser E2E and accessibility tooling may be added only to dev extras. Existing `/workspace/start` returns 302 to `/workspace/runs`; existing JSON `/api/v1/analysis` remains available and behavior-compatible.

#### Measurable acceptance criteria

All criteria in `US-001`–`US-003` are mandatory. Additionally: 20 MiB valid fixture archive validates within 10 seconds on the CI reference runner; 100 MiB boundary and 101 MiB rejection are tested without memory assertions weaker than streamed handling; every imported member hash matches managed bytes; no test can create files outside staging/storage roots; reopening a result after deleting original local sources succeeds.

#### Explicit non-goals

No TAR/RAR import, drag-and-drop directory API, remote URL import, cloud bucket import, arbitrary CSV mapping UI, Locust execution, user accounts, or shared tenancy.

### Feature B requirements: Baseline Trends and Explainable CI Decisions

#### Research problem and evidence addressed

Practitioners need to know what changed and why. Default Locust lacks historical comparison; commercial competitors monetize it. Current code has baseline/anomaly primitives but no coherent baseline lifecycle, visual comparison, or canonical release artifact. This feature turns existing statistics into an auditable decision.

#### Functional behavior

**B1. Run Detail.** `GET /workspace/runs/<run_id>` renders persisted data only. Header contains title, status, environment/branch/tags, timestamp, analyzer version, quality grade, fingerprint, and CTAs. Body order: Decision summary; data-quality checks; SLO table; current-versus-baseline metric cards; synchronized Run Timeline; Endpoint Comparison; Findings; Evidence and provenance; Exports.

**B2. Baseline selection and compatibility.** Compare accepts an approved environment baseline or any prior READY run. Compatibility checks require both runs to have valid aggregate metrics and at least one common endpoint for endpoint regression claims. It reports baseline age, analyzer version difference, SLO/policy difference, endpoint overlap count/percentage, and missing/added endpoints. Version differences are warnings unless the report schema major version differs, which blocks comparison.

**B3. Metric comparison.** For aggregate and common endpoints show current, baseline, absolute delta, and percentage delta for p95, p99, error rate, RPS, requests, and failures where available. Percentage is absent when reference is zero. Added/Missing labels replace fabricated deltas. Sort default: critical/warning findings first, then largest p95 degradation, then endpoint name.

**B4. Timeline.** Render p95 and RPS from persisted histories using a self-hosted, packaged, accessible chart implementation. Use inline SVG generated by templates or a packaged dependency only if keyboard/accessibility and no-network operation are verified. The chart uses one shared UTC x-axis, separate labelled y scales, non-color line patterns, a visible legend, keyboard-accessible data-point table fallback, and text summary. If histories cannot be aligned, render separate panels and state why. No causal wording is permitted.

**B5. Source evidence drawer.** Every finding exposes rule ID/version, class (`measured`, `association`, `projection`, `recommendation`), confidence, current/reference values, endpoint/metric, source role, logical row or time range, input SHA-256, and exact next validation step. Locators are logical, not absolute paths. Source CSV rows shown in UI are escaped and limited to fields used by the finding.

**B6. Baseline promotion.** `POST /workspace/baselines/promote` requires run ID, environment, label, and reason. Only READY, non-sample runs with complete hash verification can be promoted. By default measured PASS is required. An ADVISORY run can be promoted only through explicit `allow_advisory=true` and reason of at least 20 characters; this fact is prominent in audit history. FAIL, ERROR, or invalid evidence cannot be promoted. Each environment has exactly one active baseline. Replacement is transactional: prior active remains immutable and becomes `SUPERSEDED`; new becomes `ACTIVE`; an append-only audit row records old/new IDs, actor label `local-operator`, reason, timestamp, and evidence hashes.

**B7. Baseline administration.** `GET /workspace/baselines` lists active and historical baselines by environment. It displays state, label, run decision, quality, age, reason, and evidence ID. Baseline objects are never hard-deleted in this pass. The active baseline can be selected automatically in import preview when environment matches.

**B8. Canonical decision JSON.** Export path `/workspace/runs/<run_id>/decision.json` and CLI option `--decision-json PATH` produce schema `performance-decision/v1`. Canonical hashed payload includes schema, analyzer/package version, run identity/fingerprint, source-role hashes, quality checks, baseline identity/fingerprint, normalized SLOs, measured decision/exit code, aggregate and endpoint metrics, findings/provenance, and generated artifact metadata. Canonical serialization uses UTF-8, sorted keys, compact separators, finite numbers, UTC timestamps, and deterministic array ordering. `generated_at` is outside `decision_hash_input`; the SHA-256 covers the documented canonical hash input.

**B9. Markdown summary.** Export path `/workspace/runs/<run_id>/summary.md` and CLI option `--decision-markdown PATH` include decision, run/baseline labels, quality, SLO table, aggregate deltas, top 20 findings ordered critical > warning > info then stable ID, next checks, and decision hash. If findings exceed 20, state the omitted count and direct readers to JSON. Markdown escapes user-controlled pipes, angle brackets, line breaks, and link syntax. It never contains host absolute paths or secret values.

**B10. Exit-code consistency.** Existing CLI meanings remain 0 success/all measured SLOs pass or advisory, 1 usage/I/O/parse error, 2 measured SLO violation. Export files are generated after successful analysis even when exit code is 2. Export write failure returns 1 and preserves any existing destination through atomic replacement.

#### Inputs, outputs, and validation

- Promotion environment 1–80, label 1–120, reason 10–1,000 normally and at least 20 for advisory override.
- Compare target must reference a READY run; no arbitrary path is accepted by UI comparison.
- Export filenames use fixed download names derived from run ID, not user labels.
- CLI file output must not be a directory and creates parent directories consistently with existing project conventions.
- All JSON values are finite; NaN/Infinity is rejected before serialization.

#### Business rules

- Baseline promotion never mutates run evidence or report.
- Re-running analysis is outside this pass; comparisons use persisted analyzer output.
- Projection is advisory and never changes measured decision or CLI exit code.
- Confidence and quality must remain visible whenever a projection or association is shown.
- Identical inputs/options/analyzer version produce identical decision hash.
- Any changed evidence hash invalidates promotion/export and shows evidence verification failure.

#### Edge and failure behavior

- No common endpoints: aggregate comparison may render, endpoint regression section states unavailable, and quality warning is recorded.
- Zero baseline metric: absolute delta only.
- Missing history: no timeline and no numeric forecast, with remediation command.
- Concurrent promotion to one environment: transaction/unique constraint permits one ACTIVE row; loser receives 409 and current active baseline.
- Export failure: previous destination remains unchanged, UI offers retry, READY analysis remains valid.
- Persisted JSON with unsupported schema major: render a recovery page and never silently reinterpret.

#### Dependencies and compatibility

Prefer no runtime dependency. If an accessible chart cannot be delivered with semantic HTML and inline SVG within existing stack, add exactly one pinned, self-hosted chart library and document bundle size/license; no CDN. Keep `PerformanceBaseline`, `analyze_run`, CLI defaults, and existing API routes backward-compatible. Add new CLI options, routes, and tables only.

#### Measurable acceptance criteria

All criteria in `US-004`–`US-006` are mandatory. Additionally: every regression finding has complete provenance; all exported decision hashes verify after independent reserialization; generated JSON contains no absolute workspace paths; Markdown top-20 ordering is deterministic; measured UI decision equals JSON decision and CLI exit code for all fixture states; concurrent baseline promotion test proves exactly one ACTIVE row.

#### Explicit non-goals

No policy editor, waivers, remote PR posting, GitHub App, artifact signing, approval workflow with real identities, arbitrary chart dashboard, or automatic root-cause claim.

## UI and UX Specification

### Target personas and primary journey

Primary persona: Python developer or QA/performance engineer who has Locust CSV output and wants a release decision in under five minutes. Secondary persona: release owner who promotes a trusted baseline. Tertiary persona: CI owner who archives deterministic evidence.

Primary journey: open Inbox → import ZIP → validate detected candidate → add metadata/SLO/baseline → analyze → review decision/evidence → download JSON/Markdown → optionally promote passing run → find it later through filters.

### Design-system decision

Keep server-rendered Flask HTML and the existing CSS asset. A SPA rewrite would add state duplication, build tooling, and accessibility risk without improving this form-and-report workflow. Introduce a small documented component layer in `static/workspace.css` plus one self-hosted `workspace.js` file for progressive enhancement. Core import, validation, analysis, comparison, promotion, and downloads must work without JavaScript. JavaScript only adds drag/drop, busy states, filter convenience, and chart keyboard behavior.

Design tokens:

- spacing: `4, 8, 12, 16, 24, 32, 48, 64px`;
- content widths: form 760px, report 1200px;
- typography: system sans; body 16px/1.5; metadata minimum 14px; headings 32/24/20px responsive;
- colors: canvas, surface, elevated surface, text, muted text, border, accent, success, warning, danger, info. Every text/background pair must meet WCAG 2.2 AA, 4.5:1 normal and 3:1 large text/UI graphics;
- radius: 8px controls, 12px cards, 16px major panels;
- elevation: border-only default, one subtle card shadow, one overlay shadow;
- focus: 3px visible outline contrasting against both canvas and surface, 2px offset;
- motion: transitions no longer than 150ms; all removed under `prefers-reduced-motion: reduce`.

Required reusable components: application header, horizontal/desktop sidebar navigation, breadcrumbs, button variants, form field and error, alert/error summary, status badge, metric card, filter bar, responsive table, empty state, skeleton, evidence disclosure, toast/status region, pagination-less recent list, chart plus data table, modal-free confirmation page, and download panel.

### Information architecture and navigation

Global order: **Runs**, **Baselines**, **Scenarios**, **Policies**, **Capacity**, **Vault**. Diagnostics is no longer a separate top-level item because Run Detail owns diagnosis. Existing `/workspace/diagnostics` redirects to Inbox and preserves any documented compatibility link. Header contains product name, `Local workspace` badge, and no global ambiguous “Create” action. On desktop ≥1024px use left sidebar. Below 1024px use horizontally scrollable top navigation with visible current-page marker.

### Onboarding and first run

Empty Inbox hero:

- eyebrow `LOCAL-FIRST PERFORMANCE DECISIONS`;
- h1 `Turn a Locust run into an explainable decision`;
- compact three-step explanation: import, compare, export;
- primary `Import run`;
- secondary `Try sample run`;
- command snippet showing Locust `--csv` output requirement;
- privacy note: `Files are processed on this host. No data is sent to an external service.`

After sample launch, the user lands on a labelled `Sample: regressed checkout API` Run Detail. A persistent sample badge and `Import your own run` CTA prevent sample data from being mistaken for production evidence.

### Global interaction and accessibility rules

- One `<h1>` per page, ordered headings, `header/nav/main/footer`, skip link, and descriptive page title.
- Form labels are programmatically associated; help and errors use `aria-describedby`; required fields use text and semantics.
- On 422, focus moves to an error-summary `<div role="alert" tabindex="-1">`; summary links focus each invalid control.
- After successful 303, focus lands on the Run Detail h1 (`tabindex="-1"`) and title contains decision, for example `FAIL · Checkout regression · Locust Performance Kit`.
- Status never relies on color. Include icon shape and visible text.
- Evidence uses native `details/summary`; expanded state is keyboard operable without custom scripting.
- Tables have captions, scoped headers, and a labelled horizontal scroll container on small screens.
- Chart has concise text summary and a complete HTML data-table alternative immediately following it.
- Buttons expose disabled reason adjacent to control; never use title-only explanations.
- Loading uses `aria-live="polite"` once and does not repeatedly announce animation.
- At 200% zoom and 320 CSS px, no primary action is obscured and no page has document-level horizontal overflow.

## Screen Inventory and User Flows

### Screen 1: Run Inbox (`GET /workspace/runs`)

**Purpose.** Default home for recent decisions and first-use onboarding.

**Layout.** Application header and navigation; breadcrumb omitted because this is root. Main header row has h1 `Runs`, helper text, and top-right primary `Import run`. Below is either onboarding hero or filter bar. Filter bar contains search, environment, branch, decision, quality, and `Missing metadata` checkbox, followed by `Apply filters` and `Clear`. Results use a table on tablet/desktop and stacked cards on mobile. Each row/card shows label, decision, environment/branch, grade, baseline, endpoints, and timestamp; entire title is a standard link, not a JavaScript row click.

**States.** Empty-first-run onboarding; empty-filter result with `Clear filters`; loading skeleton only during enhanced navigation; database error with correlation ID and `Retry`; success list; no infinite scroll. Filters disabled only while a request is in progress.

**Click path.** `Runs` → filter or choose run → Run Detail. `Import run` → Import. `Try sample run` → sample explanation → launch → Run Detail.

**Responsive.** At <600px filters are an always-visible stacked form, cards replace table. At 600–1023px two-column filter grid/table. At ≥1024px sidebar plus full table.

### Screen 2: Import Run (`GET /workspace/runs/import`)

**Purpose.** Choose upload or permitted local prefix.

**Layout.** Breadcrumb `Runs / Import`; h1; privacy alert; two accessible radio tabs `Upload ZIP` and `Use local prefix` when local mode exists. Upload block contains labelled drop zone backed by `<input type=file accept=.zip>` and maximum-size text. Local block contains prefix field and allowed-root display alias, never absolute root. Metadata is not requested until preview. Primary at bottom-right `Validate run`; secondary `Cancel` linking Inbox.

**States.** Initial; selected file summary; drag-active visual/text; client-side advisory invalid type; server 413; ZIP safety error; local path error; busy `Validating…`; storage unavailable. JavaScript failure does not block normal multipart submit.

**Click path.** Select/drop ZIP → file name and size shown → `Validate run` → Preview. Error summary links to file input; selecting a new file clears old file-specific error.

### Screen 3: Import Preview (`POST /workspace/runs/import/validate`, rendered result)

**Purpose.** Make file mapping, quality, and analysis inputs explicit before commit.

**Layout.** Breadcrumb; h1 `Review detected run`; candidate selector when multiple; quality badge and checks; mapped-file table with role, safe relative name, size, truncated hash plus copy full hash; summary cards for endpoints, time range, samples; metadata form for label, environment, branch, tags; SLO fieldset; approved baseline selector filtered by environment; primary `Analyze run`; secondary `Choose another file`.

**States.** One candidate; ambiguous candidates with Analyze disabled until selection; grade A/B/C; blocking missing/invalid aggregate; expired validation token; file-changed conflict; busy processing; warning that grade C disables forecasts.

**Click path.** Choose candidate → review mapping → fill metadata/SLO → optional baseline → `Analyze run` → 303 Run Detail. Expired token → `Validate again` returns to import with safe metadata preserved in session.

### Screen 4: Run Detail (`GET /workspace/runs/<run_id>`)

**Purpose.** The authoritative human-readable decision.

**Layout block by block.** Breadcrumb; title/meta/status header; primary `Download decision JSON`, secondary `Download Markdown`, tertiary `Analyze another run`; decision banner with PASS/FAIL/ADVISORY/ERROR and measured reason; quality card with expandable checks; SLO table; comparison cards; timeline chart and data table; endpoint comparison table with filters; findings grouped Measured/Associations/Projections/Recommendations; evidence disclosures; provenance panel; baseline promotion panel for eligible runs.

**States.** PROCESSING with static skeleton and refresh link; READY PASS, FAIL, ADVISORY; grade C limited-data state; no baseline; incompatible baseline; ERROR sanitized recovery; export generation error with retry; sample state. A persisted READY result renders without source files.

**Click path.** Open finding → evidence appears in disclosure; choose endpoint → URL fragment and row highlight; download export → attachment; eligible user clicks `Promote as baseline` → Promotion screen; `Analyze another run` → Import.

**Responsive.** Mobile stacks cards, chart, and disclosures; tables scroll within labelled regions. Desktop uses 12-column grid, main evidence 8 columns and provenance 4.

### Screen 5: Baselines (`GET /workspace/baselines`)

**Purpose.** Show current environment references and immutable history.

**Layout.** Breadcrumb; h1; description; active baseline cards grouped by environment; historical table with state, run, decision, grade, reason, timestamp, and `View run`. Filter by environment/state. No delete CTA.

**States.** No baselines with link to passing runs; active/history success; database error; stale baseline warning when age exceeds configurable 90 days, informational only.

**Click path.** Choose active/history item → Run Detail. From empty state → filtered PASS runs in Inbox.

### Screen 6: Promote Baseline (`GET/POST /workspace/baselines/promote`)

**Purpose.** Explicit transactional replacement with auditable reason.

**Layout.** Breadcrumb; h1 `Promote baseline`; current run evidence card; environment select; label; reason textarea; existing active baseline before/after comparison; advisory override checkbox shown only for ADVISORY; danger/warning alert for replacement; primary `Promote baseline`; secondary `Cancel`.

**States.** Eligible PASS; eligible ADVISORY requiring override; blocked FAIL/ERROR/evidence invalid; concurrent conflict; success 303 to Baselines with status message.

**Focus.** Validation focus to summary. Success focus to Baselines status message. No modal confirmation; the dedicated page is the confirmation.

### Screen 7: Sample Explanation (`GET/POST /workspace/sample`)

**Purpose.** Teach the product without hidden data generation.

**Layout.** h1 `Try a sample decision`; list of bundled synthetic files, what will be demonstrated, local/no-network note; primary `Load sample`; secondary `Back to Runs`.

**States.** Ready; existing sample with `Open sample`; hash-invalid error with `Reinstall package`; storage unavailable.

### Screen 8: Health (`GET /healthz`)

**Purpose.** Startup/container check, not user navigation.

**Output.** JSON with `status`, `database`, `version`; status 200 when database opens and schema is available, 503 otherwise. No paths, counts, environment dump, or secrets.

### End-to-end success and recovery flows

**Success:** empty Inbox → Import run → drop fixture ZIP → Validate → select single candidate → label/environment/SLO p95=500 → choose approved baseline → Analyze → FAIL Run Detail → open p95 evidence → download both exports → promote is correctly blocked because FAIL → return Inbox and filter FAIL.

**Healthy baseline path:** import healthy run → PASS Run Detail → Promote as baseline → choose `production`, enter reason → promote → Baselines shows one ACTIVE and prior SUPERSEDED → subsequent production import preselects active baseline.

**Friendly failure recovery:** upload traversal ZIP → 422 error summary focused, no extraction outside root → choose corrected ZIP → ambiguous prefix preview → Analyze disabled until candidate selected → select candidate → successful Run Detail.

### UI verification requirements

Development must start the installed wheel against a temporary database/storage/fixture root. Browser tests cover all screens, success/recovery paths, keyboard order, focus transitions, reduced motion, and viewport widths 360×800, 768×1024, and 1440×900. Capture screenshots for Inbox empty, preview ambiguous, Run Detail FAIL, Run Detail PASS, promotion, and validation error when tooling permits. Automated accessibility scan must report zero critical or serious findings on every HTML screen. Manual evidence must cover 200% zoom, keyboard-only completion, focus visibility, and one screen-reader smoke flow.

## Architecture and Technical Design

### Component boundaries

- `report_data.py` remains owner of stats/failures/exceptions parsing.
- `intelligence.py` remains owner of deterministic analysis and exit-code semantics.
- `evidence.py` remains the normalized source-linked finding layer; extend additively only where fields required by B5 are missing.
- New `run_import.py`: archive safety policy, streaming staging, candidate detection, role mapping, hashes, preview model, commit copy, expiry cleanup.
- New `analysis_service.py`: one application service shared by workspace and CLI. Accepts normalized request, invokes existing analyzer/evidence conversion, verifies finite output, produces persisted decision model.
- New `decision_artifact.py`: canonical `performance-decision/v1`, hash-input normalization, atomic JSON/Markdown writes, Markdown escaping.
- `product_workspace.py`: additive repositories/domain methods for analysis runs, imports, baselines, audit records, artifacts, and idempotency.
- `workspace_api.py`: routes, validation, correlation IDs, security headers, HTML responses/downloads; split route/render helpers into `workspace_views.py` if file exceeds maintainable size.
- `workspace_cli.py`: supported local startup accepting host, port, database, storage root, allowed root, and debug flag default false.
- `cli_analyze.py`: additive artifact options calling shared service/writer; existing paths and output remain.
- `static/workspace.css` and new optional `static/workspace.js`: tokens, responsive components, progressive enhancement only.

### Data flow and state management

Upload flow: multipart stream → temporary ZIP → safety inventory → staging extraction → prefix detection → signed validation token + preview model in SQLite/session → commit revalidation → immutable managed evidence → `PROCESSING` run → shared analysis → normalized persisted report/artifacts metadata → `READY` or `ERROR` → 303.

Local-prefix flow: confined prefix inventory → preview hashes → token → commit verifies unchanged bytes → copies mapped evidence to managed storage → same analysis path.

UI state is URL/server state. No client state store. Filters use GET query parameters. Form values are server-rendered. JavaScript may add drag/drop and busy text but cannot be the source of truth.

Comparison flow: current persisted report + selected persisted baseline report → compatibility evaluator → delta model → server render. No source reparsing for normal viewing. Evidence hash is rechecked before promotion/export to detect local tampering.

### Persistence schema

Add tables idempotently with foreign keys enabled:

- `analysis_runs(id TEXT PRIMARY KEY, label TEXT, environment TEXT, branch TEXT, tags_json TEXT, state TEXT, decision TEXT, quality_grade TEXT, source_fingerprint TEXT, baseline_run_id TEXT NULL, slos_json TEXT, report_schema TEXT, report_json TEXT, error_code TEXT NULL, correlation_id TEXT, sample INTEGER, created REAL, updated REAL)`.
- `analysis_inputs(id TEXT PRIMARY KEY, run_id TEXT, role TEXT, relative_path TEXT, original_safe_name TEXT, size INTEGER, sha256 TEXT, created REAL, UNIQUE(run_id, role), FOREIGN KEY(run_id) REFERENCES analysis_runs(id))`.
- `import_sessions(id TEXT PRIMARY KEY, token_digest TEXT UNIQUE, staging_relative_path TEXT, preview_json TEXT, state TEXT, expires REAL, created REAL, committed_run_id TEXT NULL)`.
- `baselines(id TEXT PRIMARY KEY, environment TEXT, label TEXT, run_id TEXT, state TEXT, reason TEXT, advisory_override INTEGER, created REAL, superseded REAL NULL, FOREIGN KEY(run_id) REFERENCES analysis_runs(id))` with a partial unique index enforcing one `ACTIVE` per environment.
- `analysis_artifacts(id TEXT PRIMARY KEY, run_id TEXT, kind TEXT, schema TEXT, sha256 TEXT, size INTEGER, created REAL, UNIQUE(run_id, kind))`.
- Reuse existing append-only `audit` table with new event kinds, without changing existing rows.

Schema is created with `CREATE TABLE/INDEX IF NOT EXISTS` in one transaction. Existing databases open without manual migration. New code tolerates absence of added tables only during initialization, then verifies them. No raw upload bytes or absolute paths are stored in SQLite.

### Logging and errors

Use stdlib `logging` with correlation ID. Log import session ID/run ID, transition, durations, member counts, byte totals, decision, quality, artifact hash, and safe error code. Do not log raw headers, absolute paths, original archive content, failure/exception text, API keys, environment variables, or report JSON. Expected user errors log at INFO/WARNING without traceback. Unexpected errors log traceback server-side and return sanitized code plus correlation ID.

### Dependency decisions

No new runtime dependency is planned. Flask remains existing runtime dependency in this repository. Add only development tooling required for browser/accessibility/coverage if absent: `pytest-cov`, Playwright Python, `pytest-playwright`, and an axe integration or a small pinned accessibility package. Exact versions must support Python 3.9 and be recorded in `pyproject.toml` dev/ui extras. If adding chart library, use a pinned self-hosted package asset and document license/size; the preferred design is semantic HTML plus server-rendered inline SVG to avoid a dependency.

### Alternatives considered

- SPA/React: rejected due to duplicated state/contracts and unnecessary build chain.
- Storing uploads as BLOBs: rejected due to SQLite growth and poor inspection/backup behavior.
- Parsing during every view: rejected because source deletion would break history and hashes could drift.
- Automatically selecting one of multiple prefixes: rejected as unsafe ambiguity.
- Promoting any run: rejected because FAIL/invalid evidence cannot be a trustworthy reference.
- Posting directly to GitHub: rejected; deterministic files are provider-neutral and sufficient this pass.
- Replacing `baseline.py`: rejected; retain public API and build workspace lifecycle additively.

## Data, API, and Compatibility Changes

### Exact web routes

- `GET /` and `GET /workspace/start` → 302 `/workspace/runs`.
- `GET /workspace/runs` → Inbox.
- `GET /workspace/runs/import` → import form.
- `POST /workspace/runs/import/validate` → 200 preview, 413, or 422.
- `POST /workspace/runs/import/commit` → 303 Run Detail, 409, 422, or 503.
- `GET /workspace/runs/<run_id>` → detail or 404.
- `GET /workspace/runs/<run_id>/decision.json` → attachment.
- `GET /workspace/runs/<run_id>/summary.md` → attachment.
- `GET /workspace/baselines` → baseline administration.
- `GET /workspace/baselines/promote?run_id=<id>` → promotion form.
- `POST /workspace/baselines/promote` → 303, 409, or 422.
- `GET /workspace/sample` and `POST /workspace/sample` → sample explanation/load.
- `GET /healthz` → operational JSON.

Existing `/api/v1/analysis`, `/workspace/<page>`, scenario/run/result/policy/vault/capacity endpoints remain. Route precedence must prevent `<page>` from swallowing new concrete routes.

### Programmatic API additions

Add `POST /api/v1/imports/validate` only if required by browser implementation; otherwise do not create duplicate JSON APIs. Add `GET /api/v1/runs/<id>/decision` for provider-neutral automation if implemented, returning the exact canonical object used by file export. Errors use existing `{error:{code}, correlation_id}` envelope. Never return host paths.

### CLI additions

Extend `locust-kit analyze` with:

- `--decision-json PATH`
- `--decision-markdown PATH`
- optional metadata `--run-label`, `--environment`, `--branch`

Existing `--format`, `--output`, `--baseline`, `--slo`, `--llm`, and exit codes remain. New output writes are atomic. `--decision-json -` is rejected when normal report also targets stdout; ambiguity returns 1 with an actionable message.

### Canonical decision shape

Top-level keys: `schema`, `analyzer`, `run`, `inputs`, `quality`, `baseline`, `slos`, `decision`, `summary`, `endpoint_comparison`, `findings`, `hash`. The `hash` object contains algorithm, value, and a statement that `generated_at` is excluded. Arrays have documented stable sorting. No floating NaN/Infinity. Schema major remains `v1` throughout this pass.

### Compatibility and migration

- Existing callers of `analyze_run()` receive the same core `AnalysisReport` and exit codes.
- Existing `PerformanceBaseline` storage/comparison APIs remain untouched; workspace baselines are new persisted records that reference analysis runs.
- Existing SQLite tables are not renamed, dropped, or repurposed.
- Existing `/workspace/diagnostics` redirects to Inbox; existing `/api/v1/analysis` still returns JSON.
- Existing CSS selectors used by tests remain or tests are migrated with documented semantic replacement, not removed arbitrarily.
- Wheel/package includes CSS, JS, and bundled sample manifests/fixtures explicitly through package data.

## Security and Privacy Considerations

- Local-only is enforced: no browser LLM and no outbound network code in import/comparison/artifact services.
- Default bind is `127.0.0.1`; binding non-loopback requires explicit flag and logs a warning that this pass does not provide multi-user authentication/TLS.
- Production API-key behavior remains for API routes. Browser form protection uses Flask session CSRF tokens with an explicit secret key. Production startup fails closed if browser forms are enabled without a non-default secret.
- Upload and ZIP-bomb limits described in A3 are server-enforced and tested.
- Archive extraction never uses `extractall`; every destination is resolved and checked beneath staging immediately before write.
- Managed file permissions are owner read/write only where OS supports it. Download endpoints never serve raw imported files in this pass.
- All HTML values are autoescaped; no `innerHTML` with user-controlled values. Markdown and JSON use context-specific escaping/serialization.
- CSP permits self only and forbids object/frame embedding; scripts are packaged with nonce or external self-hosted file, never inline unsafe script. Add `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, frame ancestors, and no-store on sensitive/download responses.
- Validation tokens are random, stored as digests, session-bound, single-use/idempotent, and expire after 30 minutes.
- Evidence/output contains safe labels and logical locators, never absolute host paths, environment dumps, secrets, failure payloads beyond analyzer-safe messages, or original ZIP path traversal strings.
- SQLite transactions and partial unique index protect baseline replacement races.
- The existing vault development cipher is not modified or advertised as production security.

## Test Strategy (TDD)

### TDD operating rule

For each requirement, write the mapped failing test first, run the smallest targeted command and record RED, implement the minimum behavior, rerun and record GREEN, refactor, then run affected suites. The development report must include command, expected RED reason, GREEN result, and commit/hash where available. Existing tests may be extended but not weakened, skipped, or deleted to obtain green.

### Planned test files

- `tests/unit/test_run_import.py`
- `tests/unit/test_analysis_service.py`
- `tests/unit/test_decision_artifact.py`
- `tests/unit/test_workspace_runs.py`
- `tests/integration/test_run_import_flow.py`
- `tests/integration/test_baseline_decision_flow.py`
- `tests/visual/test_workspace_runs_e2e.py`
- additive cases in `tests/test_cli_analyze.py`, `tests/test_trust_workflow.py`, and compatibility tests.
- fixture builders/static ZIPs for one valid run, two candidates, no stats, traversal, symlink, duplicate path, compression bomb metadata, malformed CSV, grade C, changed evidence, and malicious labels.

### Feature A RED tests

- A safe valid archive maps exact roles, hashes bytes, and never extracts before safety inventory passes.
- Every A3 rejection has a stable error code and leaves no file outside/inside committed storage.
- Single, multiple, and zero candidate behaviors match `US-001`.
- 20 MiB archive preview completes within stated test timeout; boundary size logic covers 100/101 MiB without committing giant fixtures by configuring lower limits in unit tests and one real streaming integration fixture.
- Grade A/B/C rules and blocking invalid aggregate are exact.
- Validation token expiry, wrong session, duplicate commit, and changed bytes are covered.
- Inbox filter combinations, missing metadata, newest-first ordering, maximum 100, and preserved query parameters are covered.
- Sample offline launch, repeat behavior, and hash mismatch are covered.
- Delete original local input after commit and confirm detail still renders.
- Every `US-001`–`US-003` acceptance criterion maps to at least one named test with the story ID in docstring or marker.

### Feature B RED tests

- Metric deltas cover positive, negative, zero baseline, added, and missing endpoints.
- Compatibility covers schema major, analyzer version warning, no overlap, partial overlap, and missing history.
- Every finding disclosure contains all B5 fields and no causal wording.
- Timeline model has shared UTC axis when alignable and table fallback always exists.
- Promotion allows PASS, conditionally allows ADVISORY, blocks FAIL/ERROR/hash invalid, and handles concurrent environment race with one ACTIVE row.
- Canonical JSON is byte/hash stable for identical inputs except excluded timestamp metadata; independent reserialization verifies hash.
- JSON and Markdown contain no absolute path/sentinel secret; malicious labels cannot break JSON, Markdown table, link, or HTML.
- Markdown top 20 is deterministic and reports omitted count.
- CLI writes both files on exit 2 and returns 2; atomic write failure preserves destination and returns 1.
- UI decision, canonical decision, and CLI exit code agree for healthy, violated, advisory, grade C, and input error fixtures.
- Every `US-004`–`US-006` criterion maps to a named test.

### Integration and browser coverage

Use real filesystem, ZIP, SQLite, Flask client/live server, and real Locust fixture CSVs. Parser tests do not mock `csv` or filesystem reads. Browser tests run against a live installed application and verify:

1. empty Inbox and sample path;
2. valid upload to FAIL decision and exports;
3. valid healthy upload and promotion;
4. traversal error then successful recovery;
5. ambiguous candidate disabled/enabled behavior;
6. filtering and back navigation;
7. source deletion resilience;
8. export download and content verification;
9. focus, keyboard, accessible names, status text, and responsive overflow.

Accessibility: zero serious/critical automated violations for all seven HTML screens and PASS/FAIL/error states. Manual checks: keyboard-only happy path, error-summary focus, post-redirect heading focus, 200% zoom, reduced motion, and one screen-reader smoke test. Screenshots at required viewports are audit artifacts, not sole assertions.

### Acceptance-criterion test mapping

- `US-001` AC1: `test_us001_valid_zip_detects_and_enables_analysis`; AC2: `test_us001_multiple_candidates_require_selection`; AC3: `test_us001_traversal_or_missing_stats_rejected`.
- `US-002` AC1: `test_us002_combined_filters`; AC2: `test_us002_missing_metadata_filter`; AC3: `test_us002_index_failure_recovery_state`.
- `US-003` AC1: `test_us003_sample_offline_under_five_seconds`; AC2: `test_us003_repeat_does_not_overwrite`; AC3: `test_us003_hash_failure_blocks_sample`.
- `US-004` AC1: `test_us004_complete_common_endpoint_deltas`; AC2: `test_us004_added_missing_no_fake_percent`; AC3: `test_us004_invalid_baseline_blocks_recalculation`.
- `US-005` AC1: `test_us005_promotion_audit`; AC2: `test_us005_replacement_is_immutable`; AC3: `test_us005_ineligible_promotion_lists_prerequisites`.
- `US-006` AC1: `test_us006_canonical_hash_stability`; AC2: `test_us006_markdown_top_twenty`; AC3: `test_us006_atomic_export_failure`.

### Commands

Use repository-supported commands and add only declared tooling. On Linux/macOS:

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q tests/unit/test_run_import.py
.venv/bin/python -m pytest -q tests/unit/test_decision_artifact.py tests/test_cli_analyze.py
.venv/bin/python -m pytest -q tests/integration/test_run_import_flow.py tests/integration/test_baseline_decision_flow.py
.venv/bin/python -m pytest -q -m visual tests/visual/test_workspace_runs_e2e.py
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/pyright
.venv/bin/python -m build
```

After adding the mandated lab scripts, run from repository root:

```bash
bash scripts/tdd-gate-v3.sh
bash scripts/bdd-gate.sh
bash scripts/security-gate.sh
bash scripts/doc-sync-check.sh
bash scripts/ui-gate.sh
bash scripts/git-push-verify.sh
```

The development pass must add these scripts if absent, with deterministic non-interactive behavior and documentation. They may orchestrate existing pytest/Ruff/Pyright/build/browser/security checks but must not return unconditional success. `git-push-verify.sh` must verify clean worktree, current branch has upstream, local HEAD equals upstream HEAD after push, and required gates succeeded for the same commit.

Startup/package verification:

```bash
.venv/bin/python -m pip install build
.venv/bin/python -m build
python -m venv /tmp/lpk-wheel
/tmp/lpk-wheel/bin/python -m pip install dist/*.whl
LOCUST_WORKSPACE_DB=/tmp/lpk.db LOCUST_WORKSPACE_STORAGE_ROOT=/tmp/lpk-storage LOCUST_WORKSPACE_ALLOWED_ROOT="$PWD/tests/fixtures" /tmp/lpk-wheel/bin/locust-workspace --host 127.0.0.1 --port 8090
curl --fail --silent http://127.0.0.1:8090/healthz
```

Also build the Docker image, start it with mounted database/storage/allowed-root directories and required production secrets, and verify `/healthz`. No test, type, browser, security, or gate skip is accepted as complete.

### Coverage and objective pass/fail

Changed/new domain, import, artifact, route, and persistence modules require ≥90% statement and ≥85% branch coverage; `run_import.py` archive safety and `decision_artifact.py` canonicalization require ≥95% statement coverage. Full project test count must not decrease. Pass requires all acceptance tests, full suite, Ruff, Pyright, build/wheel install, CLI artifact smoke, workspace startup/health, Docker smoke, browser flows, accessibility criteria, six lab gates, and verified push. Any critical skipped test, unverified artifact hash, path escape, serious accessibility violation, or dirty/unpushed release commit is failure.

## Documentation Deliverables

The developer must update or create:

- `README.md`: a single recommended “Run to decision” quick start; ZIP requirements; Inbox/sample/import/compare/promote/export journey; local privacy statement; CLI artifact examples; startup variables; explicit non-goals.
- `CHANGELOG.md`: dated minor-release entry listing smart import, Inbox, baseline lifecycle, decision schema, CLI options, additive tables, security limits, compatibility, and only test totals actually observed.
- `docs/run-inbox-and-import.md`: archive limits/safety, file-role detection, grades, validation errors, storage lifecycle, routes, sample behavior, troubleshooting.
- `docs/baseline-decisions.md`: promotion rules, states, compatibility, delta rules, decision JSON schema, hash rules, Markdown ordering, CLI options/exit codes, examples.
- `docs/performance-workspace.md`: updated IA, startup, environment variables, local-only boundary, persistence/backup guidance, and production limitations.
- `docs/ci-cd-gates.md`: provider-neutral artifact generation and verification examples; no claim of automatic posting.
- `FEATURES-DONE.md`: completed outcomes only, exact routes/options/schema/tables/UI states/test evidence/limitations.
- `development-report.md`: executive summary; baseline; scope; files; schema; UI screenshots; RED/GREEN evidence; AC-to-tests matrix; targeted/full results; coverage; Ruff/Pyright/build/wheel/startup/Docker; accessibility; security; lab gate outputs; documentation verification; git commit/push/upstream equality; known limitations; artifact inventory; no weakened/skipped test declaration.

Every documented command must be executed against source or installed wheel and recorded. Documentation must not advertise deferred observability, collaboration, cloud execution, or security capabilities.

## Expected File Changes

Expected additions:

- `src/locust_templates/run_import.py`
- `src/locust_templates/analysis_service.py`
- `src/locust_templates/decision_artifact.py`
- `src/locust_templates/workspace_cli.py`
- optional `src/locust_templates/workspace_views.py`
- `src/locust_templates/static/workspace.js`
- bundled sample assets and manifest under package data
- new unit/integration/browser tests and narrowly scoped fixtures
- `docs/run-inbox-and-import.md`
- `docs/baseline-decisions.md`
- `development-report.md`
- `scripts/tdd-gate-v3.sh`, `bdd-gate.sh`, `security-gate.sh`, `doc-sync-check.sh`, `ui-gate.sh`, `git-push-verify.sh`

Expected modifications:

- `src/locust_templates/product_workspace.py`
- `src/locust_templates/workspace_api.py`
- `src/locust_templates/intelligence.py` and/or `evidence.py` only for additive provenance/serialization needs
- `src/locust_templates/cli_analyze.py`
- `src/locust_templates/__init__.py`
- `src/locust_templates/static/workspace.css`
- `pyproject.toml` package data, script, and dev tooling
- `Dockerfile`, `start.sh`, or deployment files only as required for one verified workspace startup contract
- `README.md`, `CHANGELOG.md`, `FEATURES-DONE.md`, and focused docs
- additive compatibility assertions in existing tests.

Unrelated Locust protocol templates, OpenAPI generator, notification providers, Grafana dashboards, and existing report formats must not change.

## Traceability Matrix

| Research need | Research evidence | User story id (US-xxx) | Planned requirement | Acceptance criterion | Planned implementation location | Planned test evidence | Priority |
|---|---|---|---|---|---|---|---|
| Remove path/naming friction | Locust exports file sets; current UI needs prefix knowledge | US-001 | A2–A6 safe upload, mapping, preview, commit | Valid 20 MB ZIP maps files and enables Analyze ≤10s | `run_import.py`, workspace routes/views | `test_us001_valid_zip_detects_and_enables_analysis` + live flow | P0 |
| Avoid ambiguous import | Multiple stats prefixes are realistic | US-001 | A4 candidate selection | Two candidates require explicit selection | importer/preview | `test_us001_multiple_candidates_require_selection` | P0 |
| Prevent archive/path harm | Local-first trust and privacy | US-001 | A3 archive policy | Traversal/missing stats rejected; no outside write | importer/security middleware | `test_us001_traversal_or_missing_stats_rejected` | P0 |
| Persist and find decisions | History/comparison requires external stack today | US-002 | A1 Inbox/filtering | Combined filters return only matches and count | persistence/routes/views | `test_us002_combined_filters` | P0 |
| Make missing metadata explicit | Imported runs can lack CI context | US-002 | A1 missing-metadata filter | Unlabelled branch excluded normally and discoverable explicitly | query repository | `test_us002_missing_metadata_filter` | P0 |
| Friendly recovery | Research UX baseline | US-002 | Inbox error/retry state | Read failure shows retry and no stale status | routes/views | `test_us002_index_failure_recovery_state`, E2E | P0 |
| First-use value without own files | Onboarding gap | US-003 | A7 verified bundled sample | Sample completes offline ≤5s | package sample/service | `test_us003_sample_offline_under_five_seconds` | P0 |
| Preserve user data | Trust requirement | US-003 | Repeat sample is idempotent/copy-safe | No overwrite on repeat | sample service/persistence | `test_us003_repeat_does_not_overwrite` | P0 |
| Verified sample provenance | Evidence integrity differentiation | US-003 | Sample hash manifest | Invalid sample hash blocks analysis | sample manifest/service | `test_us003_hash_failure_blocks_sample` | P0 |
| Explain what changed | Reports/observations are hardest; comparison is paid value | US-004 | B2–B5 comparison/detail/evidence | Complete common endpoint deltas with exact values | comparison service/views | `test_us004_complete_common_endpoint_deltas` + E2E | P0 |
| Avoid fabricated math | Trust and data-quality guardrail | US-004 | B3 added/missing/zero rules | Added/Missing have no fake percentage | comparison service | `test_us004_added_missing_no_fake_percent` | P0 |
| Reject invalid evidence | Deterministic auditability | US-004 | Hash/schema compatibility | Invalid baseline blocks recalculation | evidence verifier/service | `test_us004_invalid_baseline_blocks_recalculation` | P0 |
| Establish explicit approved reference | Teams need environment baselines | US-005 | B6 promotion transaction/audit | PASS promotion records old/new/reason/actor/time | persistence/routes | `test_us005_promotion_audit` | P0 |
| Preserve historical audit | Release governance | US-005 | B6/B7 immutable history | Prior baseline SUPERSEDED, not overwritten | baseline repository | `test_us005_replacement_is_immutable` | P0 |
| Block unsafe baseline | Trust risk | US-005 | Eligibility rules | FAIL/invalid evidence blocked with prerequisites | promotion service/views | `test_us005_ineligible_promotion_lists_prerequisites` | P0 |
| Reproducible CI evidence | Commercial tools monetize analysis; users need portable decisions | US-006 | B8 canonical JSON/hash | Identical hash input produces byte-identical canonical content/hash | `decision_artifact.py`, CLI/routes | `test_us006_canonical_hash_stability` | P0 |
| Concise PR review | CI owner needs readable summary | US-006 | B9 deterministic top 20 | Top 20 shown; complete JSON referenced | artifact renderer | `test_us006_markdown_top_twenty` | P0 |
| Never publish partial artifact | Audit reliability | US-006 | B10 atomic output | Existing destination preserved on write failure | artifact writer/CLI | `test_us006_atomic_export_failure` | P0 |
| Preserve existing users | Project constraint | US-001–US-006 | Additive routes/tables/CLI | Existing full suite and APIs remain green | all touched modules | compatibility and full regression | P0 |
| Accessible product UI | Modern UX research baseline | US-001–US-006 | Screen specs/global rules | Zero serious/critical; keyboard/320px/200% pass | views/CSS/JS | browser + accessibility + screenshots | P0 |
| Lab governance | Mandatory lab policy | US-001–US-006 | Six real gate scripts and verified push | All gates run against pushed HEAD | `scripts/`, development report | gate logs + upstream equality | P0 |

## Risks and Mitigations

- **ZIP-bomb/path escape:** inventory before extraction, strict member/count/size/ratio limits, resolved containment, malicious fixture tests.
- **Scope expansion into orchestration:** enforce explicit non-goals and accept only existing run evidence.
- **Schema drift:** version canonical decision and persisted report; compatibility tests; no silent schema-major coercion.
- **False causal interpretation:** finding classes, non-causal language tests, exact next check, visible confidence/quality.
- **SQLite concurrency:** short transactions, foreign keys, unique active-baseline index, concurrency test, WAL only if verified across deployment.
- **Sensitive data leakage:** no raw download, role-limited evidence, safe labels, absolute-path/sentinel scans in HTML/JSON/Markdown/logs.
- **Import storage leakage:** single-use sessions, expiry cleanup, orphan cleanup transaction, owner-only permissions, quota limits.
- **UI test brittleness:** semantic selectors and state assertions; screenshots for audit, not pixel-only gates.
- **Dependency bloat:** server rendering and inline SVG preferred; dev-only browser tooling; no new runtime dependency without recorded justification.
- **Performance on large archives:** streamed upload/copy/hash, bounded parsing, configurable limits, real 20 MiB integration test.
- **Baseline misuse:** eligibility rules, advisory override friction, immutable history, explicit current active baseline.
- **Documentation drift:** `doc-sync-check.sh` validates route/option/schema strings and every example is executed.
- **Gate scripts becoming facades:** scripts must execute tools, propagate failures, log commit SHA, and are directly tested where practical.
- **Git push unavailable:** development phase is incomplete until upstream equality is verified; report blocker rather than claiming done.

## Definition of Done

- [ ] Feature A and Feature B are complete end to end with no production placeholder, facade, fake result, or unconditional success.
- [ ] All six embedded BDD stories retain their IDs and every acceptance criterion has named passing test evidence.
- [ ] Empty Inbox → ZIP validation → preview → analyze → persisted Run Detail → exports works against real Locust fixtures.
- [ ] Healthy run → baseline promotion → replacement history → future default selection works transactionally.
- [ ] Valid, ambiguous, missing-stats, traversal, symlink, duplicate-path, compression-limit, malformed, changed-evidence, and expired-session cases are covered.
- [ ] PASS, FAIL, ADVISORY, ERROR, grade A/B/C, no-baseline, incompatible-baseline, no-overlap, and export-error UI states work.
- [ ] Every displayed finding has rule/version, class, confidence, supporting values, logical locator, input hash, and next check.
- [ ] Every JSON/Markdown artifact independently verifies its decision hash and contains no absolute paths or sentinel secrets.
- [ ] Existing CLI output and 0/1/2 semantics remain; exit 2 still writes requested decision artifacts.
- [ ] Existing public APIs, routes, SQLite data, report formats, and full regression tests remain compatible.
- [ ] Targeted tests and complete `pytest` regression pass with no weakened, deleted, or critical skipped tests.
- [ ] Changed/new modules meet ≥90% statement and ≥85% branch coverage; importer/artifact modules meet ≥95% statement coverage.
- [ ] Ruff, Pyright, package build, clean wheel install, CLI smoke, workspace startup, `/healthz`, and Docker smoke pass.
- [ ] Browser E2E passes at 360×800, 768×1024, and 1440×900; required screenshots are recorded when tooling permits.
- [ ] Automated accessibility scans show zero serious/critical issues; keyboard, focus, 200% zoom, reduced motion, and screen-reader smoke are recorded.
- [ ] CSRF/session behavior, root confinement, ZIP limits, escaping, security headers, no outbound access, atomic writes, and logging redaction pass tests.
- [ ] `README.md`, `CHANGELOG.md`, API/CLI/workspace docs, `FEATURES-DONE.md`, and `development-report.md` match verified behavior.
- [ ] `scripts/tdd-gate-v3.sh`, `bdd-gate.sh`, `security-gate.sh`, `doc-sync-check.sh`, and `ui-gate.sh` all pass against the release commit.
- [ ] No secrets, virtual environments, caches, coverage files, build outputs, temporary uploads/databases, downloaded browser binaries, or scratch artifacts are committed.
- [ ] Requirement → story → implementation → test → documentation traceability is complete in `development-report.md`.
- [ ] Changes are committed and pushed; `scripts/git-push-verify.sh` confirms a clean worktree and local HEAD equals upstream HEAD.
- [ ] The complete project is packaged with no extra enclosing directory, ZIP integrity-tested, listed, separately extracted, and required files verified.
