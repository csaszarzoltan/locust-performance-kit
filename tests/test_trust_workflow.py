from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from locust_templates.evidence import build_evidence_findings
from locust_templates.evidence_bundle import create_evidence_bundle

FIXTURES = Path(__file__).parent / "fixtures" / "intelligence"


def test_findings_are_source_linked_and_actionable() -> None:
    findings = build_evidence_findings(
        str(FIXTURES / "run_b" / "run_b"),
        baseline_prefix=str(FIXTURES / "run_a" / "run_a"),
        slos={"p95": 500.0},
    )
    assert findings
    for finding in findings:
        assert finding.rule_id.startswith("lpk.")
        assert finding.rule_version == "1.0"
        assert finding.confidence in {"low", "medium", "high"}
        assert finding.data_quality_grade in {"A", "B", "C", "D"}
        assert finding.sources
        assert finding.next_check
        assert "caused by" not in finding.message.lower()


def test_bundle_contains_stable_reports_and_verified_manifest(tmp_path: Path) -> None:
    output = tmp_path / "evidence.zip"
    result = create_evidence_bundle(
        str(FIXTURES / "run_b" / "run_b"),
        output,
        baseline_prefix=str(FIXTURES / "run_a" / "run_a"),
        slos={"p95": 500.0},
    )
    assert result == output
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert {"manifest.json", "report.json", "summary.md", "junit.xml", "provenance.json"} <= names
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["schema_version"] == 1
        for item in manifest["files"]:
            assert hashlib.sha256(archive.read(item["path"])).hexdigest() == item["sha256"]
        report = json.loads(archive.read("report.json"))
        assert report["schema_version"] == 1
        assert report["findings"]


def test_bundle_rejects_itself_as_output_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="ZIP"):
        create_evidence_bundle("missing", tmp_path / "bad.txt")


def test_guided_workspace_exposes_complete_first_run_flow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCUST_WORKSPACE_DB", str(tmp_path / "workspace.db"))
    from locust_templates.workspace_api import create_workspace_app

    client = create_workspace_app().test_client()
    page = client.get("/workspace/start")
    assert page.status_code == 200
    text = page.get_data(as_text=True)
    assert "Analyze an existing Locust run" in text
    assert "aria-live" in text
    assert "Evidence bundle" in text

    response = client.post("/api/v1/analysis", json={
        "csv_prefix": str(FIXTURES / "run_b" / "run_b"),
        "baseline_prefix": str(FIXTURES / "run_a" / "run_a"),
        "slos": {"p95": 500.0},
    })
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["exit_code"] == 2
    assert payload["findings"]


def test_analysis_rejects_prefix_outside_configured_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCUST_WORKSPACE_ROOT", str(FIXTURES.resolve()))
    monkeypatch.setenv("LOCUST_WORKSPACE_DB", str(tmp_path / "workspace.db"))
    from locust_templates.workspace_api import create_workspace_app

    client = create_workspace_app().test_client()
    response = client.post("/api/v1/analysis", json={"csv_prefix": "/etc/passwd"})
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_production_mode_requires_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCUST_WORKSPACE_ENV", "production")
    monkeypatch.setenv("LOCUST_WORKSPACE_API_KEY", "review-key")
    monkeypatch.setenv("LOCUST_WORKSPACE_DB", str(tmp_path / "workspace.db"))
    monkeypatch.setenv("LOCUST_WORKSPACE_ROOT", str(FIXTURES.resolve()))
    from locust_templates.workspace_api import create_workspace_app

    client = create_workspace_app().test_client()
    assert client.get("/workspace/start").status_code == 401
    assert client.get("/workspace/start", headers={"X-API-Key": "review-key"}).status_code == 200


def test_workspace_result_page_contains_real_finding_details(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCUST_WORKSPACE_ROOT", str(FIXTURES.resolve()))
    monkeypatch.setenv("LOCUST_WORKSPACE_DB", str(tmp_path / "workspace.db"))
    from locust_templates.workspace_api import create_workspace_app

    client = create_workspace_app().test_client()
    response = client.post("/api/v1/analysis", json={
        "csv_prefix": str((FIXTURES / "run_b" / "run_b").resolve()),
        "baseline_prefix": str((FIXTURES / "run_a" / "run_a").resolve()),
        "slos": {"p95": 500.0},
    })
    payload = response.get_json()
    assert payload["findings"][0]["current_value"] is not None
    assert "row_numbers" in payload["findings"][0]["sources"][0]


def test_bundle_includes_source_inputs_and_runtime_provenance(tmp_path: Path) -> None:
    output = tmp_path / "evidence.zip"
    create_evidence_bundle(
        str(FIXTURES / "run_b" / "run_b"), output,
        baseline_prefix=str(FIXTURES / "run_a" / "run_a"), slos={"p95": 500.0},
    )
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert any(name.startswith("sources/current/") for name in names)
        provenance = json.loads(archive.read("provenance.json"))
        assert provenance["python_version"]
        assert provenance["platform"]
        assert provenance["data_quality_grade"] in {"A", "B", "C", "D"}
