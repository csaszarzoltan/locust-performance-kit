import io
import zipfile
from pathlib import Path

import pytest

from locust_templates.workspace_api import create_workspace_app

FIX=Path(__file__).parents[1]/"fixtures/intelligence/run_b"

def zipped():
 b=io.BytesIO()
 with zipfile.ZipFile(b,"w") as z:
  for p in FIX.iterdir():z.writestr(p.name,p.read_bytes())
 b.seek(0);return b
@pytest.fixture
def client(tmp_path,monkeypatch):
 monkeypatch.setenv("LOCUST_WORKSPACE_DB",str(tmp_path/"w.db"));monkeypatch.setenv("LOCUST_WORKSPACE_STORAGE_ROOT",str(tmp_path/"store"));monkeypatch.setenv("LOCUST_WORKSPACE_ENV","development")
 app=create_workspace_app();app.config["TESTING"]=True;return app.test_client()
def test_us001_to_us004_real_import_decision_flow(client):
 assert client.get("/workspace/runs").status_code==200
 r=client.post("/workspace/runs/import/validate",data={"archive":(zipped(),"run.zip")},content_type="multipart/form-data")
 assert r.status_code==200 and b"Quality" in r.data
 text=r.get_data(as_text=True); sid=text.split('name="session_id" value="')[1].split('"')[0]
 r=client.post("/workspace/runs/import/commit",data={"session_id":sid,"candidate":"0","label":"Release run","environment":"prod","branch":"main","p95":"500"})
 assert r.status_code==303
 page=client.get(r.headers["Location"]);assert b"FAIL" in page.data and b"Decision hash" in page.data
 assert client.get(r.headers["Location"]+"/decision.json").status_code==200
 assert client.get(r.headers["Location"]+"/summary.md").status_code==200
def test_us001_traversal_friendly_recovery(client):
 b=io.BytesIO()
 with zipfile.ZipFile(b,"w") as z:z.writestr("../escape","x")
 b.seek(0);r=client.post("/workspace/runs/import/validate",data={"archive":(b,"bad.zip")},content_type="multipart/form-data")
 assert r.status_code==422 and b"ARCHIVE_PATH_UNSAFE" in r.data and b"Import failed" in r.data
def test_health_and_security_headers(client):
 r=client.get("/healthz");assert r.status_code==200 and r.json["database"]=="ok"
 assert r.headers["X-Content-Type-Options"]=="nosniff" and "frame-ancestors" in r.headers["Content-Security-Policy"]
def test_us003_sample_offline_and_idempotent(client):
 r=client.post("/workspace/sample");assert r.status_code==303
 first=r.headers["Location"];assert b"Sample: regressed" in client.get(first).data
 r2=client.post("/workspace/sample");assert r2.status_code==303 and r2.headers["Location"]==first
