"""Safe Locust result archive discovery and evidence staging."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import stat
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO


class ImportValidationError(ValueError):
    """A stable, user-correctable import validation failure."""
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class MappedFile:
    role: str
    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class RunCandidate:
    prefix: str
    files: tuple[MappedFile, ...]
    endpoint_count: int
    history_samples: int
    has_aggregate: bool
    quality_grade: str
    checks: tuple[str, ...]


@dataclass(frozen=True)
class ImportPreview:
    candidates: tuple[RunCandidate, ...]
    created_at: float

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


class SafeRunImporter:
    """Validate and extract bounded ZIP evidence without path traversal."""
    def __init__(self, staging_root: str | Path, *, max_archive=100*1024*1024,
                 max_uncompressed=500*1024*1024, max_members=2000,
                 max_ratio=100.0) -> None:
        self.root = Path(staging_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_archive=max_archive; self.max_uncompressed=max_uncompressed
        self.max_members=max_members; self.max_ratio=max_ratio

    @staticmethod
    def _safe_name(name: str) -> str:
        if any(ord(c)<32 for c in name):
            raise ImportValidationError("ARCHIVE_NAME_INVALID", "Archive member contains a control character")
        p=PurePosixPath(name.replace("\\","/"))
        if p.is_absolute() or ".." in p.parts or (p.parts and ":" in p.parts[0]):
            raise ImportValidationError("ARCHIVE_PATH_UNSAFE", "Archive contains an unsafe path")
        clean=str(p)
        if clean in {"", "."}: raise ImportValidationError("ARCHIVE_NAME_INVALID", "Archive member name is empty")
        return clean

    def extract(self, source: str | Path | BinaryIO, session_id: str) -> tuple[Path, ImportPreview]:
        if isinstance(source, (str, Path)):
            size = Path(source).stat().st_size
        else:
            source.seek(0, 2)
            size = source.tell()
            source.seek(0)
        if size>self.max_archive: raise ImportValidationError("ARCHIVE_TOO_LARGE", "Archive exceeds the configured size limit")
        target=(self.root/session_id).resolve()
        if target.exists(): shutil.rmtree(target)
        target.mkdir(mode=0o700)
        try:
            with zipfile.ZipFile(source) as z:
                infos=z.infolist()
                if not infos: raise ImportValidationError("ARCHIVE_EMPTY", "Archive is empty")
                if len(infos)>self.max_members: raise ImportValidationError("ARCHIVE_TOO_MANY_MEMBERS", "Archive contains too many members")
                seen=set(); total=0
                for info in infos:
                    name=self._safe_name(info.filename)
                    key=name.casefold()
                    if key in seen: raise ImportValidationError("ARCHIVE_DUPLICATE_PATH", "Archive contains duplicate normalized paths")
                    seen.add(key)
                    mode=info.external_attr>>16
                    if stat.S_ISLNK(mode): raise ImportValidationError("ARCHIVE_SYMLINK", "Archive symlinks are not allowed")
                    if info.flag_bits & 1: raise ImportValidationError("ARCHIVE_ENCRYPTED", "Encrypted archive members are not supported")
                    total += info.file_size
                    ratio=info.file_size/max(info.compress_size,1)
                    if total>self.max_uncompressed or ratio>self.max_ratio:
                        raise ImportValidationError("ARCHIVE_EXPANSION_LIMIT", "Archive expansion limit exceeded")
                for info in infos:
                    name=self._safe_name(info.filename)
                    out=(target/name).resolve()
                    if target != out and target not in out.parents:
                        raise ImportValidationError("ARCHIVE_PATH_UNSAFE", "Archive member escaped staging")
                    if info.is_dir(): out.mkdir(parents=True,exist_ok=True); continue
                    out.parent.mkdir(parents=True,exist_ok=True)
                    with z.open(info) as src, out.open("wb") as dst: shutil.copyfileobj(src,dst,1024*1024)
                    os.chmod(out,0o600)
                bad=z.testzip()
                if bad: raise ImportValidationError("ARCHIVE_CRC_INVALID", f"Archive member failed CRC: {bad}")
            preview=discover_candidates(target)
            return target, preview
        except Exception:
            shutil.rmtree(target,ignore_errors=True)
            raise


def _hash(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def discover_candidates(root: str | Path) -> ImportPreview:
    root=Path(root).resolve(); candidates=[]
    for stats in sorted(root.rglob("*_stats.csv")):
        if stats.name.endswith("_stats_history.csv"): continue
        prefix=stats.name[:-10]
        base=stats.with_name(prefix)
        roles={"stats":stats}
        for role,suffix in (("history","_stats_history.csv"),("history_legacy","_history.csv"),("failures","_failures.csv"),("exceptions","_exceptions.csv")):
            p=Path(str(base)+suffix)
            if p.is_file(): roles[role]=p
        endpoint_count=0; aggregate=False
        try:
            with stats.open(newline="",encoding="utf-8-sig") as f:
                reader=csv.DictReader(f)
                if not reader.fieldnames or "Name" not in reader.fieldnames:
                    raise ImportValidationError("STATS_HEADER_INVALID", f"Invalid stats header: {stats.name}")
                for row in reader:
                    if row.get("Name")=="Aggregated": aggregate=True
                    elif row.get("Name"): endpoint_count+=1
        except UnicodeError as e: raise ImportValidationError("STATS_ENCODING_INVALID", "Stats CSV is not UTF-8") from e
        if not aggregate: continue
        hp=roles.get("history") or roles.get("history_legacy"); samples=0; ordered=True
        if hp:
            last=None
            with hp.open(newline="",encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    if row.get("Name")=="Aggregated":
                        samples+=1
                        try: ts=float(row.get("Timestamp",0))
                        except ValueError: ts=0
                        if last is not None and ts<last: ordered=False
                        last=ts
        grade="A" if samples>=10 and ordered else "B" if samples>=5 else "C"
        checks=("stats:pass","aggregate:pass",f"history_samples:{samples}",f"timestamps:{'pass' if ordered else 'warning'}")
        mapped=tuple(MappedFile(r,str(p.relative_to(root)),p.stat().st_size,_hash(p)) for r,p in sorted(roles.items()))
        candidates.append(RunCandidate(str(base.relative_to(root)),mapped,endpoint_count,samples,aggregate,grade,checks))
    if not candidates: raise ImportValidationError("STATS_NOT_FOUND", "No valid Locust *_stats.csv with Aggregated row was found")
    return ImportPreview(tuple(candidates),time.time())


def commit_candidate(staging: str | Path, storage: str | Path, run_id: str, candidate: RunCandidate) -> dict[str,str]:
    staging=Path(staging).resolve(); destination=(Path(storage).resolve()/run_id)
    destination.mkdir(parents=True,exist_ok=False,mode=0o700); result={}
    try:
        for item in candidate.files:
            src=(staging/item.path).resolve()
            if staging not in src.parents or _hash(src)!=item.sha256:
                raise ImportValidationError("EVIDENCE_CHANGED", "Validated evidence changed before commit")
            suffix={"stats":"_stats.csv","history":"_stats_history.csv","history_legacy":"_history.csv","failures":"_failures.csv","exceptions":"_exceptions.csv"}[item.role]
            dst=destination/f"run{suffix}"
            shutil.copyfile(src,dst); os.chmod(dst,0o600)
            result[item.role]=str(dst)
        return result
    except Exception:
        shutil.rmtree(destination,ignore_errors=True); raise

__all__=["ImportPreview","ImportValidationError","MappedFile","RunCandidate","SafeRunImporter","commit_candidate","discover_candidates"]
