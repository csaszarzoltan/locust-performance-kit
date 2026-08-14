# Research Findings

## Executive Summary

Locust Performance Kit 1.7.0 is no longer merely a template library. It is a local-first, Python-native performance decision workspace that imports Locust evidence, grades its quality, compares runs with immutable baselines, emits deterministic CI artifacts, and exposes the workflow through CLI and Flask interfaces. The strongest commercial wedge is therefore not cloud load generation. It is a trustworthy, low-operations **run-to-decision product for Locust teams**.

Current market evidence converges on three needs: teams want performance tests inside CI/CD; raw load results still require substantial manual interpretation; and paid products monetize history, comparison, collaboration, automatic insights, and managed scale. Locust itself has strong Python scripting, a live UI, CSV exports, and built-in distributed execution, but leaves durable history and decision governance to external tooling. Grafana Cloud k6, Gatling Enterprise, and LoadForge validate willingness to pay for the missing layer, while their cloud and usage economics create room for a private, self-hosted alternative.

Recommended next-pass priorities are:

1. **P0: Release-grade Run Inbox and evidence trust**: turn import, quality grading, provenance, and recovery into the unmistakable default experience.
2. **P0: Policy-aware baseline campaigns**: evolve single comparisons into release/environment campaigns with explicit policy versions and drift detection.
3. **P1: Optional OpenTelemetry and Prometheus evidence attachments**: correlate client-side load findings with server-side evidence without making an observability backend mandatory.

The scope should stay narrow. Do not build hosted load generators, billing, a broad recorder, or a universal scenario IDE before design-partner validation.

## Project Understanding

### Verified purpose, users, and behavior

The package describes itself as production-ready Locust templates for enterprise performance testing (`pyproject.toml`). Verified capabilities include reusable HTTP and protocol templates (`src/locust_templates/api_load.py`, `grpc.py`, `graphql.py`, `websocket.py`), OpenAPI generation (`openapi_parser.py`, `locust_generator.py`), report generation (`report_data.py`, `exporters.py`), deterministic statistical analysis (`intelligence.py`), source-linked evidence (`evidence.py`, `evidence_bundle.py`), safe ZIP import (`run_import.py`), deterministic decision artifacts (`decision_artifact.py`), workspace analysis (`analysis_service.py`, `workspace_views.py`, `workspace_api.py`), and CLI entry points (`pyproject.toml [project.scripts]`).

The primary target users are Python developers, performance engineers, QA/SDET teams, SRE/platform engineers, and CI owners already using Locust. The strongest initial buyer is an engineering lead or platform team that needs repeatable decisions but cannot justify a commercial cloud platform or does not want test topology and failures sent to a third party.

### Architecture and stack

- Python 3.9+ and setuptools (`pyproject.toml`).
- Locust, Flask 3.1.3, Gunicorn, requests, PyYAML, OpenAPI validation; optional gRPC, OpenTelemetry, and WebSocket packages.
- Server-rendered Flask workspace with packaged CSS/JavaScript (`workspace_api.py`, `workspace_views.py`, `static/workspace.css`, `static/workspace.js`).
- SQLite-backed local workspace (`product_workspace.py`).
- Deterministic analysis, with optional OpenAI-compatible enrichment separated from authoritative results (`intelligence.py`).
- Four CLIs: `locust-report`, `locust-gen`, `locust-kit`, and `locust-workspace` (`pyproject.toml`).
- Strong automated verification: project documents report 1,113 passing tests, one intentionally guarded browser test, 98% changed-scope coverage, wheel startup checks, and CI definitions (`development-report.md`).

### Principal user flow

The implemented flow is: launch `locust-workspace`; open the Run Inbox; import a ZIP or use a sample; validate candidate prefixes and evidence quality; commit the selected evidence to managed local storage; view a stable Run Detail page; compare with an active baseline; inspect a p95/RPS timeline and endpoint deltas; promote eligible PASS evidence as a baseline; export canonical JSON or Markdown. The corresponding routes and contracts are documented in `docs/run-inbox-and-import.md` and `docs/baseline-decisions.md` and implemented in `run_import.py`, `analysis_service.py`, `comparison_view.py`, `decision_artifact.py`, and workspace modules.

### Current strengths

1. Local-first operation and no mandatory outbound data path.
2. Deterministic, auditable findings and stable decision hashes.
3. Locust-native Python workflow rather than a replacement load engine.
4. Safe archive handling with explicit limits and traversal/symlink/CRC defenses.
5. Real-I/O fixtures and unusually broad regression coverage.
6. Additive CLI, API, and package design with preserved public compatibility.
7. Accessible intent, responsive layouts, data-table fallback, and explicit empty/error states.

### Constraints for planning

- Preserve Python 3.9+, Locust compatibility, and existing CLI exit codes.
- Keep deterministic analysis authoritative; optional AI must never alter gate status.
- Keep local operation useful without Grafana, Prometheus, OTel, Kubernetes, or cloud accounts.
- Do not weaken safe-import limits, path confinement, artifact hashing, or baseline immutability.
- Treat production identity, RBAC, TLS, CSRF, KMS, backup, and rate limiting as explicit deployment boundaries, not implied capabilities.
- Browser E2E and Docker verification remain CI obligations until executed in a connected environment (`development-report.md`).

## Current-State Gap Analysis

| Area | Verified state | Remaining gap | Implication |
|---|---|---|---|
| Onboarding | Inbox, sample, ZIP import, stable Run Detail exist | README badges/version text are stale and the golden path is diluted by broad legacy features | Make the decision workflow the product homepage and packaging story |
| Trust | Hashes, provenance, data-quality grades, source rows | No signed artifact/attestation or reproducibility command embedded in every export | Add optional signing and one-command revalidation |
| Baselines | Immutable environment promotion and history | No campaign/release grouping, policy drift alert, or expiration review queue | Build policy-aware campaigns before more analytics |
| Comparison | Endpoint deltas and aligned p95/RPS timeline | Limited cross-run trend set and no cohort view across many runs | Add small-multiples trend and release campaign summary |
| Observability | OTel examples and Grafana dashboards | Server-side metrics/traces are not attached to a decision finding | Add optional bounded evidence adapters |
| Collaboration | Local/single-operator product | No identity, comments, approvals, RBAC, or shared deployment contract | Keep single-user positioning until a security phase |
| Distribution | Wheel, Dockerfile, Railway assets, CI | No polished upgrade/migration story, support boundary, or monetization package | Validate paid self-hosted/team packaging with design partners |
| UI verification | Playwright/axe flows are defined | Chromium execution was blocked locally; screenshots are not evidence yet | Require CI browser artifact before public release |
| Documentation | Extensive guides | Inconsistent versions and examples increase trust risk | Run doc-sync, executable snippets, and version-source unification |

## Target Users and Jobs to Be Done

| Segment | Core job | Current alternative | Fit |
|---|---|---|---|
| Python product team | Know whether a release caused a measurable performance regression | CSV review, spreadsheets, ad hoc scripts | Very high |
| Performance engineer | Preserve evidence, compare runs, and explain a gate decision | Grafana dashboards plus custom notebooks | Very high |
| Platform/DevOps team | Enforce deterministic SLO gates and provide a reviewable artifact | k6 thresholds, custom CI jobs, JUnit only | High |
| Regulated/local-first team | Keep endpoints, payload patterns, and failure evidence inside its boundary | Self-hosted OSS stack or expensive enterprise platform | High |
| Small QA team | Get SaaS-like analysis without operating a telemetry platform | Commercial cloud service | Medium to high |
| Nontechnical tester | Author complex scenarios visually | JMeter, Gatling no-code, k6 Studio | Low for the next pass |

## Target-Market Pain Points

| Problem | Segment | Recurrence | Evidence | Confidence | Product implication |
|---|---|---:|---|---|---|
| Generating load is easier than interpreting results | Performance engineers | Repeated across guides and product positioning | OneUptime, “How to Analyze Locust Test Results,” 2026-01-28; Gatling Enterprise comparison, accessed 2026-08-14 | HIGH | Keep findings source-linked and action-oriented |
| Teams need CI pass/fail criteria, not only charts | DevOps and developers | Repeated across k6, Locust comparisons, and current project docs | Grafana k6 product page; QASkills k6 vs Locust, 2026-06-15 | HIGH | Preserve measured-only exit code and add policy provenance |
| Historical comparison and campaigns are paid differentiators | Larger teams | Repeated across Gatling and LoadForge | Gatling Community vs Enterprise; LoadForge product page | HIGH | Invest in campaign/history UX rather than another report format |
| Cloud pricing and data exposure push some users toward self-hosting | Regulated and cost-sensitive teams | Repeated in self-hosted comparisons and vendor pricing | Pi Stack self-hosted comparison, 2026-04-15; Grafana pricing | MEDIUM-HIGH | Position local-first as a primary benefit, not a fallback |
| Tool choice follows team language and workflow | Developers/SDETs | Repeated across comparisons and community discussion | QASkills; Reddit r/QualityAssurance discussion | HIGH | Own the Python/Locust niche instead of broad engine competition |
| Locust CSV history behavior requires specialist knowledge | Locust users | Official documentation and issue history | Locust CSV docs; locustio/locust issue #1837 | HIGH | Continue strict validation and quality grading |
| Broad setup and unintuitive tools cause teams to skip testing | Small teams | Reported by industry comparisons | PFLB best tools 2026 | MEDIUM | Keep first run under five minutes with sample/import guidance |

## Competitor Weaknesses

### Grafana Cloud k6

Strongest end-to-end developer platform and observability integration, but not Python-native. Cloud usage, retention, and enterprise economics can become complex, and the best collaboration and Cloud Insights experience is coupled to Grafana Cloud. Opportunity: local-first Locust evidence and deterministic offline decisions.

### Gatling Enterprise

Provides history, campaigns, SLO tracking, run comparison, collaboration, distributed generators, and AI summaries. Weaknesses for this project’s segment are JVM DSL fit, paid platform dependence for continuous intelligence, and a starting Basic price of €89/month billed annually. Opportunity: a simpler Python-native local workspace with auditable artifacts.

### LoadForge

Offers hosted scale, Python/Locust compatibility, AI test analysis, trends, schedules, alerts, and geographic load. Annual pricing begins at $67/month, while richer plans are $242 and $417/month. It is optimized for managed execution. Opportunity: analysis-only, bring-your-own execution, private evidence, and no VU-minute economics.

### Locust core

Free, MIT-licensed, Python-native, extensible, with a live UI, CSV exports, and built-in distributed master/worker mode. Its core mission is load generation, not durable decision management. Opportunity: remain a complementary layer rather than a fork or replacement.

### Apache JMeter / ad hoc Grafana stack

JMeter wins on protocol breadth and familiarity; Grafana/Prometheus wins on flexibility. Both impose setup and maintenance costs when the user only wants a reliable release decision. Opportunity: opinionated defaults, evidence validation, and a short path from run files to an auditable answer.

## Competitor Comparison

| Product | Audience | Current packaging | Core flow | Strength | Exploitable gap |
|---|---|---|---|---|---|
| Grafana Cloud k6 | JS/DevOps and Grafana teams | Free; Pro from $19/month plus usage; Enterprise from $25,000/year spend | Script/record, run, analyze in Cloud, correlate telemetry | Integrated observability and global scale | Not Python-native; cloud/usage dependency |
| Gatling Enterprise | JVM teams and organizations industrializing performance | Basic €89/month annual; Team €356/month annual; Enterprise custom | Create, orchestrate, compare, campaign, collaborate | Mature campaign/history and reporting | Price and JVM/platform fit |
| LoadForge | SRE/DevOps wanting managed cloud load | $67/$242/$417 monthly annual plans | Create/import, run globally, monitor, trend, alert | Managed scale and broad automation | Hosted execution focus and subscription cost |
| Locust | Python teams | Free, MIT | Write Python, run live/headless/distributed, export | Flexibility and built-in distributed mode | No durable decision workspace |
| Locust Performance Kit | Python/Locust, local-first teams | OSS package today | Import, validate, analyze, compare, promote, export | Evidence trust and deterministic decisions | Needs release polish, campaigns, optional server evidence |

## Validated Demand Signals

1. Locust’s official documentation treats CSV output as the automation interface and records aggregate history by default, proving both a standard input surface and the need for quality-aware interpretation. Confidence: HIGH.
2. Locust’s distributed mode is built in and can scale across processes/machines, so a complementary decision layer can avoid the capital-intensive hosted-generator market. Confidence: HIGH.
3. Grafana promotes SLO-based CI testing, run comparison, automatic Cloud Insights, and telemetry correlation, validating the desired outcome rather than only load generation. Confidence: HIGH.
4. Gatling explicitly differentiates static one-time reports from continuous performance intelligence, history, campaigns, SLO tracking, run comparison, and AI summaries. Confidence: HIGH.
5. LoadForge markets historical trends, scheduled tests, custom thresholds, alerts, AI analysis, and collaboration, independently validating the same paid feature cluster. Confidence: HIGH.
6. Community discussion repeatedly frames Locust as highly customizable and Python-friendly while recommending alternatives based on language and CI fit. Confidence: MEDIUM because individual comments are anecdotal.
7. Public issue history around CSV files continuing to update outside active tests shows that ingestion must handle imperfect evidence and lifecycle artifacts. Confidence: MEDIUM.

## Market and Pricing Evidence

The category has strong adoption direction but reliable narrow “load-testing software TAM” data is weak. A 2026 market listing estimates the load-testing-tools market at $1.64 billion in 2025 and 14.23% CAGR, but the methodology is not public enough to use as a planning-grade TAM. This report therefore does not adopt that figure as a business case.

Adjacent observability research is more mature but still varies by taxonomy. MarketsandMarkets projects observability tools/platforms from $11.91 billion in 2026 to $22.99 billion in 2031, while The Business Research Company reports $3.53 billion in 2026 and $5.52 billion in 2030. The disagreement confirms that category boundaries differ substantially; it supports direction, not a precise TAM.

Pricing evidence is clearer:

- Grafana Cloud has a free tier, Pro from $19/month plus usage, and Enterprise from a $25,000/year spend commitment.
- Gatling Enterprise lists Basic at €89/month and Team at €356/month when billed annually.
- LoadForge lists annual-billing plans at $67, $242, and $417 per month.

This supports two realistic experiments: an open-source core with a paid team/self-hosted edition in the $49–$149/month range, or a one-time commercial license with paid updates/support. No willingness-to-pay interview data exists in the repository, so these are test ranges, not validated prices. Subscription fatigue and one-time-purchase demand were not reliably evidenced for this exact buyer, so the planning phase should not assume either model.

## Modern UX Expectations

A credible 2026 baseline for this category is:

- **Navigation**: Inbox, Run Detail, Baselines, Policies/Campaigns, Integrations, Settings.
- **First use**: sample run, drag-and-drop ZIP, server-prefix option, validation preview, clear local-data statement, and time-to-first-decision under five minutes.
- **States**: explicit empty, validating, importing, analyzing, partial-evidence, incompatible-baseline, no-history, permission, conflict, storage, and success states.
- **Run Detail**: status, quality grade, confidence, exact SLO/policy, baseline identity, high-severity findings, timeline, endpoint deltas, source evidence, and exports above the fold.
- **Responsiveness**: 360/768/1440 layouts with tables that transform to cards or offer horizontal scroll and complete accessible fallback.
- **Accessibility**: WCAG 2.2 AA target; keyboard workflows, visible focus, semantic headings, form labels, `aria-live`, non-color status indicators, and chart data tables.
- **Trust**: input hashes, analyzer version, policy version, generated timestamp, local/no-network indicator, reproducibility command, and decision hash.
- **Security**: constrained imports, least-privilege storage, secret-free artifacts, explicit production deployment checklist, and no silent LLM calls.
- **Discoverability**: progressive disclosure from decision to diagnosis to raw source evidence.
- **Automation**: stable JSON/Markdown/JUnit, exit codes, GitHub/GitLab/Jenkins examples, and artifact verification.

The project meets much of the trust/import baseline. The largest missing expectations are campaign-level trends, release-ready browser evidence, unified versioning/docs, and optional server-side evidence correlation.

## Open-Source and Automation Opportunities

- Reuse Locust CSV and distributed execution rather than building a load engine.
- Add optional OpenTelemetry trace/metric references using semantic conventions and bounded time windows.
- Add a Prometheus HTTP adapter that stores only queried, redacted evidence and query provenance.
- Supply GitHub Check/Job Summary templates without requiring a GitHub App.
- Generate SLSA-style provenance or optional Sigstore/minisign signatures for decision bundles, while keeping unsigned local use simple.
- Add a `locust-kit verify-decision` command that re-hashes sources and canonical JSON.
- Use existing pytest/Playwright/axe pipelines to make accessibility and screenshots actual release evidence.
- Track relevant Locust schema changes through fixture-generation automation against supported Locust versions.

## Differentiation Opportunities

| Capability | Problem solved | User | Evidence | Competitor gap | Value | Complexity | Risk | Priority | Success criterion |
|---|---|---|---|---|---|---|---|---|---|
| Signed reproducible decision bundle | Reviewers cannot prove artifact/source integrity | CI owner, regulated team | Existing hashes plus enterprise trust expectations | Cloud tools centralize trust; local tools rarely sign | High | MEDIUM | Key-management confusion | P0 | 100% of signed bundles verify offline; tampering fails deterministically |
| Release campaign and policy drift | One run does not explain release readiness | Platform/perf teams | Gatling campaigns/history; LoadForge trends | Current project is run-centric | High | MEDIUM | Overcomplicated policy model | P0 | Campaign page summarizes ≥10 runs and flags policy/baseline changes |
| Baseline freshness review | Stale baselines create misleading gates | Performance engineer | Project already tracks immutable baseline history | Competitors show trends but freshness rules vary | High | LOW | False urgency | P0 | Configurable age/compatibility rules surface stale baselines with zero silent replacements |
| Optional Prometheus evidence attachment | Client symptoms lack server context | SRE/perf engineer | Grafana correlates test and server data; observability market direction | Local-first tools require manual dashboards | High | HIGH | SSRF, cardinality, secret leakage | P1 | Bounded adapter attaches redacted metric snapshots with query/time/source provenance |
| Optional OTel trace exemplars | Endpoint regression lacks request-path evidence | SRE/perf engineer | OTel adoption and existing project examples | Commercial suites couple this to hosted stacks | Medium-high | HIGH | Time alignment and PII | P1 | User can attach trace IDs to a finding without exporting raw spans by default |
| Executable release evidence dashboard | Public release claims lack browser/container proof | Maintainer/buyer | Current E2E/Docker locally blocked | Competitors provide polished trust signals | Medium | LOW | CI flakiness | P0 | Every release publishes wheel, Docker health, axe, and screenshot artifacts |
| Paid self-hosted team package experiment | No monetization or support boundary | Engineering manager | Competitor price anchors | Lower-ops local niche is under-served | High | MEDIUM | Premature packaging | P1 | 5 design partners, 3 weekly active, 2 paid pilots |

## User Stories (BDD)

```json
[
  {
    "id": "US-001",
    "epic": "Signed Reproducible Decision Bundles",
    "role": "CI owner",
    "action": "export a decision bundle with a verifiable signature and source manifest",
    "benefit": "reviewers can prove that the decision and its evidence were not altered",
    "story": "As a CI owner, I want to export a decision bundle with a verifiable signature and source manifest, so that reviewers can prove that the decision and its evidence were not altered.",
    "gui_flow": ["User opens Run Detail → sees Export decision", "User clicks Signed bundle → sees signing options", "User selects a configured key → sees key fingerprint", "User clicks Export → bundle is generated", "User downloads bundle → checksum and verification command are shown"],
    "acceptance_criteria": [
      {"type":"given","text":"a completed run and configured signing key","when":"the user exports a signed bundle","then":"the ZIP contains decision JSON, source manifest, signature, public-key fingerprint, and a verification command"},
      {"type":"given","text":"a signed bundle whose decision JSON is modified by one byte","when":"verification runs","then":"verification exits non-zero and names the mismatched entry"},
      {"type":"given","text":"the signing key is unavailable","when":"the user requests a signed export","then":"no partial bundle is committed and the UI displays a recovery action"}
    ]
  },
  {
    "id": "US-002",
    "epic": "Signed Reproducible Decision Bundles",
    "role": "release reviewer",
    "action": "verify a bundle offline",
    "benefit": "I can audit a release without access to the original workspace",
    "story": "As a release reviewer, I want to verify a bundle offline, so that I can audit a release without access to the original workspace.",
    "gui_flow": ["User opens Verify page → sees file drop target", "User drops bundle → local validation starts", "System checks ZIP, hashes, schema, and signature → progress is shown", "Validation completes → decision identity and signer are displayed", "User expands details → every file status is listed"],
    "acceptance_criteria": [
      {"type":"given","text":"a valid signed bundle","when":"offline verification completes","then":"every manifest item is PASS and the displayed decision hash equals the embedded hash"},
      {"type":"given","text":"a valid unsigned legacy bundle","when":"verification completes","then":"integrity is reported separately from signature status and the bundle is not labeled signed"},
      {"type":"given","text":"a corrupt or path-traversal ZIP","when":"it is selected","then":"validation stops before extraction and reports the violated rule"}
    ]
  },
  {
    "id": "US-003",
    "epic": "Signed Reproducible Decision Bundles",
    "role": "automation engineer",
    "action": "reproduce a decision from the recorded sources and policy",
    "benefit": "CI can detect analyzer or policy drift",
    "story": "As an automation engineer, I want to reproduce a decision from the recorded sources and policy, so that CI can detect analyzer or policy drift.",
    "gui_flow": ["User opens Run Detail → sees Reproduce command", "User copies command → command includes source and policy identities", "User runs command → analysis executes without network access", "System compares regenerated and recorded canonical JSON → differences are computed", "User sees MATCH or DRIFT with changed fields"],
    "acceptance_criteria": [
      {"type":"given","text":"identical sources, analyzer version, and policy","when":"reproduction runs","then":"the canonical decision hash exactly matches"},
      {"type":"given","text":"the same sources but a different policy version","when":"reproduction runs","then":"the result is DRIFT and lists the policy identity change"},
      {"type":"given","text":"a required source file is missing","when":"reproduction starts","then":"it exits 1 before analysis and names the missing hash/path"}
    ]
  },
  {
    "id": "US-004",
    "epic": "Release Campaigns and Policy Drift",
    "role": "performance engineer",
    "action": "group related runs into a release campaign",
    "benefit": "I can evaluate release readiness across environments and scenarios",
    "story": "As a performance engineer, I want to group related runs into a release campaign, so that I can evaluate release readiness across environments and scenarios.",
    "gui_flow": ["User opens Campaigns → sees recent campaigns", "User clicks New campaign → form opens", "User names release and selects environment/policy → eligible runs appear", "User selects runs → compatibility warnings update", "User saves → campaign summary shows PASS, FAIL, ADVISORY, and missing evidence"],
    "acceptance_criteria": [
      {"type":"given","text":"ten completed compatible runs","when":"they are added to a campaign","then":"the summary counts all statuses and links every count to its runs"},
      {"type":"given","text":"a run uses an incompatible metric schema","when":"it is selected","then":"the UI marks it incompatible and excludes it from aggregate readiness"},
      {"type":"given","text":"campaign persistence fails","when":"the user saves","then":"no partial campaign is visible and the form retains the selections for retry"}
    ]
  },
  {
    "id": "US-005",
    "epic": "Release Campaigns and Policy Drift",
    "role": "platform lead",
    "action": "see when policy or baseline identity changes inside a campaign",
    "benefit": "a gate cannot appear to improve because the rules silently changed",
    "story": "As a platform lead, I want to see when policy or baseline identity changes inside a campaign, so that a gate cannot appear to improve because the rules silently changed.",
    "gui_flow": ["User opens Campaign Detail → sees policy timeline", "User selects a run → its policy and baseline identities are highlighted", "User compares adjacent runs → changed fields are listed", "User filters to Drift only → unchanged runs are hidden", "User exports summary → drift entries are included"],
    "acceptance_criteria": [
      {"type":"given","text":"adjacent runs use different p95 SLO values","when":"Campaign Detail loads","then":"a policy-drift event shows both values and affected run IDs"},
      {"type":"given","text":"a baseline was superseded between runs","when":"comparison opens","then":"both baseline IDs and promotion timestamps are shown"},
      {"type":"given","text":"a referenced policy record cannot be loaded","when":"Campaign Detail loads","then":"readiness becomes UNKNOWN for that run and no value is fabricated"}
    ]
  },
  {
    "id": "US-006",
    "epic": "Release Campaigns and Policy Drift",
    "role": "release manager",
    "action": "export a campaign readiness summary",
    "benefit": "approvers receive one deterministic release artifact",
    "story": "As a release manager, I want to export a campaign readiness summary, so that approvers receive one deterministic release artifact.",
    "gui_flow": ["User opens Campaign Detail → sees Export", "User selects JSON and Markdown → preview shows included runs", "User clicks Generate → canonical ordering is applied", "System computes campaign hash → hash appears", "User downloads files → both contain the same readiness status"],
    "acceptance_criteria": [
      {"type":"given","text":"a campaign with PASS, FAIL, and excluded runs","when":"exports are generated twice","then":"canonical JSON bytes and campaign hash are identical"},
      {"type":"given","text":"one required scenario is missing","when":"readiness is calculated","then":"status is INCOMPLETE and the missing requirement is listed"},
      {"type":"given","text":"artifact writing fails","when":"export is requested","then":"temporary files are removed and the existing artifact is not overwritten"}
    ]
  },
  {
    "id": "US-007",
    "epic": "Optional Observability Evidence Attachments",
    "role": "SRE",
    "action": "attach a bounded Prometheus metric snapshot to a finding",
    "benefit": "I can test whether server saturation coincides with the client-side regression",
    "story": "As an SRE, I want to attach a bounded Prometheus metric snapshot to a finding, so that I can test whether server saturation coincides with the client-side regression.",
    "gui_flow": ["User opens a finding → sees Attach server evidence", "User selects Prometheus connection and approved query template → time range is prefilled", "User previews query → host, range, and maximum samples are shown", "User runs attachment → progress and cancellation are available", "Result appears with chart, data table, query, timestamps, and source identity"],
    "acceptance_criteria": [
      {"type":"given","text":"an approved connection and query template","when":"attachment runs","then":"stored evidence contains query ID, source ID, UTC range, sample count, and redacted values"},
      {"type":"given","text":"the query returns more than the configured maximum samples","when":"attachment runs","then":"the result is deterministically downsampled and the reduction is disclosed"},
      {"type":"given","text":"the target resolves to a disallowed address or times out","when":"attachment starts","then":"the request is blocked or cancelled, no secret is logged, and the finding remains unchanged"}
    ]
  },
  {
    "id": "US-008",
    "epic": "Optional Observability Evidence Attachments",
    "role": "performance engineer",
    "action": "link trace exemplars to a regressed endpoint",
    "benefit": "I can inspect representative server paths without importing an entire trace store",
    "story": "As a performance engineer, I want to link trace exemplars to a regressed endpoint, so that I can inspect representative server paths without importing an entire trace store.",
    "gui_flow": ["User opens endpoint regression → sees Trace exemplars", "User selects an OTel-compatible source → matching window is shown", "User requests exemplars → identifiers and durations load", "User selects an exemplar → redacted span summary opens", "User attaches it → finding records source and time alignment"],
    "acceptance_criteria": [
      {"type":"given","text":"traces overlap the load-test window","when":"exemplars are requested","then":"at most the configured limit is returned, ordered by duration and error status"},
      {"type":"given","text":"trace attributes contain configured PII keys","when":"the summary is stored","then":"those values are replaced with redaction markers"},
      {"type":"given","text":"the trace source is unavailable","when":"the user requests exemplars","then":"the UI reports the timeout and does not infer a root cause"}
    ]
  },
  {
    "id": "US-009",
    "epic": "Optional Observability Evidence Attachments",
    "role": "security administrator",
    "action": "control which outbound evidence sources and fields are allowed",
    "benefit": "local-first guarantees remain enforceable",
    "story": "As a security administrator, I want to control which outbound evidence sources and fields are allowed, so that local-first guarantees remain enforceable.",
    "gui_flow": ["User opens Integrations policy → sees outbound disabled by default", "User adds an allowlisted source → connection validation runs", "User chooses permitted query templates and redaction keys → policy preview updates", "User saves → policy version and hash are shown", "User opens audit history → all connection attempts and outcomes are listed without secrets"],
    "acceptance_criteria": [
      {"type":"given","text":"a fresh installation","when":"a user attempts an outbound attachment","then":"the request is blocked because outbound access is disabled by default"},
      {"type":"given","text":"an allowlisted HTTPS source and approved template","when":"an attachment runs","then":"only the configured host, path, and query template are used"},
      {"type":"given","text":"a credential or response includes a secret-pattern value","when":"audit events are written","then":"the value is absent from logs, artifacts, and UI error text"}
    ]
  }
]
```

## Priority-Ranked Development Recommendations

1. **P0: Ship release-trust closure**. Execute browser/Docker CI, unify version strings, fix stale docs/examples, and publish evidence. This is smaller than a feature and directly improves buyer confidence.
2. **P0: Implement signed/reproducible decision bundles**. Build on existing canonical hashing rather than inventing a new artifact model.
3. **P0: Implement release campaigns, policy drift, and baseline freshness**. This is the clearest expansion of the validated decision-history value.
4. **P1: Pilot a Prometheus adapter behind an outbound-disabled-by-default policy**. Keep it optional and bounded.
5. **P1: Add trace exemplars only after the metric adapter’s security and provenance model is stable**.
6. **P1: Conduct five design-partner interviews and two paid pilots before multi-user/RBAC or hosted execution**.
7. **P2: Defer scenario recording, billing, global generators, and broad observability ingestion**.

## Recommended Scope for the Next Development Pass

Deliver one coherent release called **Campaign Trust and Verification**:

- close browser, accessibility, Docker, wheel, and documentation release evidence;
- add offline decision verification and optional signing;
- add campaign grouping, required-scenario checklist, policy/baseline drift, baseline freshness, and deterministic campaign export;
- retain single-operator/local-first deployment;
- write targeted and full regression tests after each functional change, including real-I/O bundle tampering, campaign persistence failures, compatibility edges, CLI exit codes, and complete suite execution.

Do not include Prometheus/OTel implementation in the same pass unless the trust/campaign scope finishes with all gates green. The planning phase may specify adapter interfaces, threat model, and fixtures as preparatory work.

## Risks, Unknowns, and Assumptions

- No direct customer interviews, conversion data, MRR, or willingness-to-pay survey exists. Pricing is a hypothesis.
- Competitor public pages change frequently; verify pricing during planning and before publication.
- Browser screenshots and Docker health are configured but were not executed in the supplied host. Treat them as incomplete evidence.
- The current application is still single-operator. Exposing it to teams requires identity, authorization, CSRF, TLS, backups, and KMS decisions.
- Signing creates key-management UX and support burden. A verification-only unsigned mode must remain useful.
- Prometheus/OTel adapters introduce SSRF, secret, cardinality, time-alignment, PII, and causal-overclaim risks.
- Market-size estimates conflict by taxonomy. Do not build a forecast from them.
- The report assumes the intended product remains complementary to Locust, not a competing load engine.

## Sources

Accessed 2026-08-14 unless a publication date is listed.

1. Locust, “Locust Documentation,” https://docs.locust.io/
2. Locust, “Distributed load generation,” https://docs.locust.io/en/stable/running-distributed.html
3. Locust, “Retrieve test statistics in CSV format,” https://docs.locust.io/en/2.37.0/retrieving-stats.html
4. locustio/locust GitHub issue #1837, “Stats History CSV is always growing,” https://github.com/locustio/locust/issues/1837
5. OneUptime, “How to Analyze Locust Test Results,” published 2026-01-28, https://oneuptime.com/blog/post/2026-01-28-analyze-locust-test-results/view
6. Grafana Labs, “Performance and Load Testing | Grafana Cloud k6,” https://grafana.com/products/cloud/performance-load-testing-k6/
7. Grafana Labs, “Grafana Pricing,” https://grafana.com/pricing/
8. Grafana k6, “Load testing for engineering teams,” https://k6.io/
9. Gatling, “Pricing,” https://gatling.io/pricing
10. Gatling, “Gatling Open Source vs. Gatling Enterprise,” https://gatling.io/community-vs-enterprise
11. LoadForge, “Load Testing Pricing & Plans,” https://loadforge.com/pricing
12. LoadForge, “Load Testing Platform,” https://loadforge.com/
13. Pi Stack, “k6 vs Locust vs Gatling: Best Self-Hosted Load Testing Tools 2026,” published 2026-04-15, https://www.pistack.xyz/posts/k6-vs-locust-vs-gatling-self-hosted-load-testing-guide-2026/
14. QASkills, “k6 vs Locust 2026,” published 2026-06-15, https://qaskills.sh/blog/k6-vs-locust-2026
15. Reddit r/QualityAssurance, “Load/performance testing tools research,” published 2021-04-13, https://www.reddit.com/r/QualityAssurance/comments/mpyxuy/loadperformance_testing_tools_research_k6_locust/
16. PFLB, “Best Load Testing Tools 2026,” published 2026-03-02, https://pflb.us/blog/best-load-testing-tools/
17. MarketsandMarkets, “Observability Tools & Platforms Market,” published 2026-07, https://www.marketsandmarkets.com/Market-Reports/observability-tools-and-platforms-market-69804486.html
18. The Business Research Company, “Observability Tools and Platforms Global Market Report 2026,” https://www.thebusinessresearchcompany.com/report/observability-tools-and-platforms-global-market-report
19. Data Insights Market, “Load Testing Tools: Growth Opportunities and Competitive Landscape Overview 2026-2034,” published 2026-05-12, https://www.datainsightsmarket.com/reports/load-testing-tools-1942725
20. Project source and documentation: `pyproject.toml`, `README.md`, `CHANGELOG.md`, `development-report.md`, `src/locust_templates/`, `docs/`, and `tests/` in the supplied archive.
