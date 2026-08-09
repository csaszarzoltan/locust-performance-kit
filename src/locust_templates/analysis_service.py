"""Shared application service for deterministic run decisions."""
from __future__ import annotations

from pathlib import Path

from locust_templates.decision_artifact import build_decision
from locust_templates.intelligence import analyze_run


def analyze_decision(prefix: str, *, baseline_prefix: str|None=None, slos: dict[str,float]|None=None, label: str|None=None, environment: str|None=None, branch: str|None=None, input_hashes: dict[str,str]|None=None):
    report=analyze_run(prefix,baseline_prefix=baseline_prefix,slos=slos)
    return report,build_decision(report,run_label=label or Path(prefix).name,environment=environment,branch=branch,input_hashes=input_hashes)
__all__=["analyze_decision"]
