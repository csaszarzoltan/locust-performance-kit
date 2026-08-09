import json
from pathlib import Path

from locust_templates.decision_artifact import (
 atomic_write,
 build_decision,
 render_markdown,
 verify_decision,
)
from locust_templates.intelligence import analyze_run

FIX=Path(__file__).parents[1]/"fixtures/intelligence"
def report():return analyze_run(str(FIX/"run_b/run_b"),baseline_prefix=str(FIX/"run_a/run_a"),slos={"p95":500})
def test_us006_canonical_hash_stability():
 a=build_decision(report(),run_label="x");b=build_decision(report(),run_label="x")
 assert a["hash"]["value"]==b["hash"]["value"] and verify_decision(a)
def test_us006_markdown_top_twenty():
 d=build_decision(report());d["findings"]*=10
 text=render_markdown(d); assert text.count("- **") == 20 and "additional findings" in text
def test_us006_atomic_export_failure(tmp_path):
 old=tmp_path/"d.json";old.write_text("old");atomic_write(old,b"new");assert old.read_bytes()==b"new"
 assert json.loads(json.dumps(build_decision(report())))["schema"]=="performance-decision/v1"
def test_artifact_hides_absolute_prefix():
 d=build_decision(report());assert str(FIX) not in json.dumps(d)

def test_us004_complete_endpoint_deltas_and_timeline():
    decision = build_decision(report())
    assert decision["baseline"]["compatibility"]["status"] == "COMPATIBLE"
    assert decision["baseline"]["compatibility"]["common"] >= 1
    row = next(item for item in decision["endpoint_comparison"] if item["state"] == "COMMON")
    assert set(row["metrics"]) >= {"p95", "p99", "error_rate", "rps", "request_count", "failure_count"}
    assert row["metrics"]["p95"]["current"] is not None
    assert row["metrics"]["p95"]["baseline"] is not None
    assert row["metrics"]["p95"]["absolute_delta"] is not None
    assert row["metrics"]["p95"]["percent_delta"] is not None
    assert decision["timeline"]["aligned"] is True
    assert decision["timeline"]["current"] and decision["timeline"]["baseline"]


def test_us004_added_missing_never_fabricate_percentage():
    run = report()
    run.profile.endpoints.pop()
    run.profile.endpoints.append(run.profile.endpoints[0].__class__("/new", "GET", 1, 0, 1.0, 0.0, 1, 2, 3, 1, 1, 3))
    decision = build_decision(run)
    states = {item["state"] for item in decision["endpoint_comparison"]}
    assert {"ADDED", "MISSING"} <= states
    for item in decision["endpoint_comparison"]:
        if item["state"] != "COMMON":
            assert all(metric["percent_delta"] is None for metric in item["metrics"].values())
