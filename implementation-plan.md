# Implementation Plan

## Executive Summary

This pass is a **completion and release-hardening pass** for the partially implemented Campaign Trust and Verification scope. It selects two coherent features:

1. **Complete Offline Verification Journey**: connect persisted Run Detail evidence to deterministic bundle export, add safe short-lived verification sessions, reproduce decisions from packaged current/baseline sources, expose MATCH/DRIFT/UNREPRODUCIBLE in UI and CLI, and cover the complete archive attack matrix.
2. **Complete Release Campaign Workflow**: add multi-slot draft creation and editing, optimistic concurrency, policy/baseline/freshness drill-down, immutable finalization, and atomic persisted campaign artifacts.

The pass also closes release blockers directly associated with these features: ≥90% coverage on all changed modules, green supported repository gates, build/install/startup verification, executable browser/axe/screenshot flows, and truthful Git/push handling. It does not add digital signatures, observability integrations, collaboration, hosted execution, or new dependencies.

## Current-State Validation

The research remains aligned with the project: the durable product wedge is a local-first, auditable run-to-decision layer for Locust teams. The supplied tree now contains partial implementations of the two previously planned P0 areas:

- `src/locust_templates/verification_bundle.py` creates deterministic ZIPs, validates archive membership and hashes, verifies `performance-decision/v1`, extracts validated bundles, and computes JSON-pointer differences.
- `src/locust_templates/campaigns.py` computes campaign readiness, policy identity, baseline identity, 30-day freshness, drift, and Markdown.
- `product_workspace.py` has additive `campaigns` and `campaign_slots` persistence plus create/read/list/finalize methods.
- `workspace_api.py` and `workspace_views.py` expose basic Verify, Campaign List, New Campaign, Campaign Detail, finalization, and export routes.
- `cli_analyze.py` has a basic `locust-kit verify` command.
- Focused tests pass, but `development-report.md` records incomplete Run Detail export, no reproduction, request-only verification, single-slot UI, no edit/concurrency, no persisted atomic artifacts, incomplete attack coverage, 83% verification-module coverage, failed full regression/gates, and no browser screenshots.

The existing implementation must be extended rather than replaced. Existing bundle and campaign schemas remain v1 unless a backward-compatible optional field is added. No current public route, CLI option, decision hash, or database record may be removed.

## Research Priorities

Research-ranked candidates are:

1. Reproducible decision integrity and one-command revalidation.
2. Release campaigns, policy drift, baseline drift, and baseline freshness.
3. Release-trust closure through real tests, browser evidence, packaging, and consistent documentation.
4. Digital signatures and key management.
5. Prometheus and OTel evidence attachments.
6. Multi-user/team packaging and commercial validation.

Items 1 through 3 form the selected completion scope. Items 4 through 6 remain deferred because they add key management, outbound security, identity, or commercial risk before the current P0 workflow is complete.

## Selected Scope for This Pass

### Feature A: Complete Offline Verification Journey

Finalize US-001 through US-003. A persisted non-sample run can generate and download a deterministic source-backed verification ZIP. A reviewer can upload it, receive exact integrity results, reproduce its recorded decision in an isolated temporary workspace, inspect canonical differences, and download `verification-result/v1` JSON. CLI behavior matches the UI.

### Feature B: Complete Release Campaign Workflow

Finalize US-004 through US-006. A user can create and edit a draft with multiple required environment/scenario slots, select only eligible runs, detect concurrent changes, inspect exact drift/freshness evidence, finalize an immutable snapshot, and download atomically persisted canonical JSON/Markdown artifacts.

### Release closure

All directly affected tests, gates, docs, package/startup checks, browser checks, and screenshots must be completed. Missing legacy workflow assets that are required by existing tests must be restored from documented project behavior if absent, without redesigning unrelated CI functionality.

## Deferred Scope and Rationale

1. **Digital signatures**: future security phase after reproducibility is complete. Requires key provider, rotation, revocation, trust store, and signature-format decisions.
2. **Prometheus adapter**: future observability-security phase. Requires SSRF-safe allowlists, credential handling, bounded queries, and redaction.
3. **OTel exemplars**: follows the metric-adapter provenance and privacy model.
4. **RBAC, SSO, comments, and approvals**: future team-security phase; current product remains local/single-operator.
5. **Hosted load generation, billing, browser recording, and broad scenario authoring**: deferred pending paid design-partner validation.
6. **Configurable baseline-freshness policy**: v1 remains fixed at 30 days to avoid policy-surface expansion.

## User Stories (BDD)

```json
[
  {
    "id": "US-001",
    "epic": "Complete Offline Verification Journey",
    "role": "CI owner",
    "action": "export a deterministic verification bundle from a persisted Run Detail",
    "benefit": "the exact decision, policy, provenance, and source evidence can be reviewed elsewhere",
    "story": "As a CI owner, I want to export a deterministic verification bundle from a persisted Run Detail, so that the exact decision, policy, provenance, and source evidence can be reviewed elsewhere.",
    "gui_flow": [
      "User opens a non-sample Run Detail → Verify and reproduce card shows source count and eligibility",
      "User clicks Generate verification bundle → button becomes disabled and status announces generation",
      "Service re-hashes every managed source → progress text reports validation without exposing paths",
      "Generation succeeds → bundle schema, SHA-256, byte size, and file count appear",
      "User clicks Download ZIP → <run-id>-verification.zip downloads with no navigation",
      "User refreshes Run Detail → existing verified artifact metadata and Download ZIP remain visible"
    ],
    "acceptance_criteria": [
      {"type":"given","text":"a persisted non-sample run with current and optional baseline input records whose bytes match stored hashes","when":"bundle generation completes","then":"the persisted artifact contains decision.json, summary.md, policy.json, provenance.json, manifest.json, every current source, and every recorded baseline source"},
      {"type":"given","text":"the same unchanged run and source records","when":"bundle generation is requested twice","then":"the complete ZIP bytes, SHA-256, member order, timestamps, and manifest identity are identical"},
      {"type":"given","text":"a source is missing, outside managed storage, or hash-mismatched","when":"generation is requested","then":"BUNDLE_SOURCE_MISMATCH is shown, no new final artifact is committed, and a prior valid artifact remains byte-identical"}
    ]
  },
  {
    "id": "US-002",
    "epic": "Complete Offline Verification Journey",
    "role": "release reviewer",
    "action": "verify an uploaded bundle against the full archive and manifest security contract",
    "benefit": "corruption and malicious archive structures are rejected before evidence is trusted",
    "story": "As a release reviewer, I want to verify an uploaded bundle against the full archive and manifest security contract, so that corruption and malicious archive structures are rejected before evidence is trusted.",
    "gui_flow": [
      "User opens Verify bundle → local-only statement and ZIP limits are visible",
      "User selects a ZIP → safe filename and size appear and Verify becomes enabled",
      "User clicks Verify bundle → upload is streamed to owner-only staging and status is announced",
      "Verifier checks archive, exact members, manifest, hashes, schemas, and decision → check table appears",
      "Valid result enables Reproduce decision and Download verification JSON",
      "User clicks Verify another → staging is deleted, form resets, and focus returns to the picker"
    ],
    "acceptance_criteria": [
      {"type":"given","text":"a valid performance-verification-bundle/v1 ZIP","when":"verification completes","then":"status is VALID and archive, exact-member, manifest-identity, byte-size, hash, decision, policy, provenance, and source checks report PASS"},
      {"type":"given","text":"a valid-manifest archive using an unsupported verification schema","when":"verification completes","then":"status is UNSUPPORTED, confirmed integrity checks remain visible, reproduction is disabled, and exit code is 1"},
      {"type":"given","text":"an archive with traversal, absolute or drive path, backslash path, symlink, special file, encryption, duplicate normalized or case-folded name, control character, CRC error, compressed/expanded/member/ratio limit breach, missing member, extra member, size mismatch, or hash mismatch","when":"verification runs","then":"status is INVALID, the stable rule code and safe member label are shown, no extraction is committed, and staging is removed after expiry or reset"}
    ]
  },
  {
    "id": "US-003",
    "epic": "Complete Offline Verification Journey",
    "role": "automation engineer",
    "action": "reproduce a verified decision offline in UI or CLI",
    "benefit": "I can distinguish an exact match from policy, analyzer, or evidence drift",
    "story": "As an automation engineer, I want to reproduce a verified decision offline in UI or CLI, so that I can distinguish an exact match from policy, analyzer, or evidence drift.",
    "gui_flow": [
      "User verifies a valid bundle → Reproduce decision becomes enabled for 15 minutes",
      "User clicks Reproduce decision → isolated extraction and deterministic analysis begin",
      "Current and optional baseline prefixes plus packaged SLO policy are reconstructed → status is announced",
      "Canonical recorded and regenerated decisions are compared → MATCH, DRIFT, or UNREPRODUCIBLE is displayed",
      "User expands Differences → sorted JSON-pointer paths and recorded/regenerated values appear",
      "User downloads verification JSON → result includes identities, differences, stable error code, and exit code"
    ],
    "acceptance_criteria": [
      {"type":"given","text":"valid complete sources, supported analyzer contract, and unchanged policy","when":"reproduction runs","then":"status is MATCH, canonical hashes match, differences is empty, and UI/CLI exit code is 0"},
      {"type":"given","text":"an integrity-valid bundle whose policy or recorded decision differs from regenerated output","when":"reproduction runs","then":"status is DRIFT, differences are lexically sorted JSON-pointer records including exact changed values, and exit code is 1"},
      {"type":"given","text":"an expired session, unsupported analyzer schema, missing required source role, or parse failure","when":"reproduction is requested","then":"status is UNREPRODUCIBLE, no decision is guessed, exit code is 1, temporary contents are removed, and the user receives a verify-again recovery action"}
    ]
  },
  {
    "id": "US-004",
    "epic": "Complete Release Campaign Workflow",
    "role": "performance engineer",
    "action": "create and edit a draft containing multiple required release slots",
    "benefit": "release completeness is evaluated across all required environments and scenarios",
    "story": "As a performance engineer, I want to create and edit a draft containing multiple required release slots, so that release completeness is evaluated across all required environments and scenarios.",
    "gui_flow": [
      "User opens Campaigns and clicks New campaign → identity form starts with one required slot",
      "User clicks Add required slot twice → three independently labeled slot rows appear",
      "User enters environment and scenario for each slot → eligible run choices update per row",
      "User selects runs and clicks Save draft → one transaction persists campaign and ordered slots",
      "Campaign Detail opens → readiness, filled count, missing slots, and drift summary appear",
      "User clicks Edit campaign → existing values load and successful save returns to preserved detail context"
    ],
    "acceptance_criteria": [
      {"type":"given","text":"a unique label and one to twenty unique required environment/scenario pairs","when":"a draft is saved","then":"the campaign and every ordered slot commit atomically and Campaign Detail lists each pair exactly once"},
      {"type":"given","text":"a slot is empty, duplicated case-insensitively, or selects a sample/ineligible/mismatched-environment run","when":"the form is submitted","then":"HTTP 422 returns an error summary linked to each invalid row and no partial database change occurs"},
      {"type":"given","text":"two edit forms share the same updated token and one saves first","when":"the second submits","then":"HTTP 409 CAMPAIGN_CHANGED preserves submitted values and offers Reload latest without overwriting the first change"}
    ]
  },
  {
    "id": "US-005",
    "epic": "Complete Release Campaign Workflow",
    "role": "platform lead",
    "action": "inspect exact policy, baseline, and freshness drift before finalization",
    "benefit": "a release cannot appear healthier because its evidence or rules silently changed",
    "story": "As a platform lead, I want to inspect exact policy, baseline, and freshness drift before finalization, so that a release cannot appear healthier because its evidence or rules silently changed.",
    "gui_flow": [
      "User opens Campaign Detail → readiness and drift counts appear above the slot table",
      "User selects Policy, Baseline, or Freshness filter → only matching drift records remain and count is announced",
      "User expands a policy event → exact differing schema, analyzer, SLO, or quality-rule fields appear",
      "User expands a baseline event → baseline IDs, promotion times, age, and 30-day threshold appear",
      "User follows a run link → Run Detail includes Back to campaign",
      "User returns → selected drift filter and focus target are restored from query parameters"
    ],
    "acceptance_criteria": [
      {"type":"given","text":"selected runs have different decision schema, analyzer version, SLO map, or quality-rules version","when":"detail is calculated","then":"POLICY_DRIFT lists affected run IDs and exact differing fields without exposing absolute paths"},
      {"type":"given","text":"runs in the same environment reference different baselines or a baseline age is greater than 30 days","when":"detail is calculated","then":"BASELINE_DRIFT or BASELINE_STALE is shown and readiness is ADVISORY unless FAIL or INCOMPLETE has precedence"},
      {"type":"given","text":"a referenced run, baseline, promotion timestamp, or policy field is missing","when":"detail loads","then":"the affected slot is UNKNOWN, readiness is INCOMPLETE, finalization is disabled, and no identity or metric is fabricated"}
    ]
  },
  {
    "id": "US-006",
    "epic": "Complete Release Campaign Workflow",
    "role": "release manager",
    "action": "finalize an immutable campaign and export atomic canonical artifacts",
    "benefit": "approvers receive one stable release-readiness record",
    "story": "As a release manager, I want to finalize an immutable campaign and export atomic canonical artifacts, so that approvers receive one stable release-readiness record.",
    "gui_flow": [
      "User opens a complete draft → Finalize campaign is enabled and preview lists readiness consequences",
      "User clicks Finalize campaign → accessible confirmation states that slots become immutable",
      "User confirms → readiness recalculates in the transaction and immutable projection is stored",
      "Campaign Detail reloads → Edit is absent and JSON/Markdown export actions appear",
      "User downloads both formats → filenames, byte sizes, hashes, and audit events are listed",
      "User revisits after active-baseline changes → finalized readiness and campaign identity remain unchanged"
    ],
    "acceptance_criteria": [
      {"type":"given","text":"every required slot references a valid persisted run","when":"finalization succeeds","then":"state becomes FINALIZED, one immutable canonical projection is stored, later edits return CAMPAIGN_FINALIZED, and active-baseline changes do not mutate it"},
      {"type":"given","text":"a finalized campaign is exported repeatedly without record changes","when":"JSON and Markdown are generated","then":"each format is byte-identical across runs, both contain the same readiness/slots/drift/campaign hash, and artifact metadata matches actual bytes"},
      {"type":"given","text":"artifact writing or metadata persistence fails","when":"export is requested","then":"temporary files are removed, an existing valid artifact is not overwritten, CAMPAIGN_EXPORT_FAILED is returned, and no success audit event is written"}
    ]
  }
]
```

## Product Requirements

### Feature A requirements

**Evidence addressed**: research P0 reproducibility, local-first trust, safe import, deterministic CI artifacts, and the documented partial implementation gaps.

**Inputs**:

- persisted non-sample `analysis_runs`, `analysis_inputs`, optional `baseline_run_id`, and managed source bytes;
- `performance-decision/v1` report and SLO policy;
- uploaded bundle with compressed size ≤100 MiB, expanded size ≤500 MiB, ≤2,000 members, and per-member ratio ≤100:1;
- CLI path to a bundle.

**Outputs**:

- deterministic `performance-verification-bundle/v1` ZIP persisted under managed artifacts;
- `verification-result/v1` with `VALID|UNSUPPORTED|INVALID|MATCH|DRIFT|UNREPRODUCIBLE`, checks, files, identities, differences, error code/member, and exit code;
- HTML result and JSON download;
- CLI text/JSON output.

**Rules**:

- bundle members, timestamps, permissions, compression settings, JSON bytes, and member order are deterministic;
- source roles explicitly map current and baseline stats/history/failures/exceptions to reconstructable `run_*` prefixes;
- pre-export re-hashing is mandatory and confined to managed storage;
- exact-member validation rejects both missing and extra entries;
- central-directory validation precedes extraction/body processing;
- VALID session metadata stores only token digest, staging-relative path, safe filename, result JSON, state, created, and 15-minute expiry;
- reproduction consumes or expires the session and always removes staging in `finally`;
- canonical comparison excludes only documented generated timestamps and host paths, never metrics, policy, quality, findings, or identities;
- CLI adds `--reproduce` and maintains existing `locust-kit analyze` behavior;
- exit 0 means VALID without reproduction or MATCH with reproduction; every other result is 1.

**Failure behavior**: stable codes, no stack traces, no partial artifacts, prior artifact preserved, request/body limits enforced before unbounded reads, cleanup after reset/expiry/use.

**Compatibility**: preserve `performance-decision/v1`, existing basic `verify` syntax, existing evidence bundles, and all analyze exit codes. Accept the current partial v1 bundle if it already contains sufficient role data; otherwise report UNREPRODUCIBLE rather than INVALID.

**Non-goals**: digital signatures, remote verifier, signer identity, network calls, automatic repair, or retention beyond managed run artifacts and 15-minute sessions.

### Feature B requirements

**Evidence addressed**: research validation of campaigns/history as paid differentiators, immutable baselines, and the documented single-slot/concurrency/artifact gaps.

**Inputs**:

- campaign label 1–120 characters, description ≤1,000 characters;
- 1–20 unique slots, each environment/scenario 1–80 characters;
- eligible non-sample `performance-decision/v1` runs;
- hidden `updated` token for edits.

**Outputs**:

- persisted DRAFT or FINALIZED campaign;
- deterministic readiness and drift projection;
- atomically persisted `performance-campaign/v1` JSON and Markdown;
- audit records for create, edit, finalize, successful export, and failures without secrets/content.

**Rules**:

- readiness precedence is FAIL, INCOMPLETE, ADVISORY, PASS;
- run must match slot environment; scenario is taken from `scenario:<name>` tag or `unspecified`;
- duplicate slot comparison is Unicode case-folded after trimming;
- draft edits replace slot set transactionally while preserving campaign ID and created time;
- optimistic concurrency compares exact persisted `updated` numeric token;
- policy identity covers decision schema, analyzer name/version, sorted SLO map, and quality-rules version;
- baseline identity prefers stored baseline run ID; fallback uses label plus sorted input hashes;
- age `>30 days` is STALE; exactly 30 days is ACTIVE; missing time is UNKNOWN;
- FINALIZED stores canonical projection and is immutable;
- atomic export uses `atomic_write`, deterministic bytes, managed relative path, SHA-256, size, schema, and audit.

**Failure behavior**: 422 validation with per-row errors, 409 concurrency/finalized/incomplete, 404 missing campaign, 503 unavailable storage, no partial rows/artifacts.

**Compatibility**: additive migrations only. Migrate existing partial campaign rows without loss; their missing fields receive safe defaults. Existing Run/Baseline routes and legacy workspace remain.

**Non-goals**: approvals, comments, notifications, arbitrary campaign policy DSL, scheduling, multi-user identity, or campaign CLI.

## UI and UX Specification

### Personas and journey

Primary personas are CI owner, release reviewer, performance engineer, platform lead, and release manager. Golden path: Run Detail → Generate bundle → Verify → Reproduce MATCH → Campaigns → New campaign with multiple slots → inspect drift → finalize → export readiness.

### Information architecture

Primary navigation order: Runs, Campaigns, Baselines, Verify bundle. Existing secondary workflows remain available under existing navigation without a frontend rewrite. `aria-current="page"` is exact. Mobile navigation scrolls horizontally with visible labels.

### Design system

Retain server-rendered Flask views and packaged CSS/JavaScript. No React, Tailwind, Bootstrap, bundler, or runtime dependency. Consolidate reusable helpers for breadcrumbs, alerts, badges, tables, empty states, action bars, field errors, progress, disclosure, and confirmation dialog.

Tokens remain CSS custom properties: 4/8/12/16/24/32/48 px spacing, 8 px controls, 12 px cards, 999 px pills, 1,200 px shell, 720 px prose, 16 px body with 1.5 line-height, 44 px minimum controls, 3 px visible focus, text contrast ≥4.5:1, non-color status labels, and reduced-motion overrides.

Breakpoints: mobile 0–767, tablet 768–1023, desktop ≥1024. Mobile uses one column and sticky form action bar; tablet may use two columns; desktop uses 8/4 main/asides. Tables use labeled overflow container plus complete semantic table.

All forms implement idle, client-invalid, server-invalid, submitting (`aria-busy` and changed label), conflict, success, and recovery states. Server validation preserves values. Error summary receives focus. Successful result heading receives focus. No fake percentage or unnecessary skeleton is used for local server renders.

## Screen Inventory and User Flows

### 1. Run Detail verification card

Placed after decision identity. Left: `Verify this decision`, local-only explanation, schema, source count, baseline inclusion. Right: primary `Generate verification bundle`, secondary `Open bundle verifier`. Ineligible sample/missing-source state shows exact disabled reason. Generating state disables button. Success shows short/full hash, size, file count, generated time, and `Download ZIP`. Source mismatch shows `Evidence changed` and `Re-import run`.

### 2. Verify Bundle

Breadcrumb, H1, local-only trust message, ZIP picker, 100 MiB limit, selected safe name/size, primary `Verify bundle`, and “What is checked” disclosure. Results show VALID/UNSUPPORTED/INVALID banner, check summary, full file table, safe rule/member diagnostics, `Reproduce decision` only for VALID, `Download verification JSON`, and `Verify another`. Reset deletes session and returns focus to picker.

### 3. Reproduction Result

Validated-bundle summary, `Reproducing decision…` live status, MATCH/DRIFT/UNREPRODUCIBLE banner, recorded/regenerated hash cards, sorted differences table, escaped values with disclosure for values >240 characters, exit-code explanation, JSON download, and verify-again action. Expired session directs to re-upload.

### 4. Campaign List

H1, explanation, `New campaign`, filters for query/state/readiness, Apply/Clear, deterministic updated-descending rows showing state, readiness, filled/required, drift, and update time. First-use empty state explains slots; filtered empty state offers Clear; storage failure has Retry.

### 5. New/Edit Campaign

Campaign identity section and repeatable Required slots section. Each row has numbered legend, Environment, Scenario, Selected run, eligibility facts, and `Remove slot`. `Add required slot` appends up to 20. Save Draft/Cancel action bar. Edit includes concurrency token. Invalid rows have linked errors; no eligible runs gives import/tag guidance. Finalized campaign has no edit action or editable route.

### 6. Campaign Detail

Breadcrumb, label, state, readiness, campaign hash, updated/finalized times; actions based on state. Summary cards show required/filled/PASS/FAIL/ADVISORY/UNKNOWN. Slot table includes run, quality, policy short hash, baseline, age/freshness, and status. Drift filters use query parameters. Expandable drift events show exact fields/identities. Run links include `return_to` campaign URL. Audit disclosure lists event types and timestamps only.

### 7. Finalization confirmation

Native `<dialog>` with accessible fallback. It names readiness, missing blockers, immutability, and export consequences. `Finalize campaign` and `Keep editing`. Disabled when incomplete/unknown. Success redirects to `#campaign-status` and focuses status.

### 8. Artifact download state

Finalized detail shows JSON and Markdown actions plus metadata table. Download endpoints return attachment/no-store. Draft export returns 409 recovery page. Export failure shows retry and guarantees prior artifact preservation.

### End-to-end flows

Success: Run Detail → generate/download → Verify VALID → Reproduce MATCH → Campaigns → New → add three slots → save → inspect no drift → finalize PASS → export JSON/Markdown.

Failure recovery: upload tampered bundle → INVALID/HASH_MISMATCH → Verify another → valid upload → VALID; separately, stale campaign edit → CAMPAIGN_CHANGED → Reload latest → reapply change.

## Architecture and Technical Design

### Boundaries

- `verification_bundle.py`: deterministic format, inventory, verification, extraction, role reconstruction, canonical diff, reproduction result. Pure domain/I/O, no Flask/SQLite.
- `campaigns.py`: identities, drift, readiness, canonical projection, JSON/Markdown bytes. Pure domain.
- `product_workspace.py`: additive migrations, verification sessions, bundle/campaign artifact metadata, transactional CRUD/concurrency/finalization.
- `workspace_views.py`: pure escaped HTML helpers/screens.
- `workspace_api.py`: validation, CSRF, streaming uploads, orchestration, status mapping, downloads, cleanup.
- `cli_analyze.py`: verify/reproduce automation only.
- `run_import.py`: shared archive-security primitives; no duplicate implementation.
- `decision_artifact.py`: expose canonical payload helper only if byte-compatibility tests prove no v1 change.

### Data flows

Export: Run Detail POST → load run/input records → confine/re-hash sources → build deterministic ZIP → atomic managed write → artifact metadata/audit transaction → redirect to detail.

Verify: bounded streamed upload → random owner-only staging → inventory/verify → verification session token digest + result/expiry → render. Reset/expiry/use removes file and row.

Reproduce: consume valid session → safe extraction → map role files to current/baseline prefixes → `analyze_decision` with packaged policy → canonical diff → result JSON → cleanup.

Campaign: form → validate/eligibility → transaction inserts/replaces slots with optimistic token → calculate projection. Finalize recalculates inside write transaction and stores immutable JSON/hash. Export produces deterministic bytes and atomically updates artifact metadata.

### Error/logging

Stable codes already defined remain. Add `VERIFICATION_SESSION_EXPIRED`, `VERIFICATION_SESSION_INVALID`, `CAMPAIGN_SLOT_INELIGIBLE`, and `CAMPAIGN_STORAGE_UNAVAILABLE`. Log correlation ID, operation, schema, counts, size, short hash, and code only. Never log source contents, secrets, absolute paths, full uploaded names, or full hashes at warning/error levels.

### Alternatives rejected

- No reimplementation around a SPA: existing Flask stack is sufficient and lower risk.
- No in-memory session map: not restart-safe and leaks staging lifecycle.
- No database BLOB artifacts: managed files plus transactional metadata preserve atomicity and database size.
- No signature library: deferred by scope.

## Data, API, and Compatibility Changes

### Schema

Add/migrate:

- `verification_sessions(id, token_digest UNIQUE, staging_relative_path, original_safe_name, result_json, state, expires, created)`;
- extend or rebuild additively through migration helper campaign fields required by the plan: `policy_hash`, `campaign_hash`, `finalized_json`, timestamps;
- `campaign_artifacts(id, campaign_id, kind, schema, sha256, size, relative_path, created, UNIQUE(campaign_id,kind))`;
- ensure `campaign_slots` includes ordinal and unique campaign/environment/scenario.

Because SQLite lacks convenient `ADD COLUMN IF NOT EXISTS`, implement a versioned `_migrate()` using `PRAGMA table_info`, additive `ALTER TABLE` only where missing, and one transaction. Enable foreign keys on every connection. Preserve current partial records.

### Web API/routes

- `POST /workspace/runs/<run_id>/verification-bundle`
- `GET /workspace/runs/<run_id>/verification.zip`
- `GET|POST /workspace/verify`
- `POST /workspace/verify/reset`
- `POST /workspace/verify/reproduce`
- `GET /workspace/verify/<session_id>/result.json`
- `GET /workspace/campaigns`
- `GET|POST /workspace/campaigns/new`
- `GET|POST /workspace/campaigns/<id>/edit`
- `GET /workspace/campaigns/<id>`
- `POST /workspace/campaigns/<id>/finalize`
- `GET /workspace/campaigns/<id>/readiness.json`
- `GET /workspace/campaigns/<id>/summary.md`

HTML success uses 303. Validation 422, conflicts/expired 409, too large 413, not found 404, storage unavailable 503. Downloads use attachment and no-store.

### CLI

`locust-kit verify BUNDLE [--reproduce] [--format json|text] [--output PATH|-]`. Maintain basic verify behavior. Text output includes status and error/difference count. JSON is `verification-result/v1`. No campaign CLI.

### CSRF and compatibility

Apply double-submit CSRF to all browser state-changing forms, including existing import/baseline/sample forms. Cookie is random, `SameSite=Strict`, `Secure` in production, not HttpOnly because form bootstrapping uses it, and constant-time compared. API-key JSON/CLI routes remain exempt. Tests receive a helper to fetch and submit tokens. Existing GET routes and CLI behavior remain.

## Security and Privacy Considerations

- No outbound network in selected flows.
- Stream and bound uploads; never unbounded-read user input.
- Reuse one archive-security implementation and test every listed attack.
- Stage under configured storage with random names, `0700` directories and `0600` files where supported.
- Token values are never stored, only SHA-256 digest; compare in constant time.
- Cleanup expired sessions at app startup and before verify operations, with a bounded query.
- Confine all persisted artifact paths to managed storage and reject symlink escapes.
- Escape all labels, member names, diff values, and errors.
- Use no-store and attachment headers.
- Do not claim signatures, identity, non-repudiation, causality, or multi-user authorization.
- Add security regression for secret/path absence in logs and artifacts.

## Test Strategy (TDD)

### RED sequence

1. Add `test_us_001_*` export/artifact tests and run red.
2. Add full `test_us_002_*` archive matrix and session lifecycle tests and run red.
3. Add real-I/O `test_us_003_*` reproduction/CLI tests and run red.
4. Add `test_us_004_*` multi-slot/edit/concurrency tests and run red.
5. Add `test_us_005_*` exact drift/freshness/missing-reference tests and run red.
6. Add `test_us_006_*` finalization/atomic export tests and run red.
7. Implement, refactor, run affected groups after each story, then full suite/gates.

### Feature A tests

Unit: deterministic complete ZIP; role map; source confinement; source mismatch; exact membership; every archive attack; session TTL; canonical exclusions; JSON-pointer order; status/exit precedence.

Integration: persist real run_a/run_b inputs; Run Detail export; verify; reproduce MATCH; integrity-valid policy mutation gives DRIFT; missing history gives UNREPRODUCIBLE; prior artifact survives injected write failure; CLI JSON/text/file/exit behavior.

Browser: export from Run Detail; valid verify; MATCH; tampered INVALID recovery; expired session recovery; keyboard/file reset; axe; 360/768/1440 screenshots for empty, VALID, INVALID, and DRIFT.

### Feature B tests

Unit: 1/20/21 slot boundaries; Unicode case-fold duplicates; eligibility; readiness precedence; policy field-level differences; same-environment baseline drift; 30-day exact boundary; UNKNOWN behavior; canonical byte stability.

Integration: populated DB migration; create/update rollback; multi-slot ordering; optimistic 409; immutable finalization; active baseline change does not mutate snapshot; atomic export and metadata/audit; CSS/HTML escaping.

Browser: empty Campaigns; add/remove three slots; validation summary; edit conflict; drift filters; incomplete finalization disabled; finalize/export; keyboard dialog/fallback; axe and screenshots at required widths.

### Commands

Supported commands:

```bash
python -m pytest -q tests/unit/test_verification_bundle.py tests/integration/test_verification_flow.py
python -m pytest -q tests/unit/test_campaigns.py tests/integration/test_campaign_flow.py
python -m pytest -q tests/unit/test_workspace_runs.py tests/integration/test_run_import_flow.py
python -m pytest -q
python -m ruff check src tests
python -m pyright
python -m build
bash scripts/tdd-gate-v3.sh
bash scripts/bdd-gate.sh
bash scripts/security-gate.sh
bash scripts/doc-sync-check.sh
bash scripts/ui-gate.sh
bash scripts/coverage-gate.sh
```

Fix repository gate portability rather than relying on ambient `PYTHONPATH` or executable-only `coverage`: scripts must use `PYTHONPATH=src python -m ...` where applicable. Restore the tested `.github/workflows/perf-test.yml` if absent using existing documented CI contract. Do not weaken tests or gate thresholds.

Coverage targets: `verification_bundle.py`, `campaigns.py`, new repository methods, and new route/view branches each ≥90%; pure domain modules ≥95%; archive validation critical paths ≥95%. Full pass requires zero failing tests and zero serious/critical axe violations.

Build/startup: clean sdist/wheel in an isolated venv, install wheel, run `locust-kit verify --help`, start `locust-workspace` on loopback, verify `/healthz` and all new GET screens. Use existing Playwright `LPK_RUN_E2E=1` convention. Docker build/health where available; otherwise CI must execute and local result is BLOCKED, not PASS.

### Acceptance-to-test mapping

- US-001 AC1–3: source-backed export, deterministic bytes, mismatch/atomic preservation tests.
- US-002 AC1–3: valid, unsupported, exhaustive attack matrix, session cleanup tests.
- US-003 AC1–3: real MATCH, policy/decision DRIFT, expired/unsupported/parse UNREPRODUCIBLE and CLI tests.
- US-004 AC1–3: boundaries/order transaction, per-row validation, optimistic conflict tests.
- US-005 AC1–3: exact policy fields, baseline drift/30-day boundary, missing-reference tests.
- US-006 AC1–3: immutable snapshot, JSON/Markdown stability/parity, atomic failure/audit tests.

## Documentation Deliverables

Development updates:

- `README.md`: golden path from run to verification to campaign; exact CLI; prerequisites; local-only/security boundaries; troubleshooting; current version/test badges.
- `CHANGELOG.md`: completed release entry, schemas, migrations, UI, CLI, security, compatibility, tests, docs.
- `docs/decision-verification.md`: layout, roles, session TTL, UI/CLI, statuses/exits, full threat model, reproduction and canonical differences.
- `docs/release-campaigns.md`: slots, eligibility, editing/concurrency, readiness precedence, drift/freshness, finalization, artifacts, routes.
- `docs/run-inbox-and-import.md`, `docs/baseline-decisions.md`, `docs/trustworthy-run-workflow.md`: cross-links and exact integrated path.
- `FEATURES-DONE.md`: only fully completed US-001 through US-006 after tests prove them.
- `development-report.md`: exact RED/GREEN, full tests, measured coverage, all gates, lint/type/build/startup, E2E/screenshots, Docker, Git/push, limitations, files, and traceability.

Every snippet must be executed. No claim of signatures, browser pass, Docker pass, or push without evidence.

## Expected File Changes

Expected additions:

- `tests/integration/test_verification_flow.py`
- `tests/integration/test_campaign_flow.py`
- optional committed safe bundle fixtures under `tests/fixtures/verification/`
- `.github/workflows/perf-test.yml` only if absent and required by existing tests

Expected modifications:

- `src/locust_templates/verification_bundle.py`
- `src/locust_templates/campaigns.py`
- `src/locust_templates/product_workspace.py`
- `src/locust_templates/workspace_api.py`
- `src/locust_templates/workspace_views.py`
- `src/locust_templates/cli_analyze.py`
- `src/locust_templates/run_import.py`
- `src/locust_templates/decision_artifact.py` only with byte-compatibility proof
- `src/locust_templates/static/workspace.css`
- `src/locust_templates/static/workspace.js`
- `tests/unit/test_verification_bundle.py`
- `tests/unit/test_campaigns.py`
- `tests/unit/test_workspace_runs.py`
- `tests/e2e/test_workspace_rc.py`
- gate scripts only for portable invocation, not threshold reduction
- `pyproject.toml` type-check/package/version scope only, no runtime dependency
- README, CHANGELOG, feature docs, cross-link docs, FEATURES-DONE, development-report

No public test, fixture, route, schema, or compatibility behavior may be deleted to pass gates.

## Traceability Matrix

| Research need | Research evidence | User story id | Planned requirement | Acceptance criterion | Planned implementation location | Planned test evidence | Priority |
|---|---|---|---|---|---|---|---|
| Portable trusted evidence | P0 reproducible bundle; current partial export | US-001 | Run Detail source-backed deterministic artifact | all current/baseline members and stable ZIP bytes | verification bundle, repository, Run Detail routes | real-I/O export and byte-stability tests | P0 |
| Evidence mutation recovery | Existing source hashes and safe managed storage | US-001 | re-hash before atomic write | mismatch preserves prior artifact | bundle builder/artifact repository | mismatch and injected-write tests | P0 |
| Comprehensive safe verification | Safe-import strength and local-first demand | US-002 | full archive/member/hash/schema contract | exhaustive listed attacks INVALID | shared import security and verifier | parametrized attack matrix | P0 |
| Restart-safe local verification | Current request-only upload limitation | US-002 | 15-minute digest-backed session and cleanup | valid session persists; reset/expiry deletes | repository/API | TTL/reset/startup cleanup tests | P0 |
| Reproducible CI decision | Research one-command revalidation | US-003 | reconstruct current/baseline and analyze | unchanged package MATCH | reproduction service/CLI | real run_a/run_b MATCH | P0 |
| Explain policy/analyzer drift | Silent rule changes undermine trust | US-003 | canonical sorted differences | changed SLO shows exact pointer/values | diff/result/UI | integrity-valid DRIFT tests | P0 |
| Multi-run completeness | Gatling campaigns and LoadForge trends | US-004 | 1–20 editable ordered slots | atomic create/edit; no duplicates | campaign repository/form/API | boundary, rollback, E2E tests | P0 |
| Lost-update prevention | Local concurrency and auditable state | US-004 | optimistic updated token | stale save returns 409 and preserves values | repository/API/view | two-client conflict test | P0 |
| Policy transparency | SLO/history competitor evidence | US-005 | field-level policy drift | exact fields and run IDs shown | campaigns/detail view | policy-difference tests | P0 |
| Baseline governance | Existing immutable baseline model | US-005 | baseline drift and fixed freshness | >30 stale; =30 active; missing unknown | campaigns/repository | boundary/snapshot tests | P0 |
| Stable release artifact | Explainable CI artifact demand | US-006 | immutable final projection | active baseline cannot mutate final | repository/campaigns | post-finalization mutation test | P0 |
| Atomic exports | Existing atomic decision pattern | US-006 | persisted JSON/Markdown metadata | failure preserves prior bytes/audit truth | campaign artifact service | fault-injection tests | P0 |
| Release confidence | Current failed gates/no screenshots | US-001–US-006 | green tests/gates/build/E2E | objective commands all pass | scripts/CI/docs | recorded outputs and screenshots | P0 |

## Risks and Mitigations

- **Completion scope still broad**: no new product capability beyond closing explicit partials; implement stories sequentially and prohibit observability/signing expansion.
- **Existing partial schema**: versioned additive migration with populated-DB tests; no destructive DDL.
- **Canonical drift from host data**: whitelist only generated timestamp and host-path exclusions; regression-test all decision metrics.
- **ZIP security duplication**: centralize shared primitives and keep SafeRunImporter API compatible.
- **Session leakage**: digest tokens, owner-only staging, bounded TTL cleanup, consume-on-reproduce, no raw token logs.
- **CSRF regression**: test helper and route matrix cover every browser POST while API-key JSON remains unaffected.
- **Gate environment variance**: invoke Python modules portably; do not weaken assertions; report unavailable Docker/browser honestly.
- **UI scope creep**: server-rendered reusable components only; no frontend migration.
- **Finalized history mutation**: persist complete immutable projection and test after baseline changes.
- **Git metadata absent**: attempt commit/push only if repository metadata exists; otherwise record BLOCKED and rely on verified complete ZIP without claiming success.

## Definition of Done

- [ ] US-001 through US-006 pass every acceptance criterion with real tests; no PARTIAL story remains.
- [ ] Run Detail export, exhaustive verify, MATCH/DRIFT/UNREPRODUCIBLE, multi-slot edit, concurrency, drift detail, finalization, and atomic exports work end to end.
- [ ] No placeholder, production mock, process-global upload session, or unconditional success path remains.
- [ ] Existing `performance-decision/v1`, analyze CLI, routes, and databases remain compatible.
- [ ] Every story has recorded RED then GREEN evidence.
- [ ] Targeted and full `python -m pytest -q` pass with zero failures/errors.
- [ ] New/changed modules meet ≥90%; pure domain and archive critical paths meet ≥95%.
- [ ] `python -m ruff check src tests` and configured Pyright pass.
- [ ] Clean sdist/wheel build and installed-wheel CLI/workspace startup pass.
- [ ] `/healthz` plus all selected GET screens return 200 from installed wheel.
- [ ] `tdd-gate-v3.sh`, `bdd-gate.sh`, `security-gate.sh`, `doc-sync-check.sh`, `ui-gate.sh`, and `coverage-gate.sh` pass without threshold reduction.
- [ ] Browser E2E, axe, keyboard flows, and screenshots at 360/768/1440 pass; blocked local execution remains a CI requirement and is not mislabeled.
- [ ] Docker build/health passes where available or is truthfully blocked with CI evidence requirement.
- [ ] README, CHANGELOG, CLI/API docs, FEATURES-DONE, and development-report match tested behavior.
- [ ] Secret scan and final-tree cleanup find no credentials, staging, caches, coverage/build outputs, virtualenvs, or dependency directories.
- [ ] Traceability maps every research need, story, requirement, implementation, and test to COMPLETE.
- [ ] Git add/commit/pull-rebase/push is attempted; clean status and `git-push-verify.sh` pass when a remote exists. Missing repository metadata/remote is documented as BLOCKED, never success.
- [ ] Complete project ZIP is integrity-tested, listed, separately extracted, checked for root layout and required documents, and delivered.
