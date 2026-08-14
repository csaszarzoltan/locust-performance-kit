import time
from locust_templates.campaigns import build_campaign,render_campaign_markdown
def run(i,status="PASS",slo=500,created=None):
 return {"id":i,"decision":status,"quality_grade":"A","created":created or time.time(),"report":{"schema":"performance-decision/v1","analyzer":{"name":"x","version":"1"},"slos":{"p95":slo},"baseline":{"label":None},"inputs":{}}}
def test_us_004_missing_slot_is_incomplete():
 c=build_campaign("R","",[{"environment":"prod","scenario":"api","run":None}],now=time.time());assert c["readiness"]=="INCOMPLETE"
def test_us_005_policy_drift_is_advisory():
 c=build_campaign("R","",[{"environment":"prod","scenario":"a","run":run("1",slo=500)},{"environment":"prod","scenario":"b","run":run("2",slo=600)}],now=time.time());assert c["readiness"]=="ADVISORY" and c["drift"][0]["kind"]=="POLICY_DRIFT"
def test_us_006_artifact_is_deterministic():
 slots=[{"environment":"prod","scenario":"api","run":run("1")}];a=build_campaign("R","",slots,now=1);b=build_campaign("R","",slots,now=2);assert a==b and a["campaign_hash"] in render_campaign_markdown(a)
