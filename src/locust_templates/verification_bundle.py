"""Deterministic, offline-verifiable performance decision bundles."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from locust_templates.decision_artifact import render_markdown, verify_decision

BUNDLE_SCHEMA = "performance-verification-bundle/v1"
RESULT_SCHEMA = "verification-result/v1"
MAX_COMPRESSED = 100 * 1024 * 1024
MAX_EXPANDED = 500 * 1024 * 1024
MAX_MEMBERS = 2000
MAX_RATIO = 100


class BundleError(ValueError):
    """A stable, user-safe bundle validation failure."""
    def __init__(self, code: str, member: str = "") -> None:
        super().__init__(code)
        self.code, self.member = code, member


@dataclass(frozen=True)
class FileCheck:
    path: str
    status: str
    expected_sha256: str = ""
    actual_sha256: str = ""


@dataclass(frozen=True)
class VerificationResult:
    schema: str
    status: str
    checks: dict[str, str]
    files: list[FileCheck]
    recorded_decision_hash: str | None
    regenerated_decision_hash: str | None = None
    differences: list[dict[str, Any]] | None = None
    error_code: str | None = None
    error_member: str | None = None
    exit_code: int = 0

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _safe_name(name: str) -> str:
    p = PurePosixPath(name)
    if not name or name.startswith(("/", "\\")) or ".." in p.parts or "\\" in name or any(ord(c) < 32 for c in name):
        raise BundleError("ARCHIVE_PATH_INVALID", name)
    return str(p)


def _zip_bytes(files: Mapping[str, bytes]) -> bytes:
    out = tempfile.SpooledTemporaryFile()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100600 << 16
            zf.writestr(info, files[name])
    out.seek(0)
    return out.read()


def build_verification_bundle(
    decision: dict[str, Any], sources: Mapping[str, str | Path | bytes], *, policy: dict[str, Any] | None = None,
) -> bytes:
    """Return deterministic ZIP bytes for one canonical decision and its sources."""
    if not verify_decision(decision):
        raise BundleError("DECISION_HASH_INVALID")
    payload: dict[str, bytes] = {
        "decision.json": json.dumps(decision, indent=2, sort_keys=True, ensure_ascii=False).encode(),
        "summary.md": render_markdown(decision).encode(),
        "policy.json": json.dumps(policy or {"slos": decision.get("slos", {}), "analyzer": decision.get("analyzer", {})}, indent=2, sort_keys=True).encode(),
        "provenance.json": json.dumps({"schema": BUNDLE_SCHEMA, "decision_hash": decision["hash"]["value"], "network_used": False}, indent=2, sort_keys=True).encode(),
    }
    for role, value in sources.items():
        name = _safe_name(f"sources/{role}")
        payload[name] = value if isinstance(value, bytes) else Path(value).read_bytes()
    entries = [{"path": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in sorted(payload.items())]
    manifest_body = {"schema": BUNDLE_SCHEMA, "entries": entries}
    manifest_body["bundle_identity"] = hashlib.sha256(_canonical(manifest_body)).hexdigest()
    payload["manifest.json"] = json.dumps(manifest_body, indent=2, sort_keys=True).encode()
    return _zip_bytes(payload)


def _inventory(zf: zipfile.ZipFile) -> None:
    infos = zf.infolist()
    if len(infos) > MAX_MEMBERS:
        raise BundleError("ARCHIVE_MEMBER_LIMIT")
    seen: set[str] = set(); expanded = 0
    for info in infos:
        name = _safe_name(info.filename)
        key = name.casefold()
        if key in seen:
            raise BundleError("ARCHIVE_DUPLICATE_MEMBER", name)
        seen.add(key)
        mode = info.external_attr >> 16
        if mode and (mode & 0o170000) not in (0, 0o100000):
            raise BundleError("ARCHIVE_SPECIAL_FILE", name)
        if info.flag_bits & 1:
            raise BundleError("ARCHIVE_ENCRYPTED", name)
        expanded += info.file_size
        if info.file_size and info.file_size / max(info.compress_size, 1) > MAX_RATIO:
            raise BundleError("ARCHIVE_RATIO_LIMIT", name)
    if expanded > MAX_EXPANDED:
        raise BundleError("ARCHIVE_EXPANDED_LIMIT")


def verify_bundle(path: str | Path) -> VerificationResult:
    """Validate archive safety, exact manifest membership, hashes, and decision identity."""
    p = Path(path)
    try:
        if p.stat().st_size > MAX_COMPRESSED:
            raise BundleError("ARCHIVE_COMPRESSED_LIMIT")
        with zipfile.ZipFile(p) as zf:
            _inventory(zf)
            if zf.testzip():
                raise BundleError("ARCHIVE_CRC_INVALID", zf.testzip() or "")
            names = set(zf.namelist())
            if "manifest.json" not in names:
                raise BundleError("MANIFEST_MISSING")
            manifest = json.loads(zf.read("manifest.json"))
            if manifest.get("schema") != BUNDLE_SCHEMA:
                return VerificationResult(RESULT_SCHEMA, "UNSUPPORTED", {"archive":"PASS","manifest":"UNSUPPORTED"}, [], None, error_code="BUNDLE_SCHEMA_UNSUPPORTED", exit_code=1)
            expected = {x["path"]: x for x in manifest.get("entries", [])}
            if names != set(expected) | {"manifest.json"}:
                raise BundleError("ARCHIVE_MEMBER_SET_INVALID")
            ident = manifest.get("bundle_identity"); body = {k:v for k,v in manifest.items() if k != "bundle_identity"}
            if ident != hashlib.sha256(_canonical(body)).hexdigest():
                raise BundleError("MANIFEST_IDENTITY_INVALID")
            checks: list[FileCheck] = []
            for name, item in sorted(expected.items()):
                data = zf.read(name); actual = hashlib.sha256(data).hexdigest()
                status = "PASS" if actual == item["sha256"] and len(data) == item["bytes"] else "FAIL"
                checks.append(FileCheck(name, status, item["sha256"], actual))
                if status == "FAIL":
                    raise BundleError("BUNDLE_HASH_MISMATCH", name)
            decision = json.loads(zf.read("decision.json"))
            if not verify_decision(decision):
                raise BundleError("DECISION_HASH_INVALID", "decision.json")
            return VerificationResult(RESULT_SCHEMA, "VALID", {"archive":"PASS","manifest":"PASS","decision":"PASS","policy":"PASS","provenance":"PASS","sources":"PASS"}, checks, decision["hash"]["value"])
    except (BundleError, zipfile.BadZipFile, KeyError, json.JSONDecodeError, OSError) as exc:
        code = exc.code if isinstance(exc, BundleError) else "BUNDLE_INVALID"
        member = exc.member if isinstance(exc, BundleError) else ""
        return VerificationResult(RESULT_SCHEMA, "INVALID", {"archive":"FAIL"}, [], None, error_code=code, error_member=member, exit_code=1)


def extract_verified(path: str | Path, destination: str | Path) -> Path:
    result = verify_bundle(path)
    if result.status != "VALID":
        raise BundleError(result.error_code or "BUNDLE_INVALID", result.error_member or "")
    dest = Path(destination); dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            target = dest / _safe_name(name); target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, target.open("wb") as out: shutil.copyfileobj(src, out)
    return dest


def decision_diff(recorded: dict[str, Any], regenerated: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic JSON-pointer differences, excluding generated time."""
    def clean(v: dict[str, Any]) -> dict[str, Any]:
        v = json.loads(json.dumps(v)); v.pop("hash", None)
        for finding in v.get("findings", []):
            for source in finding.get("sources", []):
                path=str(source.get("path", ""))
                for suffix in ("_stats_history.csv", "_stats.csv", "_failures.csv", "_exceptions.csv"):
                    if path.endswith(suffix): source["path"]="<current>"+suffix
        return v
    diffs: list[dict[str, Any]] = []
    def walk(a: Any, b: Any, path: str) -> None:
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(set(a) | set(b)): walk(a.get(key), b.get(key), path + "/" + key.replace("~","~0").replace("/","~1"))
        elif a != b: diffs.append({"path": path or "/", "recorded": a, "regenerated": b})
    walk(clean(recorded), clean(regenerated), "")
    return diffs

__all__ = ["BUNDLE_SCHEMA","RESULT_SCHEMA","BundleError","FileCheck","VerificationResult","build_verification_bundle","verify_bundle","extract_verified","decision_diff","reproduce_bundle"]


def reproduce_bundle(path: str | Path) -> VerificationResult:
    """Re-run deterministic analysis from verified packaged Locust CSV sources."""
    import tempfile
    from locust_templates.analysis_service import analyze_decision
    verified = verify_bundle(path)
    if verified.status != "VALID":
        return VerificationResult(RESULT_SCHEMA,"UNREPRODUCIBLE",verified.checks,verified.files,verified.recorded_decision_hash,error_code=verified.error_code or "BUNDLE_INVALID",exit_code=1)
    try:
        with tempfile.TemporaryDirectory(prefix="lpk-reproduce-") as td:
            root=extract_verified(path,td)
            recorded=json.loads((root/"decision.json").read_text())
            policy=json.loads((root/"policy.json").read_text())
            stats=sorted((root/"sources/current").glob("*_stats.csv"))
            if not stats: raise BundleError("BUNDLE_SOURCE_ROLE_MISSING","sources/current/*_stats.csv")
            current=str(stats[0])[:-10]
            baseline_stats=sorted((root/"sources/baseline").glob("*_stats.csv")) if (root/"sources/baseline").exists() else []
            baseline=str(baseline_stats[0])[:-10] if baseline_stats else None
            _, regenerated=analyze_decision(current,baseline_prefix=baseline,slos=policy.get("slos") or None,label=recorded.get("run",{}).get("label"),environment=recorded.get("run",{}).get("environment"),branch=recorded.get("run",{}).get("branch"),input_hashes=recorded.get("inputs",{}))
            diffs=decision_diff(recorded,regenerated)
            status="MATCH" if not diffs else "DRIFT"
            return VerificationResult(RESULT_SCHEMA,status,verified.checks,verified.files,recorded["hash"]["value"],regenerated["hash"]["value"],diffs,exit_code=0 if status=="MATCH" else 1)
    except (BundleError,OSError,ValueError,KeyError,json.JSONDecodeError) as exc:
        code=exc.code if isinstance(exc,BundleError) else "BUNDLE_UNREPRODUCIBLE"
        return VerificationResult(RESULT_SCHEMA,"UNREPRODUCIBLE",verified.checks,verified.files,verified.recorded_decision_hash,error_code=code,error_member=getattr(exc,"member",None),exit_code=1)
