"""Flask delivery layer for the performance engineering workspace."""

from __future__ import annotations

import hmac
import json
import os
import secrets
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from flask import Blueprint, Flask, Response, jsonify, redirect, request

from locust_templates.analysis_service import analyze_decision
from locust_templates.decision_artifact import render_markdown
from locust_templates.evidence import evidence_from_report
from locust_templates.intelligence import analyze_run
from locust_templates.product_workspace import (
    PerformanceWorkspace,
    VaultAccessDenied,
    render_workspace,
)
from locust_templates.run_import import (
    ImportValidationError,
    SafeRunImporter,
    commit_candidate,
)
from locust_templates.workspace_views import baselines as baselines_view
from locust_templates.workspace_views import detail as detail_view
from locust_templates.workspace_views import import_form, inbox, promote_form
from locust_templates.workspace_views import preview as preview_view


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


_IMPORTS: dict[str, dict[str, Any]] = {}


def create_workspace_blueprint() -> Blueprint:
    """Create versioned workspace API and server-rendered pages."""
    bp = Blueprint("performance_workspace", __name__)

    @bp.before_request
    def require_api_key() -> tuple[Response, int] | None:
        if not _authorized():
            return _error("AUTHENTICATION_REQUIRED", 401)
        return None

    @bp.get("/")
    def root() -> Response:
        return redirect("/workspace/runs", code=302)

    @bp.get("/workspace/runs")
    def run_inbox() -> Response:
        q={key:request.args.get(key,"") for key in ("q","environment","branch","decision","quality")}
        rows=_store().list_analysis_runs(query=q["q"],environment=q["environment"],branch=q["branch"],decision=q["decision"],quality=q["quality"],missing_metadata=request.args.get("missing_metadata")=="1")
        return Response(inbox(rows,q),mimetype="text/html")

    @bp.get("/workspace/runs/import")
    def run_import_form() -> Response:
        return Response(import_form(),mimetype="text/html")

    @bp.post("/workspace/runs/import/validate")
    def run_import_validate() -> tuple[Response,int] | Response:
        upload=request.files.get("archive")
        if not upload: return Response(import_form("Select one ZIP archive."),status=422,mimetype="text/html")
        session_id=secrets.token_urlsafe(18)
        try:
            staging_root=Path(os.getenv("LOCUST_WORKSPACE_STORAGE_ROOT","/tmp/locust-workspace"))/"staging"
            staging, result=SafeRunImporter(staging_root).extract(upload.stream,session_id)
            _IMPORTS[session_id]={"staging":str(staging),"preview":result,"created":time.time()}
            return Response(preview_view(session_id,list(result.candidates)),mimetype="text/html")
        except ImportValidationError as exc:
            return Response(import_form(f"{exc.code}: {exc}"),status=422,mimetype="text/html")
        except Exception:
            return Response(import_form("ARCHIVE_INVALID: the file is not a valid ZIP."),status=422,mimetype="text/html")

    @bp.post("/workspace/runs/import/commit")
    def run_import_commit() -> tuple[Response,int] | Response:
        sid=request.form.get("session_id",""); data=_IMPORTS.get(sid)
        if not data or time.time()-data["created"]>1800: return Response(import_form("IMPORT_SESSION_EXPIRED: validate the file again."),status=409,mimetype="text/html")
        try:
            index=int(request.form.get("candidate","-1")); candidate=data["preview"].candidates[index]
            label=request.form.get("label","").strip()
            if not label or len(label)>120: raise ValueError("RUN_LABEL_INVALID")
            p95=request.form.get("p95","").strip(); slos={"p95":float(p95)} if p95 else None
            if p95 and not (0<float(p95)<=3600000): raise ValueError("SLO_INVALID")
            run_id=f"analysis_{uuid.uuid4().hex}"
            storage=Path(os.getenv("LOCUST_WORKSPACE_STORAGE_ROOT","/tmp/locust-workspace"))/"runs"
            files=commit_candidate(data["staging"],storage,run_id,candidate)
            prefix=str(Path(files["stats"]).with_name("run"))
            hashes={x.role:x.sha256 for x in candidate.files}
            report,decision=analyze_decision(prefix,slos=slos,label=label,environment=request.form.get("environment",""),branch=request.form.get("branch",""),input_hashes=hashes)
            _store().save_analysis_run(run_id=run_id,label=label,environment=request.form.get("environment",""),branch=request.form.get("branch",""),decision=decision,slos=slos)
            shutil.rmtree(data["staging"],ignore_errors=True); _IMPORTS.pop(sid,None)
            return redirect(f"/workspace/runs/{run_id}",code=303)
        except (ValueError,IndexError,ImportValidationError) as exc:
            return Response(preview_view(sid,list(data["preview"].candidates),str(exc)),status=422,mimetype="text/html")

    @bp.get("/workspace/runs/<run_id>")
    def run_detail(run_id: str) -> Response | tuple[Response,int]:
        try: return Response(detail_view(_store().analysis_run(run_id)),mimetype="text/html")
        except KeyError: return _error("RUN_NOT_FOUND",404)

    @bp.get("/workspace/runs/<run_id>/decision.json")
    def decision_json(run_id: str) -> Response | tuple[Response,int]:
        try:
            payload=json.dumps(_store().analysis_run(run_id)["report"],indent=2,sort_keys=True).encode()
            return Response(payload,mimetype="application/json",headers={"Content-Disposition":f'attachment; filename="{run_id}-decision.json"',"Cache-Control":"no-store"})
        except KeyError: return _error("RUN_NOT_FOUND",404)

    @bp.get("/workspace/runs/<run_id>/summary.md")
    def decision_markdown(run_id: str) -> Response | tuple[Response,int]:
        try:
            payload=render_markdown(_store().analysis_run(run_id)["report"])
            return Response(payload,mimetype="text/markdown",headers={"Content-Disposition":f'attachment; filename="{run_id}-summary.md"',"Cache-Control":"no-store"})
        except KeyError: return _error("RUN_NOT_FOUND",404)

    @bp.get("/workspace/baselines")
    def baseline_list() -> Response:
        return Response(baselines_view(_store().list_baselines(request.args.get("environment",""))),mimetype="text/html")

    @bp.route("/workspace/baselines/promote",methods=["GET","POST"])
    def baseline_promote() -> Response | tuple[Response,int]:
        run_id=request.values.get("run_id","")
        try: run=_store().analysis_run(run_id)
        except KeyError: return _error("RUN_NOT_FOUND",404)
        if request.method=="GET": return Response(promote_form(run),mimetype="text/html")
        try:
            _store().promote_baseline(run_id,request.form.get("environment",""),request.form.get("label",""),request.form.get("reason",""),allow_advisory=request.form.get("allow_advisory")=="1")
            return redirect("/workspace/baselines",code=303)
        except ValueError as exc: return Response(promote_form(run,str(exc)),status=422,mimetype="text/html")

    @bp.route("/workspace/sample", methods=["GET", "POST"])
    def sample_info() -> Response:
        from locust_templates.workspace_views import shell
        sample_root=Path(__file__).with_name("sample")
        if request.method == "GET":
            body="<h1>Try a sample decision</h1><p>The bundled synthetic baseline and regressed run demonstrate an explainable failure. No network call is made.</p><form method='post'><button class='primary'>Load sample</button> <a class='button' href='/workspace/runs'>Back to Runs</a></form>"
            return Response(shell("Try sample",body),mimetype="text/html")
        try:
            import hashlib
            manifest=json.loads((sample_root/"manifest.json").read_text())
            for rel,digest in manifest["files"].items():
                if hashlib.sha256((sample_root/rel).read_bytes()).hexdigest()!=digest: raise ValueError("SAMPLE_ASSET_INVALID")
            existing=[x for x in _store().list_analysis_runs(query="Sample: regressed") if x["sample"]]
            if existing: return redirect(f"/workspace/runs/{existing[0]['id']}",code=303)
            run_id=f"sample_{uuid.uuid4().hex}"
            _,decision=analyze_decision(str(sample_root/"run_b/run_b"),baseline_prefix=str(sample_root/"run_a/run_a"),slos={"p95":500},label="Sample: regressed checkout API",environment="sample",branch="demo")
            _store().save_analysis_run(run_id=run_id,label="Sample: regressed checkout API",environment="sample",branch="demo",decision=decision,slos={"p95":500},sample=True)
            return redirect(f"/workspace/runs/{run_id}",code=303)
        except Exception as exc:
            return Response(shell("Sample unavailable",f"<h1>Sample unavailable</h1><div class='alert danger'>SAMPLE_ASSET_INVALID: {type(exc).__name__}. Reinstall the package.</div>"),status=500,mimetype="text/html")

    @bp.get("/healthz")
    def health() -> tuple[Response,int] | Response:
        try:
            _store().list_analysis_runs(); return jsonify({"status":"ok","database":"ok","version":"1.7.0"})
        except Exception: return jsonify({"status":"unavailable","database":"error","version":"1.7.0"}),503

    @bp.get("/workspace/start")
    def guided_start() -> Response:
        """Render the legacy guided entry point for compatibility."""
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

    @bp.after_request
    def secure_headers(response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options","nosniff")
        response.headers.setdefault("Referrer-Policy","no-referrer")
        response.headers.setdefault("Content-Security-Policy","default-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'")
        return response

    return bp


def create_workspace_app() -> Flask:
    """Return a standalone Flask app for development and deployment."""
    app = Flask(__name__, static_folder="static", static_url_path="/assets")
    app.register_blueprint(create_workspace_blueprint())
    return app
