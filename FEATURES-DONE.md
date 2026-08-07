## Features Done (this pass)
- evidence-linked-diagnosis: Deterministic findings now include exact source files/metrics, windows, rule version, confidence, data-quality grade, and a non-causal next validation step.
- guided-run-workspace: Responsive Flask first-run page and analysis API connect CSV selection, baseline comparison, SLO gating, results, and friendly errors in one accessible flow.
- portable-ci-evidence-bundle: Atomic schema-v1 ZIP export contains JSON, Markdown, JUnit, provenance, and a SHA-256 manifest via `--bundle` or Python API.
- distribution-readiness: Declared Flask runtime support, repaired container startup, and documented a single guided workspace command.
- security-hardening: Production mode requires an API key, confines CSV prefixes to a configured workspace root, and runs through Gunicorn.
- reproducible-delivery: Restored CI workflow dotfiles, pinned requirements, removed generated package metadata, and verified 1085 tests.
## Sources
- research-findings.md items addressed: P0.1 Evidence-linked comparison and diagnosis, P0.2 Guided run workspace, P0.3 Portable CI evidence bundle
- CHANGELOG.md section this maps to
