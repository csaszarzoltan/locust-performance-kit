# Offline Decision Verification

`locust-kit verify BUNDLE --format json` validates a `performance-verification-bundle/v1` ZIP without network access. The verifier checks archive safety, exact membership, byte sizes, SHA-256 hashes, and the embedded `performance-decision/v1` identity. Exit code 0 means VALID; exit code 1 means invalid or unsupported.

The workspace route `/workspace/verify` provides the same local verification flow. Uploaded bundles are held only for the request and are not committed to the run store.

A verification bundle contains `decision.json`, `summary.md`, `policy.json`, `provenance.json`, `manifest.json`, and source evidence under `sources/`. The current release proves integrity, not signer identity or non-repudiation.

## Reproduction

Use `locust-kit verify BUNDLE --reproduce --format json` to safely extract a valid bundle into an isolated temporary directory, reconstruct current and optional baseline Locust CSV prefixes, rerun deterministic analysis, and return MATCH, DRIFT, or UNREPRODUCIBLE. Host-specific source prefixes and generated decision timestamps are normalized during comparison; measured values, policy, quality, and findings remain authoritative.
