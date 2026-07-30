from pathlib import Path

import pytest

from locust_templates.product_workspace import (
    PerformanceWorkspace,
    VaultAccessDenied,
    render_workspace,
)


def ws(tmp_path: Path) -> PerformanceWorkspace:
    return PerformanceWorkspace(tmp_path / "workspace.db")


def test_scenario_export_round_trip_preserves_steps_and_secret_refs(
    tmp_path: Path,
) -> None:
    app = ws(tmp_path)
    sid = app.create_scenario(
        "Checkout",
        [
            {
                "protocol": "http",
                "method": "GET",
                "path": "/health",
                "secret_ref": "secret://team-a/api",
            }
        ],
    )
    payload = app.export_scenario(sid)
    imported = app.import_scenario(payload)
    assert app.scenario(imported)["steps"] == app.scenario(sid)["steps"]


def test_worker_loss_marks_run_partial_and_replaces_only_missing_capacity(
    tmp_path: Path,
) -> None:
    app = ws(tmp_path)
    rid = app.create_run("scenario-1", {"eu": 2, "us": 1})
    app.connect_worker(rid, "eu", "worker-1")
    app.connect_worker(rid, "us", "worker-2")
    plan = app.recovery_plan(rid)
    assert plan == {"eu": 1}
    assert app.run(rid)["state"] == "PARTIAL"


def test_regression_drilldown_links_endpoint_cascade_and_trace_without_double_counting(
    tmp_path: Path,
) -> None:
    app = ws(tmp_path)
    result = app.ingest_result(
        "run-1",
        [
            {
                "endpoint": "/pay",
                "p95": 450,
                "baseline_p95": 300,
                "cascade_id": "c1",
                "trace_id": "t1",
            },
            {
                "endpoint": "/pay",
                "p95": 450,
                "baseline_p95": 300,
                "cascade_id": "c1",
                "trace_id": "t1",
            },
        ],
    )
    diag = app.diagnostics(result)
    assert len(diag["hotspots"]) == 1
    assert diag["hotspots"][0]["trace_id"] == "t1"


def test_expired_waiver_cannot_convert_failed_gate_to_pass(tmp_path: Path) -> None:
    app = ws(tmp_path)
    policy = app.create_policy("prod", {"p95": 300})
    app.add_waiver(policy, "p95", expires_at=1)
    decision = app.evaluate_policy(policy, {"p95": 400}, now=2)
    assert decision["state"] == "FAIL"


def test_cross_tenant_run_cannot_resolve_secret_reference(tmp_path: Path) -> None:
    app = ws(tmp_path)
    ref = app.put_secret("team-a", "api", "sensitive")
    with pytest.raises(VaultAccessDenied, match="CROSS_TENANT_DENIED"):
        app.resolve_secret(ref, tenant="team-b")
    assert "sensitive" not in app.audit_export()


def test_estimate_rejects_stale_rate_card_before_approval(tmp_path: Path) -> None:
    app = ws(tmp_path)
    card = app.set_rate_card("cloud", 0.15, effective_at=1)
    estimate = app.estimate_capacity(1000, 30, 2, card, now=10, max_age=5)
    assert estimate["state"] == "STALE"
    with pytest.raises(ValueError, match="ESTIMATE_NOT_APPROVABLE"):
        app.approve_estimate(estimate["id"])


def test_all_workspaces_expose_accessible_recovery_states(tmp_path: Path) -> None:
    app = ws(tmp_path)
    for page in ("scenarios", "runs", "diagnostics", "policies", "vault", "capacity"):
        html = render_workspace(page, app)
        assert "Skip to content" in html
        assert 'aria-live="polite"' in html
        assert "Try again" in html
        assert "Performance workspace" in html


def test_versioned_workspace_routes_are_registered(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCUST_WORKSPACE_DB", str(tmp_path / "api.db"))
    from locust_templates.workspace_api import create_workspace_app

    app = create_workspace_app()
    paths = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/workspace/<page>" in paths
    assert "/api/v1/scenarios" in paths
    assert "/api/v1/runs" in paths
    assert "/api/v1/results" in paths
    assert "/api/v1/policies" in paths
    assert "/api/v1/vault/secrets" in paths
    assert "/api/v1/capacity/estimates" in paths
