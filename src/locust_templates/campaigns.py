"""Deterministic release-campaign readiness and artifacts."""
from __future__ import annotations
import hashlib, json
from typing import Any, Sequence
SCHEMA="performance-campaign/v1"
FRESHNESS_DAYS=30

def _canon(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def policy_identity(decision:dict[str,Any])->str:
    v={"schema":decision.get("schema"),"analyzer":decision.get("analyzer"),"slos":decision.get("slos",{}),"quality_rules":"v1"}
    return hashlib.sha256(_canon(v)).hexdigest()
def baseline_identity(run:dict[str,Any])->str|None:
    if run.get("baseline_run_id"): return str(run["baseline_run_id"])
    base=run.get("report",{}).get("baseline",{}); label=base.get("label")
    return hashlib.sha256(_canon({"label":label,"inputs":run.get("report",{}).get("inputs",{})})).hexdigest() if label else None
def build_campaign(label:str,description:str,slots:Sequence[dict[str,Any]],*,now:float, freshness_days:int=FRESHNESS_DAYS)->dict[str,Any]:
    rendered=[]; drift=[]; policy_ids=set(); bases:dict[str,set[str]]={}
    for slot in slots:
        run=slot.get("run")
        if not run:
            rendered.append({"environment":slot["environment"],"scenario":slot["scenario"],"status":"UNKNOWN","run_id":None}); continue
        report=run.get("report",{}); pid=policy_identity(report); policy_ids.add(pid)
        bid=baseline_identity(run); bases.setdefault(slot["environment"],set()).update([bid] if bid else [])
        age=None; fresh="UNKNOWN"
        if slot.get("baseline_created") is not None:
            age=(run.get("created",now)-slot["baseline_created"])/86400; fresh="STALE" if age>freshness_days else "ACTIVE"
            if fresh=="STALE": drift.append({"kind":"BASELINE_STALE","run_id":run["id"],"age_days":round(age,2)})
        rendered.append({"environment":slot["environment"],"scenario":slot["scenario"],"status":run.get("decision","UNKNOWN"),"run_id":run["id"],"quality":run.get("quality_grade"),"policy_identity":pid,"baseline_identity":bid,"freshness":fresh})
    if len(policy_ids)>1: drift.append({"kind":"POLICY_DRIFT","identities":sorted(policy_ids)})
    for env,ids in sorted(bases.items()):
        if len(ids)>1: drift.append({"kind":"BASELINE_DRIFT","environment":env,"identities":sorted(ids)})
    statuses={x["status"] for x in rendered}
    readiness="FAIL" if "FAIL" in statuses else "INCOMPLETE" if "UNKNOWN" in statuses else "ADVISORY" if "ADVISORY" in statuses or drift else "PASS"
    payload={"schema":SCHEMA,"label":label.strip(),"description":description.strip(),"freshness_days":freshness_days,"readiness":readiness,"slots":sorted(rendered,key=lambda x:(x["environment"],x["scenario"])),"drift":sorted(drift,key=lambda x:(x["kind"],str(x)))}
    payload["campaign_hash"]=hashlib.sha256(_canon(payload)).hexdigest(); return payload
def render_campaign_markdown(c:dict[str,Any])->str:
    lines=["# Release Campaign",f"**{c['readiness']}** · `{c['campaign_hash']}`","","| Environment | Scenario | Run | Status | Quality | Freshness |","|---|---|---|---|---|---|"]
    for x in c["slots"]: lines.append(f"| {x['environment']} | {x['scenario']} | {x['run_id'] or 'missing'} | {x['status']} | {x.get('quality') or 'n/a'} | {x.get('freshness') or 'UNKNOWN'} |")
    lines += ["","## Drift"]+[f"- {x['kind']}" for x in c["drift"]]
    return "\n".join(lines)+"\n"
__all__=["SCHEMA","FRESHNESS_DAYS","policy_identity","baseline_identity","build_campaign","render_campaign_markdown"]
