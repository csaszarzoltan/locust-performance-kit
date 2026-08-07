"""Portable, reproducible CI evidence bundle writer."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import tempfile
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from locust_templates.evidence import evidence_from_report
from locust_templates.intelligence import analyze_run


def _junit(exit_code: int, findings: int) -> bytes:
    suite = ET.Element("testsuite", name="locust-performance-evidence", tests="1", failures=str(int(exit_code == 2)))
    case = ET.SubElement(suite, "testcase", classname="performance", name="measured-slo-gate")
    if exit_code == 2:
        ET.SubElement(case, "failure", type="SLOViolation", message="Measured SLO violation")
    ET.SubElement(case, "system-out").text = f"source-linked-findings={findings}"
    return ET.tostring(suite, encoding="utf-8", xml_declaration=True)


def create_evidence_bundle(
    csv_prefix: str,
    output: str | Path,
    *,
    baseline_prefix: str | None = None,
    slos: dict[str, float] | None = None,
) -> Path:
    """Create an atomic schema-v1 ZIP with reports, checksums, and provenance."""
    destination = Path(output)
    if destination.suffix.lower() != ".zip":
        raise ValueError("Evidence bundle output must be a ZIP file")
    report = analyze_run(csv_prefix, baseline_prefix=baseline_prefix, slos=slos)
    findings = evidence_from_report(report)
    generated = datetime.now(timezone.utc).isoformat()
    report_data = report.to_json()
    report_data.update({"schema_version": 1, "findings": [asdict(item) for item in findings]})
    grade = findings[0].data_quality_grade if findings else "D"
    provenance = {
        "schema_version": 1,
        "generated_at": generated,
        "tool": "locust-performance-kit",
        "tool_version": "1.6.0",
        "csv_prefix": csv_prefix,
        "baseline": baseline_prefix,
        "slos": slos or {},
        "network_calls": False,
        "analysis_mode": "deterministic",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "data_quality_grade": grade,
    }
    payloads = {
        "report.json": json.dumps(report_data, indent=2, sort_keys=True).encode(),
        "summary.md": report.to_markdown().encode(),
        "junit.xml": _junit(report.exit_code, len(findings)),
        "provenance.json": json.dumps(provenance, indent=2, sort_keys=True).encode(),
    }
    for role, prefix in (("current", csv_prefix), ("baseline", baseline_prefix)):
        if not prefix:
            continue
        for suffix in ("_stats.csv", "_failures.csv", "_exceptions.csv", "_stats_history.csv", "_history.csv"):
            source = Path(f"{prefix}{suffix}")
            if source.is_file():
                payloads[f"sources/{role}/{source.name}"] = source.read_bytes()
    manifest = {
        "schema_version": 1,
        "files": [
            {"path": name, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in sorted(payloads.items())
        ],
    }
    payloads["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(payloads.items()):
                archive.writestr(name, data)
        os.replace(temp_name, destination)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise
    return destination


__all__ = ["create_evidence_bundle"]
