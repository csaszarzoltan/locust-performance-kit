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
