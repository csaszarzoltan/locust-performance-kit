import json, zipfile
from pathlib import Path
from locust_templates.decision_artifact import build_decision
from locust_templates.intelligence import analyze_run
from locust_templates.verification_bundle import build_verification_bundle, verify_bundle, decision_diff
FIX=Path(__file__).parents[1]/"fixtures/intelligence/run_a/run_a"
def decision(): return build_decision(analyze_run(str(FIX),slos={"p95":500}))
def test_us_001_deterministic_complete_bundle(tmp_path):
 d=decision(); data=build_verification_bundle(d,{"current/run_stats.csv":Path(str(FIX)+"_stats.csv")}); assert data==build_verification_bundle(d,{"current/run_stats.csv":Path(str(FIX)+"_stats.csv")})
 p=tmp_path/"x.zip";p.write_bytes(data)
 with zipfile.ZipFile(p) as z: assert {"decision.json","summary.md","policy.json","provenance.json","manifest.json","sources/current/run_stats.csv"}==set(z.namelist())
 assert verify_bundle(p).status=="VALID"
def test_us_002_tamper_is_invalid(tmp_path):
 p=tmp_path/"x.zip"; p.write_bytes(build_verification_bundle(decision(),{"current/a":b"ok"}))
 q=tmp_path/"bad.zip"
 with zipfile.ZipFile(p) as zin,zipfile.ZipFile(q,"w") as zout:
  for n in zin.namelist(): zout.writestr(n,b"changed" if n=="sources/current/a" else zin.read(n))
 r=verify_bundle(q); assert r.status=="INVALID" and r.exit_code==1
def test_us_003_diff_reports_slo_path():
 a=decision(); b=json.loads(json.dumps(a)); b["slos"]["p95"]=600
 assert any(x["path"]=="/slos/p95" for x in decision_diff(a,b))
