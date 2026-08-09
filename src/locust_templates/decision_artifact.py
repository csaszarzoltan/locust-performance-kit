"""Canonical release decision JSON and Markdown artifacts."""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from locust_templates.evidence import evidence_from_report

SCHEMA="performance-decision/v1"

def _finite(value: Any) -> Any:
    if isinstance(value,float) and not math.isfinite(value): raise ValueError("Decision contains non-finite number")
    if isinstance(value,dict): return {k:_finite(v) for k,v in value.items()}
    if isinstance(value,list): return [_finite(v) for v in value]
    return value

def _safe_label(value: str|None) -> str|None:
    return None if value is None else Path(value).name

def build_decision(report: Any, *, run_label: str|None=None, environment: str|None=None, branch: str|None=None, input_hashes: dict[str,str]|None=None) -> dict[str,Any]:
    findings=[asdict(x) for x in evidence_from_report(report)]
    for finding in findings:
        for source in finding.get("sources", []):
            source["path"] = Path(source["path"]).name
    findings.sort(key=lambda x:({"critical":0,"warning":1,"info":2}.get(x["severity"],3),x["rule_id"],x["message"]))
    payload={"schema":SCHEMA,"analyzer":{"name":"locust-performance-kit","version":"1.6.0"},
      "run":{"label":run_label or _safe_label(report.csv_prefix),"environment":environment,"branch":branch},
      "inputs":dict(sorted((input_hashes or {}).items())),"quality":{"grade": findings[0]["data_quality_grade"] if findings else ("A" if len(report.profile.history)>=10 else "C")},
      "baseline":{"label":_safe_label(report.profile.baseline.csv_prefix) if report.profile.baseline else None},
      "slos":{x.metric:x.slo_value for x in report.slo_violations},"decision":{"status":"FAIL" if report.exit_code==2 else ("PASS" if report.slo_violations else "ADVISORY"),"exit_code":report.exit_code},
      "summary":report.to_json().get("summary",{}),"endpoint_comparison":[],"findings":findings}
    payload=_finite(payload)
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    digest=hashlib.sha256(canonical).hexdigest()
    return {**payload,"hash":{"algorithm":"sha256","value":digest,"generated_at":datetime.now(timezone.utc).isoformat(),"generated_at_excluded":True}}

def verify_decision(decision: dict[str,Any])->bool:
    raw={k:v for k,v in decision.items() if k!="hash"}
    digest=hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    return digest==decision.get("hash",{}).get("value")

def render_markdown(decision: dict[str,Any])->str:
    esc=lambda v:str(v).replace("\\","\\\\").replace("|","\\|").replace("<","&lt;").replace(">","&gt;").replace("\n"," ")
    lines=["# Performance Decision",f"**{decision['decision']['status']}** · quality {decision['quality']['grade']}","",f"Decision hash: `{decision['hash']['value']}`","","## Findings"]
    findings=decision["findings"][:20]
    lines += [f"- **{esc(x['severity'].upper())}** {esc(x['message'])} Next check: {esc(x['next_check'])}" for x in findings]
    if len(decision["findings"])>20: lines.append(f"- {len(decision['findings'])-20} additional findings are available in decision JSON.")
    return "\n".join(lines)+"\n"
def atomic_write(path: str|Path, data: bytes)->Path:
    dest=Path(path); dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.is_dir(): raise IsADirectoryError(dest)
    fd,tmp=tempfile.mkstemp(dir=dest.parent,prefix=f".{dest.name}.")
    try:
        with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,dest)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise
    return dest
__all__=["SCHEMA","atomic_write","build_decision","render_markdown","verify_decision"]
