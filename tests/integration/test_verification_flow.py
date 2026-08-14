import json,zipfile
from pathlib import Path
from locust_templates.analysis_service import analyze_decision
from locust_templates.verification_bundle import build_verification_bundle,reproduce_bundle,verify_bundle
FIX=Path(__file__).parents[1]/"fixtures/intelligence/run_a/run_a"
def files():
 return {f"current/run{x}":Path(str(FIX)+x) for x in ("_stats.csv","_stats_history.csv","_failures.csv","_exceptions.csv")}
def test_us_003_real_io_reproduction_match(tmp_path):
 _,d=analyze_decision(str(FIX),slos={"p95":500}); p=tmp_path/"a.zip";p.write_bytes(build_verification_bundle(d,files()))
 r=reproduce_bundle(p); assert r.status=="MATCH" and r.exit_code==0 and r.differences==[]
def test_us_002_extra_member_rejected(tmp_path):
 _,d=analyze_decision(str(FIX),slos={"p95":500}); p=tmp_path/"a.zip";p.write_bytes(build_verification_bundle(d,files())); q=tmp_path/"b.zip"
 with zipfile.ZipFile(p) as a,zipfile.ZipFile(q,"w") as b:
  for n in a.namelist():b.writestr(n,a.read(n))
  b.writestr("extra",b"x")
 assert verify_bundle(q).error_code=="ARCHIVE_MEMBER_SET_INVALID"
