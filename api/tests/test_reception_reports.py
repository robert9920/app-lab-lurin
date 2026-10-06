"""Reception summaries and report search on fictitious PostgreSQL, with rollback."""

from datetime import datetime, timezone
from uuid import uuid4

from test_v3 import second_technician
from test_v4 import declaration
from test_v7 import response

from database import execute, one
from services import workflow as w
from validation import Action, AssaysReview, Reception, RequestCreate, WorkOrder


def received_request(db, users, conditions):
    assay = one(db, "SELECT id FROM catalogo_ensayos WHERE codigo='HUM'")["id"]
    payload = declaration(
        title="Caracterización de materiales",
        samples=[
            {"client_code": f"M-{i}", "material": "Suelo", "assay_ids": [assay]}
            for i in range(len(conditions))
        ],
    )
    rid = w.create_request(db, users["cliente"], RequestCreate(**payload))["id"]
    w.action(db, users["cliente"], rid, Action(version=1, action="submit"))
    request = w.detail(db, users["jefe"], rid)
    received = [
        {
            "sample_id": s["id"],
            "condition": condition,
            "codigo_recepcion": "REC-PRUEBA",
            "codigo_laboratorio": "LAB-" + str(s["id"]),
            "reception_notes": "Observación ficticia" if condition != "OK" else "",
        }
        for s, condition in zip(request["samples"], conditions, strict=True)
        if condition != "NOT_RECEIVED"
    ]
    if received:
        w.reception(
            db,
            users["jefe"],
            rid,
            Reception(
                version=request["version"],
                received_at=datetime.now(timezone.utc),
                samples=received,
            ),
        )
    return rid, w.detail(db, users["jefe"], rid)


def test_reception_counts_combined_conditions_and_independent_ot(db, users):
    rid, request = received_request(
        db, users, ["NOT_RECEIVED", "NOT_RECEIVED", "OBSERVED", "DAMAGED", "INSUFFICIENT", "OK"]
    )
    expected = {"NOT_RECEIVED": 2, "OBSERVED": 1, "DAMAGED": 1, "INSUFFICIENT": 1}
    for user in (users["admin"], users["jefe"]):
        for condition in ("", "NOT_RECEIVED", "issues", "NO_OT"):
            listed = response(db, user, q=request["code"], view="reception", condition=condition)
            assert listed["total"] == 1
            assert listed["items"][0]["reception_counts"] == expected
            assert listed["items"][0]["pending_samples"] == sum(expected.values())
            assert listed["items"][0]["codigo_ot"] is None
    assert "reception_counts" not in response(db, users["cliente"], q=request["code"])["items"][0]
    w.work_order(db, users["jefe"], rid, WorkOrder(version=request["version"], codigo_ot="OT-PRUEBA"))
    assert response(db, users["jefe"], q=request["code"], view="reception", condition="NO_OT")["total"] == 0
    listed = response(db, users["jefe"], q=request["code"], view="reception")
    assert listed["items"][0]["reception_counts"] == expected
    assert listed["items"][0]["codigo_ot"] == "OT-PRUEBA"


def test_reception_counts_respect_each_technician_and_filters(db, users):
    rid, request = received_request(db, users, ["NOT_RECEIVED", "OBSERVED", "DAMAGED", "INSUFFICIENT", "OK"])
    w.review_assays(
        db,
        users["jefe"],
        rid,
        AssaysReview(
            version=request["version"],
            decisions=[{"task_id": t["id"], "decision": "APPROVED"} for t in request["tasks"]],
        ),
    )
    other = second_technician(db)
    for i, sample in enumerate(request["samples"]):
        execute(
            db,
            "UPDATE ensayos_muestra SET tecnico_id=:u WHERE muestra_id=:s",
            u=users["tecnico"]["id"] if i < 2 else other["id"],
            s=sample["id"],
        )
    # Two assigned assays on one sample must not duplicate its reception count.
    execute(
        db,
        "INSERT INTO ensayos_muestra(muestra_id,ensayo_id,tecnico_id,estado_revision) "
        "SELECT :s,id,:u,'APPROVED' FROM catalogo_ensayos WHERE codigo<>'HUM' LIMIT 1",
        s=request["samples"][0]["id"],
        u=users["tecnico"]["id"],
    )
    mine = response(db, users["tecnico"], q=request["code"], view="reception")
    assert mine["items"][0]["reception_counts"] == {
        "NOT_RECEIVED": 1,
        "OBSERVED": 1,
        "DAMAGED": 0,
        "INSUFFICIENT": 0,
    }
    assert mine["items"][0]["pending_samples"] == 2
    theirs = response(db, other, q=request["code"], view="reception", condition="issues")
    assert theirs["items"][0]["reception_counts"] == {
        "NOT_RECEIVED": 0,
        "OBSERVED": 0,
        "DAMAGED": 1,
        "INSUFFICIENT": 1,
    }
    assert response(db, other, q=request["code"], view="reception", condition="NOT_RECEIVED")["total"] == 0
    assert (
        response(db, users["tecnico"], q=request["code"], view="reception", project="EXTERNO")["total"] == 0
    )


def test_reception_conforming_without_ot_and_terminal_exclusion(db, users):
    rid, request = received_request(db, users, ["OK"])
    listed = response(db, users["jefe"], q=request["code"], view="reception")
    assert listed["total"] == 1
    assert listed["items"][0]["reception_counts"] == {
        "NOT_RECEIVED": 0,
        "OBSERVED": 0,
        "DAMAGED": 0,
        "INSUFFICIENT": 0,
    }
    assert listed["items"][0]["codigo_ot"] is None
    for condition in ("NOT_RECEIVED", "issues"):
        assert (
            response(db, users["jefe"], q=request["code"], view="reception", condition=condition)["total"]
            == 0
        )
    for lifecycle in ("CANCELLED", "CLOSED"):
        execute(db, "UPDATE solicitudes SET estado_general=:state WHERE id=:id", state=lifecycle, id=rid)
        assert (
            response(db, users["jefe"], q=request["code"], view="reception", condition="NO_OT")["total"] == 0
        )


def test_reports_search_request_code_or_title_and_project_separately(db, users):
    rid, request = received_request(db, users, ["OK"])
    execute(db, "UPDATE solicitudes SET proyecto_id='PROYECTO-UNICO-REPORTES' WHERE id=:id", id=rid)
    for version in (1, 2):
        execute(
            db,
            "INSERT INTO informes(solicitud_id,version,nombre,clave_archivo,sha256,tamano_bytes,subido_por) "
            "VALUES(:r,:v,'Resultado.pdf',:key,'ficticio',100,:u)",
            r=rid,
            v=version,
            key=str(uuid4()),
            u=users["jefe"]["id"],
        )
    for user in (users["admin"], users["jefe"], users["cliente"]):
        for query in (request["code"].lower(), "MATERIALES", "caracterización"):
            listed = response(db, user, "reports", q=query)
            assert listed["total"] == 2
            assert {x["version"] for x in listed["items"]} == {1, 2}
        assert response(db, user, "reports", q="proyecto-unico-reportes")["total"] == 0
        assert response(db, user, "reports", project="PROYECTO-UNICO-REPORTES", q="materiales")["total"] == 2
        assert response(db, user, "reports", project="DEMO-001", q=request["code"])["total"] == 0
    assert response(db, users["externo"], "reports", q=request["code"])["total"] == 0
    assert response(db, users["tecnico"], "reports", q=request["code"])["total"] == 0
