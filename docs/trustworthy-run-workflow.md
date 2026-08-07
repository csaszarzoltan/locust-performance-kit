# Trustworthy run-to-decision workflow

This development pass connects the three highest-ranked research priorities into one local-first path.

## Start the guided workspace

```bash
flask --app locust_templates.workspace_api:create_workspace_app run
```

Open `http://127.0.0.1:5000/workspace/start`. Enter a current Locust CSV prefix, optional baseline prefix, and P95 SLO. The responsive page covers empty, running, result, and friendly error states. Its API is `POST /api/v1/analysis`.

## Evidence-linked diagnosis

`build_evidence_findings()` wraps deterministic analysis. Every finding has source files and metric context, rule ID/version, confidence, data-quality grade, and a next validation step. Wording intentionally avoids causal root-cause claims.

## Portable CI evidence bundle

```bash
locust-kit analyze --csv results --baseline baseline --slo p95=500 \
  --format json --output report.json --bundle evidence.zip
```

The atomic ZIP contains `report.json`, `summary.md`, `junit.xml`, `provenance.json`, and `manifest.json`. Manifest entries include SHA-256 and byte size. Schema version 1 is backward-compatibility tested.

The bundle never includes secrets or environment values and does not make network calls. Only configured CSV-derived report data and analysis provenance are included.


## Production deployment

Set a dedicated data root and a strong API key. Production mode rejects requests without `X-API-Key` and refuses CSV prefixes outside the configured root.

```bash
export LOCUST_WORKSPACE_ENV=production
export LOCUST_WORKSPACE_ROOT=/srv/locust-data
export LOCUST_WORKSPACE_API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
gunicorn --bind 0.0.0.0:8080 --workers 2 'locust_templates.workspace_api:create_workspace_app()'
```

The Docker image enforces the same fail-closed API-key requirement. Place TLS termination, identity-aware access, CSRF protection for browser deployments, and rate limiting at the reverse proxy. The local vault remains a development abstraction and must not be used as a production KMS.

Evidence bundles now include the current and baseline Locust source CSV files under `sources/`, along with runtime platform, Python version, data-quality grade, configured SLOs, and checksums.
