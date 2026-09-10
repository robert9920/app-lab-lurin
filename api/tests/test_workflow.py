import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

import azure.functions as func
import pytest
from reportlab.pdfgen import canvas

from database import execute, one
from errors import AppError
from function_app import app
from security import new_session
from services import workflow as w
from services.documents import validate_pdf
from validation import Action, Reception, RequestCreate, TaskUpdate

FUNCTIONS = {f.get_function_name(): f.get_user_function() for f in app.get_functions()}
ORIGIN = "http://localhost:5173"
RID = "40000000-0000-0000-0000-000000000001"


def invoke(name, method="GET", payload=None, route=None, headers=None, params=None):
    return FUNCTIONS[name](
        func.HttpRequest(
            method=method,
            url="http://localhost/api/test",
            headers={
                "origin": ORIGIN,
                **({"content-type": "application/json"} if payload is not None else {}),
                **(headers or {}),
            },
            params=params or {},
            route_params=route or {},
            body=json.dumps(payload).encode() if payload is not None else b"",
        )
    )


def identity(db, user):
    data, cookie = new_session(db, user)
    return {"cookie": cookie.split(";")[0], "x-csrf-token": data["csrf"]}


def pdf():
    stream = BytesIO()
    doc = canvas.Canvas(stream)
    doc.drawString(30, 750, "INFORME FICTICIO DE PRUEBA")
    doc.save()
    return stream.getvalue()


def test_partial_reception_and_immediate_work(db, users):
    rid = one(db, "SELECT id FROM solicitudes WHERE codigo='SOL-DEMO-001'")["id"]
    r = w.detail(db, users["jefe"], rid)
    missing = next(s for s in r["samples"] if s["client_code"] == "M-02")
    task = next(t for t in r["tasks"] if t["sample_id"] == missing["id"])
    w.update_tasks(
        db,
        users["jefe"],
        rid,
        TaskUpdate(
            version=r["version"], task_ids=[task["id"]], action="assign", technician_id=users["tecnico"]["id"]
        ),
    )
    with pytest.raises(AppError) as err:
        w.update_tasks(
            db, users["tecnico"], rid, TaskUpdate(version=2, task_ids=[task["id"]], action="start")
        )
    assert err.value.status == 409
    at = datetime.now(timezone.utc) - timedelta(hours=2)
    w.reception(
        db,
        users["tecnico"],
        rid,
        Reception(
            version=2,
            received_at=at,
            transport="Vehículo prueba",
            samples=[
                {
                    "sample_id": missing["id"],
                    "codigo_recepcion": "REC-TEST",
                    "codigo_laboratorio": "LAB-TEST-M02",
                    "condition": "OK",
                    "received_quantity": 12,
                }
            ],
        ),
    )
    r = w.detail(db, users["cliente"], rid)
    assert r["samples"][0]["received_at"] != r["samples"][1]["received_at"]
    w.update_tasks(db, users["tecnico"], rid, TaskUpdate(version=3, task_ids=[task["id"]], action="start"))
    assert (
        one(db, "SELECT estado_ensayo FROM ensayos_muestra WHERE id=:id", id=task["id"])["state"] == "RUNNING"
    )


def test_reception_correction_reason_and_history(db, users):
    r = w.detail(db, users["jefe"], RID)
    sid = r["samples"][0]["id"]
    data = dict(
        version=1,
        received_at=datetime.now(timezone.utc),
        samples=[
            {
                "sample_id": sid,
                "codigo_recepcion": "REC-TEST",
                "codigo_laboratorio": "LAB-TEST-" + str(sid),
                "condition": "OK",
                "received_quantity": 14,
            }
        ],
    )
    with pytest.raises(AppError):
        w.reception(db, users["tecnico"], RID, Reception(**data))
    w.reception(db, users["tecnico"], RID, Reception(**data, reason="Corrección de pesaje"))
    history = one(db, "SELECT detalle FROM actividad WHERE solicitud_id=:id ORDER BY id DESC LIMIT 1", id=RID)
    assert history["detail"]["samples"][0]["before"]["received_quantity"] == "15"
    with pytest.raises(AppError):
        w.reception(
            db,
            users["tecnico"],
            RID,
            Reception(
                **{
                    **data,
                    "version": 2,
                    "samples": [
                        {
                            "sample_id": sid,
                            "codigo_recepcion": "REC-TEST",
                            "codigo_laboratorio": "LAB-TEST-" + str(sid),
                            "condition": "DAMAGED",
                            "reception_notes": "Rotura",
                        }
                    ],
                },
                reason="Reevaluación",
            ),
        )


def test_full_service_and_project_isolation(db, users):
    project = one(db, "SELECT id FROM proyectos WHERE codigo='DEMO-001'")["id"]
    assay = one(db, "SELECT id FROM catalogo_ensayos WHERE codigo='HUM'")["id"]
    rid = w.create_request(
        db,
        users["cliente"],
        RequestCreate(
            project_id=project,
            title="Recorrido completo",
            samples=[{"client_code": "MEZCLA-01", "notes": "Componentes A y B", "assay_ids": [assay]}],
        ),
    )["id"]
    for user, action, version in ((users["cliente"], "submit", 1), (users["jefe"], "approve", 2)):
        w.action(db, user, rid, Action(version=version, action=action))
    with pytest.raises(AppError):
        w.detail(db, users["externo"], rid)
    data = w.detail(db, users["jefe"], rid)
    sid = data["samples"][0]["id"]
    tid = data["tasks"][0]["id"]
    w.reception(
        db,
        users["jefe"],
        rid,
        Reception(
            version=3,
            received_at=datetime.now(timezone.utc),
            samples=[
                {
                    "sample_id": sid,
                    "codigo_recepcion": "REC-TEST",
                    "codigo_laboratorio": "LAB-TEST-" + str(sid),
                }
            ],
        ),
    )
    w.update_tasks(
        db,
        users["jefe"],
        rid,
        TaskUpdate(version=4, task_ids=[tid], action="assign", technician_id=users["tecnico"]["id"]),
    )
    w.update_tasks(db, users["tecnico"], rid, TaskUpdate(version=5, task_ids=[tid], action="start"))
    w.update_tasks(db, users["tecnico"], rid, TaskUpdate(version=6, task_ids=[tid], action="complete"))
    with pytest.raises(AppError):
        w.action(db, users["jefe"], rid, Action(version=7, action="close"))
    execute(
        db,
        "INSERT INTO informes(solicitud_id,version,nombre,clave_archivo,sha256,tamano_bytes,subido_por) VALUES(:rid,1,'Test.pdf',:key,'test',1,:uid)",
        rid=rid,
        key=str(uuid4()),
        uid=users["tecnico"]["id"],
    )
    w.action(db, users["jefe"], rid, Action(version=7, action="close"))
    assert w.detail(db, users["cliente"], rid)["status"] == "CLOSED"


def test_pdf_immediate_versions_and_access(db, users):
    tech = identity(db, users["tecnico"])
    client = identity(db, users["cliente"])
    external = identity(db, users["externo"])
    ids = []
    for v in (1, 2):
        response = FUNCTIONS["upload"](
            func.HttpRequest(
                method="POST",
                url="http://localhost/api/test",
                params={},
                route_params={"rid": RID},
                headers={
                    "origin": ORIGIN,
                    **tech,
                    "content-type": "application/pdf",
                    "x-request-version": str(v),
                },
                body=pdf(),
            )
        )
        assert response.status_code == 200, response.get_body()
        doc = json.loads(response.get_body())
        ids.append(doc["id"])
        assert doc["version"] == v
        downloaded = invoke("download", route={"did": doc["id"]}, headers=client)
        assert downloaded.status_code == 200 and downloaded.get_body().startswith(b"%PDF")
        assert invoke("download", route={"did": doc["id"]}, headers=external).status_code == 404
    assert ids[0] != ids[1]
    with pytest.raises(AppError):
        validate_pdf(b"not pdf")
    with pytest.raises(AppError):
        validate_pdf(b"%PDF-" + b"x" * 20971520)


def test_dashboard_over_100_requests_and_sql_reconciliation(db, users):
    execute(
        db,
        "INSERT INTO solicitudes(proyecto_id,creado_por,titulo,estado_solicitud)\n        SELECT '30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000004','Carga masiva '||n,'APPROVED'\n        FROM generate_series(1,130) n",
    )
    execute(
        db,
        "INSERT INTO muestras(solicitud_id,codigo_cliente) SELECT id,'BATCH' FROM solicitudes WHERE titulo LIKE 'Carga masiva %'",
    )
    execute(
        db,
        "INSERT INTO ensayos_muestra(muestra_id,ensayo_id) SELECT s.id,c.id FROM muestras s CROSS JOIN catalogo_ensayos c\n        WHERE s.codigo_cliente='BATCH' AND c.codigo='HUM'",
    )
    data = json.loads(invoke("dashboard", headers=identity(db, users["admin"])).get_body())
    expected = one(
        db,
        "SELECT count(*) n FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id JOIN solicitudes r ON r.id=s.solicitud_id\n        WHERE r.estado_solicitud='APPROVED' AND a.estado_ensayo NOT IN ('COMPLETED','CANCELLED')",
    )["n"]
    assert data["totals"]["open"] == expected and expected > 130
    assert sum(x["count"] for x in data["by_type"]) == expected
    assert sum(x["count"] for x in data["by_technician"]) == expected
    assert len(data["weekly"]) == 8
    assert data["totals"]["overdue"] == 1
    assert data["totals"]["undated"] == 132
    assert invoke("dashboard", headers=identity(db, users["cliente"])).status_code == 403


def test_bulk_rolls_back_on_conflict(db, users):
    task = one(
        db,
        "SELECT a.id FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.codigo_cliente='M-02'",
    )
    h = identity(db, users["jefe"])
    response = invoke(
        "work",
        "POST",
        {
            "requests": [{"request_id": RID, "version": 999, "task_ids": [str(task["id"])]}],
            "action": "assign",
            "technician_id": str(users["tecnico"]["id"]),
        },
        headers=h,
    )
    assert response.status_code == 409
    assert (
        one(db, "SELECT estado_ensayo FROM ensayos_muestra WHERE id=:id", id=task["id"])["state"] == "PENDING"
    )


def test_schema_thirteen_tables(db):
    assert (
        one(
            db,
            "SELECT count(*) n FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'",
        )["n"]
        == 13
    )
