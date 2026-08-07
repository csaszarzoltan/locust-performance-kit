# Research Findings

## Executive Summary

Locust Performance Kit is a mature, Python-first companion product for Locust that bundles reusable test templates, multi-protocol users, OpenAPI script generation, reporting, baselines, CI gates, observability assets, a server-rendered performance workspace, and a deterministic “AI Performance Intelligence” analyzer. Verified behavior is spread across 34 Python modules and 73 test/fixture files; the public package targets Python 3.9+, ships three CLIs (`locust-report`, `locust-gen`, `locust-kit`), and is versioned 1.6.0 (`pyproject.toml`; `src/locust_templates/__init__.py`; `src/locust_templates/cli*.py`).

The strongest market opportunity is not another load generator. Locust itself is established, extensible, and free, while k6, Gatling, BlazeMeter, and LoadFocus increasingly monetize the workflow around test creation, cloud execution, collaboration, historical comparison, and actionable analysis [S1][S4][S7][S8]. This project should become the **local-first performance engineering control plane for Python/Locust teams**: easy scenario creation, trustworthy run comparison, evidence-linked diagnostics, and portable CI artifacts without forcing test data into a SaaS.

Demand is validated by recurring signals: developers value code-first scripting, realistic flows, CI integration, and open-source economics; they struggle with generator capacity, setup complexity, fragmented plugins, interpreting results, maintaining authentication/test data, and converting findings into actions [S2][S3][S9][S10][S11][S12]. Commercial pricing also demonstrates willingness to pay for workflow and scale: Grafana Cloud k6 starts with a free allowance then usage pricing; Gatling lists €89 and €356 monthly annual-billed tiers; BlazeMeter lists $99/$499 effective monthly annual performance tiers; LoadFocus lists $79/$329/$499 monthly tiers and explicitly bundles AI analyses [S4][S5][S6][S7].

The next development pass should be deliberately narrow:

1. **P0: Guided run workspace and first-run path** that connects existing scenario import/generation, execution configuration, artifacts, and analysis in one coherent responsive flow.
2. **P0: Evidence-linked comparison and diagnosis** that shows current versus baseline, confidence, contributing endpoints/time windows, and recommended next checks, with deterministic analysis always visible.
3. **P1: Portable CI evidence bundle** that exports a stable JSON/Markdown/JUnit package plus a PR-ready summary and provenance, making local and CI results reproducible.

These priorities exploit capabilities already present, close the largest UX and trust gaps, and avoid competing with cloud vendors on raw distributed infrastructure.

## Project Understanding

### What the project currently does

Verified from the source tree:

- Provides reusable HTTP, stress, spike, soak, web UI, gRPC, GraphQL, and WebSocket Locust users (`src/locust_templates/api_load.py:APIUser`; `stress.py:StressUser`; `spike.py:SpikeUser`; `soak.py:SoakUser`; `grpc.py:GrpcUser`; `graphql.py:GraphQLUser`; `websocket.py:WebSocketUser`).
- Parses Locust CSV output and renders HTML, JSON, Markdown, and JUnit reports (`report_data.py:ReportData.from_csv`; `exporters.py:HTMLExporter`, `JSONExporter`, `MarkdownExporter`, `JUnitXMLExporter`; `cli.py:main`).
- Saves and compares named baselines (`baseline.py:PerformanceBaseline`).
- Correlates request chains and cascade failures (`correlator.py:RequestCorrelator`).
- Provides live metrics and rule-based alerts (`live_dashboard.py:LiveDashboard`; `alerts.py:AlertEngine`).
- Parses OpenAPI/Swagger documents and generates Locust scripts (`openapi_parser.py:parse_spec`; `locust_generator.py:generate_locust_script`; `cli_gen.py`).
- Parses run history, detects anomalies/bottlenecks, projects capacity, checks SLOs, creates deterministic insights, and optionally calls an OpenAI-compatible endpoint (`intelligence.py:RunProfile`, `AnomalyDetector`, `BottleneckDetector`, `CapacityProjector`, `InsightGenerator`, `LLMInsightProvider`, `analyze_run`; `cli_analyze.py`).
- Includes a Flask/SQLite performance engineering workspace with scenario, recovery, diagnostics, policy, test-data vault, estimate, API, and server-rendered workspace concepts (`product_workspace.py:PerformanceWorkspace`; `workspace_api.py:create_workspace_blueprint`; `render_workspace`).
- Supplies Grafana dashboards, GitHub Actions guidance/workflow assets, Docker/Railway deployment files, examples, and extensive documentation (`grafana/dashboards/`; `.github/workflows/perf-test.yml`; `docs/`; `examples/`).

### Target users and primary use cases

**Verified positioning:** “Production-ready Locust load testing templates for enterprise performance testing” (`pyproject.toml`). README use cases cover API load testing, stress/spike/soak tests, CI/CD integration, baselines, reporting, notifications, observability, and a performance engineering workspace (`README.md`, especially “Use Cases” and “Performance Engineering Workspace”).

**Likely core users, inferred from the code and market:**

1. Python backend developers who want realistic tests without adopting JavaScript/Scala tooling.
2. QA and performance engineers standardizing Locust across teams.
3. DevOps/SRE teams adding performance gates and artifacts to CI.
4. Security-conscious or regulated teams preferring local/self-hosted analysis.
5. Small teams that cannot justify $79–$649 monthly cloud plans but need better workflow than raw Locust CSVs [S4][S5][S6][S7].

### Architecture and technology stack

- Python package with `src/` layout; Python >=3.9; setuptools build (`pyproject.toml`).
- Core dependencies: Locust, Requests, python-dotenv, PyYAML, and openapi-spec-validator. Optional gRPC, OpenTelemetry, and WebSocket groups (`pyproject.toml`).
- Dataclass-heavy domain and report models; argparse CLIs; standard-library statistical analysis and HTTP for the optional LLM (`intelligence.py`).
- Flask blueprint and SQLite-backed workspace service (`workspace_api.py`; `product_workspace.py`). Flask is imported by workspace code but is not declared in the package dependencies, creating an installability risk for that feature.
- Server-rendered HTML and self-contained report output; Grafana JSON dashboards; GitHub Actions YAML.
- Test suite organized into unit, integration, visual, CLI/intelligence tests, and static real-Locust-shaped fixture CSVs (`tests/`).

### Existing UI and principal user flows

There are three partially separate experiences:

1. **Locust native web UI** to configure and run tests, inherited from Locust.
2. **Command-line workflow**: generate/import scenario, run Locust with CSV, then call `locust-report` or `locust-kit analyze` and inspect artifacts (`README.md`; `docs/getting-started.md`; `docs/ai-performance-intelligence.md`).
3. **Performance workspace**: server-rendered Flask pages/API around scenarios, recovery, diagnostics, policies, secrets, and estimates (`product_workspace.py:render_workspace`; `workspace_api.py`).

The principal end-to-end flow is not yet unified. A user must understand which surface owns authoring, execution, monitoring, analysis, and retention. This is the central product gap.

### Current strengths

- Broad functional coverage for a small open-source package.
- Strong Python/Locust fit and extensibility, matching community praise for Locust’s ability to model essentially anything Python can do [S9][S10].
- Deterministic analysis that does not require an LLM, a strong trust and privacy differentiator as developers rank privacy, pricing, and better alternatives above “lack of AI” when rejecting tools [S19].
- Multi-format outputs and clear CI exit-code semantics.
- Real Locust-shaped fixtures and an unusually large test surface for parser/analysis behavior.
- Local-first operation and no mandatory vendor account.
- Existing observability, baseline, and workspace primitives create leverage for a coherent product without a rewrite.

### Maturity assessment

The repository is feature-rich and test-oriented, but product maturity is uneven. Release documentation claims 1,068 passing tests (`CHANGELOG.md`), while this research environment could not execute the suite because Locust and Ruff were not installed. The collection failure was environmental (`ModuleNotFoundError: locust`), not evidence of test failures. Distribution readiness is weakened by inconsistent setup instructions (`docs/getting-started.md` says `pip install -r requirements.txt`, while the package is defined in `pyproject.toml`), a malformed Docker command (`Dockerfile` has `EXPOSE $` and a broken shell expression), and an undeclared Flask dependency for workspace modules.

## Current-State Gap Analysis

| Area | What exists | Gap | Evidence / implication |
|---|---|---|---|
| Product coherence | Three CLIs, examples, native Locust UI, separate Flask workspace | No single happy path from spec/scenario to run to diagnosis | New users must compose the product mentally; onboarding should unify existing assets before adding more engines. |
| Authoring | OpenAPI parser/generator and templates | No guided preview/edit/validate workflow; generated path parameters and payloads still require user repair | k6 Studio and Gatling support capture/visual or no-code creation [S4][S8]. |
| Execution | Locust commands, shapes, CI workflow | Workspace is not clearly wired to actual local/distributed run orchestration | Users cite local generator exhaustion and prefer cloud for large stress tests [S10]. Product should show generator saturation and remote-run adapters rather than promise cloud scale. |
| Analysis | Strong deterministic analyzer, baselines, reports | Results are reports, not an evidence graph; recommendations do not visibly link to exact rows/time windows/telemetry | AI distrust is material: 46% distrust accuracy and 66% dislike “almost right” outputs [S19]. Explainability is table stakes. |
| Historical collaboration | Named baselines, JSON artifacts, workspace data | No first-class project/run history, approvals, comments, ownership, or review workflow | Competitors sell collaboration, trends, and centralized results [S4][S8]. |
| UX states | Workspace docs mention empty/current/partial/error states | No verified screenshots or end-to-end visual regression artifacts in the archive | The project’s own `AGENTS.md` asks for visual tests/screenshots, but current visual tests are structural. |
| Accessibility | Workspace documentation claims keyboard/focus/ARIA behavior | No automated accessibility test dependency or audit | Add semantic/keyboard and contrast checks to acceptance criteria. |
| Security | Vault abstraction, tenant checks, LLM key handling guidance | Local cipher explicitly not production KMS; auth boundary, CSRF, tenant identity, and rate limits are deployment responsibilities | `docs/performance-workspace.md` correctly states these limits; UI must expose deployment-security status. |
| Packaging | PyPI-style package, Docker/Railway assets | Flask undeclared; Dockerfile malformed; README/install paths conflict | Fixing distribution is essential before marketing the workspace. |
| Documentation | 20 docs files and long README | Duplication, contradictions, stale statements, and a static generated timestamp limitation | Documentation needs task-oriented consolidation and executable examples. |
| Test execution | Large tests and fixtures | No lock-step bootstrap command visible; environment lacks declared dev setup here | Add `make verify` or equivalent and package/workspace extras. |
| Monetization | None | No paid value boundary | Market indicates payment for collaboration, retention, distributed capacity, support, and analysis rather than basic local generation [S4][S5][S6][S7]. |

## Target Users and Jobs to Be Done

| Segment | Primary job | Success definition | Current fit |
|---|---|---|---|
| Python backend developer | “Turn an API/spec/user flow into a realistic load test and know whether my change regressed performance.” | Working test in <15 minutes; CI gate; actionable diff | Strong primitives, fragmented flow |
| QA/performance engineer | “Standardize scenarios, SLOs, test data, reports, and evidence across projects.” | Reusable policies, reviewable runs, repeatability | Good domain concepts, weak collaboration UI |
| SRE/DevOps engineer | “Run repeatable tests in CI and connect regressions to service telemetry.” | Portable artifact, stable exit codes, links to metrics/traces | Good CI/report pieces, missing end-to-end correlation |
| Engineering manager | “Understand release risk and capacity without reading raw CSVs.” | Concise, trustworthy, comparable decision summary | Analyzer helps; trust/provenance and history need work |
| Regulated/self-hosted team | “Keep sensitive traffic models and results inside our boundary.” | No mandatory SaaS; auditable storage and access | Strong local-first direction; production security adapters incomplete |
| Consultant/small agency | “Deliver branded, defensible performance findings at predictable cost.” | Shareable evidence bundle and reusable templates | Reports exist; project packaging/branding and client separation are incomplete |

## Target-Market Pain Points

| User problem | Segment | Recurrence observed | Evidence | Confidence | Implication |
|---|---|---:|---|---|---|
| Raw load-test output does not explain what broke or what to do next | Developers, QA, managers | Repeated across commercial positioning and analysis-focused products | Grafana Cloud Insights, Gatling AI analysis, LoadFocus AI explanations [S4][S7][S8] | HIGH | Make diagnosis evidence-linked and deterministic, not just narrative. |
| Local generator capacity can become the bottleneck before the system under test | Developers/SRE | Direct practitioner report plus widespread cloud-scale positioning | Reddit practitioner; k6/Gatling/BlazeMeter cloud scale [S10][S4][S5][S8] | MEDIUM-HIGH | Add generator-health checks and pluggable remote execution, not a proprietary cloud in the next pass. |
| Teams want realistic flows and code-level flexibility | Developers | Repeated community praise | Reddit QA and ExperiencedDevs; Locust official positioning [S9][S10][S1] | HIGH | Preserve Python-first test-as-code and expose code rather than hiding it. |
| Locust users repeatedly rebuild basic integrations and data-management features | Performance engineers | Explicit ecosystem rationale, broad plugin catalog | locust-plugins and Awesome Locust [S12][S13][S14] | HIGH | Integrate via adapters and compatibility, avoid duplicating mature plugins. |
| Authentication refresh and evolving tokens complicate long tests | API teams | Current Locust feature request; project already has auth abstractions | Locust issue #3437 [S11] | MEDIUM | Add request-time credential refresh hooks and secret health status. |
| Downloaded or static reports need clearer behavior and richer analysis | QA/managers | Current upstream issue plus competitor investment | Locust issue #3407; Grafana/Gatling analysis pages [S11][S4][S8] | MEDIUM | Make reports self-describing, timestamped, provenance-rich, and linked to source artifacts. |
| Users want pause/resume and operational control from a UI | Test operators | Current upstream feature request | Locust issue #3387 [S11] | MEDIUM | Workspace run control is valuable, but must reflect actual Locust capability and distributed state. |
| Tool choice is constrained by pricing and privacy | Small teams, regulated teams | Broad developer survey plus pricing spread | Stack Overflow 2025; official vendor pricing [S19][S4][S5][S6][S7] | HIGH | Local-first free core with optional paid collaboration/support is credible. |
| AI-generated conclusions are hard to trust | All accountable technical roles | Strong cross-developer survey signal | 46% distrust AI accuracy; 66% cite almost-right answers [S19] | HIGH | Always show formulas, source rows, confidence, and non-LLM fallback. |
| Product setup and learning curves block adoption | New users | Repeated in reviews and tool comparisons | k6/Gatling/BlazeMeter review summaries and community discussions [S20][S21][S9] | MEDIUM | Optimize first-run success and progressive disclosure. |

## Competitor Weaknesses

### Grafana Cloud k6

- Strong developer experience, test studio, browser/API testing, cloud scale, insights, trends, and observability correlation [S4].
- Weakness/opportunity: paid usage beyond the free allowance, a $19 platform fee plus usage pricing, and a $25,000/year enterprise minimum; JavaScript-centric authoring; deep value is tied to Grafana Cloud [S4].
- Exploitable gap: a Python-native, self-hosted evidence workflow with portable outputs and no mandatory observability-cloud commitment.

### Gatling Enterprise

- Strong asynchronous engine, multi-language SDKs, no-code/Postman options, AI analysis, campaigns, collaboration, distributed testing, and enterprise management [S8].
- Weakness/opportunity: paid tiers and enterprise boundary; Community Edition lacks the centralized workflow; code-first SDKs still impose a language/tool learning curve [S5][S20].
- Exploitable gap: simpler Python onboarding and local-first diagnostics for teams already invested in Locust.

### BlazeMeter

- Strong breadth across performance, API, functional testing, service virtualization, test data, many open-source frameworks, and enterprise scale [S6][S22].
- Weakness/opportunity: pricing jumps from $99 effective monthly annual to $499 for Pro, then custom enterprise; broad platform complexity can be excessive for small Python teams [S6][S21].
- Exploitable gap: focused performance-engineering workflow, predictable deployment, and fewer concepts.

### LoadFocus

- Strong browser-based setup, multi-location cloud execution, JMeter/k6 support, monitoring, and bundled AI analyses [S7].
- Weakness/opportunity: closed cloud platform, monthly analysis limits, data-retention tiers, and no Locust-native positioning [S7].
- Exploitable gap: unlimited local deterministic analysis, source-level explainability, and Locust-specific workflows.

### Raw Locust plus community plugins

- Strongest flexibility, open-source economics, Python fit, distributed execution, and ecosystem [S1][S12][S14].
- Weakness/opportunity: Locust core is intentionally bare bones; users assemble reporting, checks, test data, dashboards, protocols, and orchestration themselves [S12].
- Exploitable gap: curated integration, coherent UX, opinionated defaults, and support without forking Locust.

## Competitor Comparison

| Product | Primary audience / positioning | Pricing observed 2026 | Creation and onboarding | Analysis / collaboration | Main strength | Gap for this project |
|---|---|---|---|---|---|---|
| Grafana Cloud k6 | Developer-centric performance testing integrated with observability | Free 500 VUh; Pro from $0.15/VUh plus $19/month; Enterprise minimum $25k/year [S4] | k6 Studio, JS, browser and API flows | Cloud Insights, trends, observability correlation | Polished end-to-end cloud workflow | Python/Locust-native, local-first, privacy-conscious alternative |
| Gatling Enterprise | Continuous performance intelligence for teams and enterprises | Basic €89/month, Team €356/month annual billed, Enterprise custom [S5] | Code, no-code, Postman, multiple SDKs | AI analysis, campaigns, dashboards, collaboration | High-scale engine and team workflow | Simpler Python learning curve, self-hosted lightweight workflow |
| BlazeMeter | Broad enterprise continuous testing across many frameworks | Performance Basic $99/month annual, Pro $499/month annual, enterprise custom [S6] | Upload/import across 20+ frameworks | Real-time analytics, CI, enterprise management | Breadth, scale, service virtualization | Focused and affordable Locust workflow |
| LoadFocus | Accessible cloud load testing/monitoring with AI explanations | $79/$329/$499 monthly; free/starter options; AI quotas [S7] | Browser configuration, JMeter/k6 upload | AI analysis, baseline comparison on higher tiers | Simple cloud launch and explanation | Unlimited local analysis and source-linked trust |
| Raw Locust ecosystem | Python test-as-code and extensibility | Free/open source [S1] | Python code, web UI, plugins | Basic web UI/CSV; assemble extras | Flexibility and community | Coherent product experience and maintained integrations |

## Validated Demand Signals

| Signal | Observation | Strength | Product interpretation |
|---|---|---|---|
| Locust community scale | Official GitHub shows roughly 28k stars and 3.2k forks; Locust positions itself as scalable Python load testing [S1][S11] | HIGH | Large addressable open-source installed base, though stars are not paying users. |
| Python flexibility | Practitioners describe Locust as highly customizable and good for realistic scenarios/CI [S9][S10] | HIGH | Keep code-first Python at the center. |
| Cloud scale demand | Practitioner reports local machine exhaustion; all major paid products emphasize distributed/global load [S10][S4][S8][S22] | HIGH | Remote execution adapters and load-generator diagnostics matter. |
| Result-analysis demand | In the archived k6 feature-request repo, result analysis was the largest issue label group (30 of 74 issues) [S15] | MEDIUM-HIGH | Analysis and history are recurring needs, not a novelty. |
| Plugin fragmentation | locust-plugins explicitly exists because basic functionality is repeatedly reinvented [S12] | HIGH | Curate and compose ecosystem capabilities. |
| AI adoption with distrust | 84% use/plan AI tools, but 46% distrust accuracy and lack of AI ranks low as a purchase rejection reason [S19] | HIGH | “Trustworthy automation” beats “AI-first” branding. |
| Willingness to pay | Multiple vendors sustain tiers from ~$79 to ~$649 monthly and enterprise contracts [S4][S5][S6][S7] | HIGH | Buyers pay for scale, retention, team workflow, and support. |
| Shift-left and CI | Vendor positioning and market reports consistently emphasize CI/SLO gating [S4][S8][S16][S17] | MEDIUM-HIGH | PR-ready, deterministic gates should be a first-class workflow. |
| Market growth | Published estimates vary sharply: QYResearch estimates $961M in 2024 to $1.32B by 2031 (4.7% CAGR), while TrendX estimates $2.25B in 2025 to $9.09B by 2034 (16.8%) [S16][S17] | LOW-MEDIUM | Direction is positive, but do not use a single TAM/CAGR in investor claims. Definitions differ materially. |

## Market and Pricing Evidence

### Market direction

The reliable conclusion is directional, not a precise TAM: performance testing is moving toward continuous CI execution, cloud/distributed load, observability correlation, automated interpretation, and easier scenario creation [S4][S8][S16]. Two market studies disagree by multiples on both base size and growth, illustrating weak category boundaries and proprietary methodologies [S16][S17]. Therefore, the planning phase should not anchor strategy to a single market-size number.

### Search-interest and adoption proxies

No defensible Google Trends time series was available in this research environment. Better observable proxies are:

- Locust’s large GitHub footprint and very low current open-issue count [S1][S11].
- Active locust-plugins releases, 669 stars, 380 dependents, and a broad integration catalog [S12].
- Commercial vendors adding studio/no-code creation, AI analysis, trends, observability, and global load zones [S4][S7][S8].
- Community discussions that repeatedly compare Locust, k6, Gatling, JMeter, and cloud options based on language, scale, price, and CI fit [S9][S10].

### Buying behavior and monetization patterns

1. **Freemium plus usage:** Grafana Cloud k6 offers free usage, then platform fee plus VUh consumption [S4].
2. **Tiered subscription:** Gatling and LoadFocus package seats, minutes/VUs, generators, retention, and analyses [S5][S7].
3. **Feature/capacity tiers:** BlazeMeter packages concurrent users, VUH, test count, duration, virtual services, and support [S6].
4. **Enterprise custom:** all major platforms reserve private deployment, premium support, security, high scale, and custom limits for negotiated plans [S4][S5][S6].

### Recommended pricing logic for this project

The project should not charge for basic local Locust execution or deterministic analysis. A plausible future model is:

- **Open-source core:** templates, local CLI, reports, analyzer, one-user workspace.
- **Team/self-hosted paid add-on:** shared run history, approvals, RBAC/SSO, durable artifact store, policy packs, audit log, supported database/KMS adapters, and upgrade tooling.
- **Optional managed service:** remote generators and retained run history, usage-based.
- **Support subscription:** onboarding, architecture reviews, prioritized fixes.

A realistic initial self-hosted team price hypothesis is **$39–$99 per team/month** or **$499–$999/year**, below LoadFocus Basic and BlazeMeter Basic while charging for collaboration rather than local compute. This is a hypothesis to validate with interviews, not established willingness-to-pay evidence.

## Modern UX Expectations

### Expected information architecture

1. **Projects**: scenario assets, environments, SLO/policy set, secrets references.
2. **Scenarios**: import OpenAPI/HAR, generate, edit, validate, dry run.
3. **Runs**: configure load profile and location/runner, start/stop, see generator health.
4. **Results**: overview, endpoints, errors, time series, baseline diff, capacity, evidence.
5. **Recommendations**: ranked, confidence-labeled actions linked to evidence.
6. **Policies and CI**: SLOs, waivers, branch/release gates, artifact schema.
7. **Integrations**: Grafana/Prometheus/OTel, notifications, remote runners.
8. **Administration**: storage, security status, retention, users, audit.

### Onboarding and first use

Modern competitors reduce time to first test through recording, visual editing, Postman/spec import, or browser configuration [S4][S7][S8]. The project should provide a five-step path:

1. Create project.
2. Import OpenAPI or select a template.
3. Validate generated requests and required secrets/test data.
4. Run a 1-user smoke check.
5. Run a short load test and receive a baseline-ready report.

Each step should expose the generated Python so advanced users retain control.

### Required UI states

- **Empty:** explain the next useful action with an example project.
- **Loading/running:** show progress, current users/RPS, elapsed/remaining time, generator CPU/memory/network, and cancel behavior.
- **Partial:** distinguish missing history, failed telemetry correlation, lost workers, and incomplete artifacts.
- **Error:** actionable cause, affected step, retry safety, and raw log link.
- **Disabled:** state prerequisites, not merely gray the control.
- **Success:** summarize pass/fail, baseline delta, artifact locations, and recommended next action.
- **Stale:** clearly mark old rate cards, baselines, credentials, or agent versions.

### Responsiveness and accessibility

- Desktop-first dense analysis tables, but run controls and summaries must work at 360px width.
- Keyboard navigation, visible focus, semantic headings/landmarks, form labels, live-region updates, color-independent status, and WCAG 2.2 AA contrast.
- Tables need sticky headers, column selection, CSV export, and a card fallback on narrow screens.
- Charts need textual summaries and accessible data tables.

### Trust, privacy, and security indicators

- “Analyzed locally” badge and explicit network-call status.
- Provenance panel: input hashes, tool version, configuration, baseline ID, algorithm version, timestamp.
- Deterministic and LLM-enriched sections visually separated.
- Confidence labels with “why this was flagged” drill-down.
- Secret-store/KMS status, encryption adapter, tenant, retention, and audit status.
- Sanitization warnings for endpoint names, payloads, and exported reports.

### Progressive disclosure and discoverability

Default screens should answer: “Did it pass?”, “What changed?”, “Where is the bottleneck?”, and “What should I inspect next?” Advanced statistics, raw CSV, formulas, and model inputs should be one click away. This addresses both managerial readability and expert auditability.

### Current expectation coverage

| Expectation | Met | Partial | Missing |
|---|:---:|:---:|:---:|
| Code-first authoring | ✓ | | |
| OpenAPI import | ✓ | | |
| Visual/recorded authoring | | | ✓ |
| CI/SLO gates | ✓ | | |
| Multi-format artifacts | ✓ | | |
| Baseline comparison | ✓ | | |
| Evidence-linked diagnosis | | ✓ | |
| Historical run workspace | | ✓ | |
| Collaboration/approvals | | ✓ | |
| Remote load zones | | | ✓ |
| Observability correlation | | ✓ | |
| Responsive/accessibility claims | | ✓ | |
| Automated accessibility verification | | | ✓ |
| Production-grade identity/KMS | | ✓ | |
| Coherent first-run wizard | | | ✓ |

## Open-Source and Automation Opportunities

1. **locust-plugins adapter layer.** Reuse its test-data readers, Timescale/Grafana integration, transaction manager, checks, and protocol users rather than reimplementing them [S12]. Compatibility risk is manageable through optional extras and version checks.
2. **Locust native CSV and event contracts.** Continue treating official CSV names/history semantics as the source of truth [S2][S3]. Add schema-version detection and provenance to avoid silent drift.
3. **OpenTelemetry correlation.** The repository already ships OTel examples and Tempo dashboards. Standardize trace/span links in analysis artifacts rather than inventing another telemetry format.
4. **OpenAPI plus HAR/Postman ingestion.** OpenAPI exists; HAR-to-Locust tools are part of the ecosystem [S13][S14]. A common intermediate scenario model can support preview, validation, and round-trip editing.
5. **CI annotations.** Emit GitHub Checks/Step Summary/PR Markdown from the same stable evidence bundle. This is a low-complexity extension of existing Markdown/JUnit/JSON exporters.
6. **Runner providers.** Define a small interface for local, SSH, Kubernetes, and CI-hosted Locust workers. Community projects already cover distributed orchestration [S13][S14].
7. **Policy as code.** Store SLOs, baseline selection, minimum sample quality, allowed waivers, and required telemetry in versioned YAML/JSON, validated by schema.
8. **Automated data-quality checks.** Before analysis, detect short runs, missing full history, generator saturation, warm-up contamination, unstable RPS, and baseline incompatibility.
9. **Reproducible artifact envelope.** Package run config, input hashes, analyzer output, logs, and selected CSVs as a signed/checksummed bundle for audits and comparisons.
10. **Accessible component tests.** Add browser-level keyboard/ARIA/state snapshots for the workspace, matching the project’s documented visual-test intent.

## Differentiation Opportunities

| Capability | Problem solved / target | Evidence | Competitor gap | Product value | Complexity | Main risk | Priority | Success criterion |
|---|---|---|---|---|---|---|---|---|
| Evidence-linked Performance Diagnosis | Developers, QA, managers need trustworthy “why” | Analysis demand [S4][S7][S8][S15]; AI distrust [S19] | Cloud tools explain, but local/source-auditable workflows are weaker | Converts CSV into defensible action | MEDIUM | False causal implication | P0 | ≥80% of findings link to exact metric rows/time windows and one next check; user study ≥4/5 trust |
| Guided Project-to-Run Workspace | New users face fragmented tools | Studio/no-code investments [S4][S7][S8] | Locust ecosystem remains assembled manually [S12] | Faster activation without abandoning Python | HIGH | Scope explosion | P0 | Median first smoke test <15 minutes in 5-user usability test |
| Portable CI Evidence Bundle | SRE/QA need reproducible gates and review artifacts | CI and SLO emphasis [S4][S8][S16] | SaaS results can be platform-bound | Local/cloud neutral, auditable release evidence | LOW-MEDIUM | Schema churn | P0 | One command produces versioned JSON, Markdown, JUnit, hashes, config, and baseline metadata; backward-compat tests |
| Run Quality and Generator Health Guard | Avoid misleading conclusions when generator or data quality is bad | Local capacity report [S10], official CSV semantics [S2] | Many tools emphasize target findings more than evidence quality | Prevents false regressions/capacity claims | MEDIUM | Platform metrics portability | P1 | Analyzer blocks or downgrades confidence for short/missing/saturated runs in fixture tests |
| Scenario Import, Preview, and Repair | Generated tests need validation and realistic data | k6 Studio/Gatling/Postman/LoadFocus flows [S4][S7][S8] | Existing generator outputs code but lacks guided repair | Open source “studio” for Python | HIGH | Safe code editing | P1 | Import OpenAPI, resolve required params, run 1-user validation, export Python in one flow |
| Local-First Team History | Teams want trends without SaaS lock-in | Competitor trend/collaboration features [S4][S8]; privacy/pricing concerns [S19] | Self-hosted lightweight option is scarce | Paid collaboration boundary | HIGH | Security/RBAC/data migration | P1 | 20 comparable runs/project, baseline promotion, comments/approval, tenant isolation tests |
| Ecosystem Integration Packs | Users reinvent data/protocol/observability integrations | locust-plugins rationale/catalog [S12][S14] | Raw Locust is intentionally bare | Faster adoption and less duplication | MEDIUM | Version compatibility | P2 | Three supported packs with compatibility matrix and end-to-end examples |

## Priority-Ranked Development Recommendations

### P0.1 Evidence-linked comparison and diagnosis

Enhance the existing `AnalysisReport` rather than replacing it. Every anomaly, bottleneck, projection, and recommendation should carry:

- source metric(s), endpoint, row/time window, baseline value, current value;
- algorithm/rule identifier and version;
- confidence and data-quality grade;
- a “next validation step,” not an asserted root cause;
- links to relevant trace/dashboard when available.

Add a comparison-first UI with overview, change drivers, endpoint drill-down, and raw evidence. Keep LLM enrichment optional and visually subordinate.

### P0.2 Guided run workspace

Connect existing scenario generation, configuration, policies, runner command building, and analysis. Do not create a new test engine. The first release should support one local runner and imported OpenAPI, then expose provider interfaces for later distributed backends.

### P0.3 Portable CI evidence bundle

Define a versioned artifact schema and a `locust-kit bundle` or `analyze --bundle` output containing checksums, tool/config versions, baseline identity, data-quality result, report JSON, Markdown summary, JUnit, and selected source files. Add GitHub Step Summary output and annotations.

### P1.1 Run-quality guardrails

Detect insufficient duration/sample count, absent/full history limitations, unstable throughput, warm-up period, generator saturation, baseline mismatch, clock gaps, and high missing-data rates. Findings should downgrade or suppress capacity claims.

### P1.2 Scenario preview and validation

Add a guided editor around existing OpenAPI generation. Required parameters, auth, example payloads, task weights, and variable data should be shown before export. A 1-user validation run should be mandatory before load.

### P1.3 Local team history and approvals

Only after single-user flow works, add durable run history, named baseline promotion, comments, approvals, branch/release metadata, and supported storage/KMS/auth adapters. This is the strongest future paid boundary.

### P2. Ecosystem packs

Document and test compatibility with locust-plugins, OTel/Grafana, and at least one remote runner. Prefer adapters and examples over duplicated implementations.

## Recommended Scope for the Next Development Pass

**Theme: “Trustworthy run-to-decision workflow.”**

Ship only these integrated outcomes:

1. A project/run page that can select an existing Locust CSV prefix or launch a local configured run.
2. A baseline comparison screen backed by the current analyzer.
3. Evidence detail for each finding, including source rows/time windows, rule version, confidence, and data-quality warnings.
4. A portable CI evidence bundle with stable schema, Markdown/JUnit/JSON, checksums, and provenance.
5. Distribution fixes required to make this flow installable: declare the workspace extra/dependency, repair Docker startup, and provide one verified bootstrap command.
6. End-to-end tests and visual/accessibility state coverage for empty, running, partial, error, pass, and fail states.

**Explicitly out of scope:** proprietary cloud load generation, a full visual scenario IDE, multi-tenant enterprise RBAC, billing, a new statistics engine, and additional protocols. These are valuable later but would dilute the highest-value pass.

## Risks, Unknowns, and Assumptions

- **No direct customer interviews were available.** Community posts and public issues validate recurring problems, but not exact purchase intent.
- **Market-size estimates conflict materially.** Do not quote a single TAM/CAGR without defining the category and method [S16][S17].
- **Current workspace behavior was assessed from source/docs, not a live browser session.** Flask was not installed in the research environment.
- **The full test suite was not executable in this environment** because the runtime lacked Locust and Ruff. The repository’s claimed pass count is documentation evidence, not independently reproduced here.
- **Causal diagnosis is dangerous.** Correlation between load and latency/error does not prove database, pool, or scaling root cause. Recommendations must remain hypotheses until corroborated by telemetry.
- **Remote execution can become a platform business.** Keep a provider interface first; avoid building cloud infrastructure prematurely.
- **Security boundary is incomplete by design.** The local vault cipher, identity, CSRF, rate limiting, KMS, and tenant enforcement need production adapters before team deployment.
- **Pricing hypothesis is unvalidated.** Interview 8–12 target teams and test a landing page or design-partner offer before implementing billing.
- **Open-source compatibility creates maintenance cost.** Integration packs need pinned compatibility matrices and contract tests.
- **The optimal primary persona is assumed to be Python/Locust teams.** Validate whether consultants/QA leads or backend developers own purchasing and workflow decisions.

## Sources

Accessed 2026-08-06 unless otherwise noted.

- **[S1]** Locust, “A modern load testing framework” and GitHub repository. Locust / GitHub. https://locust.io/ ; https://github.com/locustio/locust
- **[S2]** Locust documentation, “Retrieve test statistics in CSV format.” https://docs.locust.io/en/2.37.0/retrieving-stats.html
- **[S3]** Locust GitHub, current `retrieving-stats.rst`. https://github.com/locustio/locust/blob/master/docs/retrieving-stats.rst
- **[S4]** Grafana Labs, “Performance & Load Testing with Grafana Cloud k6,” including current packaging and capabilities. https://grafana.com/products/cloud/performance-load-testing-k6/
- **[S5]** Gatling, “Pricing.” https://gatling.io/pricing
- **[S6]** Perforce BlazeMeter, “Pricing.” https://www.blazemeter.com/pricing
- **[S7]** LoadFocus, “Pricing and Plans” and product homepage. https://loadfocus.com/pricing ; https://loadfocus.com/
- **[S8]** Gatling, product homepage and documentation. https://gatling.io/ ; https://docs.gatling.io/
- **[S9]** Reddit r/QualityAssurance, “Load/performance testing tools research - K6, Locust, Artillery, etc.” https://www.reddit.com/r/QualityAssurance/comments/mpyxuy/loadperformance_testing_tools_research_k6_locust/
- **[S10]** Reddit r/ExperiencedDevs, “What tools are you using for load tests?” https://www.reddit.com/r/ExperiencedDevs/comments/16oiqwf/what_tools_are_you_using_for_load_tests/
- **[S11]** Locust GitHub issues, including auth refresh, downloaded-report chart behavior, and pause/resume requests. https://github.com/locustio/locust/issues
- **[S12]** Svenska Spel, `locust-plugins` repository and README. https://github.com/SvenskaSpel/locust-plugins
- **[S13]** Awesome Locust, curated ecosystem list. https://aliesbelik.github.io/awesome-locust/
- **[S14]** Awesome Locust GitHub repository. https://github.com/aliesbelik/awesome-locust
- **[S15]** Ecosyste.ms issue statistics for archived k6 Cloud feature requests. https://issues.ecosyste.ms/hosts/GitHub/repositories/grafana/k6-cloud-feature-requests
- **[S16]** TrendX Insights, “Performance Testing Market Analysis, Size, Share & Growth Forecast 2026–2034.” https://trendxinsights.com/syndicated-market-research-reports/performance-testing-market/
- **[S17]** QYResearch, “Global Performance Testing Market Research Report 2025.” Published 2025-02-27. https://www.qyresearch.com/reports/4323645/performance-testing
- **[S18]** Gatling GitHub issues and repository. https://github.com/gatling/gatling/issues ; https://github.com/gatling/gatling
- **[S19]** Stack Overflow, “2025 Developer Survey,” especially AI trust/frustration and technology purchase rejection factors. https://survey.stackoverflow.co/2025/
- **[S20]** Stackpick, “Gatling Pricing 2026,” used only as supplementary review/learning-curve evidence; official pricing takes precedence. https://stackpick.net/pricing/gatling/
- **[S21]** TestGuild, “BlazeMeter Review: Features, Pricing & Alternatives 2025,” supplementary independent strengths/weaknesses. https://testguild.com/tools/blazemeter
- **[S22]** Perforce BlazeMeter, product overview and open-source framework positioning. https://www.blazemeter.com/
- **[S23]** Grafana archived k6 Cloud feature-request repository, workflow and disposition. https://github.com/grafana-cold-storage/k6-cloud-feature-requests/
- **[S24]** Locust documentation, “Third party extensions.” https://docs.locust.io/en/stable/extensions.html
