# Performance Engineering Workspace

## Architecture

```text
Responsive Flask pages and /api/v1 contracts
    -> workspace delivery schemas and error mapping
        -> PerformanceWorkspace application/domain service
            -> transactional SQLite repository
                -> existing Locust templates, runner, reports, and CI gates
```

The workspace is additive. Existing Python APIs, `locust-report`, examples, exporters, and GitHub workflows do not depend on it.

## Workflows and recovery

Scenario documents carry a `schema_version` and round-trip without resolving `secret://tenant/name` references. Run recovery compares desired worker counts with connected workers and requests only missing capacity. Diagnostics use endpoint, cascade, and trace identity to avoid double-counting imported evidence. An expired policy waiver never changes a failed decision to pass. Estimates derived from stale rate cards cannot be approved.

## Security boundary

Secret plaintext is encrypted before persistence and excluded from audit records. Tenant mismatch fails closed. The bundled local cipher is an abstraction seam for development, not a substitute for a production KMS: production must inject a managed envelope-encryption adapter and rotate keys. Identity, tenant membership, rate limits, and CSRF protection belong at the deployment authentication boundary before registering the workspace blueprint.

## Data compatibility

Tables are created additively with `CREATE TABLE IF NOT EXISTS`. Scenario exports include schema version 1. Rollback disables the blueprint and preserves data for export. Existing 1.4 modules and public functions are not renamed or removed.

## UI states

Every workspace includes empty, current, partial/recovery, and error-oriented guidance. Navigation is keyboard accessible, focus is visible, status is announced through `aria-live`, mobile navigation scrolls horizontally, and the primary action becomes sticky on narrow screens.

## Run Decision Workspace

The supported entry point is `locust-workspace`. It binds to `127.0.0.1` by default and uses `LOCUST_WORKSPACE_DB` plus `LOCUST_WORKSPACE_STORAGE_ROOT`. Runs, baselines, scenarios, policies, capacity, and vault form the navigation. Imported evidence stays local; browser analysis never enables optional LLM enrichment. Back up the SQLite database and managed storage together. This release remains a local/single-operator product and is not a substitute for SSO, RBAC, TLS, or a production KMS.
