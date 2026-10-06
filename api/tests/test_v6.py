import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from test_v4 import declaration

from database import execute, one
from errors import AppError
from services import workflow as w
from test_workflow import identity, invoke
from validation import Action, AssaysEdit, AssaysResubmit, AssaysReview, RequestCreate, TaskUpdate


def submitted(db, users):
    aid = one(db, "SELECT id FROM catalogo_ensayos WHERE codigo='HUM'")["id"]
    payload = declaration()
    for sample in payload["samples"]:
        sample["assay_ids"] = [aid]
    rid = w.create_request(db, users["cliente"], RequestCreate(**payload))["id"]
    w.action(db, users["cliente"], rid, Action(version=1, action="submit"))
    return rid, w.detail(db, users["jefe"], rid)


def test_independent_decisions_rejection_reason_and_resubmission(db, users):
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
                {"task_id": second["id"], "decision": "REJECTED", "reason": "Revisar el método solicitado"},
            ],
        ),
    )
    r = w.detail(db, users["cliente"], rid)
    assert r["status"] == "APPROVED" and r["unapproved_count"] == 0
    rejected = next(t for t in r["tasks"] if not t["approved"])
    assert (
        rejected["review_status"] == "REJECTED"
        and rejected["review_reason"] == "Revisar el método solicitado"
    )
    assert rejected["can_resubmit"] and rejected["allowed_actions"] == []
    assert any("Revisar el método" in " ".join(e["description_lines"]) for e in r["activity"])
    with pytest.raises(AppError):
        w.edit_assays(
            db,
            users["cliente"],
            rid,
            AssaysEdit(version=r["version"], samples=[{"sample_id": rejected["sample_id"], "assay_ids": []}]),
        )
    with pytest.raises(AppError):
        w.update_tasks(
            db,
            users["jefe"],
            rid,
            TaskUpdate(
                version=r["version"],
                task_ids=[rejected["id"]],
                action="assign",
                technician_id=users["tecnico"]["id"],
            ),
        )
    w.resubmit_assays(
        db, users["cliente"], rid, AssaysResubmit(version=r["version"], task_ids=[rejected["id"]])
    )
    r = w.detail(db, users["jefe"], rid)
    assert r["status"] == "APPROVED" and r["unapproved_count"] == 1
    assert r["tasks"][1]["id"] == second["id"] and r["tasks"][1]["review_reason"] == ""
    assert any("Revisar el método" in " ".join(e["description_lines"]) for e in r["activity"])
    w.review_assays(
        db,
        users["jefe"],
        rid,
        AssaysReview(version=r["version"], decisions=[{"task_id": second["id"], "decision": "APPROVED"}]),
    )
    assert all(t["approved"] for t in w.detail(db, users["cliente"], rid)["tasks"])


def test_all_rejected_observed_then_back_to_review(db, users):
    rid, r = submitted(db, users)
    w.review_assays(
        db,
        users["jefe"],
        rid,
        AssaysReview(
            version=r["version"],
            decisions=[
                {"task_id": t["id"], "decision": "REJECTED", "reason": "Datos por confirmar"}
                for t in r["tasks"]
            ],
        ),
    )
    r = w.detail(db, users["cliente"], rid)
    assert r["status"] == "OBSERVED" and not r["unapproved_count"]
    w.resubmit_assays(
        db, users["cliente"], rid, AssaysResubmit(version=r["version"], task_ids=[r["tasks"][0]["id"]])
    )
    r = w.detail(db, users["jefe"], rid)
    assert r["status"] == "SUBMITTED" and r["unapproved_count"] == 1
    assert len(r["tasks"]) == 2


def test_review_atomicity_permissions_duplicates_and_concurrency(db, users):
    rid, r = submitted(db, users)
    h = identity(db, users["jefe"])
    decision = {"task_id": str(r["tasks"][0]["id"]), "decision": "APPROVED"}
    payload = {
        "version": r["version"],
        "decisions": [decision, {"task_id": str(uuid4()), "decision": "APPROVED"}],
    }
    response = invoke("review_assays", method="POST", route={"rid": str(rid)}, headers=h, payload=payload)
    assert response.status_code == 404
    assert w.detail(db, users["jefe"], rid)["version"] == r["version"]
    assert not any(t["approved"] for t in w.detail(db, users["jefe"], rid)["tasks"])
    payload["decisions"] = [decision, decision]
    assert (
        invoke(
            "review_assays", method="POST", route={"rid": str(rid)}, headers=h, payload=payload
        ).status_code
        == 400
    )
    payload["decisions"] = [decision]
    # Demo ADMIN also has MANAGER. Verify an administrator without that role.
    execute(db, "UPDATE usuarios SET roles=ARRAY['ADMIN'] WHERE id=:id", id=users["admin"]["id"])
    for role in ("cliente", "tecnico", "admin"):
        assert (
            invoke(
                "review_assays",
                method="POST",
                route={"rid": str(rid)},
                headers=identity(db, users[role]),
                payload=payload,
            ).status_code
            == 403
        )
    assert (
        invoke(
            "review_assays", method="POST", route={"rid": str(rid)}, headers=h, payload=payload
        ).status_code
        == 200
    )
    assert (
        invoke(
            "review_assays", method="POST", route={"rid": str(rid)}, headers=h, payload=payload
        ).status_code
        == 409
    )
    assert (
        invoke(
            "actions",
            method="POST",
            route={"rid": str(rid)},
            headers=h,
            payload={"version": 3, "action": "approve"},
        ).status_code
        == 409
    )


def test_rejection_requires_reason(db, users):
    rid, r = submitted(db, users)
    with pytest.raises(ValidationError):
        AssaysReview(
            version=r["version"],
            decisions=[{"task_id": r["tasks"][0]["id"], "decision": "REJECTED", "reason": "  "}],
        )


def test_resubmission_scope_atomicity_and_reviewed_tasks(db, users):
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
                {"task_id": second["id"], "decision": "REJECTED", "reason": "Confirmar método"},
            ],
        ),
    )
    r = w.detail(db, users["cliente"], rid)
    payload = {"version": r["version"], "task_ids": [str(second["id"])]}
    for role, code in (("jefe", 403), ("tecnico", 403), ("externo", 404)):
        assert (
            invoke(
                "resubmit_assays",
                method="POST",
                route={"rid": str(rid)},
                headers=identity(db, users[role]),
                payload=payload,
            ).status_code
            == code
        )
    h = identity(db, users["cliente"])
    payload["task_ids"].append(str(first["id"]))
    assert (
        invoke(
            "resubmit_assays", method="POST", route={"rid": str(rid)}, headers=h, payload=payload
        ).status_code
        == 409
    )
    assert w.detail(db, users["cliente"], rid)["version"] == r["version"]
    assert (
        one(db, "SELECT estado_revision FROM ensayos_muestra WHERE id=:id", id=second["id"])["review_status"]
        == "REJECTED"
    )
    payload["task_ids"] = [str(second["id"]), str(second["id"])]
    assert (
        invoke(
            "resubmit_assays", method="POST", route={"rid": str(rid)}, headers=h, payload=payload
        ).status_code
        == 400
    )
    assert (
        invoke(
            "review_assays",
            method="POST",
            route={"rid": str(rid)},
            headers=identity(db, users["jefe"]),
            payload={
                "version": r["version"],
                "decisions": [{"task_id": str(first["id"]), "decision": "REJECTED", "reason": "Cambio"}],
            },
        ).status_code
        == 409
    )
    payload["task_ids"] = [str(second["id"])]
    assert (
        invoke(
            "resubmit_assays", method="POST", route={"rid": str(rid)}, headers=h, payload=payload
        ).status_code
        == 200
    )
    assert (
        invoke(
            "resubmit_assays", method="POST", route={"rid": str(rid)}, headers=h, payload=payload
        ).status_code
        == 409
    )


def test_status_filters_include_approved_with_pending_and_missing_assays(db, users):
    rid, r = submitted(db, users)
    w.review_assays(
        db,
        users["jefe"],
        rid,
        AssaysReview(
            version=r["version"], decisions=[{"task_id": r["tasks"][0]["id"], "decision": "APPROVED"}]
        ),
    )
    execute(
        db,
        "INSERT INTO muestras(solicitud_id,codigo_cliente,material) VALUES(:r,'SIN-ENSAYOS','Suelo')",
        r=rid,
    )
    headers = identity(db, users["jefe"])
    for status in ("SUBMITTED", "WAITING_ASSAYS", "APPROVED", "SUBMITTED,WAITING_ASSAYS"):
        response = invoke("requests", headers=headers, params={"status": status, "q": "Muestras antes"})
        assert str(rid) in {x["id"] for x in json.loads(response.get_body())["items"]}
    assert invoke("requests", headers=headers, params={"status": "INVALID"}).status_code == 400
    # Filters do not reveal a draft, even for an administrator with its exact title.
    draft = w.create_request(db, users["cliente"], RequestCreate(**declaration()))["id"]
    response = invoke(
        "requests", headers=identity(db, users["admin"]), params={"status": "SUBMITTED,WAITING_ASSAYS,DRAFT"}
    )
    assert str(draft) not in {x["id"] for x in json.loads(response.get_body())["items"]}


def test_rejected_resolved_does_not_block_closure(db, users):
    rid, r = submitted(db, users)
    w.review_assays(
        db,
        users["jefe"],
        rid,
        AssaysReview(
            version=r["version"],
            decisions=[
                {"task_id": r["tasks"][0]["id"], "decision": "APPROVED"},
                {"task_id": r["tasks"][1]["id"], "decision": "REJECTED", "reason": "No requerido"},
            ],
        ),
    )
    execute(
        db,
        "UPDATE ensayos_muestra SET estado_ensayo='COMPLETED',tecnico_id=:u,iniciado_en=now(),completado_en=now() WHERE id=:id",
        u=users["tecnico"]["id"],
        id=r["tasks"][0]["id"],
    )
    execute(
        db,
        "INSERT INTO informes(solicitud_id,version,nombre,clave_archivo,sha256,tamano_bytes,subido_por) VALUES(:r,1,'Ficticio.pdf',:key,'demo',100,:u)",
        r=rid,
        key=str(uuid4()),
        u=users["jefe"]["id"],
    )
    w.action(db, users["jefe"], rid, Action(version=3, action="close"))
    assert w.detail(db, users["cliente"], rid)["status"] == "CLOSED"


def test_session_company_name(db, users):
    h = identity(db, users["cliente"])
    response = invoke("current_session", headers=h)
    result = json.loads(response.get_body())
    assert (
        result["user"]["organization_name"]
        == one(db, "SELECT nombre FROM empresas WHERE id=:id", id=users["cliente"]["organization_id"])["name"]
    )
