# ruff: noqa: E501
"""Persistent domain services and accessible views for performance engineering."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class VaultAccessDenied(RuntimeError):
    """Raised when a tenant attempts to resolve another tenant's secret."""


_PAGES = {
    "scenarios": (
        "Visual scenario studio",
        "Compose protocol journeys and export reviewable Python.",
    ),
    "runs": (
        "Distributed run orchestrator",
        "Provision zones, watch capacity, and recover workers.",
    ),
    "diagnostics": (
        "Results diagnostics",
        "Drill from regressions to cascades and traces.",
    ),
    "policies": (
        "Performance policy gate",
        "Version release rules, waivers, and decisions.",
    ),
    "vault": (
        "Secure test data vault",
        "Deliver scoped secrets without exposing values.",
    ),
    "capacity": (
        "Capacity and cost planner",
        "Estimate workers, virtual-user hours, and risk.",
    ),
}


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _seal(value: str, key: bytes) -> str:
    raw = value.encode()
    stream = hashlib.sha256(key).digest()
    data = bytes(char ^ stream[index % len(stream)] for index, char in enumerate(raw))
    return base64.urlsafe_b64encode(data).decode()


def _open(value: str, key: bytes) -> str:
    raw = base64.urlsafe_b64decode(value.encode())
    stream = hashlib.sha256(key).digest()
    return bytes(
        char ^ stream[index % len(stream)] for index, char in enumerate(raw)
    ).decode()


class PerformanceWorkspace:
    """Own six additive workflows and their transactional SQLite persistence."""

    def __init__(self, path: str | Path, *, vault_key: bytes | None = None) -> None:
        self.path = str(path)
        self._vault_key = vault_key or b"local-development-key-change-in-production"
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS scenarios(id TEXT PRIMARY KEY,name TEXT,steps TEXT,state TEXT,version INTEGER,created REAL);
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,scenario_id TEXT,zones TEXT,state TEXT,created REAL);
                CREATE TABLE IF NOT EXISTS workers(id TEXT PRIMARY KEY,run_id TEXT,zone TEXT,state TEXT,UNIQUE(run_id,id));
                CREATE TABLE IF NOT EXISTS results(id TEXT PRIMARY KEY,run_id TEXT,records TEXT,state TEXT,created REAL);
                CREATE TABLE IF NOT EXISTS policies(id TEXT PRIMARY KEY,name TEXT,rules TEXT,state TEXT,version INTEGER,created REAL);
                CREATE TABLE IF NOT EXISTS waivers(id TEXT PRIMARY KEY,policy_id TEXT,metric TEXT,expires REAL,state TEXT);
                CREATE TABLE IF NOT EXISTS secrets(id TEXT PRIMARY KEY,tenant TEXT,name TEXT,cipher TEXT,digest TEXT,state TEXT,created REAL,UNIQUE(tenant,name));
                CREATE TABLE IF NOT EXISTS rate_cards(id TEXT PRIMARY KEY,provider TEXT,unit_price REAL,effective REAL,state TEXT);
                CREATE TABLE IF NOT EXISTS estimates(id TEXT PRIMARY KEY,users INTEGER,minutes REAL,zones INTEGER,card_id TEXT,cost REAL,workers INTEGER,state TEXT,created REAL);
                CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY,kind TEXT,resource_id TEXT,data TEXT,created REAL);
                CREATE TABLE IF NOT EXISTS idempotency(key TEXT PRIMARY KEY,resource_id TEXT,created REAL);
                CREATE TABLE IF NOT EXISTS analysis_runs(id TEXT PRIMARY KEY,label TEXT,environment TEXT,branch TEXT,tags_json TEXT,state TEXT,decision TEXT,quality_grade TEXT,source_fingerprint TEXT,baseline_run_id TEXT,slos_json TEXT,report_schema TEXT,report_json TEXT,error_code TEXT,correlation_id TEXT,sample INTEGER,created REAL,updated REAL);
                CREATE TABLE IF NOT EXISTS analysis_inputs(id TEXT PRIMARY KEY,run_id TEXT,role TEXT,relative_path TEXT,original_safe_name TEXT,size INTEGER,sha256 TEXT,created REAL,UNIQUE(run_id,role));
                CREATE TABLE IF NOT EXISTS import_sessions(id TEXT PRIMARY KEY,token_digest TEXT UNIQUE,staging_relative_path TEXT,preview_json TEXT,state TEXT,expires REAL,created REAL,committed_run_id TEXT);
                CREATE TABLE IF NOT EXISTS baselines(id TEXT PRIMARY KEY,environment TEXT,label TEXT,run_id TEXT,state TEXT,reason TEXT,advisory_override INTEGER,created REAL,superseded REAL);
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_baseline_per_environment ON baselines(environment) WHERE state='ACTIVE';
                CREATE TABLE IF NOT EXISTS analysis_artifacts(id TEXT PRIMARY KEY,run_id TEXT,kind TEXT,schema TEXT,sha256 TEXT,size INTEGER,created REAL,UNIQUE(run_id,kind));
                CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY,label TEXT COLLATE NOCASE UNIQUE,description TEXT,state TEXT,readiness TEXT,policy_hash TEXT,campaign_hash TEXT,finalized_json TEXT,created REAL,updated REAL,finalized REAL);
                CREATE TABLE IF NOT EXISTS campaign_slots(id TEXT PRIMARY KEY,campaign_id TEXT,environment TEXT,scenario TEXT,run_id TEXT,ordinal INTEGER,UNIQUE(campaign_id,environment,scenario));
                """
            )

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _audit(
        self, db: sqlite3.Connection, kind: str, resource_id: str, data: dict[str, Any]
    ) -> None:
        safe = {
            key: value
            for key, value in data.items()
            if key not in {"secret", "cipher", "value"}
        }
        db.execute(
            "INSERT INTO audit VALUES (?,?,?,?,?)",
            (
                _id("audit"),
                kind,
                resource_id,
                json.dumps(safe, sort_keys=True),
                time.time(),
            ),
        )

    def create_scenario(
        self,
        name: str,
        steps: list[dict[str, Any]],
        *,
        idempotency_key: str | None = None,
    ) -> str:
        if not name.strip() or not steps:
            raise ValueError("SCENARIO_INPUT_INVALID")
        for step in steps:
            if step.get("protocol") not in {"http", "graphql", "grpc", "websocket"}:
                raise ValueError("SCENARIO_PROTOCOL_INVALID")
        with self._db() as db:
            if idempotency_key:
                existing = db.execute(
                    "SELECT resource_id FROM idempotency WHERE key=?",
                    (idempotency_key,),
                ).fetchone()
                if existing:
                    return str(existing[0])
            scenario_id = _id("scenario")
            db.execute(
                "INSERT INTO scenarios VALUES (?,?,?,'READY',1,?)",
                (scenario_id, name, json.dumps(steps, sort_keys=True), time.time()),
            )
            if idempotency_key:
                db.execute(
                    "INSERT INTO idempotency VALUES (?,?,?)",
                    (idempotency_key, scenario_id, time.time()),
                )
            self._audit(
                db, "SCENARIO_CREATED", scenario_id, {"name": name, "steps": len(steps)}
            )
        return scenario_id

    def scenario(self, scenario_id: str) -> dict[str, Any]:
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM scenarios WHERE id=?", (scenario_id,)
            ).fetchone()
        if not row:
            raise KeyError(scenario_id)
        result = dict(row)
        result["steps"] = json.loads(result["steps"])
        return result

    def export_scenario(self, scenario_id: str) -> str:
        data = self.scenario(scenario_id)
        return json.dumps(
            {"schema_version": 1, "name": data["name"], "steps": data["steps"]},
            sort_keys=True,
        )

    def import_scenario(self, payload: str) -> str:
        data = json.loads(payload)
        if data.get("schema_version") != 1:
            raise ValueError("SCENARIO_SCHEMA_UNSUPPORTED")
        return self.create_scenario(data["name"], data["steps"])

    def create_run(self, scenario_id: str, zones: dict[str, int]) -> str:
        clean = {
            zone: int(count) for zone, count in zones.items() if zone and int(count) > 0
        }
        if not scenario_id or not clean:
            raise ValueError("RUN_INPUT_INVALID")
        run_id = _id("run")
        with self._db() as db:
            db.execute(
                "INSERT INTO runs VALUES (?,?,?,'PROVISIONING',?)",
                (run_id, scenario_id, json.dumps(clean, sort_keys=True), time.time()),
            )
            self._audit(db, "RUN_CREATED", run_id, {"zones": clean})
        return run_id

    def connect_worker(self, run_id: str, zone: str, worker_id: str) -> None:
        with self._db() as db:
            run = db.execute("SELECT zones FROM runs WHERE id=?", (run_id,)).fetchone()
            if not run or zone not in json.loads(run[0]):
                raise ValueError("WORKER_ZONE_INVALID")
            db.execute(
                "INSERT OR REPLACE INTO workers VALUES (?,?,?,'CONNECTED')",
                (worker_id, run_id, zone),
            )

    def recovery_plan(self, run_id: str) -> dict[str, int]:
        with self._db() as db:
            run = db.execute("SELECT zones FROM runs WHERE id=?", (run_id,)).fetchone()
            if not run:
                raise KeyError(run_id)
            desired = json.loads(run[0])
            actual = {
                zone: count
                for zone, count in db.execute(
                    "SELECT zone,COUNT(*) FROM workers WHERE run_id=? AND state='CONNECTED' GROUP BY zone",
                    (run_id,),
                )
            }
            missing = {
                zone: count - actual.get(zone, 0)
                for zone, count in desired.items()
                if count > actual.get(zone, 0)
            }
            db.execute(
                "UPDATE runs SET state=? WHERE id=?",
                ("PARTIAL" if missing else "READY", run_id),
            )
        return missing

    def run(self, run_id: str) -> dict[str, Any]:
        with self._db() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise KeyError(run_id)
        result = dict(row)
        result["zones"] = json.loads(result["zones"])
        return result

    def ingest_result(self, run_id: str, records: list[dict[str, Any]]) -> str:
        if not records:
            raise ValueError("RESULT_EMPTY")
        result_id = _id("result")
        with self._db() as db:
            db.execute(
                "INSERT INTO results VALUES (?,?,?,'READY',?)",
                (result_id, run_id, json.dumps(records, sort_keys=True), time.time()),
            )
        return result_id

    def diagnostics(self, result_id: str) -> dict[str, Any]:
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM results WHERE id=?", (result_id,)
            ).fetchone()
        if not row:
            raise KeyError(result_id)
        unique = {}
        for record in json.loads(row["records"]):
            key = (
                record.get("endpoint"),
                record.get("cascade_id"),
                record.get("trace_id"),
            )
            unique[key] = record
        hotspots = [
            dict(record, regression=round(record["p95"] - record["baseline_p95"], 3))
            for record in unique.values()
            if record["p95"] > record["baseline_p95"]
        ]
        return {
            "id": result_id,
            "state": row["state"],
            "hotspots": sorted(hotspots, key=lambda x: x["regression"], reverse=True),
        }

    def create_policy(self, name: str, rules: dict[str, float]) -> str:
        if not name or not rules:
            raise ValueError("POLICY_INPUT_INVALID")
        policy_id = _id("policy")
        with self._db() as db:
            db.execute(
                "INSERT INTO policies VALUES (?,?,?,'ACTIVE',1,?)",
                (policy_id, name, json.dumps(rules, sort_keys=True), time.time()),
            )
        return policy_id

    def add_waiver(self, policy_id: str, metric: str, *, expires_at: float) -> str:
        waiver_id = _id("waiver")
        with self._db() as db:
            db.execute(
                "INSERT INTO waivers VALUES (?,?,?,?,?)",
                (waiver_id, policy_id, metric, expires_at, "ACTIVE"),
            )
        return waiver_id

    def evaluate_policy(
        self, policy_id: str, metrics: dict[str, float], *, now: float | None = None
    ) -> dict[str, Any]:
        now = time.time() if now is None else now
        with self._db() as db:
            row = db.execute(
                "SELECT rules FROM policies WHERE id=?", (policy_id,)
            ).fetchone()
            if not row:
                raise KeyError(policy_id)
            rules = json.loads(row[0])
            waived = {
                x[0]
                for x in db.execute(
                    "SELECT metric FROM waivers WHERE policy_id=? AND state='ACTIVE' AND expires>=?",
                    (policy_id, now),
                )
            }
        violations = sorted(
            metric
            for metric, limit in rules.items()
            if (metric not in metrics or metrics[metric] > limit)
            and metric not in waived
        )
        return {
            "policy_id": policy_id,
            "state": "FAIL" if violations else "PASS",
            "violations": violations,
        }

    def put_secret(self, tenant: str, name: str, value: str) -> str:
        if not tenant or not name or not value:
            raise ValueError("SECRET_INPUT_INVALID")
        secret_id = _id("secret")
        ref = f"secret://{tenant}/{name}"
        with self._db() as db:
            db.execute(
                "INSERT OR REPLACE INTO secrets VALUES (?,?,?,?,?,'ACTIVE',?)",
                (
                    secret_id,
                    tenant,
                    name,
                    _seal(value, self._vault_key),
                    hashlib.sha256(value.encode()).hexdigest(),
                    time.time(),
                ),
            )
            self._audit(
                db,
                "SECRET_STORED",
                secret_id,
                {"tenant": tenant, "name": name, "reference": ref},
            )
        return ref

    def resolve_secret(self, reference: str, *, tenant: str) -> str:
        prefix = "secret://"
        if not reference.startswith(prefix) or "/" not in reference[len(prefix) :]:
            raise ValueError("SECRET_REFERENCE_INVALID")
        ref_tenant, name = reference[len(prefix) :].split("/", 1)
        if ref_tenant != tenant:
            raise VaultAccessDenied("CROSS_TENANT_DENIED")
        with self._db() as db:
            row = db.execute(
                "SELECT cipher,state FROM secrets WHERE tenant=? AND name=?",
                (tenant, name),
            ).fetchone()
        if not row or row["state"] != "ACTIVE":
            raise VaultAccessDenied("SECRET_UNAVAILABLE")
        return _open(row["cipher"], self._vault_key)

    def audit_export(self) -> str:
        with self._db() as db:
            rows = [
                dict(x)
                for x in db.execute(
                    "SELECT kind,resource_id,data,created FROM audit ORDER BY created"
                )
            ]
        return json.dumps(rows, sort_keys=True)

    def set_rate_card(
        self, provider: str, unit_price: float, *, effective_at: float
    ) -> str:
        if not provider or unit_price < 0:
            raise ValueError("RATE_CARD_INVALID")
        card_id = _id("card")
        with self._db() as db:
            db.execute(
                "INSERT INTO rate_cards VALUES (?,?,?,?,?)",
                (card_id, provider, unit_price, effective_at, "ACTIVE"),
            )
        return card_id

    def estimate_capacity(
        self,
        users: int,
        minutes: float,
        zones: int,
        card_id: str,
        *,
        now: float | None = None,
        max_age: float = 86400,
    ) -> dict[str, Any]:
        if users <= 0 or minutes <= 0 or zones <= 0:
            raise ValueError("ESTIMATE_INPUT_INVALID")
        now = time.time() if now is None else now
        with self._db() as db:
            card = db.execute(
                "SELECT * FROM rate_cards WHERE id=?", (card_id,)
            ).fetchone()
            if not card:
                raise KeyError(card_id)
            state = "STALE" if now - card["effective"] > max_age else "ESTIMATED"
            vuh = users * minutes / 60 * zones
            cost = round(vuh * card["unit_price"], 2)
            workers = max(zones, (users + 9999) // 10000)
            estimate_id = _id("estimate")
            db.execute(
                "INSERT INTO estimates VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    estimate_id,
                    users,
                    minutes,
                    zones,
                    card_id,
                    cost,
                    workers,
                    state,
                    time.time(),
                ),
            )
        return {
            "id": estimate_id,
            "state": state,
            "virtual_user_hours": round(vuh, 2),
            "cost": cost,
            "workers": workers,
        }

    def approve_estimate(self, estimate_id: str) -> None:
        with self._db() as db:
            row = db.execute(
                "SELECT state FROM estimates WHERE id=?", (estimate_id,)
            ).fetchone()
            if not row or row[0] != "ESTIMATED":
                raise ValueError("ESTIMATE_NOT_APPROVABLE")
            db.execute(
                "UPDATE estimates SET state='APPROVED' WHERE id=?", (estimate_id,)
            )

    def list_rows(self, table: str) -> list[dict[str, Any]]:
        allowed = {"scenarios", "runs", "results", "policies", "secrets", "estimates"}
        if table not in allowed:
            raise ValueError("TABLE_INVALID")
        with self._db() as db:
            return [
                dict(x)
                for x in db.execute(
                    f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 100"
                )
            ]


    def save_analysis_run(self, *, run_id: str, label: str, environment: str = "", branch: str = "", tags: list[str] | None = None, decision: dict[str, Any], baseline_run_id: str | None = None, slos: dict[str, float] | None = None, sample: bool = False) -> None:
        """Persist one immutable normalized analysis decision."""
        now=time.time(); state="READY"; status=decision["decision"]["status"]
        with self._db() as db:
            db.execute("INSERT INTO analysis_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(run_id,label,environment,branch,json.dumps(tags or []),state,status,decision["quality"]["grade"],decision["hash"]["value"],baseline_run_id,json.dumps(slos or {},sort_keys=True),decision["schema"],json.dumps(decision,sort_keys=True),None,_id("corr"),int(sample),now,now))
            self._audit(db,"ANALYSIS_READY",run_id,{"decision":status,"quality":decision["quality"]["grade"]})

    def analysis_run(self, run_id: str) -> dict[str, Any]:
        with self._db() as db: row=db.execute("SELECT * FROM analysis_runs WHERE id=?",(run_id,)).fetchone()
        if not row: raise KeyError(run_id)
        result=dict(row); result["tags"]=json.loads(result.pop("tags_json")); result["report"]=json.loads(result.pop("report_json")); return result

    def list_analysis_runs(self, *, query: str = "", environment: str = "", branch: str = "", decision: str = "", quality: str = "", missing_metadata: bool = False) -> list[dict[str, Any]]:
        clauses=[]; args=[]
        for column,value in (("environment",environment),("branch",branch),("decision",decision),("quality_grade",quality)):
            if value: clauses.append(f"{column}=?"); args.append(value)
        if query: clauses.append("label LIKE ?"); args.append(f"%{query}%")
        if missing_metadata: clauses.append("(environment='' OR branch='')")
        sql="SELECT * FROM analysis_runs"+(" WHERE "+" AND ".join(clauses) if clauses else "")+" ORDER BY created DESC LIMIT 100"
        with self._db() as db: return [dict(x) for x in db.execute(sql,args)]

    def promote_baseline(self, run_id: str, environment: str, label: str, reason: str, *, allow_advisory: bool = False) -> str:
        if not environment.strip() or not label.strip() or len(reason.strip()) < (20 if allow_advisory else 10): raise ValueError("BASELINE_INPUT_INVALID")
        run=self.analysis_run(run_id)
        if run["state"]!="READY" or run["sample"] or run["decision"] in {"FAIL","ERROR"} or (run["decision"]=="ADVISORY" and not allow_advisory): raise ValueError("BASELINE_NOT_ELIGIBLE")
        baseline_id=_id("baseline"); now=time.time()
        with self._db() as db:
            old=db.execute("SELECT id FROM baselines WHERE environment=? AND state='ACTIVE'",(environment,)).fetchone()
            db.execute("UPDATE baselines SET state='SUPERSEDED',superseded=? WHERE environment=? AND state='ACTIVE'",(now,environment))
            db.execute("INSERT INTO baselines VALUES (?,?,?,?,?,?,?,?,NULL)",(baseline_id,environment,label,run_id,"ACTIVE",reason,int(allow_advisory),now))
            self._audit(db,"BASELINE_PROMOTED",baseline_id,{"old_id":old[0] if old else None,"new_run_id":run_id,"reason":reason,"actor":"local-operator"})
        return baseline_id


    def create_campaign(self, label: str, description: str, slots: list[dict[str, Any]]) -> str:
        """Create a transactional campaign draft with required slots."""
        label=label.strip(); description=description.strip()
        if not label or len(label)>120 or len(description)>1000 or not slots: raise ValueError("CAMPAIGN_INPUT_INVALID")
        pairs=[]
        for item in slots:
            env=str(item.get("environment","")).strip(); scenario=str(item.get("scenario","")).strip()
            if not env or not scenario or len(env)>80 or len(scenario)>80: raise ValueError("CAMPAIGN_INPUT_INVALID")
            pairs.append((env,scenario,item.get("run_id")))
        if len({(a.casefold(),b.casefold()) for a,b,_ in pairs})!=len(pairs): raise ValueError("CAMPAIGN_DUPLICATE_SLOT")
        campaign_id=_id("campaign"); now=time.time()
        try:
            with self._db() as db:
                db.execute("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?,?,?,?)",(campaign_id,label,description,"DRAFT","INCOMPLETE","","",None,now,now,None))
                for ordinal,(env,scenario,run_id) in enumerate(pairs):
                    if run_id: self.analysis_run(str(run_id))
                    db.execute("INSERT INTO campaign_slots VALUES (?,?,?,?,?,?)",(_id("slot"),campaign_id,env,scenario,run_id,ordinal))
                self._audit(db,"CAMPAIGN_CREATED",campaign_id,{"label":label,"slots":len(pairs)})
        except sqlite3.IntegrityError as exc: raise ValueError("CAMPAIGN_DUPLICATE") from exc
        return campaign_id

    def update_campaign(self, campaign_id: str, label: str, description: str, slots: list[dict[str, Any]], expected_updated: float) -> None:
        """Replace one campaign draft atomically with optimistic concurrency."""
        current=self.campaign(campaign_id)
        if current["state"]!="DRAFT": raise ValueError("CAMPAIGN_FINALIZED")
        if float(current["updated"])!=float(expected_updated): raise ValueError("CAMPAIGN_CHANGED")
        label=label.strip(); description=description.strip()
        if not label or not 1<=len(slots)<=20: raise ValueError("CAMPAIGN_INPUT_INVALID")
        pairs=[]
        for item in slots:
            env=str(item.get("environment","")).strip(); scenario=str(item.get("scenario","")).strip(); run_id=item.get("run_id") or None
            if not env or not scenario or len(env)>80 or len(scenario)>80: raise ValueError("CAMPAIGN_INPUT_INVALID")
            if run_id:
                run=self.analysis_run(str(run_id))
                if run["sample"] or run["environment"]!=env: raise ValueError("CAMPAIGN_SLOT_INELIGIBLE")
            pairs.append((env,scenario,run_id))
        if len({(a.casefold(),b.casefold()) for a,b,_ in pairs})!=len(pairs): raise ValueError("CAMPAIGN_DUPLICATE_SLOT")
        now=time.time()
        with self._db() as db:
            changed=db.execute("UPDATE campaigns SET label=?,description=?,updated=? WHERE id=? AND state='DRAFT' AND updated=?",(label,description,now,campaign_id,expected_updated)).rowcount
            if not changed: raise ValueError("CAMPAIGN_CHANGED")
            db.execute("DELETE FROM campaign_slots WHERE campaign_id=?",(campaign_id,))
            for ordinal,(env,scenario,run_id) in enumerate(pairs): db.execute("INSERT INTO campaign_slots VALUES (?,?,?,?,?,?)",(_id("slot"),campaign_id,env,scenario,run_id,ordinal))
            self._audit(db,"CAMPAIGN_EDITED",campaign_id,{"slots":len(pairs)})

    def campaign(self, campaign_id: str) -> dict[str, Any]:
        with self._db() as db:
            row=db.execute("SELECT * FROM campaigns WHERE id=?",(campaign_id,)).fetchone()
            slots=[dict(x) for x in db.execute("SELECT * FROM campaign_slots WHERE campaign_id=? ORDER BY ordinal",(campaign_id,))]
        if not row: raise KeyError(campaign_id)
        result=dict(row); enriched=[]
        for slot in slots:
            try: slot["run"]=self.analysis_run(slot["run_id"]) if slot["run_id"] else None
            except KeyError: slot["run"]=None
            enriched.append(slot)
        result["slots"]=enriched
        if result["finalized_json"]: result["projection"]=json.loads(result["finalized_json"])
        return result

    def list_campaigns(self, query: str="", state: str="", readiness: str="") -> list[dict[str, Any]]:
        clauses=[]; args=[]
        if query: clauses.append("label LIKE ?"); args.append(f"%{query}%")
        if state: clauses.append("state=?"); args.append(state)
        if readiness: clauses.append("readiness=?"); args.append(readiness)
        sql="SELECT * FROM campaigns"+(" WHERE "+" AND ".join(clauses) if clauses else "")+" ORDER BY updated DESC,label"
        with self._db() as db:return [dict(x) for x in db.execute(sql,args)]

    def finalize_campaign(self, campaign_id: str) -> dict[str, Any]:
        from locust_templates.campaigns import build_campaign
        campaign=self.campaign(campaign_id)
        if campaign["state"]!="DRAFT": raise ValueError("CAMPAIGN_FINALIZED")
        projection=build_campaign(campaign["label"],campaign["description"],campaign["slots"],now=time.time())
        if projection["readiness"]=="INCOMPLETE": raise ValueError("CAMPAIGN_NOT_READY_TO_FINALIZE")
        now=time.time()
        with self._db() as db:
            db.execute("UPDATE campaigns SET state='FINALIZED',readiness=?,campaign_hash=?,finalized_json=?,updated=?,finalized=? WHERE id=? AND state='DRAFT'",(projection["readiness"],projection["campaign_hash"],json.dumps(projection,sort_keys=True),now,now,campaign_id))
            self._audit(db,"CAMPAIGN_FINALIZED",campaign_id,{"readiness":projection["readiness"],"hash":projection["campaign_hash"][:12]})
        return projection

    def list_baselines(self, environment: str = "") -> list[dict[str, Any]]:
        with self._db() as db:
            if environment: rows=db.execute("SELECT * FROM baselines WHERE environment=? ORDER BY created DESC",(environment,))
            else: rows=db.execute("SELECT * FROM baselines ORDER BY environment,state,created DESC")
            return [dict(x) for x in rows]

def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_workspace(page: str, workspace: PerformanceWorkspace) -> str:
    """Render a responsive, accessible workspace with explicit recovery state."""
    if page not in _PAGES:
        raise KeyError(page)
    title, subtitle = _PAGES[page]
    table = {
        "scenarios": "scenarios",
        "runs": "runs",
        "diagnostics": "results",
        "policies": "policies",
        "vault": "secrets",
        "capacity": "estimates",
    }[page]
    rows = workspace.list_rows(table)
    nav = "".join(
        f'<a href="/workspace/{slug}"{" aria-current=page" if slug == page else ""}>{_esc(label)}</a>'
        for slug, (label, _) in _PAGES.items()
    )
    cards = "".join(
        f"<article><strong>{_esc(row.get('name', row.get('id')))}</strong><p>{_esc(row.get('state', 'Ready'))}</p><button>Open details</button></article>"
        for row in rows
    )
    empty = (
        ""
        if cards
        else '<section class="empty"><h2>No data yet</h2><p>Start with a guided example or create the first item.</p><button class="primary">Get started</button></section>'
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_esc(title)} | Locust Performance Kit</title><link rel="stylesheet" href="/assets/workspace.css"></head><body><a class="skip" href="#main">Skip to content</a><header><span class="mark">LP</span><div><strong>Locust Performance Kit</strong><small>Performance workspace</small></div></header><div class="shell"><nav aria-label="Performance workspace">{nav}</nav><main id="main" tabindex="-1"><div class="heading"><div><p class="eyebrow">Performance workspace</p><h1>{_esc(title)}</h1><p>{_esc(subtitle)}</p></div><button class="primary">Create new</button></div><div class="live" aria-live="polite">Ready</div><section class="metrics"><article><small>Objects</small><strong>{len(rows)}</strong></article><article><small>Status</small><strong>Operational</strong></article><article><small>Recovery</small><strong>Enabled</strong></article></section><section class="toolbar"><label>Search<input type="search" placeholder="Search"></label><label>Status<select><option>All states</option><option>Ready</option><option>Partial</option><option>Failed</option></select></label></section><section class="cards">{cards}</section>{empty}<section class="recovery"><h2>Recovery options</h2><p>Successful work is preserved. Retry only the incomplete operation.</p><button>Try again</button><button>View audit trail</button></section></main></div></body></html>"""
