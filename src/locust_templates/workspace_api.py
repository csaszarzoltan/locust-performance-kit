"""Flask delivery layer for the performance engineering workspace."""

from __future__ import annotations

import hmac
import os
from pathlib import Path
from typing import Any

from flask import Blueprint, Flask, Response, jsonify, request

from locust_templates.evidence import evidence_from_report
from locust_templates.intelligence import analyze_run
from locust_templates.product_workspace import (
    PerformanceWorkspace,
    VaultAccessDenied,
    render_workspace,
)


def _workspace_prefix(value: str) -> str:
    """Resolve a CSV prefix and reject paths outside the configured workspace."""
    root = Path(os.getenv("LOCUST_WORKSPACE_ROOT", os.getcwd())).resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if resolved != root and root not in resolved.parents:
        raise PermissionError("PATH_OUTSIDE_WORKSPACE")
    return str(resolved)


def _authorized() -> bool:
    """Require an API key when production mode is explicitly enabled."""
    if os.getenv("LOCUST_WORKSPACE_ENV", "development").lower() != "production":
        return True
    expected = os.getenv("LOCUST_WORKSPACE_API_KEY", "")
    supplied = request.headers.get("X-API-Key", "")
    return bool(expected) and hmac.compare_digest(expected, supplied)


def _store() -> PerformanceWorkspace:
    return PerformanceWorkspace(
        Path(os.getenv("LOCUST_WORKSPACE_DB", "/tmp/locust_workspace.db"))
    )


def _error(code: str, status: int) -> tuple[Response, int]:
    return jsonify(
        {
            "error": {"code": code},
            "correlation_id": request.headers.get("X-Correlation-ID", "generated"),
        }
    ), status


def _json() -> dict[str, Any]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("JSON_OBJECT_REQUIRED")
    return data


def create_workspace_blueprint() -> Blueprint:
    """Create versioned workspace API and server-rendered pages."""
    bp = Blueprint("performance_workspace", __name__)

    @bp.before_request
    def require_api_key() -> tuple[Response, int] | None:
        if not _authorized():
            return _error("AUTHENTICATION_REQUIRED", 401)
        return None

    @bp.get("/workspace/start")
    def guided_start() -> Response:
        """Render the responsive first-run analysis workspace."""
        return Response("""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Locust Performance Workspace</title>
<link rel="stylesheet" href="/assets/workspace.css"><style>
.shell{max-width:1120px;margin:auto;padding:32px 20px}.hero{padding:48px;border-radius:24px;background:linear-gradient(135deg,#0b1739,#123c69);color:#fff;box-shadow:0 24px 60px #0b173933}.eyebrow{color:#67e8f9;font-weight:700}.grid{display:grid;grid-template-columns:1.2fr .8fr;gap:24px;margin-top:24px}.panel{background:#fff;border:1px solid #dbe5f0;border-radius:20px;padding:24px;box-shadow:0 16px 40px #0f172a12}label{display:block;font-weight:650;margin:16px 0 6px}input{width:100%;box-sizing:border-box;padding:12px;border:1px solid #94a3b8;border-radius:10px}button{margin-top:20px;padding:13px 18px;border:0;border-radius:10px;background:#2563eb;color:#fff;font-weight:700;cursor:pointer}button:focus,input:focus{outline:3px solid #f59e0b;outline-offset:2px}.steps li{margin:12px 0}.badge{display:inline-block;padding:6px 10px;border-radius:999px;background:#dbeafe;color:#1e3a8a;font-weight:700}@media(max-width:760px){.grid{grid-template-columns:1fr}.hero{padding:28px}.shell{padding:16px}}
</style></head><body><main class="shell"><section class="hero"><p class="eyebrow">LOCAL-FIRST PERFORMANCE DECISIONS</p><h1>Analyze an existing Locust run</h1><p>Compare a run, inspect source-linked findings, and export a reproducible Evidence bundle without sending test data to a SaaS.</p></section><div class="grid"><section class="panel"><h2>Start with your CSV prefix</h2><form id="analysis-form"><label for="csv">Current run prefix</label><input id="csv" required placeholder="results/run"><label for="baseline">Baseline prefix</label><input id="baseline" placeholder="results/baseline"><label for="p95">P95 SLO in ms</label><input id="p95" type="number" min="1" value="500"><button type="submit">Analyze run</button></form><div id="status" role="status" aria-live="polite"></div></section><aside class="panel"><span class="badge">5 minute path</span><h2>From run to decision</h2><ol class="steps"><li>Select current evidence</li><li>Add an optional baseline</li><li>Set the release SLO</li><li>Review confidence and exact sources</li><li>Export the Evidence bundle for CI</li></ol></aside></div></main><script>
const form=document.querySelector('#analysis-form'),status=document.querySelector('#status');form.addEventListener('submit',async(e)=>{e.preventDefault();status.textContent='Analyzing locally...';try{const r=await fetch('/api/v1/analysis',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({csv_prefix:csv.value,baseline_prefix:baseline.value||null,slos:{p95:Number(p95.value)}})});const d=await r.json();if(!r.ok)throw new Error(d.error?.code||'Analysis failed');status.innerHTML=`<h3>${d.exit_code===2?'SLO needs attention':'Run is ready'}</h3><p>${d.findings.length} source-linked findings. Data remained local.</p><div class="findings">${d.findings.slice(0,8).map(f=>`<article><strong>${f.severity.toUpperCase()} · ${f.category}</strong><p>${f.message}</p><small>Confidence ${f.confidence}; quality ${f.data_quality_grade}; source ${f.sources[0]?.path||'n/a'}</small><p><b>Next check:</b> ${f.next_check}</p></article>`).join('')}</div>`}catch(err){status.textContent=`Could not analyze: ${err.message}. Check the prefix and try again.`}});
</script></body></html>""", mimetype="text/html")

    @bp.post("/api/v1/analysis")
    def analyze_evidence() -> tuple[Response, int] | Response:
        """Analyze one run and return source-linked deterministic findings."""
        try:
            body = _json()
            report = analyze_run(
                _workspace_prefix(body["csv_prefix"]),
                baseline_prefix=_workspace_prefix(body["baseline_prefix"]) if body.get("baseline_prefix") else None,
                slos=body.get("slos") or None,
            )
            payload = report.to_json()
            payload["findings"] = [
                {
                    **finding.__dict__,
                    "sources": [source.__dict__ for source in finding.sources],
                }
                for finding in evidence_from_report(report)
            ]
            return jsonify(payload)
        except PermissionError as exc:
            return _error(str(exc), 403)
        except (KeyError, ValueError, FileNotFoundError) as exc:
            return _error(str(exc), 422)

    @bp.get("/workspace/<page>")
    def page(page: str) -> Response | tuple[Response, int]:
        try:
            return Response(render_workspace(page, _store()), mimetype="text/html")
        except KeyError:
            return _error("WORKSPACE_NOT_FOUND", 404)

    @bp.post("/api/v1/scenarios")
    def create_scenario() -> tuple[Response, int]:
        try:
            body = _json()
            sid = _store().create_scenario(
                body["name"],
                body["steps"],
                idempotency_key=request.headers.get("Idempotency-Key"),
            )
            return jsonify(
                {"id": sid, "state": "READY", "allowed_actions": ["export", "run"]}
            ), 201
        except (KeyError, ValueError) as exc:
            return _error(str(exc), 422)

    @bp.post("/api/v1/runs")
    def create_run() -> tuple[Response, int]:
        try:
            body = _json()
            rid = _store().create_run(body["scenario_id"], body["zones"])
            return jsonify(
                {"id": rid, "state": "PROVISIONING", "allowed_actions": ["cancel"]}
            ), 201
        except (KeyError, ValueError) as exc:
            return _error(str(exc), 422)

    @bp.post("/api/v1/results")
    def ingest_results() -> tuple[Response, int]:
        try:
            body = _json()
            rid = _store().ingest_result(body["run_id"], body["records"])
            return jsonify(
                {"id": rid, "state": "READY", "allowed_actions": ["diagnose"]}
            ), 201
        except (KeyError, ValueError) as exc:
            return _error(str(exc), 422)

    @bp.post("/api/v1/policies")
    def create_policy() -> tuple[Response, int]:
        try:
            body = _json()
            pid = _store().create_policy(body["name"], body["rules"])
            return jsonify(
                {"id": pid, "state": "ACTIVE", "allowed_actions": ["evaluate"]}
            ), 201
        except (KeyError, ValueError) as exc:
            return _error(str(exc), 422)

    @bp.post("/api/v1/vault/secrets")
    def create_secret() -> tuple[Response, int]:
        try:
            body = _json()
            ref = _store().put_secret(body["tenant"], body["name"], body["value"])
            return jsonify({"reference": ref, "state": "ACTIVE"}), 201
        except (KeyError, ValueError) as exc:
            return _error(str(exc), 422)

    @bp.post("/api/v1/capacity/estimates")
    def estimate() -> tuple[Response, int]:
        try:
            body = _json()
            result = _store().estimate_capacity(
                body["users"], body["minutes"], body["zones"], body["rate_card_id"]
            )
            return jsonify(result), 201
        except (KeyError, ValueError) as exc:
            return _error(str(exc), 422)

    @bp.errorhandler(VaultAccessDenied)
    def denied(exc: VaultAccessDenied) -> tuple[Response, int]:
        return _error(str(exc), 403)

    return bp


def create_workspace_app() -> Flask:
    """Return a standalone Flask app for development and deployment."""
    app = Flask(__name__, static_folder="static", static_url_path="/assets")
    app.register_blueprint(create_workspace_blueprint())
    return app
