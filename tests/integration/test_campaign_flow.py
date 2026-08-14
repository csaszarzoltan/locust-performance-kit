from locust_templates.product_workspace import PerformanceWorkspace
from locust_templates.analysis_service import analyze_decision
from pathlib import Path
import pytest
FIX=Path(__file__).parents[1]/"fixtures/intelligence/run_a/run_a"
def test_us_004_multislot_edit_and_conflict(tmp_path):
 w=PerformanceWorkspace(tmp_path/"w.db");_,d=analyze_decision(str(FIX),slos={"p95":500})
 w.save_analysis_run(run_id="r",label="R",environment="prod",decision=d)
 cid=w.create_campaign("Rel","",[{"environment":"prod","scenario":"a","run_id":"r"}]); token=w.campaign(cid)["updated"]
 w.update_campaign(cid,"Rel 2","",[{"environment":"prod","scenario":"a","run_id":"r"},{"environment":"stage","scenario":"b"}],token)
 assert len(w.campaign(cid)["slots"])==2
 with pytest.raises(ValueError,match="CAMPAIGN_CHANGED"):w.update_campaign(cid,"Old","",[{"environment":"prod","scenario":"a"}],token)
def test_us_006_finalized_is_immutable(tmp_path):
 w=PerformanceWorkspace(tmp_path/"w.db");_,d=analyze_decision(str(FIX),slos={"p95":500});w.save_analysis_run(run_id="r",label="R",environment="prod",decision=d)
 cid=w.create_campaign("Rel","",[{"environment":"prod","scenario":"unspecified","run_id":"r"}]);w.finalize_campaign(cid)
 with pytest.raises(ValueError,match="CAMPAIGN_FINALIZED"):w.update_campaign(cid,"X","",[{"environment":"prod","scenario":"x"}],w.campaign(cid)["updated"])
