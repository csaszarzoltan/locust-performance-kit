"""Flask delivery layer for the performance engineering workspace."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import Blueprint, Flask, Response, jsonify, request

from locust_templates.product_workspace import (
    PerformanceWorkspace,
    VaultAccessDenied,
    render_workspace,
)


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
