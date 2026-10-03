import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from review_helpers import approve_defined

from database import execute, one
from errors import AppError
from services import workflow as w
from test_workflow import identity, invoke
from validation import Action, Reception, RequestCreate, RequestEdit, TaskUpdate, WorkOrder


def declaration(**extra):
    return {
        "project_id": "DEMO-001",
        "title": "Muestras antes de definir ensayos",
        "district": "Lurín",
        "province": "Lima",
        "department": "Lima",
        "samples": [
            {"client_code": "M-1", "material": "Relaves", "quantity": 2, "weight": 12.5},
            {"client_code": "M-2", "material": "Suelo"},
        ],
        **extra,
    }


def current(db, user, rid):
    return w.detail(db, user, rid)


def test_pending_receipt_edit_ot_approval_and_operational_gates(db, users):
    client, manager = users["cliente"], users["jefe"]
    payload = declaration()
    rid = w.create_request(db, client, RequestCreate(**payload))["id"]
    w.action(db, client, rid, Action(version=1, action="submit"))
    r = current(db, manager, rid)
    assert r["status"] == "WAITING_ASSAYS" and r["easting"] is None and r["northing"] is None
    assert len(r["samples"]) == 2 and not r["tasks"]
    assert (
        invoke("request_detail", route={"rid": str(rid)}, headers=identity(db, users["tecnico"])).status_code
        == 404
    )
    with pytest.raises(AppError):
        w.action(db, manager, rid, Action(version=r["version"], action="approve"))
    with pytest.raises(AppError):
        w.work_order(db, manager, rid, WorkOrder(version=r["version"], codigo_ot="OT-0"))
    sid = r["samples"][0]["id"]
    w.reception(
        db,
        manager,
        rid,
        Reception(
            version=r["version"],
            received_at=datetime.now(timezone.utc),
            samples=[
                {
                    "sample_id": sid,
                    "codigo_recepcion": " rec-parcial ",
                    "codigo_laboratorio": " lab-parcial ",
                    "received_quantity": 1,
                    "received_weight": 6.4,
                    "condition": "INSUFFICIENT",
                    "reception_notes": "Falta un saco",
                }
            ],
        ),
    )
    r = current(db, client, rid)
    assert r["samples"][0]["id"] == sid and r["samples"][0]["received_weight"] == Decimal("6.4")
    w.work_order(db, manager, rid, WorkOrder(version=r["version"], codigo_ot=" ot-parcial "))
    r = current(db, client, rid)
    assert r["codigo_ot"] == "OT-PARCIAL"
    samples = [{**s, "assay_ids": []} for s in payload["samples"]]
    samples[0]["id"] = sid
    samples[1]["id"] = r["samples"][1]["id"]
    aid = one(db, "SELECT id FROM catalogo_ensayos WHERE codigo='HUM'")["id"]
    for s in samples:
        s["assay_ids"] = [aid]
    w.edit_request(db, client, rid, RequestEdit(**{**payload, "samples": samples, "version": r["version"]}))
    r = current(db, manager, rid)
    assert r["status"] == "SUBMITTED" and r["samples"][0]["id"] == sid
    assert r["samples"][0]["condition"] == "INSUFFICIENT" and r["samples"][0]["received_weight"] == Decimal(
        "6.4"
    )
    edited = [dict(s) for s in samples]
    edited[0]["quantity"] = 4
    with pytest.raises(AppError):
        w.edit_request(
            db, client, rid, RequestEdit(**{**payload, "samples": edited, "version": r["version"]})
        )
    approve_defined(db, manager, rid, r["version"])
    r = current(db, manager, rid)
    task = r["tasks"][0]
    assert "assign" in task["allowed_actions"]
    w.update_tasks(
        db,
        manager,
        rid,
        TaskUpdate(
            version=r["version"], task_ids=[task["id"]], action="assign", technician_id=users["tecnico"]["id"]
        ),
    )
    r = current(db, manager, rid)
    assert "start" not in r["tasks"][0]["allowed_actions"]
    with pytest.raises(AppError):
        w.edit_request(
            db, client, rid, RequestEdit(**{**payload, "samples": samples, "version": r["version"]})
        )
    with pytest.raises(AppError):
        w.work_order(db, manager, rid, WorkOrder(version=r["version"], codigo_ot="OT-CORREGIDA"))


def test_external_standard_code_author_only_and_company_snapshot(db, users):
    external = users["externo"]
    rid = w.create_request(db, external, RequestCreate(**declaration(project_id="FORGED")))["id"]
    w.action(db, external, rid, Action(version=1, action="submit"))
    r = current(db, external, rid)
    assert r["project_id"] == "EXTERNO"
    another = one(
        db,
        "INSERT INTO usuarios(nombre,correo,empresa_id,roles,hash_contrasena) VALUES('Otro cliente',:email,:org,ARRAY['CLIENT'],'!NOT_INITIALIZED') RETURNING *",
        email=str(uuid4()) + "@example.com",
        org=external["organization_id"],
    )
    h = identity(db, another)
    assert invoke("request_detail", route={"rid": str(rid)}, headers=h).status_code == 404
    assert not json.loads(invoke("requests", params={"q": r["code"]}, headers=h).get_body())["items"]
    assert invoke("projects", params={"scope": "catalog"}, headers=identity(db, external)).status_code == 403
    execute(
        db,
        "UPDATE usuarios SET empresa_id=:org WHERE id=:id",
        org=users["cliente"]["organization_id"],
        id=external["id"],
    )
    assert current(db, external, rid)["organization_id"] == r["organization_id"]


def test_catalog_search_and_failure_does_not_break_existing_records(db, users, monkeypatch):
    from services import projects

    h = identity(db, users["cliente"])
    r = invoke("projects", params={"scope": "catalog", "q": "reCRECimiento"}, headers=h)
    assert r.status_code == 200 and json.loads(r.get_body())["items"][0]["code"] == "DEMO-001"
    r = invoke("projects", params={"scope": "catalog", "q": "demo-002"}, headers=h)
    assert json.loads(r.get_body())["total"] == 1

    def unavailable(*args, **kwargs):
        raise AppError(503, "Catálogo no disponible.")

    monkeypatch.setattr(projects, "catalog", unavailable)
    assert invoke("projects", params={"scope": "catalog"}, headers=h).status_code == 503
    assert invoke("requests", headers=h).status_code == 200
    assert (
        invoke("request_detail", route={"rid": "40000000-0000-0000-0000-000000000001"}, headers=h).status_code
        == 200
    )
    r = invoke("requests", "POST", declaration(), headers=h)
    assert r.status_code == 503
    r = invoke("requests", "POST", declaration(project_id=None), headers=identity(db, users["externo"]))
    assert r.status_code == 200


def test_optional_coordinates_and_required_fields_and_sacks():
    assert RequestCreate(**declaration()).easting is None
    assert RequestCreate(**declaration(easting=0, northing=None)).easting == 0
    for field in ("district", "province", "department"):
        with pytest.raises(ValidationError):
            RequestCreate(**declaration(**{field: ""}))
    for invalid in (1.5, True, 0, -1):
        with pytest.raises(ValidationError):
            RequestCreate(
                **declaration(samples=[{"client_code": "M", "material": "Suelo", "quantity": invalid}])
            )
    with pytest.raises(ValidationError):
        RequestCreate(**declaration(easting="NaN"))


def test_ot_gate_and_legacy_running_completion(db, users):
    rid = "40000000-0000-0000-0000-000000000001"
    execute(db, "UPDATE solicitudes SET codigo_ot=NULL WHERE id=:id", id=rid)
    r = current(db, users["jefe"], rid)
    for task in r["tasks"]:
        if task["state"] == "PENDING":
            assert task["allowed_actions"] == ["cancel"]
    running = next(t for t in r["tasks"] if t["state"] == "RUNNING")
    assert set(running["allowed_actions"]) == {"observe", "complete", "cancel"}
    w.update_tasks(
        db,
        users["tecnico"],
        rid,
        TaskUpdate(version=r["version"], task_ids=[running["id"]], action="complete"),
    )


def test_receipt_filter_and_dashboard_include_waiting_requests(db, users):
    rid = w.create_request(db, users["cliente"], RequestCreate(**declaration()))["id"]
    w.action(db, users["cliente"], rid, Action(version=1, action="submit"))
    h = identity(db, users["jefe"])
    listed = json.loads(
        invoke("requests", params={"view": "reception", "condition": "NOT_RECEIVED"}, headers=h).get_body()
    )
    assert str(rid) in [r["id"] for r in listed["items"]]
    dash = json.loads(invoke("dashboard", headers=h).get_body())
    expected = one(
        db,
        "SELECT count(*) n FROM muestras s JOIN solicitudes r ON r.id=s.solicitud_id WHERE r.estado_solicitud IN ('WAITING_ASSAYS','SUBMITTED','OBSERVED','APPROVED') AND s.condicion='NOT_RECEIVED'",
    )["n"]
    assert dash["totals"]["pending_samples"] == expected


def test_manage_migrate_recognizes_current_schema_without_reinstall(db):
    import os
    import subprocess
    import sys
    from pathlib import Path

    before = one(db, "SELECT count(*) n FROM solicitudes")["n"]
    env = {**os.environ, "DATABASE_URL": os.environ["TEST_DATABASE_URL"]}
    result = subprocess.run(
        [sys.executable, "manage.py", "migrate"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
    )
    assert result.returncode == 0, "migrate debe aceptar el esquema actual sin reinstalar"
    assert one(db, "SELECT max(version) version FROM migraciones_esquema")["version"] == 6
    assert one(db, "SELECT count(*) n FROM solicitudes")["n"] == before
