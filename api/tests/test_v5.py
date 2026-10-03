import json
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from review_helpers import approve_defined
from test_v4 import declaration

from database import execute, one
from errors import AppError
from services import workflow as w
from services.documents import render_labels
from test_workflow import identity, invoke
from validation import Action, AssaysEdit, Reception, RequestCreate, TaskUpdate, WorkOrder


def test_partial_approval_later_assays_and_preserved_running_work(db, users):
    client, manager, tech = users["cliente"], users["jefe"], users["tecnico"]
    aid = one(db, "SELECT id FROM catalogo_ensayos WHERE codigo='HUM'")["id"]
    data = declaration()
    data["samples"][0]["assay_ids"] = [aid]
    rid = w.create_request(db, client, RequestCreate(**data))["id"]

    def current():
        return w.detail(db, manager, rid)

    w.action(db, client, rid, Action(version=1, action="submit"))
    assert current()["status"] == "WAITING_ASSAYS"
    approve_defined(db, manager, rid, 2)
    r = current()
    assert r["status"] == "APPROVED" and r["undefined_samples"] == 1
    assert r["tasks"][0]["approved"] and not r["unapproved_count"]
    sid, sid2 = [s["id"] for s in r["samples"]]
    tid = r["tasks"][0]["id"]
    w.reception(
        db,
        manager,
        rid,
        Reception(
            version=r["version"],
            received_at=datetime.now(timezone.utc),
            samples=[dict(sample_id=sid, codigo_recepcion="REC-V5", codigo_laboratorio="LAB-V5")],
        ),
    )
    w.work_order(db, manager, rid, WorkOrder(version=current()["version"], codigo_ot="OT-V5"))
    w.update_tasks(
        db,
        manager,
        rid,
        TaskUpdate(version=current()["version"], task_ids=[tid], action="assign", technician_id=tech["id"]),
    )
    w.update_tasks(db, tech, rid, TaskUpdate(version=current()["version"], task_ids=[tid], action="start"))
    started = current()["tasks"][0]["started_at"]
    with pytest.raises(AppError):
        w.action(db, manager, rid, Action(version=current()["version"], action="close"))
    with pytest.raises(AppError):
        w.edit_assays(
            db,
            client,
            rid,
            AssaysEdit(version=current()["version"], samples=[dict(sample_id=sid, assay_ids=[])]),
        )
    w.edit_assays(
        db,
        client,
        rid,
        AssaysEdit(version=current()["version"], samples=[dict(sample_id=sid2, assay_ids=[aid])]),
    )
    r = current()
    assert not r["undefined_samples"] and r["unapproved_count"] == 1
    added = next(t for t in r["tasks"] if t["id"] != tid)
    assert not added["approved"] and added["allowed_actions"] == []
    with pytest.raises(AppError):
        w.update_tasks(
            db,
            manager,
            rid,
            TaskUpdate(
                version=r["version"], task_ids=[added["id"]], action="assign", technician_id=tech["id"]
            ),
        )
    with pytest.raises(AppError):
        w.edit_assays(db, client, rid, AssaysEdit(version=1, samples=[dict(sample_id=sid2, assay_ids=[])]))
    assert (
        invoke(
            "edit_assays",
            method="PUT",
            route={"rid": str(rid)},
            payload={"version": r["version"], "samples": [{"sample_id": str(sid2), "assay_ids": []}]},
            headers=identity(db, users["externo"]),
        ).status_code
        == 404
    )
    approve_defined(db, manager, rid, r["version"])
    r = current()
    running = next(t for t in r["tasks"] if t["id"] == tid)
    assert running["state"] == "RUNNING" and running["started_at"] == started
    assert all(t["approved"] for t in r["tasks"])
    assert any(e["message"] == "Ensayo aprobado por jefatura" for e in r["activity"])


@pytest.mark.parametrize(
    "east,north",
    [(None, None), (100000, None), (None, 9999999.999), (Decimal("123456.78"), Decimal("8765432.1"))],
)
def test_coordinate_formats_optional_and_decimal(db, users, east, north):
    rid = w.create_request(db, users["cliente"], RequestCreate(**declaration(easting=east, northing=north)))[
        "id"
    ]
    assert w.detail(db, users["cliente"], rid)["easting"] == (
        Decimal(str(east)) if east is not None else None
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("easting", 0),
        ("easting", 99999.9),
        ("easting", 1000000),
        ("northing", 999999),
        ("northing", 10000000),
        ("northing", -1234567),
    ],
)
def test_coordinate_formats_rejected_by_server(db, users, field, value):
    with pytest.raises(AppError) as err:
        w.create_request(db, users["cliente"], RequestCreate(**declaration(**{field: value})))
    assert err.value.status == 400


def test_filters_dates_multiple_states_and_authorized_options(db, users):
    client = users["cliente"]
    ids = []
    for at in (
        "2026-10-02T04:59:59Z",
        "2026-10-02T05:00:00Z",
        "2026-10-03T04:59:59Z",
        "2026-10-03T05:00:00Z",
    ):
        rid = w.create_request(db, client, RequestCreate(**declaration(title="Filtro v5 de fechas")))["id"]
        w.action(db, client, rid, Action(version=1, action="submit"))
        execute(db, "UPDATE solicitudes SET creado_en=:at WHERE id=:id", at=at, id=rid)
        ids.append(str(rid))
    h = identity(db, users["jefe"])
    params = {
        "q": "Filtro v5",
        "created_from": "2026-10-02",
        "created_to": "2026-10-02",
        "status": "WAITING_ASSAYS,APPROVED",
        "requester": str(client["id"]),
        "organization": str(client["organization_id"]),
        "pending_assays": "true",
    }
    result = invoke("requests", headers=h, params=params)
    assert result.status_code == 200, result.get_body()
    data = json.loads(result.get_body())
    assert {r["id"] for r in data["items"]} == set(ids[1:3])
    assert all(r["requester_name"] == client["name"] and r["organization_name"] for r in data["items"])
    assert invoke("requests", headers=h, params={"status": "INVALID"}).status_code == 400
    assert (
        invoke(
            "requests", headers=h, params={"created_from": "2026-10-03", "created_to": "2026-10-02"}
        ).status_code
        == 400
    )
    assert (
        invoke("filter_options", headers=identity(db, client), params={"kind": "requester"}).status_code
        == 403
    )
    tech = identity(db, users["tecnico"])
    for kind in ("requester", "organization"):
        r = invoke("filter_options", headers=tech, params={"kind": kind, "view": "work", "q": ""})
        assert r.status_code == 200, r.get_body()
        options = json.loads(r.get_body())["items"]
        forbidden = str(
            users["externo"]["id"] if kind == "requester" else users["externo"]["organization_id"]
        )
        assert forbidden not in [o["id"] for o in options]


def test_label_without_ot(db, users):
    r = w.detail(db, users["jefe"], "40000000-0000-0000-0000-000000000001")
    r["codigo_ot"] = None
    r["samples"] = [s for s in r["samples"] if s["received_at"]][:1]
    text = PdfReader(BytesIO(render_labels(r))).pages[0].extract_text()
    assert "OT:" in text and "OT-DEMO" not in text and "UR origen" not in text
