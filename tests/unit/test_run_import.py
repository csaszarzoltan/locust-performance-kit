from __future__ import annotations

import io
import stat
import zipfile
from pathlib import Path

import pytest

from locust_templates.run_import import (
 ImportValidationError,
 SafeRunImporter,
 discover_candidates,
)

FIX=Path(__file__).parents[1]/"fixtures/intelligence/run_a"
def archive(names=None):
 b=io.BytesIO()
 with zipfile.ZipFile(b,"w") as z:
  if names:
   for name,data in names:z.writestr(name,data)
  else:
   for p in FIX.iterdir():z.writestr(p.name,p.read_bytes())
 b.seek(0);return b
def test_us001_valid_zip_detects_and_enables_analysis(tmp_path):
 _,p=SafeRunImporter(tmp_path).extract(archive(),"a")
 assert len(p.candidates)==1 and p.candidates[0].endpoint_count==6
 assert p.candidates[0].quality_grade in {"A","B"}
def test_us001_multiple_candidates_require_selection(tmp_path):
 b=io.BytesIO()
 with zipfile.ZipFile(b,"w") as z:
  for folder in ("one","two"):
   for p in FIX.iterdir():z.writestr(f"{folder}/{p.name}",p.read_bytes())
 b.seek(0); _,p=SafeRunImporter(tmp_path).extract(b,"b"); assert len(p.candidates)==2
def test_us001_traversal_or_missing_stats_rejected(tmp_path):
 with pytest.raises(ImportValidationError,match="unsafe path"):SafeRunImporter(tmp_path).extract(archive([("../evil","x")]),"e")
 assert not (tmp_path.parent/"evil").exists()
 with pytest.raises(ImportValidationError) as ex:SafeRunImporter(tmp_path).extract(archive([("readme.txt","x")]),"n")
 assert ex.value.code=="STATS_NOT_FOUND"
def test_rejects_duplicate_symlink_and_ratio(tmp_path):
 with pytest.raises(ImportValidationError):SafeRunImporter(tmp_path).extract(archive([("A","1"),("a","2")]),"d")
 b=io.BytesIO()
 with zipfile.ZipFile(b,"w") as z:
  i=zipfile.ZipInfo("link");i.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(i,"target")
 b.seek(0)
 with pytest.raises(ImportValidationError):SafeRunImporter(tmp_path).extract(b,"s")
def test_discovery_grade_c_without_history(tmp_path):
 p=next(FIX.glob("*_stats.csv"));(tmp_path/"x_stats.csv").write_bytes(p.read_bytes())
 assert discover_candidates(tmp_path).candidates[0].quality_grade=="C"

def test_preview_json_and_path_source_commit(tmp_path):
    source = tmp_path / "source.zip"
    source.write_bytes(archive().getvalue())
    staging, preview = SafeRunImporter(tmp_path / "stage").extract(source, "path")
    assert '"quality_grade"' in preview.to_json()
    from locust_templates.run_import import commit_candidate
    result = commit_candidate(staging, tmp_path / "store", "run1", preview.candidates[0])
    assert Path(result["stats"]).name == "run_stats.csv"


def test_size_member_empty_and_expansion_limits(tmp_path):
    with pytest.raises(ImportValidationError) as ex:
        SafeRunImporter(tmp_path, max_archive=1).extract(archive(), "large")
    assert ex.value.code == "ARCHIVE_TOO_LARGE"
    empty = io.BytesIO()
    with zipfile.ZipFile(empty, "w"):
        pass
    empty.seek(0)
    with pytest.raises(ImportValidationError) as ex:
        SafeRunImporter(tmp_path).extract(empty, "empty")
    assert ex.value.code == "ARCHIVE_EMPTY"
    with pytest.raises(ImportValidationError) as ex:
        SafeRunImporter(tmp_path, max_members=1).extract(archive(), "members")
    assert ex.value.code == "ARCHIVE_TOO_MANY_MEMBERS"
    with pytest.raises(ImportValidationError) as ex:
        SafeRunImporter(tmp_path, max_uncompressed=1).extract(archive(), "expand")
    assert ex.value.code == "ARCHIVE_EXPANSION_LIMIT"


def test_invalid_control_header_encoding_and_history_timestamp(tmp_path):
    with pytest.raises(ImportValidationError) as ex:
        SafeRunImporter._safe_name("bad\x00name")
    assert ex.value.code == "ARCHIVE_NAME_INVALID"
    (tmp_path / "x_stats.csv").write_text("Wrong,Header\na,b\n")
    with pytest.raises(ImportValidationError) as ex:
        discover_candidates(tmp_path)
    assert ex.value.code == "STATS_HEADER_INVALID"
    (tmp_path / "x_stats.csv").write_bytes(b"\xff\xfe")
    with pytest.raises(ImportValidationError) as ex:
        discover_candidates(tmp_path)
    assert ex.value.code in {"STATS_HEADER_INVALID", "STATS_ENCODING_INVALID"}
    stats = next(FIX.glob("*_stats.csv"))
    (tmp_path / "x_stats.csv").write_bytes(stats.read_bytes())
    history = next(FIX.glob("*_stats_history.csv")).read_text().splitlines()
    history[1] = history[1].replace("1700000000", "not-a-time")
    (tmp_path / "x_stats_history.csv").write_text("\n".join(history))
    assert discover_candidates(tmp_path).candidates[0].quality_grade in {"A", "B"}


def test_commit_detects_changed_evidence_and_cleans_destination(tmp_path):
    from locust_templates.run_import import commit_candidate
    staging, preview = SafeRunImporter(tmp_path / "stage").extract(archive(), "changed")
    candidate = preview.candidates[0]
    (staging / candidate.files[0].path).write_text("changed")
    with pytest.raises(ImportValidationError) as ex:
        commit_candidate(staging, tmp_path / "store", "run2", candidate)
    assert ex.value.code == "EVIDENCE_CHANGED"
    assert not (tmp_path / "store" / "run2").exists()
