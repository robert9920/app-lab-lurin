"""State aggregation, authorization and terminal requests on real fictitious PostgreSQL."""

import json
from uuid import uuid4

import pytest
from test_v4 import declaration
from test_v6 import submitted

from database import execute, one
from errors import AppError
from services import workflow as w
from test_workflow import identity, invoke
from validation import Action, AssaysReview, RequestCreate


def response(db, user, route="requests", **params):
    result = invoke(route, headers=identity(db, user), params={k: str(v) for k, v in params.items()})
    assert result.status_code == 200, result.get_body().decode()
    return json.loads(result.get_body())


def test_partial_counts_filters_and_virtual_rows(db, users):
    payload = declaration()
    aid = one(db, "SELECT id FROM catalogo_ensayos WHERE codigo='LC-001'")["id"]
    payload["samples"][0]["assay_ids"] = [aid]
    rid = w.create_request(db, users["cliente"], RequestCreate(**payload))["id"]
    w.action(db, users["cliente"], rid, Action(version=1, action="submit"))
    r = w.detail(db, users["cliente"], rid)
    assert r["request_status"] == "CREATED"
    assert r["assay_counts"]["PENDING_REVIEW"] == r["assay_counts"]["WAITING_ASSAYS"] == 1
    for state in ("PENDING_REVIEW", "WAITING_ASSAYS"):
        data = response(db, users["cliente"], q=r["code"], assay_status=state, request_status="CREATED")
        assert data["total"] == 1 and data["items"][0]["assay_counts"] == r["assay_counts"]
        work = response(db, users["jefe"], "work", request=rid, assay_status=state)
        assert work["total"] == 1
        item = work["items"][0]
        assert item["assay_status"] == state and not item["allowed_actions"]
        if state == "WAITING_ASSAYS":
            assert item["id"] is None and item["row_kind"] == "sample_without_assays"
    w.review_assays(
        db,
        users["jefe"],
        rid,
        AssaysReview(
            version=r["version"], decisions=[{"task_id": r["tasks"][0]["id"], "decision": "APPROVED"}]
        ),
    )
    r = w.detail(db, users["cliente"], rid)
    assert r["assay_counts"]["PENDING_EXECUTION"] == 1 and not r["assay_counts"]["PENDING_REVIEW"]
    assert r["request_status"] == "CREATED" and r["assay_counts"]["WAITING_ASSAYS"] == 1
    assert response(db, users["jefe"], "work", request=rid, assay_status="PENDING_EXECUTION")["total"] == 1


def test_exclusive_categories_and_mixed_decisions(db, users):
    rid, r = submitted(db, users)
    first, second = r["tasks"]
    w.review_assays(
        db,
        users["jefe"],
        rid,
        AssaysReview(
            version=r["version"],
            decisions=[
                {"task_id": first["id"], "decision": "APPROVED"},
                {"task_id": second["id"], "decision": "REJECTED", "reason": "Método no aplicable"},
            ],
        ),
    )
    r = w.detail(db, users["cliente"], rid)
    assert sum(r["assay_counts"].values()) == 2
    assert r["assay_counts"]["REJECTED"] == r["assay_counts"]["PENDING_EXECUTION"] == 1
    for state in ("RUNNING", "OBSERVED", "COMPLETED", "CANCELLED"):
        execute(
            db,
            "UPDATE ensayos_muestra SET tecnico_id=:u,estado_ensayo=:state,iniciado_en=now(),completado_en=CASE WHEN :state='COMPLETED' THEN now() ELSE NULL END WHERE id=:id",
            u=users["tecnico"]["id"],
            state=state,
            id=first["id"],
        )
        r = w.detail(db, users["jefe"], rid)
        assert r["assay_counts"][state] == 1 and r["assay_counts"]["REJECTED"] == 1
        assert sum(r["assay_counts"].values()) == 2
        data = response(db, users["jefe"], "work", request=rid, assay_status=state)
        assert data["total"] == 1 and data["items"][0]["assay_status"] == state


def test_cancel_permissions_reason_concurrency_and_privacy(db, users):
    rid, r = submitted(db, users)
    for user in ({**users["admin"], "roles": ["ADMIN"]}, users["externo"], users["tecnico"]):
        with pytest.raises(AppError):
            w.action(db, user, rid, Action(version=r["version"], action="cancel", reason="No autorizado"))
    for payload in (
        Action(version=r["version"], action="cancel"),
        Action(version=1, action="cancel", reason="Obsoleto"),
    ):
        with pytest.raises(AppError):
            w.action(db, users["cliente"], rid, payload)
    w.action(
        db, users["cliente"], rid, Action(version=r["version"], action="cancel", reason="Ya no se requiere")
    )
    r = w.detail(db, users["cliente"], rid)
    assert r["request_status"] == "CANCELLED" and not r["can_edit"] and not r["can_cancel"]
    assert r["assay_counts"]["CANCELLED"] == 2 and not r["assay_counts"]["PENDING_REVIEW"]
    assert all(not t["allowed_actions"] and not t["can_review"] for t in r["tasks"])
    assert response(db, users["jefe"], q=r["code"], view="reception")["total"] == 0
    assert response(db, users["cliente"], q=r["code"], request_status="CANCELLED")["total"] == 1
    blocked = invoke(
        "comments",
        "POST",
        {"version": r["version"], "body": "Cambio", "internal": False},
        {"rid": str(rid)},
        identity(db, users["cliente"]),
    )
    assert blocked.status_code == 409
    draft = w.create_request(db, users["cliente"], RequestCreate(**declaration()))["id"]
    for user in (users["jefe"], users["admin"]):
        assert (
            invoke("request_detail", route={"rid": str(draft)}, headers=identity(db, user)).status_code == 404
        )
    with pytest.raises(AppError) as error:
        w.action(
            db, users["cliente"], draft, Action(version=1, action="cancel", reason="Borrador innecesario")
        )
    assert error.value.status == 409
    assert (
        invoke("request_detail", route={"rid": str(draft)}, headers=identity(db, users["admin"])).status_code
        == 404
    )


def test_cancel_preserves_results_rejections_reports_and_running_dates(db, users):
    rid = one(db, "SELECT id FROM solicitudes WHERE codigo='SOL-DEMO-001'")["id"]
    r = w.detail(db, users["jefe"], rid)
    pending = next(t for t in r["tasks"] if t["state"] == "PENDING")
    execute(db, "UPDATE ensayos_muestra SET estado_revision='REJECTED' WHERE id=:id", id=pending["id"])
    snapshot = {t["id"]: t for t in w.detail(db, users["jefe"], rid)["tasks"]}
    execute(
        db,
        "INSERT INTO informes(solicitud_id,version,nombre,clave_archivo,sha256,tamano_bytes,subido_por) VALUES(:r,1,'Ficticio.pdf',:key,'demo',100,:u)",
        r=rid,
        key=str(uuid4()),
        u=users["jefe"]["id"],
    )
    w.action(
        db, users["jefe"], rid, Action(version=r["version"], action="cancel", reason="Parada del servicio")
    )
    r = w.detail(db, users["cliente"], rid)
    assert len(r["reports"]) == 1
    for task in r["tasks"]:
        old = snapshot[task["id"]]
        assert (task["technician_id"], task["started_at"], task["completed_at"], task["review_status"]) == (
            old["technician_id"],
            old["started_at"],
            old["completed_at"],
            old["review_status"],
        )
        assert task["state"] == (
            old["state"] if old["state"] == "COMPLETED" or old["review_status"] == "REJECTED" else "CANCELLED"
        )
    assert response(db, users["jefe"], "work", request=rid, assay_status="CANCELLED")["total"] > 0
    assert response(db, users["jefe"], "dashboard")["totals"]["open"] == 0
    assert response(db, users["jefe"], q=r["code"], status="APPROVED", request_status="CREATED")["total"] == 0
    received = next(s for s in r["samples"] if s["received_at"])
    printed = invoke(
        "print_document",
        route={"rid": str(rid), "kind": "labels"},
        headers=identity(db, users["jefe"]),
        params={"sample_ids": str(received["id"])},
    )
    assert printed.status_code == 200 and printed.get_body().startswith(b"%PDF")


def test_close_requires_completed_and_terminal_blocks_cancel(db, users):
    rid, r = submitted(db, users)
    w.review_assays(
        db,
        users["jefe"],
        rid,
        AssaysReview(
            version=r["version"], decisions=[{"task_id": t["id"], "decision": "APPROVED"} for t in r["tasks"]]
        ),
    )
    execute(
        db,
        "UPDATE ensayos_muestra a SET estado_ensayo='CANCELLED' FROM muestras s WHERE s.id=a.muestra_id AND s.solicitud_id=:r",
        r=rid,
    )
    execute(
        db,
        "INSERT INTO informes(solicitud_id,version,nombre,clave_archivo,sha256,tamano_bytes,subido_por) VALUES(:r,1,'Ficticio.pdf',:key,'demo',100,:u)",
        r=rid,
        key=str(uuid4()),
        u=users["jefe"]["id"],
    )
    r = w.detail(db, users["jefe"], rid)
    with pytest.raises(AppError):
        w.action(db, users["jefe"], rid, Action(version=r["version"], action="close"))
    execute(
        db,
        "UPDATE ensayos_muestra SET estado_ensayo='COMPLETED',tecnico_id=:u,iniciado_en=now(),completado_en=now() WHERE id=:t",
        u=users["tecnico"]["id"],
        t=r["tasks"][0]["id"],
    )
    w.action(db, users["jefe"], rid, Action(version=r["version"], action="close"))
    closed = w.detail(db, users["cliente"], rid)
    assert closed["request_status"] == "CLOSED" and closed["status"] == "CLOSED"
    with pytest.raises(AppError):
        w.action(
            db,
            users["cliente"],
            rid,
            Action(version=closed["version"], action="cancel", reason="No permitido"),
        )


def test_client_additional_role_preserves_own_summary_without_operating_other_tasks(db, users):
    rid, r = submitted(db, users)
    execute(db, "UPDATE usuarios SET roles=ARRAY['CLIENT','TECH'] WHERE id=:u", u=users["cliente"]["id"])
    combined = {**users["cliente"], "roles": ["CLIENT", "TECH"]}
    detail = w.detail(db, combined, rid)
    listed = response(db, combined, q=r["code"], assay_status="PENDING_REVIEW")
    assert listed["total"] == 1 and listed["items"][0]["assay_counts"] == detail["assay_counts"]
    assert detail["assay_counts"]["PENDING_REVIEW"] == 2
    assert response(db, combined, "work", request=rid)["total"] == 0


def test_sql_pagination_all_records_and_technical_scope(db, users):
    execute(
        db,
        """WITH requests AS (
        INSERT INTO solicitudes(proyecto_id,empresa_id,creado_por,observaciones,estado_solicitud)
        SELECT 'LOAD7',:org,:u,'Carga ficticia '||n,'SUBMITTED' FROM generate_series(1,125) n RETURNING id
    ), samples AS (
        INSERT INTO muestras(solicitud_id,codigo_cliente) SELECT id,'M1' FROM requests RETURNING id
    ) INSERT INTO ensayos_muestra(muestra_id,ensayo_id) SELECT s.id,c.id FROM samples s CROSS JOIN catalogo_ensayos c WHERE c.codigo='LC-001'""",
        org=users["cliente"]["organization_id"],
        u=users["cliente"]["id"],
    )
    for view in ("requests", "work"):
        data = response(db, users["jefe"], view, project="LOAD7", assay_status="PENDING_REVIEW", limit=100)
        assert data["total"] == 125 and len(data["items"]) == 100
        assert (
            len(
                response(
                    db, users["jefe"], view, project="LOAD7", assay_status="PENDING_REVIEW", page=2, limit=100
                )["items"]
            )
            == 25
        )
        assert (
            response(
                db,
                users["tecnico"],
                view,
                project="LOAD7",
                assay_status="PENDING_REVIEW",
                requester=users["cliente"]["id"],
            )["total"]
            == 0
        )
    rid = one(db, "SELECT id FROM solicitudes WHERE codigo='SOL-DEMO-001'")["id"]
    execute(db, "INSERT INTO muestras(solicitud_id,codigo_cliente) VALUES(:r,'SIN-ENSAYOS-7')", r=rid)
    assert response(db, users["tecnico"], "work", request=rid, assay_status="WAITING_ASSAYS")["total"] == 0
    personal = response(db, users["tecnico"], "work", request=rid)
    assert all(t["technician_id"] == str(users["tecnico"]["id"]) for t in personal["items"])
    assert (
        invoke("requests", headers=identity(db, users["jefe"]), params={"assay_status": "WRONG"}).status_code
        == 400
    )
