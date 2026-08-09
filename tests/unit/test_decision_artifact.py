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
