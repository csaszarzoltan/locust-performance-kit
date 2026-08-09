# Research Findings

## Executive Summary

Locust Performance Kit is a Python-first, local-first performance-engineering toolkit that extends Locust from load generation into test creation, run analysis, CI gating, evidence packaging, and a six-workflow Flask workspace. The strongest market opportunity is not another load generator. It is a **trustworthy run-to-decision layer for Locust teams**: upload or select a run, compare it with a baseline, understand why it failed, and export a reproducible decision artifact without operating Grafana/Timescale or sending test data to a commercial SaaS.

Demand evidence converges on three jobs: (1) making reports and observations is harder than generating load, (2) teams want history, comparisons, and observability correlation without infrastructure assembly, and (3) CI decisions must be explainable and reproducible. Locust itself documents CSV export but delegates hosted analysis to Azure Load Testing; Locust community answers acknowledge that the built-in UI cannot slice custom context and point users toward custom storage or a hosted product. Commercial competitors prove willingness to pay for collaboration, advanced reporting, distributed execution, and automatic insights, but price from usage-based $0.15/VUh through $89/month and $999/month tiers, leaving room for a local-first paid product or open-core team edition.

The next development pass should concentrate on a coherent vertical slice:

1. **P0: Run Inbox and Guided Analysis Workspace**: discover/import CSV bundles, validate data quality, run analysis, and show source-linked findings in an accessible history view.
2. **P0: Baseline Trends and Explainable CI Decisions**: compare runs, visualize deltas and saturation, manage SLO policies, and export stable PR/CI summaries.
3. **P1: Observability Evidence Correlation**: attach Prometheus/OpenTelemetry evidence to findings through open standards, while preserving offline/local operation.

Do not prioritize cloud load generation, browser recording, or a broad no-code scenario builder in this pass. Those are expensive, crowded areas already served by k6, Gatling, OctoPerf, LoadForge, and Azure. The defensible wedge is Locust-native, deterministic, auditable analysis with near-zero setup.

## Project Understanding

### Verified purpose and users

The package describes itself as “Production-ready Locust load testing templates for enterprise performance testing” (`pyproject.toml`). Verified capabilities span:

- reusable Locust user templates and load shapes (`src/locust_templates/api_load.py`, `stress.py`, `spike.py`, `soak.py`, `shapes.py`);
- authentication, multi-protocol support, and OpenAPI generation (`auth.py`, `grpc.py`, `graphql.py`, `websocket.py`, `openapi_parser.py`, `locust_generator.py`);
- report export, baselines, alerts, correlation, and AI-labelled deterministic intelligence (`report_data.py`, `exporters.py`, `baseline.py`, `alerts.py`, `correlator.py`, `intelligence.py`);
- CLI entry points `locust-report`, `locust-gen`, and `locust-kit` (`pyproject.toml [project.scripts]`);
- an evidence and trust layer (`evidence.py`, `evidence_bundle.py`);
- a Flask “performance engineering workspace” with scenarios, runs, diagnostics, policies, vault, and capacity workflows (`product_workspace.py`, `workspace_api.py`).

Primary verified user groups are Python developers, QA/performance engineers, SRE/platform teams, and CI owners already using Locust. A secondary inferred segment is small engineering teams that want SaaS-like analysis and governance while keeping test evidence local.

### Architecture and stack

- Python 3.9+ package using setuptools (`pyproject.toml`).
- Locust, Flask, requests, PyYAML, OpenAPI validation, Gunicorn; optional gRPC, OpenTelemetry, and WebSocket dependencies.
- SQLite persistence for workspace domain records (`PerformanceWorkspace.__init__` in `product_workspace.py`).
- Server-rendered HTML plus inline JavaScript and packaged CSS (`render_workspace`, `guided_start`; `static/workspace.css`).
- Deterministic statistical analysis and optional OpenAI-compatible enrichment (`intelligence.py`).
- Docker/Railway deployment surface (`Dockerfile`, `railway.toml`, `Procfile`).
- Large pytest suite with unit, integration, visual, trust-workflow, and real Locust-shaped CSV fixtures (`tests/`).

### Existing UI and principal flow

The most complete current user flow is `/workspace/start` in `workspace_api.py`: enter current CSV prefix, optional baseline, and a p95 SLO; submit to `/api/v1/analysis`; receive findings with severity, confidence, data-quality grade, source path, and next check. Six additional workspace pages are rendered from `_PAGES` in `product_workspace.py`, covering scenarios, runs, diagnostics, policies, vault, and capacity.

This is a credible functional prototype, but the first-run form assumes server-visible file paths rather than user-friendly import/discovery. Results are inserted into the same page rather than stored in a navigable run history. The main navigation describes broad workflows, but the product does not yet present one polished end-to-end “run to decision” experience.

### Current strengths

1. **Local-first trust story**: analysis can remain on the user’s machine and findings link back to source evidence (`workspace_api.py`, `evidence.py`).
2. **Unusually broad Locust coverage**: generation, execution helpers, reports, baselines, intelligence, CI gates, protocols, auth, and workspace APIs exist in one package.
3. **Deterministic fallback**: statistical insights do not depend on an LLM (`intelligence.py`). This is valuable for CI reproducibility.
4. **Real test fixtures and extensive tests**: the repository contains Locust 2.46.2-shaped fixtures and over a thousand tests according to `CHANGELOG.md`.
5. **Accessible intent**: focus styles, `aria-live`, responsive CSS, and explicit empty/error guidance appear in the workspace code and docs.
6. **Extensible evidence model**: source-linked findings and evidence bundles can become the product’s differentiation rather than a reporting afterthought.

### Constraints for planning

- Preserve Python 3.9+ and Locust-native workflows.
- Do not require a hosted control plane for core value.
- Keep deterministic analysis as the source of truth; LLM output stays optional and clearly separated.
- Maintain existing CLIs and public APIs.
- Treat the local SQLite cipher as development-only; production deployment requires a real KMS and authentication boundary (`docs/performance-workspace.md`).
- Avoid adding operational dependencies unless they unlock an optional integration. Grafana/Prometheus/OTel should be adapters, not prerequisites.

## Current-State Gap Analysis

| Area | Verified current state | Gap and consequence |
|---|---|---|
| First use | `/workspace/start` accepts a CSV prefix string | No file picker, ZIP import, auto-discovery, sample run, or recent runs. New users must understand Locust naming and server paths. |
| Run history | SQLite stores conceptual runs/results, while analysis endpoint returns an immediate payload | No unified persisted analysis record linking input files, baseline, policy, findings, and exported evidence. |
| Diagnostics UX | Findings include severity, confidence, source and next check | No charts or drill-down from run timeline to endpoint to raw rows; difficult to validate an automated conclusion visually. |
| Baselines | CLI accepts prior prefix or stored baseline; `baseline.py` has named baselines | Baseline creation, promotion, environment assignment, comparison history, and stale-baseline warnings are not a cohesive UI workflow. |
| CI governance | Exit codes and evidence bundles exist | No first-class PR summary/check-run contract, policy version display, waiver workflow in the guided path, or “why this gate changed” view. |
| Observability | OTel examples and Grafana dashboards exist | No direct attachment of metric/log/trace snapshots to a finding. Users still operate a separate stack and correlate manually. |
| Scenario studio | Domain/API supports protocol steps | Broad promise exceeds UI maturity. Competing no-code recorders are far ahead, creating expectation risk. |
| Security | API key in production mode; path confinement | Single API key, no user identity/RBAC/CSRF/rate limit; local vault cipher explicitly not production grade. |
| Packaging/distribution | PyPI-style package, Docker, Railway | No clear paid packaging, migration path, telemetry policy, or support boundary. |
| Documentation | Extensive reference guides | Some docs contain inconsistencies or stale examples, and breadth makes the recommended golden path hard to find. |

Maturity assessment: **late prototype / early product**. Core engines and tests are mature enough for real use, while the workspace and commercial product experience need consolidation.

## Target Users and Jobs to Be Done

| Segment | Primary job | Current alternative | Buying trigger |
|---|---|---|---|
| Python developer or small QA team using Locust | “Tell me whether this run is safe and what changed.” | CSV/HTML inspection, spreadsheets, custom scripts | Repeated release gates, unexplained regressions, no dedicated performance engineer |
| Performance engineer | “Preserve test history and find the bottleneck quickly.” | Grafana + Timescale/Prometheus, commercial cloud | Setup/maintenance burden, need for shareable evidence |
| Platform/SRE team | “Make performance gates consistent across repositories.” | CI scripts, k6/Gatling cloud, Azure Load Testing | Governance, auditability, standardized SLOs and reports |
| Regulated/security-sensitive team | “Analyze without uploading traffic, URLs, errors, or secrets.” | On-prem enterprise suite, custom internal tooling | Data residency, secrets, compliance evidence |
| Engineering manager | “Understand release risk without reading raw percentiles.” | Screenshots and expert interpretation | Need for concise, defensible go/no-go decisions |

## Target-Market Pain Points

| User problem | Segment | Recurrence observed | Evidence | Confidence | Implication |
|---|---|---:|---|---|---|
| Reporting and observations are harder than generating load | QA/performance engineers | Repeated across Reddit thread and analysis guides | Reddit “Performance testing tools” commenter: reporting/observations are “by far the hardest”; OneUptime states analysis is where value comes from. Accessed 2026-08-09. https://www.reddit.com/r/softwaretesting/comments/1c7q8l6/performance_testing_tools/ ; https://oneuptime.com/blog/post/2026-01-28-analyze-locust-test-results/view | HIGH | Lead with decision quality, not load generation. |
| Locust UI cannot filter/slice custom context | Advanced Locust users | Direct Q&A plus ecosystem workaround | Stack Overflow answer says Locust UI does not support filtering/slicing by context and suggests custom storage or cloud. Accessed 2026-08-09. https://stackoverflow.com/questions/78877954/collect-and-chart-analyze-additional-metrics-with-locust | HIGH | Add endpoint/context drill-down and portable evidence schema. |
| Historical comparison requires external infrastructure | Performance engineers | Repeated in Locust-plugins docs and third-party guides | Locust-plugins uses Postgres/Timescale + Grafana specifically to persist runs and track changes; BlazeMeter notes built-in metrics are not stored for future comparison. Accessed 2026-08-09. https://github.com/SvenskaSpel/locust-plugins/tree/master/locust_plugins/dashboards ; https://www.blazemeter.com/blog/locust-grafana | HIGH | Zero-ops local run history is a strong wedge. |
| Tool choice must align with team language and CI stack | Developers/platform teams | Multiple Reddit comments | Reddit users recommend Locust for Python shops, k6 for Grafana/JS teams, and stress version control/integration. Accessed 2026-08-09. https://www.reddit.com/r/softwaretesting/comments/1c7q8l6/performance_testing_tools/ ; https://www.reddit.com/r/QualityAssurance/comments/12q5tkf/performance_testing_options/ | HIGH | Stay Python/Locust-native and integrate rather than replace. |
| GUI tools lower entry friction, but complex workflows become hard | QA teams | Repeated comparison theme | Reddit discussion describes JMeter as easy to start but difficult for complex cases and XML/version-control heavy; k6 praised for code-first workflows. Accessed 2026-08-09. https://www.reddit.com/r/QualityAssurance/comments/12q5tkf/performance_testing_options/ | MEDIUM | Provide guided UI over versionable files, not a proprietary visual DSL. |
| Advanced analysis and collaboration are paid features | Teams and enterprises | All major commercial competitors | k6 markets run comparison and automatic insights; Gatling sells reports, collaboration and distributed testing; OctoPerf and LoadForge package analytics by tier. Accessed 2026-08-09. https://grafana.com/products/cloud/performance-load-testing-k6/ ; https://gatling.io/pricing ; https://octoperf.com/pricing/saas-and-on-premise-load-testing/ ; https://loadforge.com/pricing | HIGH | There is willingness to pay for the “after the run” workflow. |
| Self-hosted users accept setup to keep control, but resent operational tax | Platform/performance engineers | Ecosystem pattern | Locust-plugins explicitly requires Timescale/Grafana; hosted Locust documentation now points to Azure Load Testing for scalable execution, reporting and analysis. Accessed 2026-08-09. https://github.com/SvenskaSpel/locust-plugins/tree/master/locust_plugins/dashboards ; https://docs.locust.io/en/stable/hosted-load-testing.html | HIGH | Product should work from files/SQLite in minutes and optionally connect outward. |

## Competitor Weaknesses

### Grafana Cloud k6

- Strong developer experience, cloud scale, browser support, comparisons, Cloud Insights, and observability correlation.
- Weaknesses: JavaScript-centered rather than Locust/Python-native; cloud collaboration/retention is usage-priced; users report limited GUI in OSS and cloud expense as drawbacks. Official pricing is $0.15/VUh for self-serve usage, Pro begins at $19/month plus usage, and Enterprise starts at a $25,000/year spend commitment. Sources: https://grafana.com/products/cloud/performance-load-testing-k6/ ; https://gck6-calculator.grafana.com/ ; https://grafana.com/pricing/ ; https://www.g2.com/products/k6/reviews (accessed 2026-08-09).
- Exploitable gap: a Locust-native, offline analysis/history product with fixed-price team packaging and no telemetry upload.

### Gatling Enterprise

- Strong test-as-code, distributed execution, collaboration, advanced reporting, and growing AI-assisted workflow.
- Weaknesses: reviews mention setup difficulty and UI comprehension; JVM/DSL heritage and platform migration cost are barriers for Python teams. Basic is €89/month annually for 60,000 VUs, one testing hour, one generator and two seats; Team is €356/month annually for 180,000 VUs, five hours, three generators and ten seats. Sources: https://gatling.io/pricing ; https://www.peerspot.com/products/gatling-enterprise-reviews ; https://docs.gatling.io/tutorials/faq/ (accessed 2026-08-09).
- Exploitable gap: simpler local onboarding, transparent evidence, and Python-native customization.

### OctoPerf

- Strong codeless/JMeter workflow, SaaS and on-prem deployment, real-time reporting, and support.
- Weaknesses: tightly oriented around JMeter; unlimited plan starts at $999/month, making it oversized for small teams; independent summaries note onboarding and workflow complexity. Official free tier allows 50 concurrent users for 20 minutes; pay-per-test starts at $99 for a 1,000-VU test. Sources: https://octoperf.com/pricing/saas-and-on-premise-load-testing/ ; https://www.capterra.com/p/145638/Octoperf/ (accessed 2026-08-09).
- Exploitable gap: lightweight Locust workflows, code ownership, and affordable team analysis.

### LoadForge

- Directly adjacent because it supports custom Locustfiles, cloud load generation, AI analysis, and monitoring.
- Weaknesses: cloud-centric, plan caps on test duration/retention/seats, and the entry plan offers limited regions and integrations. Official annual pricing is $67/month Basic, $242/month Essential, and $417/month Premium. Sources: https://loadforge.com/pricing ; https://www.g2.com/products/loadforge/reviews (accessed 2026-08-09).
- Exploitable gap: self-hosted/local evidence, baseline governance, and no metered execution dependency.

### Azure Load Testing

- Microsoft-managed large-scale execution, built-in reporting/analysis, Application Insights integration, and CI support; Locust documentation calls it the easiest hosted path. Source: https://docs.locust.io/en/stable/hosted-load-testing.html (accessed 2026-08-09).
- Weaknesses: Azure account and cloud workflow required; broader platform complexity; less attractive to multi-cloud, local-only, or small teams.
- Exploitable gap: cloud-neutral local analysis that can later attach Azure evidence.

## Competitor Comparison

| Product | Core audience | Entry pricing observed | Best at | Repeated weakness/gap | Opportunity for this project |
|---|---|---:|---|---|---|
| Grafana Cloud k6 | Dev/SRE teams, Grafana users | Free; Pro $19/mo + usage; $0.15/VUh; Enterprise $25k/yr commit | Cloud scale, observability, browser + protocol, automatic insights | OSS has less GUI/history; cloud cost and JS ecosystem | Local Locust history and evidence, fixed-price/team option |
| Gatling Enterprise | Performance/DevOps teams | €89/mo Basic; €356/mo Team annual billing | Mature reports, distributed testing, collaboration | Setup/UI learning, JVM-centric | Python-native guided workflow |
| OctoPerf | JMeter-heavy QA/enterprise | Free; $99 per test; unlimited from $999/mo | Codeless JMeter, support, on-prem | Cost and complexity for small teams | Focused, lower-cost Locust analysis |
| LoadForge | DevOps and Locust users wanting cloud execution | $67/$242/$417 per month annual | Managed Locust scale, AI analysis, monitoring | Cloud/plan caps, retention and seat limits | Offline/unmetered analytics and policy evidence |
| Azure Load Testing | Azure engineering organizations | Usage-based, region/service dependent; no simple universal figure used here | Managed scale and App Insights | Azure dependency and platform overhead | Neutral analyzer with optional Azure adapter |
| Locust + locust-plugins | Experienced self-hosters | OSS infrastructure cost | Full custom control, detailed Grafana history | Timescale/Grafana setup and maintenance | Same decision value with SQLite/file-first setup |

## Validated Demand Signals

1. **Analysis is the expensive cognitive step**: independent guidance and practitioner discussion agree that interpreting percentiles, throughput, errors, and bottlenecks is the real value after a run. Confidence: HIGH. Sources: OneUptime (2026-01-28) and Reddit practitioner thread, accessed 2026-08-09.
2. **Persisted history and comparison are not optional for mature teams**: Locust-plugins built a complete Timescale/Grafana replacement for the Locust reporting UI, including old-run discovery and trend tracking. Confidence: HIGH. Source: locust-plugins GitHub, accessed 2026-08-09.
3. **Custom-context analysis is unmet in the default Locust UI**: a maintainer answer explicitly says slicing/filtering context is unsupported. Confidence: HIGH. Source: Stack Overflow, 2024-08-16.
4. **Commercial products monetize analysis, history, and collaboration**: all four direct commercial comparators gate these capabilities in paid tiers. Confidence: HIGH. Official pricing/product pages accessed 2026-08-09.
5. **Python alignment is a real selection criterion**: community advice repeatedly recommends Locust when the organization is Python-heavy. Confidence: MEDIUM-HIGH. Reddit threads accessed 2026-08-09.
6. **Local and private execution has durable value**: Locust’s ecosystem remains large, while hosted guidance is separate and optional. The main Locust repository showed roughly 28,000 GitHub stars in the search result, and Locust-plugins remains active with a June 2026 release. Confidence: MEDIUM. Sources: https://github.com/locustio/locust/issues ; https://pypi.org/project/locust-plugins/ (accessed 2026-08-09).

## Market and Pricing Evidence

### Direction and adoption

The category is moving toward code-first tests, CI gating, cloud-distributed execution, browser/protocol convergence, observability correlation, run comparison, and automated insights. Grafana k6 and Gatling both market automatic issue surfacing and “what changed” reporting; BrowserStack’s 2026 category review weights CI/CD, reporting/observability, scalability, and maintainability heavily. Sources: https://grafana.com/products/cloud/performance-load-testing-k6/ ; https://gatling.io/pricing ; https://www.browserstack.com/guide/performance-testing-tools (accessed 2026-08-09).

No reliable, category-specific TAM/CAGR figure was found that cleanly separates load testing from the much broader software-testing market. This report therefore does **not** provide a TAM, CAGR, or revenue forecast.

### Buying and monetization patterns

- **Usage-based**: Grafana Cloud k6 bills primarily in VUh at a published calculator rate of $0.15/VUh; browser users carry different multipliers. This aligns cost with scale but makes repeated regression runs harder to budget. Sources: https://gck6-calculator.grafana.com/ ; https://grafana.com/docs/grafana-cloud/platform/cost-management-and-billing/manage-invoices/understand-your-invoice/performance-testing-invoice/.
- **Seat/credit subscription**: Gatling combines VU/test-hour/generator quotas and seats at €89 and €356 monthly annual plans. Source: https://gatling.io/pricing.
- **High fixed-price unlimited/on-prem**: OctoPerf starts unlimited usage at $999/month, with a $99 one-test option. Source: https://octoperf.com/pricing/saas-and-on-premise-load-testing/.
- **Tiered managed service**: LoadForge spans $67 to $417/month annually with duration, retention, seat, location, and integration limits. Source: https://loadforge.com/pricing.
- **Open source plus operational cost**: Locust and locust-plugins are free software, but history/analysis requires databases, dashboards, and maintenance. Source: https://github.com/SvenskaSpel/locust-plugins/tree/master/locust_plugins/dashboards.

### Realistic pricing hypothesis

Evidence supports a low-friction open-core or local-team model, not enterprise-first pricing:

- Free: CLI and single-user local workspace, limited saved projects only by local storage.
- Team: approximately **$19–49/month per workspace** or **$199–399/year**, including shared policy packs, CI/PR summaries, longer run history, and support. This is a product hypothesis, not observed willingness-to-pay data.
- Business/self-hosted: approximately **$99–249/month** with SSO adapter, RBAC, audit retention, and supported deployment. This is also a hypothesis.

These ranges sit below managed load-generation products because the proposed product does not initially fund distributed cloud infrastructure. Validate with 10–15 customer interviews and paid design partners before implementing billing.

## Modern UX Expectations

### Category baseline

1. **Home/run inbox**: recent runs, status, environment, branch/commit, policy, baseline, and clear primary action.
2. **Import/onboarding**: drag-and-drop a ZIP or select a CSV prefix; auto-detect related files; show a sample project; validate before analysis.
3. **Run detail**: summary cards, latency/RPS/error timeline, endpoint table, SLO decision, anomaly cards, and evidence provenance.
4. **Compare view**: baseline selector, percentage and absolute deltas, confidence/data-quality indicators, and regression/improvement filters.
5. **Policy view**: versioned SLOs, scope, owner, effective date, waiver status, and preview against historical runs.
6. **Integrations/settings**: CI snippets, export formats, optional OTel/Prometheus adapters, data location, deletion controls.

### Required states

- Empty: sample run and exact command to generate compatible CSV.
- Loading: named stages such as “validating files,” “parsing history,” and “comparing baseline,” not an indefinite spinner.
- Success: decision first, then explanation and next check.
- Partial data: explicit grade and disabled analyses with reason, for example “capacity projection unavailable: 3 history points, 5 required.”
- Error: file-specific remediation and preserve the user’s selections.
- Disabled: explain permissions or prerequisites adjacent to the control.

### Responsiveness and accessibility

- Full keyboard navigation, visible focus, semantic headings/tables, programmatically associated labels, `aria-live` only for concise status updates, no color-only severity, and WCAG 2.2 AA contrast.
- Tables must become cards or horizontally scroll with sticky first column on narrow screens.
- Charts need text summaries, tooltips reachable by keyboard, and downloadable underlying data.
- Target measurable interaction standards: no layout break at 320 CSS px; all primary workflows keyboard-completable; automated axe scan with zero critical/serious violations; server response progress visible within 500 ms for local actions.

### Trust, privacy, and security expectations

- Show “data stays on this host” and exact files read.
- Display analyzer version, policy version, input hashes, and generated timestamp on every decision.
- Never transmit evidence without explicit opt-in; separate LLM enrichment from deterministic findings.
- Production UI needs secure sessions, CSRF, RBAC, tenant isolation, rate limits, audit log, and KMS-backed secret storage. The current API-key boundary and XOR-style local seal are not sufficient for a multi-user hosted product.

### Current fit

The project already meets parts of responsive design, visible focus, live status, deterministic findings, source provenance, and local-first messaging. It is missing the run inbox, import/discovery flow, persistent analysis history, visual comparison, production identity/security, and consolidated navigation.

## Open-Source and Automation Opportunities

| Opportunity | Relevant project/standard | Compatibility | Recommendation |
|---|---|---|---|
| Import full-history and per-request context | Locust CSV and `CsvRequestLogger` | Native Python/CSV | Add schema adapters and explicit data-quality detection. |
| Optional historical backend | locust-plugins Timescale schema | Python/Postgres/Grafana | Import or link existing runs; do not require Timescale. https://github.com/SvenskaSpel/locust-plugins |
| Metrics correlation | Prometheus/OpenMetrics HTTP API | Existing Grafana/Prometheus docs | Store query, time window, labels, and sampled result as evidence. |
| Trace correlation | OpenTelemetry/OTLP and W3C Trace Context | Existing OTel examples | Accept trace IDs and deep links; optionally ingest bounded trace summaries. |
| CI annotations | GitHub Checks/Step Summary, GitLab Code Quality/JUnit | Existing JSON/JUnit exports | Generate stable Markdown and machine schemas with policy/evidence hashes. |
| Portable evidence | CycloneDX-like provenance concepts, in-toto/SLSA attestations | JSON and hashing already present | Create a small versioned `performance-evidence.json` schema and sign later. |
| Local packaging | Docker Compose and SQLite | Existing Docker/Flask | Provide one-command local workspace with mounted results directory. |
| Charts | Lightweight accessible chart library | Flask/static assets | Use a maintained library with data table fallback; avoid building graphs by hand. |

Open-source evidence also highlights a boundary: Locust-plugins calls Locust “bare bones” and exists to stop teams reinventing common functionality. The project can become the curated decision workflow above that ecosystem, while contributing parsers/adapters upstream where appropriate. Source: https://github.com/SvenskaSpel/locust-plugins (accessed 2026-08-09).

## Differentiation Opportunities

| Capability | Problem solved / target | Evidence and competitor gap | Value | Complexity | Risk | Priority | Success criterion |
|---|---|---|---|---|---|---|---|
| Run Inbox + Smart Import | Paths and CSV naming block first use; all Locust users | Default Locust exports files but does not deliver persistent decision history; SaaS products provide project/run lists | Time-to-first-insight under 5 minutes | MEDIUM | ZIP/path security and schema drift | P0 | 90% of fixture bundles import without manual file mapping; first analysis completed in ≤5 min in usability test |
| Explainable Baseline Compare | Teams need to know what changed and why | History/comparison is a paid or infrastructure-heavy capability | Defensible CI decisions | MEDIUM | False causality from correlation | P0 | Every flagged regression links metric, current/baseline values, source rows, policy version, and confidence |
| Policy-to-CI Decision Artifact | Platform owners need consistent gates | Competitors gate via cloud platforms; current project has pieces but no polished contract | Auditability and cross-repo adoption | MEDIUM | Schema compatibility | P0 | Deterministic artifact hash for identical inputs; GitHub summary generated; exit code and UI decision always match |
| Observability Evidence Attachments | Engineers manually align load and system metrics | k6/Gatling monetize correlation; Locust OSS requires custom setup | Faster root-cause triage without lock-in | HIGH | Time alignment, cardinality, secret leakage | P1 | Attach at least one Prometheus series and one trace link to a finding; export contains query and bounded evidence |
| Data Quality and Confidence Guardrails | Partial history can create misleading predictions | Competitor “AI insights” often obscures evidence quality | Trust and reduced false positives | LOW | Users may dislike conservative results | P0 | No capacity prediction shown as actionable below minimum data; UI explains all disabled analyses |
| Local Team Collaboration | Security-sensitive teams cannot upload evidence | Commercial tools are cloud-first or expensive on-prem | Private shared history and reviews | HIGH | Auth/RBAC/KMS burden | P1 | Two roles, per-project access, append-only audit, supported backup/restore |
| Locust Ecosystem Importers | Existing users have Grafana/Timescale history | OSS ecosystem is fragmented | Faster switching and adoption | MEDIUM | External schema changes | P2 | Import locust-plugins run metadata and preserve source references for ≥95% of fixture records |

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
      {"type": "given", "text": "a ZIP contains one valid stats CSV and optional related files", "when": "the user imports it", "then": "the system maps the files, displays endpoint count and time range, and enables Analyze within 10 seconds for a 20 MB archive"},
      {"type": "given", "text": "a ZIP contains two possible stats prefixes", "when": "validation completes", "then": "the UI lists both candidates and requires one explicit selection before Analyze is enabled"},
      {"type": "given", "text": "an archive has an invalid path traversal entry or no stats CSV", "when": "the user imports it", "then": "the import is rejected, no file is written outside the workspace, and the UI names the failed safety or file requirement"}
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
      {"type": "given", "text": "50 saved runs across environments", "when": "the user filters by environment and failed status", "then": "every displayed run matches both filters and the result count is shown"},
      {"type": "given", "text": "a run has no branch metadata", "when": "a branch filter is active", "then": "the run is excluded and can be found under a Missing metadata filter"},
      {"type": "given", "text": "the run index cannot be read", "when": "the Inbox loads", "then": "an error state appears with a retry control and no stale status is presented as current"}
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
      {"type": "given", "text": "the workspace has no runs", "when": "the user chooses Try sample run", "then": "a sample analysis is created without network access and opens within 5 seconds"},
      {"type": "given", "text": "a sample run already exists", "when": "the user launches it again", "then": "the system opens the existing sample or creates a separately labelled copy without overwriting user data"},
      {"type": "given", "text": "sample assets are missing or fail hash verification", "when": "the user launches the sample", "then": "analysis does not run and the UI reports SAMPLE_ASSET_INVALID with a reinstall instruction"}
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
      {"type": "given", "text": "current and baseline runs share an endpoint", "when": "comparison runs", "then": "absolute and percentage p95, p99, error-rate, and request-count deltas are shown with current and baseline values"},
      {"type": "given", "text": "an endpoint exists in only one run", "when": "comparison runs", "then": "it is labelled Added or Missing and is not assigned a fabricated percentage delta"},
      {"type": "given", "text": "baseline files are unreadable or hashes changed", "when": "comparison starts", "then": "no decision is recalculated and the UI reports BASELINE_EVIDENCE_INVALID with the affected file"}
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
      {"type": "given", "text": "a run passed the selected policy and has complete evidence", "when": "an authorized user promotes it", "then": "it becomes the active baseline for that environment and an audit record captures old ID, new ID, reason, actor, and timestamp"},
      {"type": "given", "text": "an active baseline already exists", "when": "a replacement is confirmed", "then": "the prior baseline remains immutable in history and only the new baseline is marked active"},
      {"type": "given", "text": "the run failed policy or evidence verification", "when": "promotion is attempted", "then": "promotion is blocked and the UI lists each unmet prerequisite"}
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
      {"type": "given", "text": "identical input files, analyzer version, baseline, and policy", "when": "the artifact is generated twice", "then": "canonical JSON content and decision hash are byte-identical excluding an explicitly non-hashed generated-at field"},
      {"type": "given", "text": "a report has more than 20 findings", "when": "Markdown is generated", "then": "the summary shows the top 20 by severity and links to the complete JSON without changing the gate result"},
      {"type": "given", "text": "artifact writing fails", "when": "export is requested", "then": "no partial file is presented as complete and the UI reports the target path and retry action"}
    ]
  },
  {
    "id": "US-007",
    "epic": "Observability Evidence Correlation",
    "role": "SRE",
    "action": "attach Prometheus metrics to the exact load-test window",
    "benefit": "I can test whether latency regressions coincide with resource saturation",
    "story": "As an SRE, I want to attach Prometheus metrics to the exact load-test window, so that I can test whether latency regressions coincide with resource saturation.",
    "gui_flow": [
      "User opens a finding → sees Add observability evidence",
      "User selects Prometheus → enters endpoint alias and a saved query template",
      "User previews the derived start/end time and labels → sees a bounded sample count",
      "User clicks Attach → sees the metric overlaid with load-test p95 and RPS",
      "User exports evidence → query, window, labels, samples, and source URL alias are included"
    ],
    "acceptance_criteria": [
      {"type": "given", "text": "Prometheus returns a valid range vector for the run window", "when": "the user attaches it", "then": "the chart uses the same UTC time axis and the evidence stores query, start, end, step, labels, and returned samples"},
      {"type": "given", "text": "metric timestamps do not overlap at least 50% of the run window", "when": "preview runs", "then": "the UI labels alignment confidence LOW and does not state a causal conclusion"},
      {"type": "given", "text": "Prometheus is unreachable or returns invalid JSON", "when": "Attach is clicked", "then": "the finding remains unchanged and an error names the connection alias without exposing credentials"}
    ]
  },
  {
    "id": "US-008",
    "epic": "Observability Evidence Correlation",
    "role": "performance engineer",
    "action": "link a trace to a slow endpoint finding",
    "benefit": "I can move from a statistical regression to a concrete service path",
    "story": "As a performance engineer, I want to link a trace to a slow endpoint finding, so that I can move from a statistical regression to a concrete service path.",
    "gui_flow": [
      "User opens an endpoint regression → sees related trace IDs from imported context or Add trace",
      "User selects a trace ID → sees service, duration, status, and timestamp preview",
      "User clicks Attach → trace is listed under Evidence with a deep link",
      "User expands trace summary → sees the five longest spans and error spans",
      "User exports the decision → trace ID, provider alias, summary, and link template are preserved"
    ],
    "acceptance_criteria": [
      {"type": "given", "text": "a trace timestamp falls inside the finding window and endpoint identity matches", "when": "it is attached", "then": "the UI marks alignment HIGH and records the matching fields"},
      {"type": "given", "text": "a trace is outside the window or endpoint match is absent", "when": "it is attached", "then": "the UI permits it only as manual evidence and labels alignment LOW with the mismatch reason"},
      {"type": "given", "text": "the trace provider returns secret-bearing attributes", "when": "the summary is stored", "then": "configured sensitive keys are redacted and the export contains no original sensitive value"}
    ]
  },
  {
    "id": "US-009",
    "epic": "Observability Evidence Correlation",
    "role": "security-conscious platform owner",
    "action": "control whether external evidence connections may transmit run metadata",
    "benefit": "the analysis remains compliant with local-only data rules",
    "story": "As a security-conscious platform owner, I want to control whether external evidence connections may transmit run metadata, so that the analysis remains compliant with local-only data rules.",
    "gui_flow": [
      "User opens Settings → sees Data handling with Local-only enabled",
      "User opens an integration → sees exact fields and hosts used by preview and attach",
      "User attempts to enable outbound access → sees role requirement and audit notice",
      "Authorized user enables one allow-listed host → connectivity test runs",
      "User returns to Run Detail → only approved integrations are available"
    ],
    "acceptance_criteria": [
      {"type": "given", "text": "Local-only mode is enabled", "when": "any user attempts an outbound integration call", "then": "the request is blocked before DNS/network access and an audit event records integration alias and action without payload data"},
      {"type": "given", "text": "an authorized user allow-lists one HTTPS host", "when": "a connection is tested", "then": "requests are limited to that host, HTTPS is required, and redirects to other hosts are rejected"},
      {"type": "given", "text": "a non-authorized user changes data-handling policy", "when": "the form is submitted", "then": "the server returns 403, settings remain unchanged, and the UI announces insufficient permission"}
    ]
  }
]
```

## Priority-Ranked Development Recommendations

1. **P0: Build the Run Inbox + Smart Import vertical slice.** It removes the biggest onboarding defect and creates the persistence foundation for all later features. Include archive-safe import, file auto-detection, data-quality grading, saved analysis records, recent-run filtering, and sample data.
2. **P0: Unify baselines, policies, findings, and evidence into one Run Detail/Compare view.** Reuse existing analyzers and evidence models. Add timeline and endpoint drill-down, explicit baseline promotion, stale/incompatible baseline warnings, and canonical decision export.
3. **P0: Productize CI output.** Publish a versioned JSON schema, canonical hashing rules, concise Markdown summary, stable exit-code mapping, and examples for GitHub Actions/GitLab/Jenkins.
4. **P0: Make confidence and missing-data behavior first class.** Never hide insufficient data behind an “AI” label. Show why an analysis is unavailable and what command/options produce the required evidence.
5. **P1: Add bounded Prometheus and OpenTelemetry evidence adapters.** Start read-only, explicit, and local-first. Store evidence snapshots or links, not unrestricted raw telemetry.
6. **P1: Harden multi-user deployment only after local workflow validation.** Add identity, RBAC, CSRF, KMS-backed secrets, audit retention, and backup/restore as a separate business tier.
7. **P2: Import ecosystem histories.** Add locust-plugins/Timescale import and cloud-provider links after the core schema is stable.

## Recommended Scope for the Next Development Pass

### In scope

- A persistent `AnalysisRun` model linking imported files, hashes, analyzer version, status, data-quality grade, baseline, policy, findings, and exports.
- Safe ZIP/directory import with auto-detection for Locust stats/failures/exceptions/history.
- Run Inbox with empty, loading, filtering, error, and sample states.
- Run Detail with summary, timeline, endpoint table, findings, confidence, and source-row drawer.
- Baseline promotion and Compare view with immutable history.
- Canonical versioned decision JSON and Markdown PR summary.
- Full keyboard/accessibility regression tests and responsive visual states.
- Targeted tests plus the complete existing regression suite after implementation.

### Explicitly out of scope

- Hosted/distributed load generation.
- Browser recording or full no-code scenario authoring.
- Billing implementation.
- General-purpose dashboard builder.
- Automatic remediation or autonomous production changes.
- Multi-tenant SaaS before authentication/KMS architecture is complete.

This scope is small enough to ship as one coherent product pass and broad enough to test the core commercial hypothesis: users will adopt a local-first Locust decision workspace if it materially shortens time from CSV files to an explainable release decision.

## Risks, Unknowns, and Assumptions

- **Demand concentration risk**: evidence validates the problem, but not the number of Locust users willing to pay. Run 10–15 structured interviews and seek at least three paid design partners.
- **Broad repository positioning**: the project currently promises templates, generation, workspace, intelligence, dashboards, vault, capacity and more. Without a narrow landing page, users may not understand the primary value.
- **Trust risk**: statistical heuristics can be mistaken for causality. Every recommendation must expose data, method, thresholds, and limitations.
- **Security risk**: the current production API-key check and development cipher are insufficient for shared hosting. Keep next pass local/single-team by default.
- **Data compatibility risk**: Locust CSV schemas and custom listeners vary. Preserve tolerant parsing and add explicit schema/version reporting.
- **Performance risk**: large full-history or per-request archives can be substantial. Stream parsing, apply size limits, and benchmark 20 MB, 100 MB, and 1 GB cases.
- **Pricing assumption**: proposed price bands are hypotheses inferred from competitor anchors. No direct willingness-to-pay survey was found.
- **Market-size unknown**: no reliable narrow TAM/CAGR was found; none is asserted.
- **Competitor response**: k6, Gatling, and LoadForge can add more AI analysis. The moat should be evidence provenance, deterministic local operation, and Locust/Python depth.

## Sources

Access date for all web sources: **2026-08-09**, unless a publication date is stated.

1. Locust documentation, “Retrieve test statistics in CSV format.” https://docs.locust.io/en/2.37.0/retrieving-stats.html
2. Locust documentation, “Hosted load testing.” https://docs.locust.io/en/stable/hosted-load-testing.html
3. Locust GitHub issues index. https://github.com/locustio/locust/issues
4. Locust changelog highlights. https://docs.locust.io/en/stable/changelog.html
5. Stack Overflow, “Collect (and chart/analyze) additional metrics with Locust,” 2024-08-16. https://stackoverflow.com/questions/78877954/collect-and-chart-analyze-additional-metrics-with-locust
6. OneUptime, “How to Analyze Locust Test Results,” 2026-01-28. https://oneuptime.com/blog/post/2026-01-28-analyze-locust-test-results/view
7. Reddit r/softwaretesting, “Performance testing tools.” https://www.reddit.com/r/softwaretesting/comments/1c7q8l6/performance_testing_tools/
8. Reddit r/QualityAssurance, “Performance Testing Options.” https://www.reddit.com/r/QualityAssurance/comments/12q5tkf/performance_testing_options/
9. Svenska Spel, locust-plugins repository. https://github.com/SvenskaSpel/locust-plugins
10. Svenska Spel, Locust dashboards. https://github.com/SvenskaSpel/locust-plugins/tree/master/locust_plugins/dashboards
11. PyPI, locust-plugins release page. https://pypi.org/project/locust-plugins/
12. BlazeMeter, “Locust Monitoring with Grafana in Just 15 Minutes.” https://www.blazemeter.com/blog/locust-grafana
13. Grafana Labs, Grafana Cloud k6 product page. https://grafana.com/products/cloud/performance-load-testing-k6/
14. Grafana Labs, pricing. https://grafana.com/pricing/
15. Grafana Labs, k6 calculator and VUh rate. https://gck6-calculator.grafana.com/
16. Grafana Labs, Performance Testing invoice/VUh documentation. https://grafana.com/docs/grafana-cloud/platform/cost-management-and-billing/manage-invoices/understand-your-invoice/performance-testing-invoice/
17. G2, k6 reviews. https://www.g2.com/products/k6/reviews
18. Gatling, pricing. https://gatling.io/pricing
19. Gatling, FAQ. https://docs.gatling.io/tutorials/faq/
20. PeerSpot, Gatling Enterprise reviews. https://www.peerspot.com/products/gatling-enterprise-reviews
21. OctoPerf, official pricing. https://octoperf.com/pricing/saas-and-on-premise-load-testing/
22. Capterra, OctoPerf profile/review. https://www.capterra.com/p/145638/Octoperf/
23. LoadForge, official pricing. https://loadforge.com/pricing
24. G2, LoadForge reviews. https://www.g2.com/products/loadforge/reviews
25. BrowserStack, “Top 10 Performance Testing Tools in 2026,” updated 2026-06-09. https://www.browserstack.com/guide/performance-testing-tools

Project evidence reviewed includes `README.md`, `CHANGELOG.md`, `pyproject.toml`, `Dockerfile`, `docs/`, `examples/`, `src/locust_templates/`, `tests/`, workflow assets, and the pre-existing phase documents. Code-derived conclusions in this report cite the relevant paths and symbols inline.
