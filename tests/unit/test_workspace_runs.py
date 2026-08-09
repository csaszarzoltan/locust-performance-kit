from locust_templates.product_workspace import PerformanceWorkspace


def decision(status="PASS",grade="A",hashv="a"):
 return {"schema":"performance-decision/v1","decision":{"status":status},"quality":{"grade":grade},"hash":{"value":hashv}}
def test_us002_combined_filters(tmp_path):
 w=PerformanceWorkspace(tmp_path/"w.db")
 w.save_analysis_run(run_id="1",label="alpha",environment="prod",branch="main",decision=decision())
 w.save_analysis_run(run_id="2",label="beta",environment="dev",branch="x",decision=decision("FAIL",hashv="b"))
 assert [x["id"] for x in w.list_analysis_runs(environment="prod",decision="PASS")]==["1"]
def test_us002_missing_metadata_filter(tmp_path):
 w=PerformanceWorkspace(tmp_path/"w.db");w.save_analysis_run(run_id="1",label="x",decision=decision())
 assert w.list_analysis_runs(branch="main")==[] and len(w.list_analysis_runs(missing_metadata=True))==1
def test_us005_promotion_audit_and_replacement(tmp_path):
 w=PerformanceWorkspace(tmp_path/"w.db")
 for i in ("1","2"):w.save_analysis_run(run_id=i,label=i,environment="prod",branch="main",decision=decision(hashv=i))
 w.promote_baseline("1","prod","one","first stable run")
 w.promote_baseline("2","prod","two","replacement run")
 rows=w.list_baselines("prod");assert sum(x["state"]=="ACTIVE" for x in rows)==1 and any(x["state"]=="SUPERSEDED" for x in rows)
def test_us005_ineligible_promotion_lists_prerequisites(tmp_path):
 import pytest
 w=PerformanceWorkspace(tmp_path/"w.db");w.save_analysis_run(run_id="1",label="x",decision=decision("FAIL"))
 with pytest.raises(ValueError,match="NOT_ELIGIBLE"):w.promote_baseline("1","prod","x","cannot promote")
